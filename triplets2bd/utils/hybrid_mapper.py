# utils/hybrid_mapper.py
from __future__ import annotations
from typing import List, Tuple

# Importa el LLM mapper y el compilador determinista SQL
# Ajusta los imports relativos según tu estructura de paquete.
from ..llm_triplets_to_bd import bd_from_triplets
from ..triplets2sql_rule_based import compile_sql_script  # está en la raíz del paquete

Triplet = Tuple[str, str, str]

# Verbos soportados por el determinista (SQL)
SQL_REL_VERBS = {"toma", "padece", "realiza"}
SQL_PROP_VERBS = {"tiene", "categoria", "frecuencia", "gravedad", "inicio", "fin", "se toma", "periodicidad"}
SQL_SUPPORTED_VERBS = SQL_REL_VERBS | SQL_PROP_VERBS


def _split_supported_for_sql(triplets: List[Triplet]) -> tuple[list[Triplet], list[Triplet]]:
    """Separa en (soportadas_por_reglas, no_soportadas) para SQL."""
    supported, unsupported = [], []
    for s, v, o in triplets:
        v_norm = (v or "").strip().lower()
        (supported if v_norm in SQL_SUPPORTED_VERBS else unsupported).append((s, v, o))
    return supported, unsupported


def generate_hybrid_sql(triplets: List[Triplet]) -> str:
    """
    Genera script SQL en modo híbrido:
      - lo soportado por el determinista → compile_sql_script
      - el resto → LLM (bd_from_triplets con 'sql')
    """
    sup, unsup = _split_supported_for_sql(triplets)
    parts: list[str] = []
    if sup:
        parts.append("-- ==== SQL (determinista) ====")
        parts.append(compile_sql_script(sup))
    if unsup:
        parts.append("-- ==== SQL (LLM complemento) ====")
        parts.append(bd_from_triplets(unsup, "sql"))
    return "\n".join(p for p in parts if p and p.strip())


def generate_script(triplets: List[Triplet], bd: str, no_llm: bool) -> str:
    """
    Punto único de entrada:
      - si no_llm=False → TODO al LLM (Cypher o SQL)
      - si no_llm=True y bd='sql' → híbrido determinista+LLM
      - si no_llm=True y bd='neo4j' → por ahora usa LLM (puedo añadir determinista Cypher si lo quieres)
    """
    bd_low = bd.lower()
    if not no_llm:
        return bd_from_triplets(triplets, bd_low)

    if bd_low == "sql":
        return generate_hybrid_sql(triplets)

    # Neo4j (hoy sin determinista): mandamos todo al LLM para no romper el flujo
    # Si prefieres que dispare NotImplementedError para que falle temprano, dímelo y lo cambio.
    return bd_from_triplets(triplets, "neo4j")
