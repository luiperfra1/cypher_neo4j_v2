
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

# --- App ---
USER_ID=
```

---

## 🧠 4. Ejecutar el `text2triplet` (Texto Resumen → Tripletas)

Este módulo permite **extraer tripletas semánticas directamente desde texto libre**, utilizando un LLM o el extractor compatible con KG-Gen. Es el paso previo antes de convertirlas a Cypher/SQL con `triplets2bd`.

```bash
python -m text2triplets.main_kg --text TEXT3
```

Por defecto:

1. Usa el modo **LLM** (`text2triplet`)
2. Aplica el contexto y ontología definida
3. Filtra tripletas inválidas (a menos que se use `--no-drop`)
4. Muestra tiempos parciales y resultado final

### Parámetros disponibles

| Parámetro   | Descripción                                       | Valor por defecto | Ejemplo               |
| ----------- | ------------------------------------------------- | ----------------- | --------------------- |
| `--mode`    | Motor de extracción: `llm` o `kggen`              | `llm`             | `--mode kggen`        |
| `--text`    | Texto de prueba definido en `texts.py`            | `TEXT1`           | `--text TEXT4`        |
| `--model`   | Sobrescribe el modelo del `.env` o del `KGConfig` | Usa el del `.env` | `--model qwen2.5:14b` |
| `--context` | Ontología / reglas a aplicar                      | `DEFAULT_CONTEXT` | `--context "..."`     |
| `--no-drop` | Muestra también tripletas inválidas               | *Desactivado*     | `--no-drop`           |

### Ejemplos

```bash
python -m text2triplets.main_kg --text TEXT3
python -m text2triplets.main_kg --mode kggen --text TEXT3
python -m text2triplets.main_kg --text TEXT8 --no-drop
python -m text2triplets.main_kg --text TEXT4 --model qwen2.5:14b
```

### Textos disponibles (`texts.py`)

```
TEXT1, TEXT2, TEXT3, TEXT4, TEXT5, TEXT6, TEXT7, TEXT8, TEXT9, TEXT10, TEXT11
```


## 🚀 5. Ejecutar el `triplets2bd` (Tripletas → Cypher / SQL)

Este módulo transforma tripletas en sentencias **Cypher** o **SQL** y, opcionalmente, las ejecuta en Neo4j o SQLite.
Puede funcionar en modo **LLM** o en modo **Híbrido** (determinista + LLM).

```bash
python -m triplets2bd.main_tripletas_bd
```

Por defecto:

1. Usa **SQL** como backend
2. Resetea la base de datos
3. Genera el script desde las tripletas
4. Ejecuta las sentencias en SQLite

---

### 🧩 Parámetros disponibles

| Parámetro         | Descripción                                                                             | Valor por defecto          | Ejemplo                                           |
| ----------------- | --------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------- |
| `--bd`            | Backend de salida: `neo4j` o `sql`                                                      | `sql`                      | `--bd neo4j`                                      |
| `--sqlite-db`     | Ruta del fichero SQLite (solo si `--bd=sql`)                                            | `./data/users/demo.sqlite` | `--sqlite-db ./data/test.sqlite`                  |
| `--no-reset`      | No resetear la BD antes de crear esquema                                                | *Resetea por defecto*      | `--no-reset`                                      |
| `--hybrid`        | Usa modo híbrido: primero **determinista** y las tripletas fuera de esquema pasan a LLM | *Desactivado*              | `--hybrid`                                        |
| `--triplets-json` | Cargar tripletas desde JSON inline                                                      | `None`                     | `--triplets-json '[["Ana","padece","insomnio"]]'` |
| `--triplets-file` | Cargar tripletas desde fichero `.json` o `.txt`                                         | `None`                     | `--triplets-file ./ejemplo.txt`                   |

---

### 🧠 Modos de funcionamiento

| Modo                     | Cómo funciona                                                                                  | Cuándo usarlo                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **LLM (por defecto)**    | Todas las tripletas se procesan mediante LLM para generar Cypher/SQL                           | Cuando no importa el coste LLM y quieres máxima flexibilidad |
| **Híbrido (`--hybrid`)** | Primero aplica un mapeo **determinista estricto**; las tripletas fuera de formato pasan al LLM | Para máxima precisión, control y menor consumo de LLM        |

Flujo del modo híbrido:

```
Tripletas → Determinista (estricto) → [válidas] → script
                    ↓
             [no compatibles]
                    ↓
                 LLM → script extra
```



### 📄 Reporte automático en modo SQL

Si el backend es `sql`, al finalizar se genera un archivo `.txt` con el contenido de las tablas que tengan datos:

```
data/users/demo_report.txt
```

Incluye filas por tabla y una muestra de hasta 15 registros por tabla.

---


## 🔄 Flujo completo del sistema

```
Usuario
   ↓
Conversación
   ↓
LLM Extractor (limpieza + resumen canónico)
   ↓
text2triplet (LLM o KG-Gen)
   ↓
Tripletas validadas
   ↓
triplets2bd
   ↓
Cypher / SQL
   ↓
Neo4j / SQLite
```

---

## 📂 6. Estructura del proyecto

```
proyecto/
│
├── data/
│   └── users/
│       ├── demo.sqlite
│       └── demo_report.txt
│
├── triplets2bd/
│   ├── __init__.py
│   ├── main_tripletas_bd.py
│   ├── llm_triplets_to_bd.py
│   ├── make_sqlite_report.py
│   ├── sqlite_client.py
│   ├── schema_sqlite_bootstrap.py
│   ├── neo4j_client.py
│   ├── schema_bootstrap.py
│   └── tripletas_demo.py
│
├── text2triplets/
│   ├── __init__.py
│   ├── main_kg.py
│   ├── text2triplet.py
│   ├── texts.py
│   └── llm_client.py
│
├── .env
├── .gitignore
└── README.md
```

---

## 🧩 7. Requisitos previos

* Python 3.12+
* Neo4j (si se usa modo `neo4j`)
* SQLite 3 (modo `sql`)
* Acceso a LlamUS, OpenAI u Ollama según `.env`
* Conexión local o remota al servidor Neo4j configurado

---

## 🧠 8. Ejemplo de flujo completo

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m text2triplets.main_kg --text TEXT3
python -m triplets2bd.main_tripletas_bd --bd sql

type data/users/demo_report.txt
```

---

## 🧾 9. Notas adicionales

* `text2triplet` puede integrarse con un futuro módulo conversacional para generar tripletas desde diálogo real.
* El flujo soporta reemplazar el extractor LLM por uno rule-based si fuera necesario.
* `make_sqlite_report.py` puede ejecutarse de forma independiente:

```bash
python -m triplets2bd.make_sqlite_report data/users/demo.sqlite -o data/users/demo_report.txt
```

---

## 📍 10. Créditos

Desarrollado como parte del entorno de investigación en la **Universidad de Sevilla**, integrando modelos LLM, generación de tripletas y persistencia en grafos y bases de datos relacionales.
