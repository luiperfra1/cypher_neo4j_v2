# main_kg.py
from __future__ import annotations
import argparse
import time


def main():
    print("Iniciando ejecución…")
    t_import = time.time()

    # Primero parseamos mode para decidir qué importar
    parser_pre = argparse.ArgumentParser(add_help=False)
    parser_pre.add_argument("--mode", choices=["llm", "kggen"], default="llm")
    args_pre, _ = parser_pre.parse_known_args()

    mode = args_pre.mode

    # Lazy import en función del modo seleccionado
    if mode == "kggen":
        from .kg_base import run_kg, KGConfig, DEFAULT_CONTEXT
        mode_used = "KG-BASE (OpenAI-compatible)"
    else:
        from .text2triplet import run_kg, KGConfig, DEFAULT_CONTEXT
        mode_used = "LLM (text2triplet)"

    from .texts import ALL_TEXTS

    print(f"Dependencias cargadas en {time.time() - t_import:.2f}s")
    print(f"Modo seleccionado: {mode_used}\n")

    # Parser principal
    parser = argparse.ArgumentParser(
        description="Extrae tripletas con un LLM (modo 'llm') o con el extractor compatible KG-Base (modo 'kggen')."
    )

    parser.add_argument("--mode", choices=["llm", "kggen"], default=mode,
                        help="Modo de extracción: llm (por defecto) o kggen.")
    parser.add_argument("--text", default="TEXT1",
                        help="Nombre del texto (por defecto: TEXT1). Opciones: " + ", ".join(ALL_TEXTS.keys()))
    parser.add_argument("--model", default=None,
                        help="Sobrescribe el modelo (si no, usa el del .env/KGConfig).")
    parser.add_argument("--context", default=DEFAULT_CONTEXT,
                        help="Contexto/ontología a aplicar.")
    parser.add_argument("--no-drop", action="store_true",
                        help="No descartar tripletas inválidas (se mostrarán igual).")

    args = parser.parse_args()

    if args.text not in ALL_TEXTS:
        raise SystemExit(f"Texto '{args.text}' no encontrado. Opciones: {', '.join(ALL_TEXTS.keys())}")

    selected_text = ALL_TEXTS[args.text]
    cfg = KGConfig(model=args.model) if args.model else None

    print("=== INICIANDO EXTRACCIÓN ===")
    print(f"Texto: {args.text} | Modo: {args.mode} ")
    print("\nGenerando tripletas...\n")

    t0 = time.time()

    triplets = run_kg(
        input_text=selected_text,
        context=args.context,
        cfg=cfg,
        drop_invalid=not args.no_drop,
        print_triplets=True
    )

    print(f"Tiempo total: {time.time() - t0:.2f}s")
    print("=== PROCESO COMPLETADO ===")


if __name__ == "__main__":
    main()
