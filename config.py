from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    # Adapter OpenAI-compatible (opcional)
    OPENAI_API_BASE: str | None = os.getenv("OPENAI_API_BASE")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    MODEL_TRIPLETAS_CYPHER: str | None = os.getenv("MODEL_TRIPLETAS_CYPHER")

    USER_BASE_ID: str = os.getenv("USER_BASE_ID", "P001")

settings = Settings()
