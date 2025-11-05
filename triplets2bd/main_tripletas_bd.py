# triplets2bd/main_tripletas_bd.py
from __future__ import annotations
import time
import argparse
import json
from typing import List, Tuple, Optional

# =========================
# Determinista SQL (existente)
# =========================
from .triplets2sql_rule_based import (
    Triplet,
    partition_triplets_strict as partition_triplets_strict_sql,
    compile_sql_script,
)

# =========================
# Determinista Cypher (sin 'conoce')
# =========================
from .triplets2cypher_rule_based import (
    partition_triplets_strict as partition_triplets_strict_cypher,
    compile_cypher_script,
)

# LLM mapper (genera Cypher o SQL según backend)
from .llm_triplets_to_bd import bd_from_triplets

# Neo4j
from .utils.neo4j_client import Neo4jClient
from .utils.schema_bootstrap import bootstrap  # constraints/índices Neo4j

# SQLite
from .utils.sqlite_client import SqliteClient
from .utils.schema_sqlite_bootstrap import bootstrap_sqlite, reset_sql

# Reporte (solo SQL)
from .utils.make_sqlite_report import make_content_only_report

# Demos
from .tripletas_demo import *  # por ejemplo RAW_TRIPLES_DEMO4

Triplet = Tuple[str, str, str]


def _elapsed_str(start: float) -> str:
    return f"({time.time() - start:.2f}s)"


def _load_triplets_from_args(args) -> Optional[List[Triplet]]:
    """Carga tripletas desde --triplets-json o --triplets-file (.json o .txt)."""
    if args.triplets_json:
        data = json.loads(args.triplets_json)
        return [(str(a), str(b), str(c)) for a, b, c in data]

    if args.triplets_file:
        path = args.triplets_file
        if path.lower().endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [(str(a), str(b), str(c)) for a, b, c in data]

        rows: List[Triplet] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                if raw.startswith("(") and raw.endswith(")"):
                    raw = raw[1:-1]
                parts = [p.strip() for p in raw.split(",")]
                if len(parts) != 3:
                    raise ValueError(f"Línea inválida (esperado 3 campos): {line}")
                rows.append((parts[0], parts[1], parts[2]))
        return rows
    return None


# ============ LOG SQL DE SOBRANTES ============
def _ensure_sql_log_table(conn) -> None:
    """
    Crea la tabla de log si no existe.
      log(id INTEGER PK, ts TEXT, level TEXT, message TEXT, triplet TEXT, reason TEXT)
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            triplet TEXT,
            reason TEXT
        );
        """
    )


