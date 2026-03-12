"""Factory AI — MCP 서버 (FastMCP, Streamable HTTP :8501).

15개 MCP 도구를 카테고리별 모듈에서 등록.
  tools/production.py  — 생산 (3개)
  tools/defect.py      — 불량 (4개)
  tools/equipment.py   — 설비 (4개)
  tools/analytics.py   — 분석 (4개)
"""

from fastmcp import FastMCP
from tools import production, defect, equipment, analytics

mcp = FastMCP("FLOPI MCP")

# 각 모듈의 register()가 @mcp.tool() 데코레이터로 도구 등록
production.register(mcp)
defect.register(mcp)
equipment.register(mcp)
analytics.register(mcp)

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8501)


if __name__ == "__main__":
    main()
