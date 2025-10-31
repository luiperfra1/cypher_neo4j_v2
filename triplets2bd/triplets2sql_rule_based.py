# triplets2sql_rule_based.py
from __future__ import annotations
import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Tuple, Optional

Triplet = Tuple[str, str, str]

# ---------------------------
# Formato estricto admitido
# ---------------------------

ALLOWED_REL = {"padece", "toma", "realiza"}
ALLOWED_PROP = {"categoria", "frecuencia", "gravedad", "inicio", "fin", "se toma", "periodicidad"}

# ---------------------------
# Helpers
# ---------------------------

def slugify(text: str) -> str:
    s = text.strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^a-z0-9\s_-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s

def to_title_name(s: Optional[str]) -> Optional[str]:
    if not isinstance(s, str):
        return s
    parts = [p for p in s.strip().split() if p]
    return " ".join(p.capitalize() for p in parts)

def parse_age(obj: str) -> Optional[int]:
    o = obj.strip().lower()
    m = re.search(r"(\d{1,3})\s*años?", o)
    if m:
        return int(m.group(1))
    if o.isdigit():
        return int(o)
    return None

_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y")

def normalize_date(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def sql_quote(v: Optional[object]) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    s = str(v).lower().replace("'", "''")
    return f"'{s}'"

# ---------------------------
# Data accumulators
# ---------------------------

class Entity:
    def __init__(self, etype: str, key: str):
        self.etype = etype  # persona | sintoma | actividad | medicacion
        self.key = key      # user_id | sintoma_id | actividad_id | medicacion_id
        self.props: Dict[str, Optional[str]] = {}

    def set(self, k: str, v: Optional[str]):
        if v is None:
            return
        self.props[k] = v

    def ensure_minimal(self):
        if self.etype == 'persona':
            self.props.setdefault('nombre', None)
        elif self.etype == 'sintoma':
            self.props.setdefault('tipo', None)
        elif self.etype == 'actividad':
            self.props.setdefault('nombre', None)
        elif self.etype == 'medicacion':
            self.props.setdefault('tipo', None)

class Collector:
    def __init__(self):
        self.entities: Dict[Tuple[str, str], Entity] = {}
        self.relations: List[Tuple[str, str, str]] = []  # (rel_table, persona_user_id, right_key)

        # índices exactos por texto canónico -> key
        self.persona_index: Dict[str, str] = {}
        self.sintoma_index: Dict[str, str] = {}
        self.actividad_index: Dict[str, str] = {}
        self.medicacion_index: Dict[str, str] = {}

    def _get_or_new(self, etype: str, keyvalue: str) -> Entity:
        keycol = {
            'persona': 'user_id',
            'sintoma': 'sintoma_id',
            'actividad': 'actividad_id',
            'medicacion': 'medicacion_id',
        }[etype]
        k = (etype, keyvalue)
        if k not in self.entities:
            e = Entity(etype, keycol)
            e.set(keycol, keyvalue)
            self.entities[k] = e
        return self.entities[k]

    def persona_by_name(self, name: str) -> Entity:
        canonical = name.strip().lower()
        if canonical in self.persona_index:
            uid = self.persona_index[canonical]
        else:
            uid = f"persona_{slugify(canonical)}"
            self.persona_index[canonical] = uid
        e = self._get_or_new('persona', uid)
        e.set('nombre', to_title_name(name))
        return e

    def sintoma_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        if canonical in self.sintoma_index:
            sid = self.sintoma_index[canonical]
        else:
            sid = f"sintoma_{slugify(canonical)}"
            self.sintoma_index[canonical] = sid
        e = self._get_or_new('sintoma', sid)
        e.set('tipo', canonical)
        return e

    def actividad_by_name(self, nombre: str) -> Entity:
        canonical = nombre.strip().lower()
        if canonical in self.actividad_index:
            aid = self.actividad_index[canonical]
        else:
            aid = f"actividad_{slugify(canonical)}"
            self.actividad_index[canonical] = aid
        e = self._get_or_new('actividad', aid)
        e.set('nombre', canonical)
        return e

    def medicacion_by_type(self, tipo: str) -> Entity:
        canonical = tipo.strip().lower()
        if canonical in self.medicacion_index:
            mid = self.medicacion_index[canonical]
        else:
            mid = f"medicacion_{slugify(canonical)}"
            self.medicacion_index[canonical] = mid
        e = self._get_or_new('medicacion', mid)
        e.set('tipo', canonical)
        return e

# ---------------------------
# Particionador estricto
# ---------------------------

def _is_age_text(obj: str) -> bool:
    obj_l = obj.strip().lower()
    return bool(re.search(r"^\d{1,3}\s*años?$", obj_l)) or obj_l.isdigit()

def partition_triplets_strict(triplets: List[Triplet]) -> Tuple[List[Triplet], List[Tuple[Triplet, str]]]:
    """
    Separa tripletas en:
      - soportadas por el determinista (formato estricto)
      - fuera de formato con razón (para imprimir y enviar al LLM)
    """
    supported: List[Triplet] = []
    leftovers: List[Tuple[Triplet, str]] = []

    for s, v, o in triplets:
        s_l, v_l, o_l = s.strip(), v.strip().lower(), o.strip()
        if v_l in ALLOWED_REL:
            supported.append((s_l, v_l, o_l))
            continue
        if v_l in ALLOWED_PROP:
            supported.append((s_l, v_l, o_l))
            continue
        if v_l == "tiene":
            if _is_age_text(o_l):
                supported.append((s_l, v_l, o_l))
            else:
                leftovers.append(((s_l, v_l, o_l), "tiene_sin_edad"))
            continue
        leftovers.append(((s_l, v_l, o_l), "verbo_no_permitido"))

    return supported, leftovers

# ---------------------------
# Generación SQL (determinista)
# ---------------------------

PROPERTY_VERBS = {
    'categoria': ('categoria', 'node'),
    'frecuencia': ('frecuencia', 'node'),
    'gravedad': ('gravedad', 'node'),
    'inicio': ('fecha_inicio', 'date'),
    'fin': ('fecha_fin', 'date'),
    'se toma': ('periodicidad', 'node'),
    'periodicidad': ('periodicidad', 'node'),
}

RELATION_VERBS = {
    'toma': 'persona_toma_medicacion',
    'padece': 'persona_padece_sintoma',
    'realiza': 'persona_realiza_actividad',
}

def upsert_from_triplets(triplets: List[Triplet]) -> Tuple[List[str], List[str]]:
    """
    Construye sentencias SQL para entidades (UPSERT) y relaciones (INSERT OR IGNORE)
    a partir de tripletas crudas, sin LLM. Asume tripletas correctas y ordenadas.
    """
    col = Collector()
    property_buffer: List[Tuple[str, str, str]] = []
    leftovers_for_props: List[Tuple[Triplet, str]] = []

    # PASADA 1: crear entidades por relaciones y edad; y relaciones base
    for s, v, o in triplets:
        s_l, v_l, o_l = s.strip().lower(), v.strip().lower(), o.strip().lower()

        # Edad
        if v_l == 'tiene':
            age = parse_age(o_l)
            if age is not None:
                p = col.persona_by_name(s_l)
                p.set('edad', age)
            # si no es edad, ignoramos (particionador ya lo habrá marcado como leftover)
            continue

        # Relaciones canónicas
        if v_l in RELATION_VERBS:
            p = col.persona_by_name(s_l)
            if v_l == 'padece':
                snt = col.sintoma_by_type(o_l)
                col.relations.append(('persona_padece_sintoma', p.props['user_id'], snt.props['sintoma_id']))
            elif v_l == 'toma':
                med = col.medicacion_by_type(o_l)
                col.relations.append(('persona_toma_medicacion', p.props['user_id'], med.props['medicacion_id']))
            elif v_l == 'realiza':
                act = col.actividad_by_name(o_l)
                col.relations.append(('persona_realiza_actividad', p.props['user_id'], act.props['actividad_id']))
            continue

        # Propiedades permitidas: diferir a PASADA 2
        if v_l in PROPERTY_VERBS:
            property_buffer.append((s_l, v_l, o_l))
            continue

        # Otros verbos: no se procesan aquí (particionador se encarga)
        continue

    # PASADA 2: aplicar props SOLO si la entidad ya existe en índices
    for s_l, v_l, o_l in property_buffer:
        prop, kind = PROPERTY_VERBS[v_l]
        value: Optional[str] = normalize_date(o_l) if kind == 'date' else o_l

        ent: Optional[Entity] = None
        if s_l in col.sintoma_index:
            ent = col._get_or_new('sintoma', col.sintoma_index[s_l])
        elif s_l in col.actividad_index:
            ent = col._get_or_new('actividad', col.actividad_index[s_l])
        elif s_l in col.medicacion_index:
            ent = col._get_or_new('medicacion', col.medicacion_index[s_l])

        if ent is None:
            # Entrada fuera de contrato: propiedad sin entidad previa
            leftovers_for_props.append(((s_l, v_l, o_l), "prop_sin_entidad_previa"))
            continue

        ent.set(prop, value)

    # En ultra-determinista, no “inventamos” entidades a partir de props ambiguas.
    # Si hubo props sin entidad previa, las dejamos fuera para que el main las gestione (LLM si procede).

    # Asegurar props mínimas
    for ent in col.entities.values():
        ent.ensure_minimal()

    # Build SQL
    entity_sql: List[str] = []
    unique_map = {
        'persona':   ('persona',   'user_id',     ('nombre', 'edad')),
        'sintoma':   ('sintoma',   'sintoma_id',  ('tipo', 'fecha_inicio', 'fecha_fin', 'categoria', 'frecuencia', 'gravedad')),
        'actividad': ('actividad', 'actividad_id',('nombre', 'categoria', 'frecuencia')),
        'medicacion':('medicacion','medicacion_id',('tipo', 'periodicidad')),
    }


    # Entidades (orden estable)
    for (etype, key), ent in sorted(col.entities.items(), key=lambda x: (x[0][0], x[0][1])):
        table, keycol, other_cols = unique_map[etype]
        cols = [keycol] + list(other_cols)
        vals = [sql_quote(ent.props.get(c)) for c in cols]
        insert = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)})"
        updates = ",\n  ".join(f"{c} = excluded.{c}" for c in other_cols)
        entity_sql.append(insert + f"\nON CONFLICT({keycol}) DO UPDATE SET\n  {updates};")

    # Relaciones (orden estable) con propagación simple
    relation_sql: List[str] = []
    for rel_table, left_key, right_key in sorted(col.relations):
        if rel_table == 'persona_toma_medicacion':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_toma_medicacion (persona_id, medicacion_id, pauta)\n"
                "SELECT p.id, m.id, m.periodicidad FROM persona p, medicacion m\n"
                f"WHERE p.user_id = '{left_key}' AND m.medicacion_id = '{right_key}';"
            )
        elif rel_table == 'persona_realiza_actividad':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_realiza_actividad (persona_id, actividad_id)\n"
                "SELECT p.id, a.id FROM persona p, actividad a\n"
                f"WHERE p.user_id = '{left_key}' AND a.actividad_id = '{right_key}';"
            )
        elif rel_table == 'persona_padece_sintoma':
            relation_sql.append(
                "INSERT OR IGNORE INTO persona_padece_sintoma (persona_id, sintoma_id, desde)\n"
                "SELECT p.id, s.id, s.fecha_inicio FROM persona p, sintoma s\n"
                f"WHERE p.user_id = '{left_key}' AND s.sintoma_id = '{right_key}';"
            )

    return entity_sql, relation_sql

def compile_sql_script(triplets: List[Triplet]) -> str:
    entity_sql, relation_sql = upsert_from_triplets(triplets)
    return "\n".join(entity_sql + relation_sql)
