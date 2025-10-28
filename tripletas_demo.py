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
