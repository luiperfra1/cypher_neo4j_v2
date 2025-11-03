ALLOWED_REL = {"padece", "toma", "realiza"}
ALLOWED_PROP = {"categoria", "frecuencia", "gravedad", "inicio", "fin", "se toma", "periodicidad"}


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


_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y")