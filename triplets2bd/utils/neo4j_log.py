# triplets2bd/utils/neo4j_log.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from triplets2bd.utils.neo4j_client import Neo4jClient
from triplets2bd.utils.sqlite_client import SqliteClient

Triplet = Tuple[str, str, str]

def neo4j_start_run() -> str:
    return str(uuid.uuid4())

