# pipeline.py
from __future__ import annotations
import time
from typing import List, Tuple, Optional

# --- Tripletas → BD
from triplets2bd.engine import run_triplets_to_bd
from triplets2bd.utils.types import EngineOptions

# --- Textos predefinidos (ajusta el import a tu paquete real)
try:
    from text2triplets.texts import ALL_TEXTS  # dict con TEXT1, TEXT2, ...
except Exception:
    ALL_TEXTS = {}

# --- Resumen conversacional (conv2text)
try:
    # engine.py reexporta summarize_conversation en tu paquete conv2text
    from conv2text.engine import summarize_conversation as summarize_conv_text
except Exception:
    summarize_conv_text = None  # si no existe el paquete, se ignora con gracia

Triplet = Tuple[str, str, str]

# =========================
# CONFIGURACIÓN EDITABLE
# =========================
CONFIG = {
    # Fuente de datos:
    # - "text": usa TEXT_RAW o TEXT_KEY (si existe en ALL_TEXTS)
    "source": "text",  # "text" | "triplets" | "demo"

    # Si source=="text"
    "TEXT_KEY": None,  # p. ej. "TEXT1" si existe en ALL_TEXTS
    "TEXT_RAW": """LLM: ¿Cómo llevas la medicación?
user_sara: Tomo levotiroxina en ayunas cada mañana.
LLM: ¿Haces ejercicio?
user_sara: Hago pilates dos veces por semana.
""",

    # --- Resumen conv2text ---
    "print_conv_summary": True,     # imprimir conversación + resumen + tiempos
    "conv_summary_max_sentences": 10,
    "conv_summary_temperature": 0.0,

    # >>> NUEVO: usar salida conv2text para el extractor
    "use_conv2text_for_extractor": True,  # si True, el extractor recibe el resumen; si False, la conversación

    # Extractor para texto → tripletas
    "extractor_mode": "llm",   # "llm" (text2triplet) | "kggen" (kg_base)
    "extractor_model": None,   # None = usa el del .env/config del extractor
    "drop_invalid": True,      # si tu extractor soporta descarte en origen

    # Inyección en BD
    "backend": "sql",              # "neo4j" | "sql"
    "bd_mode": "deterministic",    # "deterministic" | "hybrid" | "llm"
    "reset": True,                 # True: resetear BD antes de inyectar (dominio)
    "sqlite_db_path": "./data/users/demo.sqlite",

    # Overrides opcionales:
    "triplets_json_str": None,     # JSON con tripletas
    "triplets_file_path": None,    # ruta a .json / .csv / .txt compatible con tus utils.io
}

# =========================
# IMPLEMENTACIÓN
# =========================

def _load_demo_triplets() -> List[Triplet]:
    try:
        from triplets2bd.tripletas_demo import RAW_TRIPLES_DEMO4
        return RAW_TRIPLES_DEMO4
    except Exception:
        return [
            ("ana garcia", "padece", "insomnio"),
            ("carlos perez", "realiza", "yoga"),
        ]


def _load_from_overrides(json_str: Optional[str], file_path: Optional[str]) -> Optional[List[Triplet]]:
    """Carga tripletas desde JSON string o archivo si se configura en CONFIG."""
    if json_str:
        from triplets2bd.utils.io import load_triplets_from_json_str
        return load_triplets_from_json_str(json_str)
    if file_path:
        from triplets2bd.utils.io import load_triplets_from_file
        return load_triplets_from_file(file_path)
    return None


def _extract_triplets(
    text: str,
    extractor: str,
    model: Optional[str],
    drop_invalid: bool,
    print_triplets: bool
) -> List[Triplet]:
    """
    Extrae tripletas usando el extractor seleccionado.
    - extractor: 'llm' usa text2triplet.run_kg; 'kggen' usa kg_base.run_kg
    Ajusta imports si tus módulos están en otro paquete.
    """
    if extractor == "kggen":
        from text2triplets.kg_base import run_kg, KGConfig, DEFAULT_CONTEXT  # ajusta si tu path difiere
    else:
        from text2triplets.text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT  # ajusta si tu path difiere

    cfg = KGConfig(model=model) if model else None
    return run_kg(
        input_text=text,
        context=DEFAULT_CONTEXT,
        cfg=cfg,
        drop_invalid=drop_invalid,
        print_triplets=print_triplets,
    )


def _maybe_conv2text(conversation_text: str, max_sentences: int, temperature: float) -> dict:
    """
    Ejecuta conv2text si está disponible y devuelve:
      {
        "summary": <str | None>,
        "conv_llm_s": <float>,
        "conv_total_s": <float>
      }
    Nunca rompe el pipeline si hay errores (devuelve summary=None).
    """
    out = {"summary": None, "conv_llm_s": 0.0, "conv_total_s": 0.0}
    if not summarize_conv_text:
        return out

    try:
        start_total = time.perf_counter()
        start_llm = time.perf_counter()
        summary = summarize_conv_text(
            conversation_text=conversation_text,
            max_sentences=max_sentences,
            temperature=temperature,
        )
        llm_time = time.perf_counter() - start_llm
        total_time = time.perf_counter() - start_total

        out["summary"] = (summary or "").strip() or None
        out["conv_llm_s"] = llm_time
        out["conv_total_s"] = total_time
    except Exception as e:
        print(f"\n[conv2text] Aviso: no se pudo generar el resumen ({e}). Continúo con el pipeline.")
    return out


