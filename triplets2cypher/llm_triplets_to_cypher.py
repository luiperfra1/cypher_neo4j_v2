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
    #Persona-CONOCE {relacion}->Persona


SYSTEM = (
    "CONVERSIÓN DIRECTA DE TRIPLETAS A CYPHER - SIGUE ESTRICTAMENTE ESTAS REGLAS:\n"
    "\n"
    "ESQUEMA ÚNICO PERMITIDO:\n"
    "NODOS: Persona{user_id, nombre, edad} | Sintoma{sintoma_id, tipo, fecha_inicio, fecha_fin, categoria, frecuencia, gravedad} | Actividad{actividad_id, nombre, categoria, frecuencia} | Medicacion{medicacion_id, tipo, periodicidad}\n"
    "RELACIONES: (Persona)-[:TOMA]->(Medicacion) | (Persona)-[:PADECE]->(Sintoma) | (Persona)-[:REALIZA]->(Actividad) | (Persona)-[:CONOCE]->(Persona)\n"
    "\n"

    "REGLAS DE CONVERSIÓN (OBLIGATORIAS):\n"
    "1. PROCESAR TODAS LAS TRIPLETAS: Analiza CADA tripleta (sujeto, verbo, objeto) secuencialmente\n"
    "2. EXTRACCIÓN DE PROPIEDADES:\n"
    "   - Si el verbo es 'tiene' y el objeto contiene 'años' → extraer número como edad\n"
    "   - Si el verbo es 'categoria' → asignar a propiedad 'categoria' del sujeto\n"
    "   - Si el verbo es 'frecuencia' → asignar a propiedad 'frecuencia' del sujeto\n"
    "   - Si el verbo es 'gravedad' → asignar a propiedad 'gravedad' del sujeto\n"
    "   - Si el verbo es 'inicio' → asignar a propiedad 'fecha_inicio' del sujeto\n"
    "3. GENERACIÓN DE IDs: \n"
    "   - Persona: 'Persona_' + slug(nombre) → user_id\n"
    "   - Sintoma: 'Sintoma_' + slug(tipo) → sintoma_id  \n"
    "   - Actividad: 'Actividad_' + slug(nombre) → actividad_id\n"
    "   - Medicacion: 'Medicacion_' + slug(tipo) → medicacion_id\n"
    "4. slug(texto): minúsculas, espacios→'_', sin acentos, sin signos\n"
    "\n"
    "REGLAS CRÍTICAS:\n"
    "  Usa siempre todas las tripletas recibidas, incluso si parecen redundantes o incompletas. Cada una debe reflejarse en el resultado Cypher siguiendo la estructura indicada."
    "  DEBES SIEMPRE establecer estas propiedades al crear nodos:\n"
    "   - Persona.nombre (obligatorio)\n"
    "   - Sintoma.tipo (obligatorio)\n"
    "   - Actividad.nombre (obligatorio)\n"
    "   - Medicacion.tipo (obligatorio)\n"
    "\n"
    "ORDEN DE OPERACIONES CON RELACIONES OBLIGATORIO:\n"
    "  1. PRIMERO crear todos los nodos con MERGE\n"
    "  2. DESPUÉS crear las relaciones con MATCH + MERGE\n"
    "  NUNCA intentar crear relaciones antes de asegurar que existen ambos nodos\n"
    "\n"
    "NORMALIZACIÓN DE FECHAS:\n"
    "  - Convertir '10/11/2022' → '2022-11-10' (formato ISO)\n"
    "  - Si no se puede determinar el formato, OMITIR la propiedad\n"
    "\n"
    "FORMATO CYPHER ESTRICTO:\n"
    "MERGE (n:Label {id_key: 'id_valor'})\n"
    "ON CREATE SET n.prop1 = valor1, n.prop2 = valor2;\n"
    "ON MATCH SET n.prop_opcional = valor2;\n"
    "\n"
    "MATCH (a:LabelA {id_key: 'id_a'}), (b:LabelB {id_key: 'id_b'})\n"
    "MERGE (a)-[:RELACION]->(b);\n"
    "\n"
    "PROHIBICIONES ABSOLUTAS:\n"
    " NO usar solo ON CREATE SET sin ON MATCH SET para propiedades actualizables\n"
    " NO omitir tripletas relevantes\n"
    " NO crear nodos sin propiedades obligatorias\n"
    " NO inferir propiedades/relaciones no explícitas\n"
    " NO usar MATCH sin filtro por ID\n" 
    " NO usar MERGE múltiple separado por comas\n"
    " NO explicaciones, solo Cypher\n"
    "\n"
    "EJEMPLOS DE CONVERSIÓN CORRECTA:\n"
    "Tripleta: (Juan, tiene, 25 años)\n"
    "Cypher: MERGE (p:Persona {user_id: 'persona_juan'}) ON CREATE SET p.nombre = 'Juan', p.edad = 25 ON MATCH SET p.edad = 25;\n"
    "\n"
    "Tripleta: (medicamento, se toma, cada 8 horas)\n"
    "Cypher: MERGE (m:Medicacion {medicacion_id: 'medicacion_medicamento'}) ON CREATE SET m.tipo = 'medicamento', m.periodicidad = 'cada 8 horas' ON MATCH SET m.periodicidad = 'cada 8 horas';\n"
    "\n"
    "Tripleta: (dolor, inicio, 10/11/2022)\n"
    "Cypher: MERGE (s:Sintoma {sintoma_id: 'sintoma_dolor'}) ON CREATE SET s.tipo = 'dolor', s.fecha_inicio = '2022-11-10' ON MATCH SET s.fecha_inicio = '2022-11-10';\n"
    "\n"
    "Tripleta: (Ana, conoce, María)\n"
    "Cypher: MERGE (p1:Persona {user_id: 'persona_ana'}) ON CREATE SET p1.nombre = 'Ana';\n"
    "MERGE (p2:Persona {user_id: 'persona_maria'}) ON CREATE SET p2.nombre = 'María';\n"
    "MATCH (p1:Persona {user_id: 'persona_ana'}), (p2:Persona {user_id: 'persona_maria'}) MERGE (p1)-[:CONOCE]->(p2);\n"
    "\n"
    "Tripleta: (dolor, frecuencia, diaria)\n"
    "Cypher: MERGE (s:Sintoma {sintoma_id: 'sintoma_dolor'}) ON CREATE SET s.tipo = 'dolor', s.frecuencia = 'diaria' ON MATCH SET s.frecuencia = 'diaria';\n"
    "SALIDA: ÚNICAMENTE código Cypher, sentencias separadas por ';', sin comentarios, sin markdown, sin texto explicativo."
)



SYSTEM111 = (
    "Eres un mapper que convierte tripletas crudas del estilo (sujeto, verbo, objeto) "
    "a **sentencias Cypher** que cumplan este esquema y reglas:\n"
    "ENUMS VÁLIDOS:\n"
    "- Sintoma.categoria: motor, cognitivo, afectivo, sueno, autonomico, habla_voz, deglucion, dolor_fatiga, otros_no_motor\n"
    "- Actividad.categoria: adl_higiene, adl_vestido, movilidad, sueno, habla_comunicacion, alimentacion, cognitiva, ocio_social, fisica, instrumental\n"
    "- frecuencia: nunca, rara_vez, semanal, varias_por_semana, diaria, varias_por_dia, no_aplica\n"
    "- gravedad: leve, moderada, severa, desconocida\n"
    "\n"
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

    "REGLAS OBLIGATORIAS:\n"
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