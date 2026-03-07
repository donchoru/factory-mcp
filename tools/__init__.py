"""MCP Tool 공통 유틸리티."""

import json

from db.connection import query  # noqa: F401 — 각 모듈에서 재사용


def to_json(rows: list[dict]) -> str:
    """결과를 JSON 문자열로 변환. 100행 초과 시 truncate."""
    if len(rows) > 100:
        rows = rows[:100] + [{"_truncated": f"총 {len(rows)}행 중 100행만 표시"}]
    return json.dumps(rows, ensure_ascii=False)