def main():
    cfg = CONFIG  # alias local

    print("=== PIPELINE: Texto Resumen → Tripletas → BD ===")
    print(f"Fuente={cfg['source']} | extractor={cfg['extractor_mode']} | backend={cfg['backend']} | modo BD={cfg['bd_mode']} | reset={'sí' if cfg['reset'] else 'no'}")

    # -------------------------
    # TIEMPOS (acumulados)
    # -------------------------
    t_start_total = time.perf_counter()
    load_time_s = 0.0
    conv_llm_time_s = 0.0
    conv_total_time_s = 0.0
    extract_time_s = 0.0
    inject_time_s = 0.0

    # 1) Resolver tripletas de entrada
    # 1.1) Overrides desde JSON/archivo
    over = _load_from_overrides(cfg.get("triplets_json_str"), cfg.get("triplets_file_path"))
    if over is not None:
        triplets_in = over
        print("\nEntrada: tripletas cargadas desde override (JSON/archivo).")
    else:
        # 1.2) Según 'source'
        if cfg["source"] == "triplets":
            triplets_in = cfg["TRIPLETS_STATIC"]
            print("\nEntrada: TRIPLETS_STATIC (source=triplets).")
        elif cfg["source"] == "demo":
            triplets_in = _load_demo_triplets()
            print("\nEntrada: RAW_TRIPLES_DEMO4 (source=demo).")
        elif cfg["source"] == "text":
            # Elegir texto
            t0_load = time.perf_counter()
            if cfg["TEXT_KEY"] and cfg["TEXT_KEY"] in ALL_TEXTS:
                conversation = ALL_TEXTS[cfg["TEXT_KEY"]]
                print(f"\nEntrada: texts['{cfg['TEXT_KEY']}']:")
            else:
                conversation = cfg["TEXT_RAW"]
                print("\nEntrada: TEXT_RAW:")
            print(conversation)
            load_time_s = time.perf_counter() - t0_load

            # (1) Ejecutar conv2text y (opcionalmente) imprimir
            conv2text_out = _maybe_conv2text(
                conversation_text=conversation,
                max_sentences=cfg.get("conv_summary_max_sentences", 10),
                temperature=cfg.get("conv_summary_temperature", 0.0),
            )
            conv_llm_time_s = conv2text_out.get("conv_llm_s", 0.0)
            conv_total_time_s = conv2text_out.get("conv_total_s", 0.0)

            # Si está habilitado en config, usar el RESUMEN como input del extractor
            if cfg.get("use_conv2text_for_extractor", True) and conv2text_out.get("summary"):
                text_for_extractor = conv2text_out["summary"]
                if cfg.get("print_conv_summary", True):
                    print("\n[conv2text] El extractor usará el RESUMEN como entrada.")
            else:
                text_for_extractor = conversation
                if cfg.get("print_conv_summary", True):
                    print("\n[conv2text] El extractor usará la CONVERSACIÓN como entrada (no hay resumen o está desactivado).")

            # (2) Texto → tripletas (extractor) con el TEXTO SELECCIONADO
            t0_extract = time.perf_counter()
            triplets_extracted = _extract_triplets(
                text=text_for_extractor,
                extractor=cfg["extractor_mode"],
                model=cfg["extractor_model"],
                drop_invalid=cfg["drop_invalid"],
                print_triplets=True,
            )
            extract_time_s = time.perf_counter() - t0_extract
            print(f"\nExtracción completada en {extract_time_s:.2f}s")
            triplets_in = triplets_extracted
        else:
            raise SystemExit("CONFIG['source'] debe ser 'text', 'triplets' o 'demo'.")

    # 4) Inyección BD
    opts = EngineOptions(
        backend=cfg["backend"],
        mode=cfg["bd_mode"],           # 'deterministic' | 'hybrid' | 'llm'
        reset=cfg["reset"],
        sqlite_db_path=cfg["sqlite_db_path"],
        reset_log=False,               # <<< IMPORTANTE: NO resetear el log desde triplets2bd
    )

    print("\nInyectando en la BD…")
    t0_inject = time.perf_counter()
    res = run_triplets_to_bd(triplets_in, opts)  # <— importante: usar triplets_in
    inject_time_s = time.perf_counter() - t0_inject

    print("\n=== RESULTADO BD ===")
    print(f"Backend={res.backend} | modo={res.mode} | reset={'sí' if res.reset else 'no'} | run_id={getattr(res, 'run_id', None)} | ejecutadas={res.executed_statements} | tiempo={inject_time_s:.2f}s")

    # Mostrar scripts/leftovers si están disponibles (útil para 'hybrid' y 'llm')
    if getattr(res, "det_script", None):
        print("\n─── Script determinista ───\n" + res.det_script)
    if getattr(res, "llm_script", None):
        print("\n─── Script LLM ───\n" + res.llm_script)
    if getattr(res, "leftovers", None):
        print("\n─── Sobrantes (no ejecutados determinista) ───")
        for (s, v, o), reason in res.leftovers:
            print(f"({s}, {v}, {o}) -> {reason}")

    # -------------------------
    # TIEMPO TOTAL PIPELINE
    # -------------------------
    total_time_s = time.perf_counter() - t_start_total
    print("\n=== TIEMPOS PIPELINE ===")
    print(f"Carga del texto: {load_time_s:.3f} s")
    if cfg.get("print_conv_summary", False):
        print(f"conv2text LLM: {conv_llm_time_s:.3f} s")
        print(f"conv2text bloque total: {conv_total_time_s:.3f} s")
    print(f"Extracción tripletas: {extract_time_s:.3f} s")
    print(f"Inyección BD: {inject_time_s:.3f} s")
    print(f"TOTAL: {total_time_s:.3f} s")

if __name__ == "__main__":
    main()
