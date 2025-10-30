from __future__ import annotations
import time
import argparse
from typing import List, Tuple

from .neo4j_client import Neo4jClient
from .schema_bootstrap import bootstrap
from .llm_triplets_to_bd import bd_from_triplets
from .tripletas_demo import *


def _elapsed_str(start: float) -> str:
    """Devuelve el tiempo transcurrido desde start en formato (X.XXs)."""
    return f"({time.time() - start:.2f}s)"


if __name__ == "__main__":
    # --- CLI ---
    parser = argparse.ArgumentParser(
        description="Mapea tripletas a script (Cypher o SQL) y opcionalmente ejecuta en Neo4j."
    )
    parser.add_argument(
        "--bd",
        choices=["neo4j", "sql"],
        default="neo4j",
        help="Backend de salida. 'neo4j' genera Cypher y lo ejecuta; 'sql' solo genera SQL.",
    )
    args = parser.parse_args()
    bd = args.bd

    print(f" Backend seleccionado: {bd}")

    t0_total = time.time()

    # Cuando el backend no es Neo4j, evitamos tocar la base de datos
    db = Neo4jClient() if bd == "neo4j" else None

    try:
        if bd == "neo4j":
            print(" Limpiando base de datos existente...")
            t0 = time.time()
            db.write("MATCH (n) DETACH DELETE n", {})
            print("   ✅ Base de datos vaciada", _elapsed_str(t0))

            print(" Creando constraints/índices…")
            t0 = time.time()
            bootstrap(db)
            print("   ✅ Constraints creados", _elapsed_str(t0))

        print(" LLM: mapeando tripletas crudas → script…")
        t0 = time.time()
        # Pasamos el backend seleccionado a la función (antes llamado 'valor')
        script = bd_from_triplets(RAW_TRIPLES_DEMO3, bd)
        print("   ✅ Script generado", _elapsed_str(t0))

        print("─── Script generado ───\n", script)

        if bd == "neo4j":
            # Ejecutamos únicamente si es Cypher/Neo4j
            stmts = [s.strip() for s in script.split(";") if s.strip() and s.strip() != "--SKIP--"]
            batch = [(s, {}) for s in stmts]
            print(f" Ejecutando {len(batch)} sentencias…")
            t0 = time.time()
            db.write_many(batch)
            print("   ✅ Sentencias ejecutadas", _elapsed_str(t0))
        else:
            print(" (Modo SQL) No se ejecuta nada contra Neo4j; script mostrado arriba.")

        print("✅ Proceso completo", _elapsed_str(t0_total))
    finally:
        if db is not None:
            db.close()
