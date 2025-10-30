# 🧠 Proyecto: Conversación → Cypher / SQL

Este proyecto desarrolla un sistema conversacional capaz de transformar el lenguaje natural del usuario en **tripletas semánticas**, que posteriormente se convierten en consultas **Cypher** (para Neo4j) o **SQL** (para SQLite).​

El objetivo principal es crear una infraestructura que permita **estructurar y validar información derivada de escalas médicas y conversaciones clínicas**, integrando procesamiento del lenguaje natural, lógica semántica y almacenamiento tanto en grafos como en bases relacionales.

---

## ⚙️ 1. Crear entorno virtual

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
````

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

## 🚀 4. Ejecutar el `triplets2bd`

Desde la raíz del proyecto, ejecuta el módulo principal:

```bash
python -m triplets2bd.main_tripletas_bd
```

Por defecto, el script utiliza **Neo4j** como backend y:

1. Limpia la base de datos existente.
2. Crea constraints e índices.
3. Genera las sentencias Cypher a partir de las tripletas.
4. Ejecuta las sentencias en Neo4j.

Al finalizar, mostrará el tiempo total de ejecución y confirmará las operaciones realizadas.

---

### 🧩 Parámetros disponibles

El script acepta los siguientes parámetros opcionales:

| Parámetro     | Descripción                                                     | Valor por defecto                          | Ejemplo                          |
| ------------- | --------------------------------------------------------------- | ------------------------------------------ | -------------------------------- |
| `--bd`        | Define el backend de salida. Valores posibles: `neo4j` o `sql`. | `neo4j`                                    | `--bd sql`                       |
| `--sqlite-db` | Ruta al fichero SQLite (solo si `--bd sql`).                    | `./data/users/demo.sqlite`                 | `--sqlite-db ./data/demo.sqlite` |
| `--no-reset`  | Evita resetear la base de datos antes de crear el esquema.      | *No indicado* (por defecto **sí** resetea) | `--no-reset`                     |

---

### 🧩 Ejemplos de ejecución

#### 🟦 Usar Neo4j (modo por defecto)

```bash
python -m triplets2bd.main_tripletas_bd
```

> Limpia Neo4j, crea índices, genera Cypher y lo ejecuta en la base de datos.

#### 🟨 Forzar modo Neo4j explícitamente

```bash
python -m triplets2bd.main_tripletas_bd --bd neo4j
```

#### 🟩 Ejecutar en modo SQLite

```bash
python -m triplets2bd.main_tripletas_bd --bd sql
```

> Genera y ejecuta el script SQL sobre el fichero `data/users/demo.sqlite`.

#### 🟪 Usar una base SQLite personalizada

```bash
python -m triplets2bd.main_tripletas_bd --bd sql --sqlite-db ./data/test.sqlite
```

#### 🟥 Evitar el reseteo de la base de datos

```bash
python -m triplets2bd.main_tripletas_bd --bd sql --no-reset
```

> Mantiene los datos existentes y añade las nuevas inserciones.

---

### 🧾 Reporte automático en modo SQL

Cuando se ejecuta con `--bd sql`, al finalizar la inserción de datos se genera **automáticamente** un
reporte en formato `.txt` con el contenido de las tablas **que contienen filas**.

El archivo se crea junto al `.sqlite` con el nombre:

```
data/users/demo_report.txt
```

Cada tabla con contenido se representa así:

```
Tabla: Sintoma
Filas: 1

Muestra (hasta 15 filas):
id | sintoma_id | tipo       | fecha_ini… | fecha_fin | categoria | frecuencia | gravedad | created_at | updated_at
---+------------+------------+------------+-----------+-----------+------------+----------+------------+-----------
1  | sintoma_p… | problemas… |            |           |           | diariamen… |          | 2025-10-3… | 2025-10-3…
```

---

## 📂 5. Estructura del proyecto

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
│   ├── make_sqlite_report.py       # ← genera el reporte TXT de contenido
│   ├── sqlite_client.py
│   ├── schema_sqlite_bootstrap.py
│   ├── neo4j_client.py
│   ├── schema_bootstrap.py
│   └── tripletas_demo.py
│
├── .env
├── .gitignore
└── README.md
```

---

## 🧩 6. Requisitos previos

* **Python 3.12+**
* **Neo4j** corriendo (para modo `neo4j`)
* **SQLite 3** (instalado por defecto en Python)
* Acceso a **LlamUS**, **OpenAI** o **Ollama** según el `.env`
* Conexión local o remota a la base Neo4j configurada en `.env`

---

## 🧠 7. Ejemplo de flujo completo

```bash
# 1. Crear entorno y activar
py -3.12 -m venv .venv
.venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el script (modo SQL)
python -m triplets2bd.main_tripletas_bd --bd sql

# 4. Consultar el archivo de salida
type data/users/demo_report.txt
```

Salida esperada en consola:

```
Backend seleccionado: sql | reset=sí
Preparando SQLite en ./data/users/demo.sqlite…
🧨 Esquema SQL reseteado (0.21s)
✅ Esquema SQL listo (0.04s)
LLM: mapeando tripletas crudas → script…
✅ Script generado (3.12s)
Ejecutando script SQL en SQLite…
✅ SQL aplicado en SQLite (0.05s)
Generando reporte de contenido en data/users/demo_report.txt…
✅ Reporte generado correctamente
✅ Proceso completo (3.42s)
```

---

## ⚡ 8. Notas adicionales

* El **modo Neo4j** y el **modo SQL** comparten la misma fuente de tripletas (`tripletas_demo.py`).
* Puede adaptar el flujo para usar **tripletas generadas dinámicamente** o **entrada conversacional real**.
* El archivo `make_sqlite_report.py` es totalmente independiente y puede ejecutarse por separado:

  ```bash
  python -m triplets2bd.make_sqlite_report data/users/demo.sqlite -o data/users/demo_report.txt
  ```
* El sistema imprime los tiempos parciales y totales de cada fase, para facilitar la monitorización del rendimiento.

---

## 🧾 9. Créditos

Desarrollado como parte del entorno de investigación en la **Universidad de Sevilla**, integrando técnicas de modelado semántico, generación de tripletas mediante LLMs y persistencia en grafos y bases de datos relacionales.

---

