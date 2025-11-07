# triplets2bd/engine.py
from __future__ import annotations
from typing import List, Tuple, Optional

from .utils.types import EngineOptions, EngineResult, Triplet
from .triplets2sql_rule_based import (
    partition_triplets_strict as partition_sql,
    compile_sql_script,
)
from .triplets2cypher_rule_based import (
    partition_triplets_strict as partition_cypher,
    compile_cypher_script,
)
from .llm_triplets_to_bd import bd_from_triplets

# Clientes / bootstrap
from .utils.neo4j_client import Neo4jClient
from .utils.schema_bootstrap import bootstrap as bootstrap_neo4j
from .utils.sqlite_client import SqliteClient
from .utils.schema_sqlite_bootstrap import bootstrap_sqlite, reset_sql

# LOG (siempre SQLite; solo fallos)
from utils.sql_log import (
    ensure_sql_log_table,
    insert_leftovers_log,
    clear_log,      # limpia registros (no borra tabla ni índices)
    log_event,      # para registrar ERROR o avisos de reset fallido
    new_run_id,     # generamos run_id en memoria (no se persiste si no hay fallos)
)

# Reporte
from .utils.make_sqlite_report import make_content_only_report


def _safe_reset_neo4j(log_conn, run_id: str) -> None:
    """
    Intenta resetear Neo4j. Si falla, registra un WARN en el log y continúa.
    """
    try:
        db = Neo4jClient()
        try:
            db.write("MATCH (n) DETACH DELETE n", {})
        finally:
            db.close()
    except Exception as e:
        try:
            log_event(
                log_conn,
                level="WARN",
                message="neo4j reset failed",
                run_id=run_id,
                stage="reset",
                reason=type(e).__name__,
                metadata={"error": str(e)},
            )
        except Exception:
            pass  # no interrumpir por fallo de log


def _safe_reset_sqlite_domain(sqlite_path: str, log_conn, run_id: str) -> None:
    """
    Intenta resetear las tablas de dominio en SQLite. Si falla, registra WARN y continúa.
    """
    try:
        sql = SqliteClient(sqlite_path)
        try:
            reset_sql(sql.conn)           # importante: que NO borre la tabla de log
        finally:
            sql.close()
    except Exception as e:
        try:
            log_event(
                log_conn,
                level="WARN",
                message="sqlite domain reset failed",
                run_id=run_id,
                stage="reset",
                reason=type(e).__name__,
                metadata={"error": str(e), "sqlite_db_path": sqlite_path},
            )
        except Exception:
            pass


