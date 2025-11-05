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

# Clients / bootstrap
from .utils.neo4j_client import Neo4jClient
from .utils.schema_bootstrap import bootstrap as bootstrap_neo4j
from .utils.sqlite_client import SqliteClient
from .utils.schema_sqlite_bootstrap import bootstrap_sqlite, reset_sql

# Logs
from .utils.sql_log import ensure_sql_log_table, reset_sql_log, insert_sql_leftovers_log
from .utils.neo4j_log import neo4j_start_run, neo4j_log_leftovers

# Report
from .utils.make_sqlite_report import make_content_only_report


def run_triplets_to_bd(triplets: List[Triplet], opts: EngineOptions) -> EngineResult:
    det_script = ""
    llm_script = ""
    executed = 0
    leftovers: List[Tuple[Triplet, str]] = []
    run_id: Optional[str] = None
    extras = {}

    # ========================
    # NEO4J
    # ========================
    if opts.backend == "neo4j":
        db = Neo4jClient()
        try:
            # Reset
            if opts.reset:
                db.write("MATCH (n) DETACH DELETE n", {})

            # Bootstrap constraints / índices
            bootstrap_neo4j(db)

            # Crear run_id para logs
            run_id = neo4j_start_run()

            # Modo
            if opts.mode == "llm":
                llm_script = bd_from_triplets(triplets, modo="neo4j").strip()

            else:
                # Determinista
                supported, leftovers = partition_cypher(triplets)
                det_script = compile_cypher_script(supported).strip()

                # Registrar inválidas
                if leftovers:
                    neo4j_log_leftovers(db, leftovers, run_id=run_id, backend="neo4j", mode=opts.mode)

                # Hybrid: generar LLM sólo para sobrantes
                if opts.mode == "hybrid" and leftovers:
                    llm_script = bd_from_triplets([t for (t, _) in leftovers], modo="neo4j").strip()

            # Ejecutar script final
            script = "\n".join([s for s in (det_script, llm_script) if s]).strip()
            if script:
                stmts = [s.strip() for s in script.split(";") if s.strip() and s.strip() != "--SKIP--"]
                if stmts:
                    db.write_many([(s, {}) for s in stmts])
                    executed = len(stmts)

            extras.update({"run_id": run_id})

        finally:
            db.close()

    # ========================
    # SQL
    # ========================
    else:
        sql = SqliteClient(opts.sqlite_db_path)
        try:
            # Reset total
            if opts.reset:
                reset_sql(sql.conn)
                reset_sql_log(sql.conn)

            # Bootstrap tablas base
            bootstrap_sqlite(sql.conn)
            ensure_sql_log_table(sql.conn)

            # Modo
            if opts.mode == "llm":
                llm_script = bd_from_triplets(triplets, modo="sql").strip()

            else:
                # Determinista
                supported, leftovers = partition_sql(triplets)
                det_script = compile_sql_script(supported).strip()

                # Registrar inválidas
                if leftovers:
                    insert_sql_leftovers_log(sql.conn, leftovers)

                # Hybrid: generar LLM sólo para sobrantes
                if opts.mode == "hybrid" and leftovers:
                    llm_script = bd_from_triplets([t for (t, _) in leftovers], modo="sql").strip()

            # Ejecutar script final
            script = "\n".join([s for s in (det_script, llm_script) if s]).strip()
            if script:
                sql.executescript(script if script.endswith("\n") else script + "\n")
                executed = script.count(";")  # aproximado

            # Generar reporte si procede
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

        finally:
            sql.close()

    # ========================

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
