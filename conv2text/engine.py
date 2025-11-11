# conv2text/pipeline.py
from __future__ import annotations
from typing import Optional
from .io.parsers import detect_user_tag
from .llm.summarizer_text import LLMTextSummarizer
from .core.postprocess import cleanup_summary, enforce_limits

def summarize_conversation(
    conversation_text: str,
    max_sentences: int = 10,
    temperature: float = 0.0,
    target_user_tag: Optional[str] = None,
) -> str:
    """
    Orquesta el flujo: (opcional) detecta user_<nombre>, llama al LLM y aplica postproceso.
    Devuelve SOLO el texto resumen final (frases breves con sujeto explícito).
    """
    # Se puede usar detect_user_tag para depurar o fijar usuario objetivo si quisieras.
    _ = target_user_tag or detect_user_tag(conversation_text)

    summarizer = LLMTextSummarizer(temperature=temperature)
    raw = summarizer.run(conversation_text)
    cleaned = cleanup_summary(raw)
    final = enforce_limits(cleaned, max_sentences=max_sentences)
    return final