def run_triplets_to_bd(triplets: List[Triplet], opts: EngineOptions) -> EngineResult:
    det_script = ""
    llm_script = ""
    executed = 0
    leftovers: List[Tuple[Triplet, str]] = []
    run_id: Optional[str] = None
    extras = {}

    # --- Canal de log en SQLite (independiente del backend) ---
    log_sql = SqliteClient(opts.sqlite_db_path)
    ensure_sql_log_table(log_sql.conn)

    try:
        # Limpieza por defecto SOLO de registros (no borra la tabla ni índices)
        if opts.reset_log:
            clear_log(log_sql.conn)

        # Generar run_id en memoria (no se registra si no hay fallos)
        run_id = new_run_id("run")

        # ======================================================
        # RESET CRUZADO DE AMBAS BDs SI SE SOLICITA
        # ======================================================
        if opts.reset:
            # Resetear Neo4j y SQLite de dominio SIEMPRE, independientemente del backend activo
            _safe_reset_neo4j(log_sql.conn, run_id)
            _safe_reset_sqlite_domain(opts.sqlite_db_path, log_sql.conn, run_id)

        # ======================================================
        # BACKEND NEO4J
        # ======================================================
        if opts.backend == "neo4j":
            db = Neo4jClient()
            try:
                # Tras reset cruzado, crear constraints/índices
                bootstrap_neo4j(db)

                # Modo
                if opts.mode == "llm":
                    llm_script = bd_from_triplets(triplets, modo="neo4j").strip()

                else:
                    # Determinista
                    supported, leftovers = partition_cypher(triplets)
                    det_script = compile_cypher_script(supported).strip()

                    # Registrar leftovers siempre en SQLite (WARN)
                    if leftovers:
                        insert_leftovers_log(
                            log_sql.conn,
                            leftovers,
                            run_id=run_id,
                            stage="triplet2bd_deterministic_partition",
                            message="Tripletas no compatibles con determinista (Neo4j)",
                        )

                    # Hybrid: LLM solo para sobrantes
                    if opts.mode == "hybrid" and leftovers:
                        llm_script = bd_from_triplets(
                            [t for (t, _) in leftovers],
                            modo="neo4j"
                        ).strip()

                # Ejecutar Cypher final
                script = "\n".join([s for s in (det_script, llm_script) if s]).strip()
                if script:
                    stmts = [s.strip() for s in script.split(";") if s.strip() and s.strip() != "--SKIP--"]
                    if stmts:
                        db.write_many([(s, {}) for s in stmts])
                        executed = len(stmts)

                extras.update({"run_id": run_id})

            finally:
                db.close()

        # ======================================================
        # BACKEND SQL (SQLite)
        # ======================================================
        else:
            sql = SqliteClient(opts.sqlite_db_path)
            try:
                # Tras reset cruzado, bootstrap de tablas de dominio
                bootstrap_sqlite(sql.conn)

                # Modo
                if opts.mode == "llm":
                    llm_script = bd_from_triplets(triplets, modo="sql").strip()

                else:
                    # Determinista
                    supported, leftovers = partition_sql(triplets)
                    det_script = compile_sql_script(supported).strip()

                    # Registrar leftovers siempre en SQLite (WARN)
                    if leftovers:
                        insert_leftovers_log(
                            log_sql.conn,
                            leftovers,
                            run_id=run_id,
                            stage="triplet2bd_deterministic_partition",
                            message="Tripletas no compatibles con determinista (SQL)",
                        )

                    # Hybrid: LLM solo para sobrantes
                    if opts.mode == "hybrid" and leftovers:
                        llm_script = bd_from_triplets(
                            [t for (t, _) in leftovers],
                            modo="sql"
                        ).strip()

                # Ejecutar SQL final
                script = "\n".join([s for s in (det_script, llm_script) if s]).strip()
                if script:
                    sql.executescript(script if script.endswith("\n") else script + "\n")
                    executed = script.count(";")  # estimación simple

                extras.update({"run_id": run_id})

            finally:
                sql.close()

    except Exception as exc:
        # Solo registrar ERROR (fallo de la ejecución completa)
        try:
            log_event(
                log_sql.conn,
                level="ERROR",
                message="run failed",
                run_id=run_id,
                stage="end",
                reason=type(exc).__name__,
                metadata={"error": str(exc)},
            )
        except Exception:
            pass
        raise
    finally:
        # Cerramos canal de log
        log_sql.close()

    # ------------------------------------------------------------------
    # GENERAR INFORME EN AMBOS BACKENDS (si se solicita)
    # ------------------------------------------------------------------
    if opts.generate_report:
        report_path = (
            opts.report_path
            if opts.report_path
            else opts.sqlite_db_path.replace(".sqlite", "_report.txt")
        )
        make_content_only_report(
            opts.sqlite_db_path,
            report_path,
            sample_limit=opts.report_sample_limit,
        )
        extras["report_path"] = report_path
    # ------------------------------------------------------------------

    return EngineResult(
        backend=opts.backend,
        mode=opts.mode,
        run_id=run_id,
        det_script=det_script,
        llm_script=llm_script,
        executed_statements=executed,
        leftovers=leftovers,
        reset=opts.reset,
        extras=extras,
    )
