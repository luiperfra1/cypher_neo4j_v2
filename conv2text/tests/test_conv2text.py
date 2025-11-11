# conv2text/tests/test_conv2text.py
from __future__ import annotations
import time
from conv2text.engine import summarize_conversation
from conv2text.texts import ALL_TEXTS

def run_all_tests(max_sentences: int = 10, temperature: float = 0.0):
    print("=== TEST: conv2text → summarize_conversation ===")
    print(f"Total de textos a procesar: {len(ALL_TEXTS)}")
    print(f"Parámetros: max_sentences={max_sentences}, temperature={temperature}\n")

    total_time = 0.0
    success = 0

    for key, text in ALL_TEXTS.items():
        print(f"─── [{key}] Iniciando resumen... ───")
        start_time = time.perf_counter()
        try:
            summary = summarize_conversation(
                conversation_text=text,
                max_sentences=max_sentences,
                temperature=temperature,
            )
            elapsed = time.perf_counter() - start_time
            total_time += elapsed
            success += 1
            print(f"Conversación:\n {text}\n")
            print(f"Tiempo: {elapsed:.2f}s")
            print(f"Resumen obtenido:\n{summary.strip()}\n")

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            print(f"[ERROR en {key}] ({elapsed:.2f}s): {e}\n")

    avg_time = total_time / success if success > 0 else 0.0
    print("=== RESULTADOS GLOBALES ===")
    print(f"Casos ejecutados: {success}/{len(ALL_TEXTS)}")
    print(f"Tiempo total: {total_time:.2f}s")
    print(f"Tiempo medio por texto: {avg_time:.2f}s")

if __name__ == "__main__":
    run_all_tests(max_sentences=10, temperature=0.0)
