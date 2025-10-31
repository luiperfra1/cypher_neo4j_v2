from __future__ import annotations
import time
import argparse
from typing import List, Tuple

# Neo4j
from .utils.neo4j_client import Neo4jClient
from .utils.schema_bootstrap import bootstrap  # crea constraints/índices en Neo4j

# LLM mapper (genera Cypher o SQL según backend)
from .llm_triplets_to_bd import bd_from_triplets

# Demo de tripletas
from .tripletas_demo import *

# SQLite
from .utils.sqlite_client import SqliteClient
from .utils.schema_sqlite_bootstrap import bootstrap_sqlite, reset_sql

# --- NUEVO: generador de reporte TXT ---
from .utils.make_sqlite_report import make_content_only_report


def _elapsed_str(start: float) -> str:
    """Devuelve el tiempo transcurrido desde start en formato (X.XXs)."""
    return f"({time.time() - start:.2f}s)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mapea tripletas a script (Cypher o SQL) y opcionalmente ejecuta en Neo4j/SQLite."
    )
    parser.add_argument(
        "--bd",
        choices=["neo4j", "sql"],
        default="neo4j",
        help="Backend de salida. 'neo4j' genera Cypher y lo ejecuta; 'sql' genera SQL y lo ejecuta en SQLite.",
    )
    parser.add_argument(
        "--sqlite-db",
        default="./data/users/demo.sqlite",
        help="Ruta al fichero SQLite cuando --bd=sql (por defecto ./data/users/demo.sqlite)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="No resetear la base de datos (por defecto SIEMPRE se resetea).",
    )

    args = parser.parse_args()
    bd = args.bd
    sqlite_db_path = args.sqlite_db
    do_reset = not args.no_reset  # por defecto True

    print(f" Backend seleccionado: {bd} | reset={'sí' if do_reset else 'no'}")

    t0_total = time.time()

    # Instancias según backend
    db = Neo4jClient() if bd == "neo4j" else None
    sql = SqliteClient(sqlite_db_path) if bd == "sql" else None

    try:
        if bd == "neo4j":
            if do_reset:
                print(" Limpiando base de datos existente (Neo4j)…")
                t0 = time.time()
                db.write("MATCH (n) DETACH DELETE n", {})
                print("   ✅ Base de datos vaciada", _elapsed_str(t0))

            print(" Creando constraints/índices (Neo4j)…")
            t0 = time.time()
            bootstrap(db)
            print("   ✅ Constraints/índices listos", _elapsed_str(t0))

        elif bd == "sql":
            print(f" Preparando SQLite en {sqlite_db_path}…")
            if do_reset:
                t0 = time.time()
                reset_sql(sql.conn)
                print("   🧨 Esquema SQL reseteado", _elapsed_str(t0))
            t0 = time.time()
            bootstrap_sqlite(sql.conn)
            print("   ✅ Esquema SQL listo", _elapsed_str(t0))

        # --- Generar script ---
        print(" LLM: mapeando tripletas crudas → script…")
        t0 = time.time()
        #---------------------------------------------------------------------------------------------------------------------------
        script = bd_from_triplets(RAW_TRIPLES_DEMO2, bd)
        print("   ✅ Script generado", _elapsed_str(t0))

        print("─── Script generado ───\n", script)

        # --- Ejecutar ---
        if bd == "neo4j":
            stmts = [s.strip() for s in script.split(";") if s.strip() and s.strip() != "--SKIP--"]
            if stmts:
                print(f" Ejecutando {len(stmts)} sentencias Cypher…")
                t0 = time.time()
                batch = [(s, {}) for s in stmts]
                db.write_many(batch)
                print("   ✅ Sentencias ejecutadas", _elapsed_str(t0))
            else:
                print(" (No hay sentencias Cypher para ejecutar)")

        elif bd == "sql":
            if script.strip():
                print(" Ejecutando script SQL en SQLite…")
                t0 = time.time()
                sql.executescript(script)
                print("   ✅ SQL aplicado en SQLite", _elapsed_str(t0))

                # === NUEVO BLOQUE: generar reporte automáticamente ===
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
