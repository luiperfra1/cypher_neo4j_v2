# triplets2bd/utils/sql_log.py
from __future__ import annotations
import time
from typing import List, Tuple

Triplet = Tuple[str, str, str]

def ensure_sql_log_table(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            triplet TEXT,
            reason TEXT
        );
        """
    )

def reset_sql_log(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS log;")
    conn.commit()

def insert_sql_leftovers_log(conn, leftovers: List[Tuple[Triplet, str]]) -> None:
    if not leftovers:
        return
    ensure_sql_log_table(conn)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    data = [
        (now_iso, "WARN", "Tripleta fuera de formato", f"({s}, {v}, {o})", reason)
        for (s, v, o), reason in leftovers
    ]
    conn.executemany(
        "INSERT INTO log (ts, level, message, triplet, reason) VALUES (?, ?, ?, ?, ?);",
        data,
    )
    conn.commit()