def _insert_sql_leftovers_log(conn, leftovers: List[Tuple[Triplet, str]]) -> None:
    """
    Inserta en la tabla log las tripletas fuera de formato.
    leftovers: lista de ((s, v, o), reason)
    """
    if not leftovers:
        return
    _ensure_sql_log_table(conn)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    data = [
        (now_iso, "WARN", "Tripleta fuera de formato", f"({s}, {v}, {o})", reason)
        for (s, v, o), reason in leftovers
    ]
    conn.executemany(
        "INSERT INTO log (ts, level, message, triplet, reason) VALUES (?, ?, ?, ?, ?);",
        data,
    )
    conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mapea tripletas a script (Cypher o SQL) y opcionalmente ejecuta en Neo4j/SQLite."
    )
    parser.add_argument("--bd", choices=["neo4j", "sql"], default="sql",
                        help="Backend de salida.")
    parser.add_argument("--sqlite-db", default="./data/users/demo.sqlite",
                        help="Ruta al fichero SQLite cuando --bd=sql.")
    parser.add_argument("--no-reset", action="store_true",
                        help="No resetear la BD (por defecto se resetea).")

    # Modos: por defecto hybrid; --llm (solo LLM); --no-llm (determinista puro)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--llm", action="store_true",
                       help="Solo LLM: ignora el motor determinista y mapea todo con LLM.")
    group.add_argument("--no-llm", action="store_true",
                       help="Determinista puro: nunca usa LLM. En Neo4j aborta si hay sobrantes. En SQL los sobrantes se registran en 'log' y no se ejecutan.")

    parser.add_argument("--triplets-json", type=str, default=None,
                        help='Tripletas JSON inline, p. ej. \'[["Jose","padece","insomnio"]]\'')
    parser.add_argument("--triplets-file", type=str, default=None,
                        help="Fichero .json o .txt (una tripleta por línea).")

    args = parser.parse_args()

    # Determinar modo
    if args.llm:
        mode = "llm"
    elif args.no_llm:
        mode = "deterministic"
    else:
        mode = "hybrid"  # por defecto

    bd = args.bd
    sqlite_db_path = args.sqlite_db
    do_reset = not args.no_reset

    print(f" Backend: {bd} | reset={'sí' if do_reset else 'no'} | modo={mode}")

    t0_total = time.time()
    db = Neo4jClient() if bd == "neo4j" else None
    sql = SqliteClient(sqlite_db_path) if bd == "sql" else None

    try:
        # --- Preparar BD ---
        if bd == "neo4j":
            if do_reset:
                print(" Limpiando base de datos (Neo4j)…")
                t0 = time.time()
                db.write("MATCH (n) DETACH DELETE n", {})
                print("   ✅ BD vaciada", _elapsed_str(t0))
            print(" Creando constraints/índices (Neo4j)…")
            t0 = time.time()
            bootstrap(db)
            print("   ✅ Listo", _elapsed_str(t0))
        else:
            print(f" Preparando SQLite en {sqlite_db_path}…")
            if do_reset:
                t0 = time.time()
                reset_sql(sql.conn)
                print("   🧨 Esquema reseteado", _elapsed_str(t0))
            t0 = time.time()
            bootstrap_sqlite(sql.conn)  # crea tablas de dominio
            _ensure_sql_log_table(sql.conn)  # garantizamos también la tabla de log
            print("   ✅ Esquema listo", _elapsed_str(t0))

        # --- Cargar tripletas ---
        triplets = _load_triplets_from_args(args) or RAW_TRIPLES_DEMO4

        # --- Generación de script según modo ---
        print(" Generando script…")
        t0 = time.time()
        script_parts: List[str] = []

        LLM_MARK = "// ==== CYPHER (LLM complemento) ====" if bd == "neo4j" else "-- ==== SQL (LLM complemento) ===="

        if mode == "llm":
            # Solo LLM
            llm_script = bd_from_triplets(triplets, modo=bd).strip()
            if llm_script:
                script_parts.append(LLM_MARK if bd == "neo4j" else LLM_MARK)
                script_parts.append(llm_script)

        elif mode == "deterministic":
            # Solo determinista
            if bd == "neo4j":
                supported, leftovers = partition_triplets_strict_cypher(triplets)
                det_script = compile_cypher_script(supported).strip()
                if leftovers:
                    print("─── Tripletas fuera de formato (Neo4j, determinista) ───")
                    for (s, v, o), reason in leftovers:
                        print(f"[OUT] ({s}, {v}, {o}) -> {reason}")
                    print(" Error: modo determinista en Neo4j detectó sobrantes. Abortando sin ejecutar.")
                    raise SystemExit(1)
                script_parts.append("// ==== CYPHER (determinista) ====")
                if det_script:
                    script_parts.append(det_script)
            else:
                supported, leftovers = partition_triplets_strict_sql(triplets)
                det_script = compile_sql_script(supported).strip()
                if leftovers:
                    print("─── Tripletas fuera de formato → se registran en tabla 'log' (SQL) ───")
                    for (s, v, o), reason in leftovers:
                        print(f"[LOG] ({s}, {v}, {o}) -> {reason}")
                    _insert_sql_leftovers_log(sql.conn, leftovers)
                script_parts.append("-- ==== SQL (determinista) ====")
                if det_script:
                    script_parts.append(det_script)

        else:
            # Hybrid por defecto
            if bd == "neo4j":
                supported, leftovers = partition_triplets_strict_cypher(triplets)
                det_script = compile_cypher_script(supported).strip()
                script_parts.append("// ==== CYPHER (determinista) ====")
                if det_script:
                    script_parts.append(det_script)
                if leftovers:
                    print("─── Tripletas FUERA DE FORMATO → LLM (Neo4j) ───")
                    for (s, v, o), reason in leftovers:
                        print(f"[OUT→LLM] ({s}, {v}, {o}) -> {reason}")
                    leftovers_raw = [(s, v, o) for (s, v, o), _ in leftovers]
                    llm_script = bd_from_triplets(leftovers_raw, modo=bd).strip()
                    if llm_script:
                        script_parts.append(LLM_MARK)
                        script_parts.append(llm_script)
            else:
                supported, leftovers = partition_triplets_strict_sql(triplets)
                det_script = compile_sql_script(supported).strip()
                script_parts.append("-- ==== SQL (determinista) ====")
                if det_script:
                    script_parts.append(det_script)
                if leftovers:
                    print("─── Tripletas FUERA DE FORMATO → LLM (SQL) ───")
                    for (s, v, o), reason in leftovers:
                        print(f"[OUT→LLM] ({s}, {v}, {o}) -> {reason}")
                    _insert_sql_leftovers_log(sql.conn, leftovers)  # además las registramos
                    leftovers_raw = [(s, v, o) for (s, v, o), _ in leftovers]
                    llm_script = bd_from_triplets(leftovers_raw, modo=bd).strip()
                    if llm_script:
                        script_parts.append(LLM_MARK)
                        script_parts.append(llm_script)

        script = ("\n".join(p for p in script_parts if p)).strip()
        if script and not script.endswith("\n"):
            script += "\n"

        print("   ✅ Script generado", _elapsed_str(t0))
        print("─── Script generado ───")
        print(script if script else "(vacío)")
        # --- Ejecutar ---
        if bd == "neo4j":
            stmts = [s.strip() for s in script.split(";") if s.strip() and s.strip() != "--SKIP--"]
            if stmts:
                print(f" Ejecutando {len(stmts)} sentencias Cypher…")
                t0 = time.time()
                db.write_many([(s, {}) for s in stmts])
                print("   ✅ Sentencias ejecutadas", _elapsed_str(t0))
            else:
                print(" (No hay sentencias Cypher para ejecutar)")
        else:
            if script and script.strip():
                print(" Ejecutando script SQL en SQLite…")
                t0 = time.time()
                sql.executescript(script)
                print("   ✅ SQL aplicado en SQLite", _elapsed_str(t0))
                report_path = sqlite_db_path.replace(".sqlite", "_report.txt")
                print(f" Generando reporte de contenido en {report_path}…")
                make_content_only_report(sqlite_db_path, report_path, sample_limit=15)
                print("   ✅ Reporte generado correctamente")
            else:
                print(" (No hay script SQL para ejecutar)")

        print("✅ Proceso completo", _elapsed_str(t0_total))

    finally:
        if db is not None:
            db.close()
        if sql is not None:
            sql.close()
