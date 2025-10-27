from __future__ import annotations
from typing import List, Tuple
from neo4j_client import Neo4jClient
from schema_bootstrap import bootstrap
from llm_triplets_to_cypher import cypher_from_triplets
from tripletas_demo import RAW_TRIPLES_DEMO

if __name__ == "__main__":
    db = Neo4jClient()
    try:
        print(" Limpiando base de datos existente...")
        db.write("MATCH (n) DETACH DELETE n", {})
        print(" Creando constraints/índices…")
        bootstrap(db)
        print(" LLM: mapeando tripletas crudas → Cypher…")
        cypher_script = cypher_from_triplets(RAW_TRIPLES_DEMO)
        print("─── Cypher generado ───\n", cypher_script)
        stmts = [s.strip() for s in cypher_script.split(';') if s.strip() and s.strip() != '--SKIP--']
        batch = [(s, {}) for s in stmts]
        print(" Ejecutando", len(batch), "sentencias…")
        db.write_many(batch)
        print("✅ Listo.")
    finally:
        db.close()