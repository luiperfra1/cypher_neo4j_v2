from typing import List, Tuple


RAW_TRIPLES_DEMO: List[Tuple[str, str, str]] = [
    # ---- Persona principal ----
    ("Jose Luis", "tiene", "59 años"), 

    # ---- Conoce ----
    ("Jose Luis", "conoce", "María"),              
    ("Jose Luis", "conoce", "Juan"),              

    # ---- Actividad ----
    ("Jose Luis", "realiza", "correr"),
    ("correr", "categoria", "fisica"),
    ("correr", "frecuencia", "semanal"),

    ("Jose Luis", "realiza", "ducharse"),
    ("ducharse", "categoria", "adl_higiene"),

    # ---- Sintoma ----
    ("Jose Luis", "padece", "insomnio"),
    ("insomnio", "frecuencia", "semanal"),
    

    ("Jose Luis", "padece", "cefalea"),
    ("cefalea","gravedad","leve"),

    ("Jose Luis", "padece", "dolor de espalda"),
    ("dolor de espalda","inicio","10/11/2022"),    

    # ---- Medicación ----
    ("Jose Luis", "toma", "enantium"),      
    ("Jose Luis", "toma", "paracetamol"),
    ("paracetamol","se toma","cada 8 horas"),

]

RAW_TRIPLES_DEMO2: List[Tuple[str, str, str]] = [
    # ---- Persona principal con más detalles ----
    ("Ana García", "tiene", "45 años"),
    
    # ---- Red social más compleja ----
    ("Ana García", "conoce", "Pedro Sánchez"),
    
    # ---- Actividades variadas ----
    ("Ana García", "realiza", "yoga"),
    ("yoga", "categoria", "fisica"),
    ("yoga", "frecuencia", "varias_por_semana"),
    
    # ---- Síntomas diversos ----
    
    ("Ana García", "padece", "mareos"),
    ("mareos", "categoria", "motor"),
    ("mareos", "frecuencia", "semanal"),
    ("mareos", "inicio", "15/01/2023"),
    ("dolor articular", "gravedad", "moderada"),

    
    # ---- Medicación compleja ----
    ("Ana García", "toma", "lexatin"),
    ("lexatin", "se toma", "cuando necesita"),
    
    
    # ---- Hábitos de sueño ----
    ("Ana García", "tiene", "problemas para dormir"),
    ("problemas para dormir", "frecuencia", "varias_por_semana"),
    
    # ---- Alimentación ----
    ("Ana García", "bebe", "2 litros de agua al día"),
    
    # ---- Historial médico ----
    ("Ana García", "es", "alérgica a penicilina"),
    
    # ---- Actividades sociales ----
    ("Ana García", "visita", "sus padres"),
    ("visitar padres", "frecuencia", "quincenal"),
    
]
#cambiar diaramente por semananal mente y comentar reseteo de bd
RAW_TRIPLES_DEMO3: List[Tuple[str, str, str]] = [
    ("Ana García", "conoce", "Pedro Sánchez"),
    #("Ana García", "tiene", "problemas para dormir"),
    ("problemas para dormir", "frecuencia", "diariamente"),
]
