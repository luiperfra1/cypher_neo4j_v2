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
    "TEXT_RAW": "Carlos toma ibuprofeno cuando duele. Carlos realiza yoga varias veces por semana.",

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


def main():
    cfg = CONFIG  # alias local

    print("=== PIPELINE: Texto Resumen → Tripletas → BD ===")
    print(f"Fuente={cfg['source']} | extractor={cfg['extractor_mode']} | backend={cfg['backend']} | modo BD={cfg['bd_mode']} | reset={'sí' if cfg['reset'] else 'no'}")

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
            if cfg["TEXT_KEY"] and cfg["TEXT_KEY"] in ALL_TEXTS:
                text = ALL_TEXTS[cfg["TEXT_KEY"]]
                print(f"\nEntrada: texts['{cfg['TEXT_KEY']}']:")
            else:
                text = cfg["TEXT_RAW"]
                print("\nEntrada: TEXT_RAW:")
            print(text)

            # 2) Texto → tripletas (extractor)
            t0 = time.time()
            triplets_extracted = _extract_triplets(
                text=text,
                extractor=cfg["extractor_mode"],
                model=cfg["extractor_model"],
                drop_invalid=cfg["drop_invalid"],
                print_triplets=True,
            )
            print(f"\nExtracción completada en {time.time() - t0:.2f}s")
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
    t1 = time.perf_counter()
    res = run_triplets_to_bd(triplets_in, opts)  # <— importante: usar triplets_in
    elapsed = time.perf_counter() - t1

    print("\n=== RESULTADO BD ===")
    print(f"Backend={res.backend} | modo={res.mode} | reset={'sí' if res.reset else 'no'} | run_id={getattr(res, 'run_id', None)} | ejecutadas={res.executed_statements} | tiempo={elapsed:.2f}s")

    # Mostrar scripts/leftovers si están disponibles (útil para 'hybrid' y 'llm')
    if getattr(res, "det_script", None):
        print("\n─── Script determinista ───\n" + res.det_script)
    if getattr(res, "llm_script", None):
        print("\n─── Script LLM ───\n" + res.llm_script)
    if getattr(res, "leftovers", None):
        print("\n─── Sobrantes (no ejecutados determinista) ───")
        for (s, v, o), reason in res.leftovers:
            print(f"({s}, {v}, {o}) -> {reason}")


if __name__ == "__main__":
    main()
