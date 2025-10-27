from __future__ import annotations
from typing import List, Tuple
import json, requests, re
from config import settings

# Utilidad simple para slug (debe replicarse en el LLM vía instrucciones)
_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = _slug_re.sub("_", s)
    return s.strip("_")

#Relaciones entre Nodos:   
    #" Actividad-[:EMPEORA {fecha, intensidad?}]->Sintoma\n"
    #" Actividad-[:MEJORA {fecha, intensidad?}]->Sintoma\n"
    #" Actividad-[:PROVOCA {fecha, intensidad?}]->Sintoma\n"
    #" Medicacion-[:MEJORA {fecha}]->Sintoma\n"
    #" Medicacion-[:EMPEORA {fecha}]->Sintoma\n"

#    "Relaciones las marcadas con {fecha} deben incluir prop {fecha} como fecha de alta):\n"
    # "  Persona-[:PADECE {fecha}]->Sintoma\n"

SYSTEM = (
    "Eres un mapper que convierte tripletas crudas del estilo (sujeto, verbo, objeto) "
    "a **sentencias Cypher** que cumplan este esquema y reglas:\n"

    "Nodos y props:\n"
    "  Persona{user_id, nombre, edad}\n"
    "  Sintoma{sintoma_id, tipo, fecha_inicio, fecha_fin, categoria, frecuencia, gravedad}\n"
    "  Actividad{actividad_id, nombre, categoria, frecuencia}\n"
    "  Medicacion{medicacion_id, tipo, periodicidad}\n"

    "Relaciones:\n"
    "  Persona-[:TOMA]->Medicacion\n"
    "  Persona-[:PADECE]->Sintoma\n"
    "  Persona-[:REALIZA]->Actividad\n"
    "  Persona-[:CONOCE]->Persona\n"

    "ENUMS (valores permitidos):\n"
    "  Sintoma.categoria ∈ {motor, cognitivo, afectivo, sueno, autonomico, habla_voz, deglucion, dolor_fatiga, otros_no_motor}\n"
    "  Actividad.categoria ∈ {adl_higiene, adl_vestido, movilidad, sueno, habla_comunicacion, alimentacion, cognitiva, ocio_social, fisica, instrumental}\n"
    "  frecuencia ∈ {nunca, rara_vez, semanal, varias_por_semana, diaria, varias_por_dia, no_aplica}\n"
    "  gravedad ∈ {leve, moderada, severa, desconocida}\n"

    "Reglas de IDs si faltan:\n"
    "  Persona.user_id = 'Persona_' + slug(nombre)\n"
    "  Sintoma.sintoma_id   = 'Sintoma_' + slug(tipo)\n"
    "  Actividad.actividad_id = 'Actividad_' + slug(nombre)\n"
    "  Medicacion.medicacion_id = 'Medicacion_' + slug(tipo)\n"

    "Notas importantes:\n"
    "  PROHIBIDO inferir o suponer propiedades, etiquetas o relaciones que NO aparezcan explícitamente en las tripletas de entrada.\n"
    "  Usa MERGE para nodos segun esos IDs y SET para el resto de props.\n"
    "  La edad es propiedad de Persona (no relación). Si ves 'tiene 22 años', haz SET p.edad=22.\n"
    "  Verbos: 'bebe/toma/consume/... (medicacion)'→:TOMA; 'padece/sufre/tiene/... (sintoma)'→:PADECE; 'realiza/practica/... (actividad)'→:REALIZA; 'conoce'→:CONOCE.\n"
    "  Antes de hacer un MATCH debe hacerse el MERGE de esa entidad.\n"
    "  Cada relacion debe construirse en UNA sola sentencia que incluya: MATCH o MERGE de ambos nodos y MERGE de la relación en la misma instruccion.\n"
    "  Toda relacion debe construirse con ambos nodos previamente definidos mediante MATCH (por ejemplo, MATCH (p:Persona {...}), MATCH (m:Medicacion {...}) antes de MERGE (p)-[:TOMA]->(m)).\n "  
    "  Devuelve SOLO un bloque Cypher, sin explicaciones, sin ```, sin  ```cypher, con sentencias separadas por ';'.\n"
)


def _post_chat(messages: list[dict], model: str | None = None) -> str:
    base = settings.OPENAI_API_BASE
    key = settings.OPENAI_API_KEY
    if not (base and key):
        raise RuntimeError("OPENAI_API_BASE/KEY no configurados en .env")
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": model or settings.MODEL_TRIPLETAS_CYPHER, "temperature": 0, "messages": messages}
    r = requests.post(url, headers=headers, data=json.dumps(data), timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

        
def cypher_from_triplets(raw: List[Tuple[str,str,str]]) -> str:
    normalized = [
        (a.strip().lower(), b.strip().lower(), c.strip().lower())
        for a, b, c in raw
    ]
    lines = [f"({a}, {b}, {c})" for a,b,c in normalized]
    prompt = "Tripletas:\n" + "\n".join(lines)
    messages = [
        {"role":"system","content": SYSTEM},
        {"role":"user","content": prompt},
    ]
    cypher = _post_chat(messages)
    return cypher