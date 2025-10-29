
# 🧠 Proyecto: Conversación → Cypher

Este proyecto tiene como objetivo el desarrollo de un sistema de chat conversacional capaz de
transformar el lenguaje natural del usuario en consultas Cypher, que posteriormente alimentan un
grafo de conocimiento construido en Neo4j.​

El propósito principal del grafo es validar información derivada de escalas médicas, facilitando así la
estructuración y verificación de datos clínicos provenientes de interacciones conversacionales.​

A través de esta arquitectura, se busca integrar procesamiento de lenguaje natural, lógica semántica
y almacenamiento orientado a grafos, permitiendo una forma intuitiva y eficiente de alimentar y
consultar información médica compleja.
---

## ⚙️ 1. Crear entorno virtual

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

---

## 📦 2. Instalar dependencias

Instala las librerías necesarias ejecutando:

```bash
pip install -r requirements.txt
```

---

## 🔐 3. Configurar variables de entorno

Crea un archivo llamado `.env` en la raíz del proyecto con el siguiente contenido:

```bash
# --- Neo4j ---
NEO4J_URI=***neo4j_url***
NEO4J_USER=***neo4j_user***
NEO4J_PASSWORD=***neo4j_password***


# --- Backend LLM a usar por la app ---
# Opciones: OPENAI o OLLAMA
LLAMUS_BACKEND=OPENAI
LLAMUS_API_KEY=***tu_key***

# Endpoints para el adapter
LLAMUS_URL=***url_base_llamus***
OLLAMA_URL=***url_base_ollama***


# --- OpenAI API Base ---
OPENAI_API_BASE=***url_base_openai***



# --- OpenAI API Key ---
OPENAI_API_KEY=***tu_key***


# --- Modelos ---

MODEL_TRIPLETAS_CYPHER=qwen2.5:32b
# --- App ---
USER_ID=
```

---

## 🚀 4. Ejecutar el triplets2cypher

Desde la raíz del proyecto, ejecuta:

```bash
python -m triplets2cypher.main_tripletas_cypher
```

Esto:

* Limpia la base de datos Neo4j.
* Crea índices y constraints.
* Genera las sentencias Cypher a partir de las tripletas de ejemplo.
* Inserta las entidades y relaciones en Neo4j.

---

## 📂 5. Estructura del proyecto

```
proyecto/
│
├── triplets2cypher/
│   ├── __init__.py
│   ├── main_tripletas_cypher.py
│   ├── neo4j_client.py
│   ├── llm_triplets_to_cypher.py
│   ├── schema_bootstrap.py
│   ├── tripletas_demo.py
│
├── config.py
├── .env
├── .gitignore
└── Readme.md
```

---

## 🧩 6. Requisitos previos

* Python **3.12+**
* Servidor **Neo4j** corriendo en `bolt://localhost:7687`
* Acceso a **LlamUS** o **Ollama** (según configuración del `.env`)

---


