from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Literal, Optional, Dict, Any

Triplet = Tuple[str, str, str]
Backend = Literal["sql", "neo4j"]
Mode = Literal["hybrid", "llm", "deterministic"]

@dataclass
class EngineOptions:
    backend: Backend = "sql"
    mode: Mode = "hybrid"
    reset: bool = True
    sqlite_db_path: str = "./data/users/demo.sqlite"

@dataclass
class EngineResult:
    backend: Backend
    mode: Mode
    run_id: Optional[str]
    det_script: str
    llm_script: str
    executed_statements: int
    leftovers: List[Tuple[Triplet, str]]
    reset: bool                     # ← NUEVO
    extras: Dict[str, Any]