# Factory MCP (Stage 1)

자동차 공장 생산 데이터 MCP 서버 — Open WebUI가 도구를 직접 호출.

## 아키텍처
```
User → Open WebUI (:3006) → MCP Server (:8501) → SQLite (factory.db)
```

Open WebUI에 연결된 LLM이 8개 MCP 도구를 직접 선택/호출한다.
Dify 없음. LangGraph 없음. 가장 단순한 구성.

## 기술 스택
- Python 3.12+ / `.venv/`
- FastMCP (Streamable HTTP, :8501)
- SQLite (factory.db)
- Docker: Open WebUI

## 구조
```
mcp_server.py        # MCP 서버 (:8501, 8개 도구)
config.py            # DB 설정
db/                  # DB 레이어 (schema, seed, backends)
open-webui/          # Docker Compose (Open WebUI only)
```

## 도구 8개
1. get_daily_production — 일별 생산 실적
2. get_production_summary — 기간별 요약
3. get_defect_stats — 불량 통계
4. get_line_status — 라인 현황
5. get_downtime_history — 설비 정지 이력
6. get_model_comparison — 차종별 비교
7. get_shift_analysis — 교대별 분석
8. get_production_trend — 생산 추이

## 실행
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m db.seed          # DB 생성 (최초 1회)
python mcp_server.py       # MCP 서버 (:8501)
```

## Open WebUI 연동
```bash
cd open-webui && docker compose up -d   # :3006
```
Admin → Settings → Tools → MCP Servers → `http://host.docker.internal:8501/mcp`

## DB
- 6개 테이블: production_lines, models, shifts, daily_production, defects, downtime
- 2026년 2월 가상 데이터 (seed.py)
- SQLite/Oracle 듀얼 지원 (DB_TYPE 환경변수)
