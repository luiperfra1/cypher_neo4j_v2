# conv2text/tests/test_conv2text_demo.py
from __future__ import annotations

from conv2text.engine import summarize_conversation

DEMO = """LLM: ¿Qué sueles hacer para distraerte?
user_juan: Me gusta mucho salir a correr todas las mañanas.
LLM: ¿Y tomas alguna medicación?
user_juan: Tomo ibuprofeno cuando me duele la cabeza.
"""

def demo():
    out = summarize_conversation(DEMO, max_sentences=5)
    print(out)

if __name__ == "__main__":
    demo()
