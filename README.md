# Factory MCP (Stage 1)

> 자동차 공장 생산 데이터를 자연어로 질의하는 MCP 서버.
> Open WebUI의 LLM이 8개 도구를 직접 선택/호출합니다.

## 아키텍처

```
User → Open WebUI (:3006) ──→ MCP Server (:8501) → SQLite (factory.db)
         LLM이 도구 직접 선택      8개 SQL 도구
```

**Stage 1**은 가장 단순한 구성입니다:
- Dify 없음 (분류기 불필요 — LLM이 직접 판단)
- LangGraph 없음 (멀티스텝 추론 불필요)
- Open WebUI의 내장 MCP 기능만 사용

## 빠른 시작

```bash
# 1. 환경 설정
git clone https://github.com/donchoru/factory-mcp.git
cd factory-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. DB 생성
python -m db.seed

# 3. MCP 서버 시작
python mcp_server.py    # :8501

# 4. Open WebUI 시작 (Docker)
cd open-webui && docker compose up -d    # :3006
```

## Open WebUI 설정

1. `http://localhost:3006` 접속
2. Admin → Settings → Tools → **MCP Servers**
3. URL: `http://host.docker.internal:8501/mcp`
4. 8개 도구 자동 인식

## MCP 도구 8개

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| `get_daily_production` | 일별 생산 실적 | "2월 15일 1라인 생산량" |
| `get_production_summary` | 기간별 요약 | "이번 달 생산 현황" |
| `get_defect_stats` | 불량 통계 | "3라인 불량률" |
| `get_line_status` | 라인 현황 | "라인 상태 보여줘" |
| `get_downtime_history` | 설비 정지 이력 | "이번 달 정지 이력" |
| `get_model_comparison` | 차종별 비교 | "차종별 생산량 비교" |
| `get_shift_analysis` | 교대별 분석 | "교대별 달성률 비교" |
| `get_production_trend` | 생산 추이 | "최근 생산 추이" |

## 파라미터 매핑

| 한국어 | ID |
|--------|-----|
| 1라인, 세단라인 | LINE-1 |
| 2라인, SUV라인 | LINE-2 |
| 3라인, EV라인 | LINE-3 |
| 소나타 | SONATA |
| 투싼 | TUCSON |
| GV70, 제네시스 | GV70 |
| 아이오닉6 | IONIQ6 |
| 주간 | DAY |
| 야간 | NIGHT |
| 심야 | MIDNIGHT |

## DB 구조

6개 테이블, 2026년 2월 가상 생산 데이터:

| 테이블 | 행 수 | 설명 |
|--------|-------|------|
| production_lines | 3 | LINE-1/2/3 |
| models | 4 | SONATA/TUCSON/GV70/IONIQ6 |
| shifts | 3 | DAY/NIGHT/MIDNIGHT |
| daily_production | ~252 | 일별 생산 실적 |
| defects | ~170 | 불량 상세 |
| downtime | ~18 | 설비 정지 이력 |

## Oracle 지원

`.env` 파일에서 DB_TYPE을 변경하면 Oracle로 전환됩니다:

```env
DB_TYPE=oracle
ORACLE_DSN=localhost:1521/XEPDB1
ORACLE_USER=factory
ORACLE_PASSWORD=factory123
```

## 다음 단계

- **Stage 2** ([factory-dify](https://github.com/donchoru/factory-dify)): Dify 2분류 추가
- **Stage 3** ([factory-agent](https://github.com/donchoru/factory-agent)): LangGraph 멀티에이전트 추가
