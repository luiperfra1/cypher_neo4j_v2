from __future__ import annotations
import time
from typing import List, Tuple
from neo4j_client import Neo4jClient
from schema_bootstrap import bootstrap
from llm_triplets_to_cypher import cypher_from_triplets
from tripletas_demo import *

def _elapsed_str(start: float) -> str:
    """Devuelve el tiempo transcurrido desde start en formato (X.XXs)."""
    return f"({time.time() - start:.2f}s)"

if __name__ == "__main__":
    t0_total = time.time()
    db = Neo4jClient()
    try:
        print(" Limpiando base de datos existente...")
        t0 = time.time()
        db.write("MATCH (n) DETACH DELETE n", {})
        print("   ✅ Base de datos vaciada", _elapsed_str(t0))

        print(" Creando constraints/índices…")
        t0 = time.time()
        bootstrap(db)
        print("   ✅ Constraints creados", _elapsed_str(t0))

        print(" LLM: mapeando tripletas crudas → Cypher…")
        t0 = time.time()
        cypher_script = cypher_from_triplets(RAW_TRIPLES_DEMO3)
        print("   ✅ Cypher generado", _elapsed_str(t0))

        print("─── Cypher generado ───\n", cypher_script)

        stmts = [s.strip() for s in cypher_script.split(';') if s.strip() and s.strip() != '--SKIP--']
        batch = [(s, {}) for s in stmts]
        print(f" Ejecutando {len(batch)} sentencias…")
        t0 = time.time()
        db.write_many(batch)
        print("   ✅ Sentencias ejecutadas", _elapsed_str(t0))

        print("✅ Proceso completo", _elapsed_str(t0_total))
    finally:
        db.close()
