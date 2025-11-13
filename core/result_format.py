from datetime import datetime
from time import perf_counter
from typing import Optional, Dict, Any


def _ts() -> str:
    return datetime.utcnow().isoformat() + "Z"


def make_result(*, status: str, code: str, message: str,
                command: dict, target: dict, result: Optional[dict] = None,
                diff: Optional[dict] = None, diagnostics: Optional[dict] = None,
                started: Optional[float] = None) -> dict:
    duration_ms = int((perf_counter() - started) * 1000) if started else None
    env = {
        "version": "1.0",
        "status": status,
        "code": code,
        "message": message,
        "command": command,
        "target": target,
        "result": result or {},
        "meta": {"ts": _ts()}
    }
    if duration_ms is not None: env["meta"]["duration_ms"] = duration_ms
    if diff: env["diff"] = diff
    if diagnostics: env["diagnostics"] = diagnostics
    return env


def start_timer() -> float:
    return perf_counter()

