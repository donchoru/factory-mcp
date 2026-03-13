# Factory MCP

> 자동차 공장 MES 데이터를 자연어로 질의하는 MCP 서버.
> Open WebUI의 LLM이 15개 도구를 직접 선택/호출합니다.

## 아키텍처

```
User → Open WebUI (:3006) ──→ MCP Server (:8501) → SQLite (factory.db)
         LLM이 도구 직접 선택      15개 SQL 도구
```

- Dify 없음 (분류기 불필요 — LLM이 직접 판단)
- LangGraph 없음 (멀티스텝 추론 불필요)
- Open WebUI의 내장 MCP 기능만 사용

## 요구사항

- **Python 3.11 이상**
- 운영체제: Windows / macOS / Linux

## 빠른 시작

### 자동 설정 (권장)

```bash
git clone https://github.com/donchoru/factory-mcp.git
cd factory-mcp
chmod +x setup.sh
./setup.sh          # venv + pip + DB seed
```

### 수동 설정

**macOS / Linux:**
```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m db.seed          # DB 생성 (60일 시뮬레이션)
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe -m db.seed
```

### 실행

**macOS / Linux:**
```bash
.venv/bin/python mcp_server.py       # MCP 서버 (:8501)
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\python.exe mcp_server.py
```

### Open WebUI (Docker)

```bash
cd open-webui && docker compose up -d    # :3006
```

## Open WebUI 설정

1. `http://localhost:3006` 접속
2. Admin → Settings → Tools → **MCP Servers**
3. Type: `MCP (Streamable HTTP)`
4. URL: `http://host.docker.internal:8501/mcp`
5. Auth Type: `None`
6. 15개 도구 자동 인식

> 시스템 프롬프트에 `현재 날짜: 2026-03-08. 데이터 범위: 2026-01-05 ~ 2026-03-05.` 추가 권장

## MCP 도구 15개

### 생산 (3)

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| `get_daily_production_summary` | 일별 라인별 생산/불량 | "2월 생산 현황" |
| `get_production_by_product` | 제품별 생산량 | "소나타 생산량" |
| `get_achievement_rate` | 라인별 목표 달성률 | "라인별 달성률 비교" |

### 불량 (4)

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| `get_defect_summary` | 라인별 불량 요약 | "라인별 불량률 비교" |
| `get_defect_by_type` | 유형별 불량 집계 | "불량 유형 분포" |
| `get_defect_by_cause` | 원인 TOP N | "불량 원인 뭐야?" |
| `get_defect_trend` | 불량률 추이 | "주별 불량 추이" |

### 설비 (4)

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| `get_defect_by_equipment` | 설비별 불량 현황 | "어떤 설비에서 불량 많아?" |
| `get_equipment_downtime` | 비가동 현황 | "설비 정지 이력" |
| `get_maintenance_history` | 정비 이력 | "설비 정비 이력 보여줘" |
| `get_process_params_anomaly` | 파라미터 이상치 | "공정 파라미터 이상 있어?" |

### 분석 (4)

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| `get_quality_inspections` | 품질 검사 현황 | "품질 검사 결과" |
| `get_material_yield` | 자재 수율 | "자재 수율 낮은 거 찾아줘" |
| `get_worker_performance` | 작업자별 실적 | "작업자별 실적 비교" |
| `get_period_comparison` | 두 기간 비교 | "1월 대비 2월 비교" |

## 구조

```
mcp_server.py           # MCP 서버 엔트리포인트 (:8501)
config.py               # DB 설정
tools/
├── __init__.py         # 공통 유틸 (query, to_json, log_call)
├── production.py       # 생산 도구 3개
├── defect.py           # 불량 도구 4개
├── equipment.py        # 설비 도구 4개
└── analytics.py        # 분석 도구 4개
db/
├── schema.sql          # 14 테이블 DDL + 마스터 INSERT
├── seed.py             # 60일 시뮬레이션 데이터
├── connection.py       # 브릿지 패턴 (SQLite/Oracle 자동 전환)
└── backends/
    ├── sqlite.py
    └── oracle.py
open-webui/
└── docker-compose.yml  # Open WebUI Docker
```

## DB 구조

### 마스터 (5)

| 테이블 | 건수 | 설명 |
|--------|------|------|
| PRODUCTION_LINES | 5 | BODY/PAINT/ASSEMBLY/ENGINE/QC |
| PRODUCTS | 5 | 소나타/아반떼/투싼/그랜저/아이오닉5 |
| EQUIPMENT | 20 | ROBOT/PRESS/SPRAY/CONVEYOR/TESTER |
| WORKERS | 30 | JUNIOR/MIDDLE/SENIOR |
| SHIFTS | 3 | 주간/야간/잔업 |

### 트랜잭션 (5)

| 테이블 | 건수 | 설명 |
|--------|------|------|
| WORK_ORDERS | ~600 | 작업지시 |
| PRODUCTION_LOG | ~1500 | 생산실적 |
| DEFECT_RECORDS | ~1600 | 불량상세 |
| EQUIPMENT_DOWNTIME | ~90 | 설비비가동 |
| QUALITY_INSPECTIONS | ~1500 | 품질검사 |

### 분석 (4)

| 테이블 | 건수 | 설명 |
|--------|------|------|
| PROCESS_PARAMS | - | 공정파라미터 (온도/압력/속도) |
| MATERIAL_USAGE | - | 자재사용 (계획 vs 실투입) |
| MAINTENANCE_HISTORY | ~70 | 정비이력 |
| DAILY_PRODUCTION_SUMMARY | ~300 | 일별요약 |

## 데모 시나리오

- 데이터 기간: **2026-01-05 ~ 2026-03-05** (60일)
- 도장 라인 불량 스파이크: 2주차(1/19~)부터 불량률 급등
- 원인: **스프레이건 노즐 마모** (60%)
- 데모 질문 흐름:
  1. "2월 라인별 불량률 비교해줘" → 도장 라인 1위
  2. "도장 불량 원인이 뭐야?" → 노즐 마모 60%

## Oracle 지원

`.env` 파일에서 DB_TYPE을 변경하면 Oracle로 전환됩니다:

```env
DB_TYPE=oracle
ORACLE_DSN=localhost:1521/XEPDB1
ORACLE_USER=factory
ORACLE_PASSWORD=factory123
```
