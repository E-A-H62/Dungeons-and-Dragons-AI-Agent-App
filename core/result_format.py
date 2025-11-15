"""
Standardized result format utilities.

This module provides functions for creating consistent JSON response formats
across all API operations, including timing and metadata.
"""

from datetime import datetime
from time import perf_counter
from typing import Optional, Dict, Any


def _ts() -> str:
    """Generate ISO 8601 timestamp string in UTC (ending with 'Z')."""
    return datetime.utcnow().isoformat() + "Z"


def make_result(*, status: str, code: str, message: str,
                command: dict, target: dict, result: Optional[dict] = None,
                diff: Optional[dict] = None, diagnostics: Optional[dict] = None,
                started: Optional[float] = None) -> dict:
    """
    Create a standardized result dictionary for API responses.
    
    All operations return this consistent format with:
    - status: "ok", "error", or "skipped"
    - code: Operation-specific code (e.g., "CREATED", "ERROR_NOT_FOUND")
    - message: Human-readable message
    - command: Original command that triggered this result
    - target: What resource this result applies to
    - result: Operation-specific data
    - meta: Timestamp and optional duration
    - diff: Optional change tracking information
    - diagnostics: Optional warnings or logs
    """
    # Calculate execution duration if timer was started
    duration_ms = int((perf_counter() - started) * 1000) if started else None
    
    # Build base result structure
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
    
    # Add optional fields if provided
    if duration_ms is not None: env["meta"]["duration_ms"] = duration_ms
    if diff: env["diff"] = diff
    if diagnostics: env["diagnostics"] = diagnostics
    return env


def start_timer() -> float:
    """Start a performance timer (returns current time for duration calculation)."""
    return perf_counter()

