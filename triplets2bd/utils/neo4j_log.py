# triplets2bd/utils/neo4j_log.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional

Triplet = Tuple[str, str, str]

def neo4j_start_run() -> str:
    return str(uuid.uuid4())

def neo4j_log_leftovers(db, leftovers: List[Tuple[Triplet, str]], run_id: str, backend: str, mode: str) -> int:
    if not leftovers:
        return 0
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stmts = []
    seen = set()
    for (s, v, o), reason in leftovers:
        key = (s, v, o, reason)
        if key in seen:
            continue
        seen.add(key)
        params = {
            "run_id": run_id,
            "ts": ts,
            "backend": backend,
            "mode": mode,
            "level": "WARN",
            "message": "Tripleta fuera de formato",
            "triplet": f"({s}, {v}, {o})",
            "reason": reason,
        }
        cypher = (
            "MERGE (l:Log {run_id:$run_id, triplet:$triplet, reason:$reason}) "
            "ON CREATE SET l.ts=$ts, l.backend=$backend, l.mode=$mode, "
            "l.level=$level, l.message=$message"
        )
        stmts.append((cypher, params))
    if stmts:
        db.write_many(stmts)
    return len(stmts)