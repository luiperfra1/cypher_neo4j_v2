# 🧠 Proyecto: Conversación → Tripletas → Cypher / SQL

Este proyecto desarrolla un sistema capaz de transformar lenguaje natural del usuario en **tripletas semánticas**, que posteriormente se convierten en consultas **Cypher** (para Neo4j) o **SQL** (para SQLite).

El objetivo principal es crear una infraestructura que permita **estructurar y validar información derivada de conversaciones clínicas**, integrando procesamiento del lenguaje natural, generación de tripletas y persistencia en grafos o bases relacionales.

---

## ⚙️ 1. Crear entorno virtual

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

---

## 📦 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 🔐 3. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

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
MODEL_KG_GEN=openai/qwen2.5:14b
MODEL_CONV2TEXT=qwen2.5:32b

# --- App ---
USER_ID=***id_usuario***
```

> ⚠️ **Importante:**  
> No publiques este archivo ni lo incluyas en commits (`.gitignore` debe contener `.env`).

---

## 🧠 4. Ejecutar el `text2triplet` (Texto Resumen → Tripletas)

Este módulo permite **extraer tripletas semánticas directamente desde texto libre**, utilizando un LLM o el extractor compatible con KG-Gen.

```bash
python -m text2triplets.main_kg --text TEXT3
```

### Parámetros principales

| Flag / Parámetro | Descripción | Valor por defecto | Ejemplo |
|------------------|-------------|-------------------|----------|
| `--mode` | Motor de extracción: `llm` o `kggen` | `llm` | `--mode kggen` |
| `--text` | Texto predefinido en `texts.py` | `TEXT1` | `--text TEXT3` |
| `--model` | Modelo LLM (sobrescribe `.env`) | Usa `.env` | `--model qwen2.5:14b` |
| `--context` | Ontología o contexto aplicado | `DEFAULT_CONTEXT` | `--context ...` |
| `--no-drop` | Muestra también tripletas inválidas | *Desactivado* | `--no-drop` |
| `--sqlite-db` | Ruta del fichero SQLite | `./data/users/demo.sqlite` | `--sqlite-db data/test.sqlite` |
| `--no-reset-log` | No limpiar la tabla de log al iniciar | *Desactivado* | `--no-reset-log` |
| `--generate-report` | Generar informe SQL tras ejecución | *Desactivado* | `--generate-report` |
| `--report-path` | Ruta del informe generado | *Automático* | `--report-path ./data/report.txt` |
| `--report-sample-limit` | Número de filas por tabla en reporte | `15` | `--report-sample-limit 30` |

---

## 🚀 5. Ejecutar el `triplets2bd` (Tripletas → Cypher / SQL)

Transforma tripletas en sentencias **Cypher** o **SQL**, ejecutándolas en Neo4j o SQLite según configuración.

```bash
python -m triplets2bd.main_tripletas_bd
```

### Flags disponibles

| Flag / Parámetro | Descripción | Valor por defecto | Ejemplo |
|------------------|-------------|-------------------|----------|
| `--bd` | Backend de salida: `sql` o `neo4j` | `sql` | `--bd neo4j` |
| `--sqlite-db` | Ruta del fichero SQLite | `./data/users/demo.sqlite` | `--sqlite-db ./data/test.sqlite` |
| `--no-reset` | Evita resetear la BD | *Desactivado* | `--no-reset` |
| `--no-reset-log` | Evita limpiar la tabla de log | *Desactivado* | `--no-reset-log` |
| `--llm` | Forzar modo LLM para todas las tripletas | *Desactivado* | `--llm` |
| `--no-llm` | Forzar modo determinista puro | *Desactivado* | `--no-llm` |
| `--triplets-json` | Cargar tripletas desde JSON inline | `None` | `--triplets-json '[["Ana","padece","insomnio"]]'` |
| `--triplets-file` | Cargar tripletas desde fichero | `None` | `--triplets-file ./data/tripletas.txt` |
| `--generate-report` | Crear informe tras ejecutar SQL | *Desactivado* | `--generate-report` |

---

## 🗣️ 6. Ejecutar el `conv2text` (Conversación → Resumen textual)

Resume una conversación usuario-asistente en frases breves y explícitas, listas para el extractor de tripletas.

```bash
python -m conv2text.main_conv2text --text-key TEXT1
```

### Flags principales

| Flag / Parámetro | Descripción | Valor por defecto | Ejemplo |
|------------------|-------------|-------------------|----------|
| `--in` | Archivo de entrada con conversación | `-` (stdin) | `--in data/chat.txt` |
| `--out` | Archivo de salida del resumen | *stdout* | `--out resumen.txt` |
| `--text-key` | Texto predefinido (`texts.py`) | `None` | `--text-key TEXT3` |
| `--max` | Número máximo de frases | `10` | `--max 8` |
| `--temp` | Temperatura del modelo | `0.0` | `--temp 0.3` |
| `--sqlite-db` | Ruta a la base de datos SQLite | `./data/users/demo.sqlite` | `--sqlite-db data/test.sqlite` |
| `--no-reset-log` | No limpiar la tabla `log` antes de generar resumen | *Desactivado* | `--no-reset-log` |
| `--generate-report` | Genera un informe tras ejecutar | *Desactivado* | `--generate-report` |
| `--list-texts` | Lista textos disponibles y termina | *Desactivado* | `--list-texts` |

---

## 🔄 7. Ejecutar el `pipeline` (Conversación → Resumen → Tripletas → BD)

Ejecuta automáticamente todo el flujo de transformación y persistencia.

```bash
python -m pipeline
```

### Comportamiento del pipeline

1. **Reset al inicio:** limpia la tabla `log`, el dominio SQLite y Neo4j.  
2. **Resumen automático:** usa `conv2text` si `"use_conv2text_for_extractor": True`.  
3. **Extracción:** genera tripletas con el extractor (`text2triplet` o `kggen`).  
4. **Inyección:** ejecuta `triplets2bd` con `reset=False` y `reset_log=False`.  
5. **Salida:** muestra tiempos parciales y crea `data/users/demo_report.txt` (modo SQL).

### Flags adicionales (si se ejecuta como script configurable)

| Parámetro | Descripción | Valor por defecto | Ejemplo |
|------------|-------------|-------------------|----------|
| `--no-reset` | Desactiva el reset global inicial | *Activado* | `--no-reset` |
| `--no-summary` | Omite la fase conv2text | *Desactivado* | `--no-summary` |
| `--backend` | Forzar backend de salida (`sql` o `neo4j`) | `sql` | `--backend neo4j` |
| `--mode` | Modo de BD (`deterministic`, `hybrid`, `llm`) | `deterministic` | `--mode hybrid` |
| `--temp` | Temperatura del LLM en `conv2text` | `0.0` | `--temp 0.3` |

---

## 🧩 8. Mapa general de comandos

| Módulo | Descripción | Ejemplo |
|--------|--------------|---------|
| `conv2text` | Conversación → Resumen | `python -m conv2text.main_conv2text --text-key TEXT3` |
| `text2triplets` | Texto → Tripletas | `python -m text2triplets.main_kg --text TEXT3` |
| `triplets2bd` | Tripletas → BD (SQL / Neo4j) | `python -m triplets2bd.main_tripletas_bd --bd sql` |
| `pipeline` | Flujo completo | `python -m pipeline` |

---

## 🧠 9. Ejemplo de flujo completo

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m conv2text.main_conv2text --text-key TEXT3
python -m text2triplets.main_kg --text TEXT3 --generate-report
python -m triplets2bd.main_tripletas_bd --bd sql
python -m pipeline

type data/users/demo_report.txt
```

---

## 🧾 10. Notas adicionales

- El `pipeline` no resetea durante la inyección, solo al inicio.  
- `conv2text`, `text2triplet` y `triplets2bd` pueden ejecutarse por separado.  
- `make_sqlite_report.py` genera informes directamente desde una BD SQLite:
  python -m triplets2bd.make_sqlite_report data/users/demo.sqlite -o data/users/demo_report.txt
- Compatible con **Neo4j ≥5.x** y **Python 3.12+**.  
- El fichero `.env` define los endpoints y modelos activos.  
- Todos los scripts imprimen tiempos y logs en consola.

---

## 📍 11. Créditos

Desarrollado como parte del entorno de investigación en la **Universidad de Sevilla**, integrando modelos LLM, generación de tripletas y persistencia en grafos y bases de datos relacionales.
