# conv2text/main_conv2text.py
from __future__ import annotations
import argparse
import sys
import time
from .engine import summarize_conversation
from .io.files import read_text_file, write_text_file
from .texts import ALL_TEXTS

def _read_input(path: str | None) -> str:
    if path and path != "-":
        return read_text_file(path)
    return sys.stdin.read()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Conv2Text: resume conversaciones (LLM) en frases breves con sujeto explícito."
    )
    parser.add_argument("--in", dest="inpath", default="-",
                        help="Ruta del archivo de conversación (o '-' para stdin). Ignorado si usas --text-key.")
    parser.add_argument("--out", dest="outpath", default=None,
                        help="Ruta de salida del resumen (opcional). Si no, imprime en consola.")
    parser.add_argument("--max", dest="max_sentences", type=int, default=10,
                        help="Máximo de frases del resumen.")
    parser.add_argument("--temp", dest="temperature", type=float, default=0.0,
                        help="Temperatura del LLM (0.0 por defecto).")
    parser.add_argument("--text-key", dest="text_key", default=None,
                        help="Clave de ejemplo: TEXT1, TEXT2, ... (usa conv2text/texts.py).")
    parser.add_argument("--list-texts", action="store_true",
                        help="Lista las claves disponibles y termina.")

    args = parser.parse_args()

    if args.list_texts:
        keys = sorted(ALL_TEXTS.keys(), key=lambda k: (len(k), k))
        sys.stdout.write("Textos disponibles:\n")
        for k in keys:
            sys.stdout.write(f"- {k}\n")
        return

    start_total = time.perf_counter()

    start_load = time.perf_counter()
    if args.text_key:
        if args.text_key not in ALL_TEXTS:
            sys.stderr.write(f"[conv2text] Clave no encontrada: {args.text_key}\n")
            sys.stderr.write("Usa --list-texts para ver opciones.\n")
            sys.exit(1)
        conversation = ALL_TEXTS[args.text_key]
    else:
        conversation = _read_input(args.inpath)
    load_time = time.perf_counter() - start_load

    start_llm = time.perf_counter()
    summary = summarize_conversation(
        conversation_text=conversation,
        max_sentences=args.max_sentences,
        temperature=args.temperature,
    )
    llm_time = time.perf_counter() - start_llm

    total_time = time.perf_counter() - start_total

    # Si hay --out, guardamos solo resumen
    if args.outpath:
        write_text_file(args.outpath, summary + ("\n" if not summary.endswith("\n") else ""))
        return

    # Si no hay --out → imprimir conversación + resumen + tiempos
    print("--- CONVERSACIÓN ---")
    print(conversation.strip())
    print("\n--- RESUMEN ---")
    print(summary.strip())

    print("\n--- TIEMPOS ---")
    print(f"Carga del texto: {load_time:.3f} s")
    print(f"LLM: {llm_time:.3f} s")
    print(f"Total: {total_time:.3f} s")

if __name__ == "__main__":
    main()
