# Factory MCP — 교육자 매뉴얼

> 자동차 공장 MES 데이터를 자연어로 질의하는 시스템의 전체 구조와 동작 원리.
> Open WebUI + Ollama + MCP 순수 구조.

---

## 목차

1. [시스템 전체 구조](#1-시스템-전체-구조)
2. [데이터 흐름 — 질문에서 답변까지](#2-데이터-흐름--질문에서-답변까지)
3. [계층 1: Open WebUI (프론트엔드)](#3-계층-1-open-webui-프론트엔드)
4. [계층 2: Ollama + qwen2.5:14b (LLM)](#4-계층-2-ollama--qwen2514b-llm)
5. [계층 3: MCP 서버 (도구 실행)](#5-계층-3-mcp-서버-도구-실행)
6. [계층 4: SQLite (데이터베이스)](#6-계층-4-sqlite-데이터베이스)
7. [MCP 도구 15개 상세](#7-mcp-도구-15개-상세)
8. [Outlet 필터 — 후속 질문 자동 제안](#8-outlet-필터--후속-질문-자동-제안)
9. [모델 프리셋과 시스템 프롬프트](#9-모델-프리셋과-시스템-프롬프트)
10. [저장 프롬프트 (/ 명령어)](#10-저장-프롬프트--명령어)
11. [시각화 (Vega-Lite + Mermaid)](#11-시각화-vega-lite--mermaid)
12. [DB 스키마와 시뮬레이션 데이터](#12-db-스키마와-시뮬레이션-데이터)
13. [설치 및 실행 가이드](#13-설치-및-실행-가이드)
14. [Admin Panel 설정 (1회)](#14-admin-panel-설정-1회)
15. [파일 맵](#15-파일-맵)

---

## 1. 시스템 전체 구조

```
┌──────────────────────────────────────────────────────┐
│                    사용자 (브라우저)                      │
│                  http://localhost:3009                 │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP
                       ▼
┌──────────────────────────────────────────────────────┐
│           Open WebUI (Docker 컨테이너)                  │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ 채팅 UI     │  │ 모델 프리셋  │  │ Outlet 필터  │ │
│  │ 시작 칩     │  │ 시스템프롬프트│  │ 후속질문 매핑 │ │
│  │ 저장 프롬프트│  │ Temperature │  │ (키워드기반)  │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
└──────────────────────┬───────────────────────────────┘
                       │ Ollama API (HTTP)
                       ▼
┌──────────────────────────────────────────────────────┐
│              Ollama (Mac 호스트 :11434)                 │
│                                                      │
│         qwen2.5:14b (Tool Calling 지원)               │
│         - 의도 파악                                    │
│         - MCP 도구 선택 + 호출                         │
│         - 결과 해석 + 응답 생성                         │
└──────────────────────┬───────────────────────────────┘
                       │ Streamable HTTP
                       ▼
┌──────────────────────────────────────────────────────┐
│             MCP 서버 (Mac 호스트 :8501)                 │
│                                                      │
│  FastMCP — 15개 @mcp.tool()                           │
│  ┌───────────┬───────────┬───────────┬─────────────┐ │
│  │ 생산 (3)  │ 불량 (4)  │ 설비 (4)  │ 분석 (4)    │ │
│  └─────┬─────┴─────┬─────┴─────┬─────┴──────┬──────┘ │
└────────┼───────────┼───────────┼────────────┼────────┘
         │           │           │            │
         ▼           ▼           ▼            ▼
┌──────────────────────────────────────────────────────┐
│              SQLite (factory.db)                      │
│                                                      │
│  마스터 5 + 트랜잭션 5 + 분석 4 = 14 테이블            │
│  60일 시뮬레이션 데이터 (~5,000건)                     │
└──────────────────────────────────────────────────────┘
```

**핵심 원칙**: LLM이 직접 SQL을 작성하지 않는다. 미리 정의된 15개 MCP 도구를 호출할 뿐이다.

---

## 2. 데이터 흐름 — 질문에서 답변까지

사용자가 "오늘 전체 라인 생산 현황 알려줘"를 입력했을 때:

```
[1] 사용자 → Open WebUI
    "오늘 전체 라인 생산 현황 알려줘"

[2] Open WebUI → Ollama (qwen2.5:14b)
    시스템 프롬프트 + 사용자 메시지 + 사용 가능한 도구 목록 15개 전달

[3] Ollama (qwen2.5:14b) — 의도 파악
    "생산 현황 → get_daily_production_summary 도구를 호출해야겠다"
    → tool_call: get_daily_production_summary(date_start="2026-03-09", date_end="2026-03-09")

[4] Open WebUI → MCP 서버 (:8501)
    도구 호출 요청 전달 (Streamable HTTP)

[5] MCP 서버 → SQLite
    SQL 실행:
    SELECT 날짜, 라인, 라인명, SUM(생산량), SUM(불량수), 불량률
    FROM PRODUCTION_LOG JOIN WORK_ORDERS JOIN PRODUCTION_LINES
    WHERE order_date BETWEEN '2026-03-09' AND '2026-03-09'
    GROUP BY ...

[6] SQLite → MCP 서버
    JSON 결과: [{"날짜": "2026-03-09", "라인": "BODY", "생산량": 450, ...}, ...]

[7] MCP 서버 → Ollama
    도구 실행 결과 반환

[8] Ollama — 응답 생성
    시스템 프롬프트의 규칙에 따라:
    - 마크다운 표로 정리
    - 달성률 90% 미만 → ⚠️ 주의 표시
    - 불량률 2% 이상 → 🚨 경고 표시

[9] Open WebUI — Outlet 필터 실행
    응답 텍스트에서 "생산" 키워드 감지
    → 미리 정의된 후속 질문 4개 추가:
      "불량률 TOP 3는?", "교대별 비교해줘", ...

[10] Open WebUI → 사용자
     마크다운 표 + 경고 아이콘 + 후속 질문 제안 표시
```

### 멀티턴 대화

```
[턴 1] 사용자: "오늘 생산 현황"
       → get_daily_production_summary → 표 응답 + 후속 질문 4개

[턴 2] 사용자: "불량률 TOP 3는?" (후속 질문 클릭)
       → Ollama는 [턴 1]의 대화 히스토리를 모두 받음
       → get_defect_summary 호출 → 불량 분석 응답 + 새로운 후속 질문 4개

[턴 3] 사용자: "원인별로 분석해줘"
       → [턴 1]+[턴 2] 히스토리 포함
       → get_defect_by_cause 호출 → 원인 TOP N + 후속 질문 4개
```

Open WebUI가 대화 히스토리를 관리하므로 별도 세션 관리가 필요 없다.

---

## 3. 계층 1: Open WebUI (프론트엔드)

### 역할
- 채팅 UI 제공 (웹 브라우저)
- 사용자 인증 (로그인/회원가입)
- 대화 히스토리 관리 (멀티턴)
- MCP 서버 연결 관리
- 모델 프리셋 / 저장 프롬프트 관리
- Outlet 필터 실행 (후속 질문 주입)
- Vega-Lite 차트 인라인 렌더링

### Docker 설정 (`open-webui/docker-compose.yml`)

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: factory-open-webui
    ports:
      - "3009:8080"              # 브라우저 접속 포트
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434   # Ollama 직접 연결
      WEBUI_SECRET_KEY: factory-mcp-secret-2026            # JWT 비밀키
      ENABLE_FOLLOW_UP_GENERATION: "true"                  # 후속 질문 생성 활성화
      TASK_MODEL: qwen2.5:14b                              # 후속 질문 생성용 모델
      FOLLOW_UP_GENERATION_PROMPT_TEMPLATE: >              # 후속 질문 프롬프트
        (공장 맞춤 프롬프트 — 한국어, JSON 배열 반환)
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Docker → Mac 호스트 통신
    volumes:
      - open-webui-data:/app/backend/data     # 설정/대화 영구 저장
```

**핵심 환경변수:**

| 변수 | 값 | 설명 |
|------|-----|------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Docker 컨테이너에서 Mac의 Ollama에 접근 |
| `TASK_MODEL` | `qwen2.5:14b` | 후속 질문 / 제목 생성에 사용할 모델 |
| `ENABLE_FOLLOW_UP_GENERATION` | `true` | 답변 후 후속 질문 자동 생성 |
| `extra_hosts` | `host.docker.internal:host-gateway` | Docker 내부에서 호스트 IP 해석 |

### 왜 Docker인가?
Open WebUI는 Python(FastAPI) + Svelte 앱이다. Docker 이미지로 배포되어 의존성 관리 없이 한 줄로 실행 가능.

---

## 4. 계층 2: Ollama + qwen2.5:14b (LLM)

### 역할
- 자연어 이해 (사용자 의도 파악)
- **Tool Calling** — 적절한 MCP 도구 선택 + 파라미터 결정
- 도구 결과를 해석하여 사람이 읽기 좋은 응답 생성
- 시스템 프롬프트에 따른 형식 지정 (표, 경고 아이콘, 차트)

### Tool Calling 동작

Ollama는 Open WebUI로부터 다음을 받는다:
```json
{
  "model": "qwen2.5:14b",
  "messages": [
    {"role": "system", "content": "(시스템 프롬프트)"},
    {"role": "user", "content": "오늘 생산 현황 알려줘"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_daily_production_summary",
        "description": "일별 라인별 생산 현황 조회",
        "parameters": {
          "type": "object",
          "properties": {
            "date_start": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
            "date_end": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
            "line_type": {"type": "string", "description": "라인 타입 필터"}
          },
          "required": ["date_start", "date_end"]
        }
      }
    }
    // ... 15개 도구 모두 전달
  ]
}
```

LLM이 도구가 필요하다고 판단하면:
```json
{
  "tool_calls": [{
    "function": {
      "name": "get_daily_production_summary",
      "arguments": "{\"date_start\": \"2026-03-09\", \"date_end\": \"2026-03-09\"}"
    }
  }]
}
```

### 왜 qwen2.5:14b인가?
- M4 Pro 24GB에서 쾌적하게 동작하는 최대 크기
- **한국어 성능 우수** (Qwen 계열 강점)
- Tool Calling / Function Calling 네이티브 지원
- 9.0GB VRAM — 로컬 추론 가능

---

## 5. 계층 3: MCP 서버 (도구 실행)

### MCP란?

**Model Context Protocol** — Anthropic이 제안한 표준 프로토콜.
LLM이 외부 도구(DB, API, 파일 등)를 호출할 수 있게 하는 인터페이스.

```
LLM ←→ MCP 클라이언트 (Open WebUI) ←→ MCP 서버 (:8501) ←→ DB
```

### FastMCP

Python으로 MCP 서버를 빠르게 구축하는 라이브러리.
`@mcp.tool()` 데코레이터로 함수를 MCP 도구로 노출.

### 서버 코드 (`mcp_server.py`)

```python
from fastmcp import FastMCP
from tools import production, defect, equipment, analytics

mcp = FastMCP("Factory AI")

# 각 모듈이 mcp에 도구 등록
production.register(mcp)    # 3개
defect.register(mcp)        # 4개
equipment.register(mcp)     # 4개
analytics.register(mcp)     # 4개

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8501)
```

### 도구 등록 패턴 (예: `tools/production.py`)

```python
def register(mcp):
    @mcp.tool()
    def get_daily_production_summary(
        date_start: str,
        date_end: str,
        line_type: str = "",
    ) -> str:
        """일별 라인별 생산 현황 조회 — 생산량, 불량수, 불량률.

        Args:
            date_start: 시작일 (YYYY-MM-DD)
            date_end: 종료일 (YYYY-MM-DD)
            line_type: 라인 타입 필터 (BODY/PAINT/ASSEMBLY/ENGINE/QC). 빈 문자열이면 전체.
        """
        sql = """
        SELECT 날짜, 라인, 라인명, SUM(생산량), SUM(불량수), 불량률
        FROM PRODUCTION_LOG
        JOIN WORK_ORDERS ...
        WHERE order_date BETWEEN ? AND ?
        """
        params = [date_start, date_end]
        if line_type:
            sql += " AND pline.line_type = ?"
            params.append(line_type.upper())
        return to_json(query(sql, tuple(params)))
```

**핵심 포인트:**
- `docstring`이 LLM에게 전달되는 도구 설명이 됨
- `Args` 섹션이 파라미터 설명이 됨
- 반환값은 항상 JSON 문자열
- SQL은 미리 작성된 것 — LLM이 SQL을 생성하지 않음 (보안)

### DB 연결 — 브릿지 패턴 (`db/connection.py`)

```python
from db.backends import get_backend

def query(sql, params=()):
    return get_backend().query(sql, params)  # → list[dict]
```

`get_backend()`가 `config.py`의 `DB_TYPE`에 따라 SQLite 또는 Oracle 백엔드를 반환.
도구 코드는 DB 종류를 몰라도 된다.

### 유틸리티 (`tools/__init__.py`)

```python
def to_json(rows: list[dict]) -> str:
    """결과를 JSON 문자열로 변환. 100행 초과 시 truncate."""
    if len(rows) > 100:
        rows = rows[:100] + [{"_truncated": f"총 {len(rows)}행 중 100행만 표시"}]
    return json.dumps(rows, ensure_ascii=False)
```

100행 제한은 LLM 컨텍스트 윈도우 보호를 위한 것.

---

## 6. 계층 4: SQLite (데이터베이스)

### 파일: `factory.db`
`python -m db.seed`로 생성. 14 테이블 + 60일 시뮬레이션 데이터.

### ER 다이어그램 (간략)

```
PRODUCTION_LINES ─┬─ WORK_ORDERS ─── PRODUCTION_LOG ─┬─ DEFECT_RECORDS
(5 라인)          │  (작업지시)      (생산실적)        │  (불량상세)
                  │                                   │
PRODUCTS ─────────┘                                   ├─ QUALITY_INSPECTIONS
(5 제품)                                              │  (품질검사)
                                                      │
EQUIPMENT ─────── EQUIPMENT_DOWNTIME                  ├─ PROCESS_PARAMS
(20 설비)         (비가동이력)                          │  (공정파라미터)
    │
    └──────────── MAINTENANCE_HISTORY                  MATERIAL_USAGE
                  (정비이력)                            (자재사용)

WORKERS ──────────────────────────────────────────────
(30 작업자)

SHIFTS
(3교대)

DAILY_PRODUCTION_SUMMARY
(일별요약)
```

### 데이터 시나리오
- **기간**: 2026-01-05 ~ 2026-03-05 (60일)
- **도장 라인 불량 스파이크**: 2주차(1/19~)부터 불량률 급등
  - 원인: 스프레이건 노즐 마모 (60%)
  - 데모: "도장 불량률이 왜 높아?" → `get_defect_summary` → `get_defect_by_cause` → "노즐 마모"

---

## 7. MCP 도구 15개 상세

### 생산 (3개)

| 도구 | 설명 | 주요 파라미터 |
|------|------|-------------|
| `get_daily_production_summary` | 일별 라인별 생산/불량/불량률 | date_start, date_end, line_type |
| `get_production_by_product` | 제품별 생산량 | date_start, date_end, product_code |
| `get_achievement_rate` | 라인별 목표 달성률 | date_start, date_end, line_type |

### 불량 (4개)

| 도구 | 설명 | 주요 파라미터 |
|------|------|-------------|
| `get_defect_summary` | 라인별 불량 요약 | date_start, date_end, line_type, product_code |
| `get_defect_by_type` | 유형별 불량 집계 (APPEARANCE/DIMENSION/FUNCTION/PAINT/WELD) | date_start, date_end, line_type |
| `get_defect_by_cause` | 원인 TOP N | date_start, date_end, line_type, top_n |
| `get_defect_trend` | 일별/주별/월별 불량률 추이 | date_start, date_end, group_by, line_type |

### 설비 (4개)

| 도구 | 설명 | 주요 파라미터 |
|------|------|-------------|
| `get_defect_by_equipment` | 설비별 불량 현황 | date_start, date_end, line_type |
| `get_equipment_downtime` | 비가동 현황 (사유별) | date_start, date_end, line_type, reason_code |
| `get_maintenance_history` | 정비 이력 | date_start, date_end, equip_id, top_n |
| `get_process_params_anomaly` | 공정 파라미터 이상치 | date_start, date_end, equip_id |

### 분석 (4개)

| 도구 | 설명 | 주요 파라미터 |
|------|------|-------------|
| `get_quality_inspections` | 품질 검사 현황 | date_start, date_end, inspection_type, result |
| `get_material_yield` | 자재 수율 (계획 vs 실투입) | date_start, date_end, product_code |
| `get_worker_performance` | 작업자별 실적 | date_start, date_end, line_type |
| `get_period_comparison` | 두 기간 비교 | period_a/b_start/end, line_type |

---

## 8. Outlet 필터 — 후속 질문 자동 제안

### 왜 Outlet인가?

Open WebUI의 Function 시스템은 **Inlet/Outlet 패턴**을 제공:

```
사용자 입력 → [Inlet] → LLM → [Outlet] → 사용자 표시
               전처리            후처리
```

- **Inlet**: LLM에 보내기 전에 메시지를 가공 (컨텍스트 추가, 필터링 등)
- **Outlet**: LLM 답변 후에 후처리 (후속 질문 추가, 포맷 변경 등)

### 동작 원리 (`open-webui/factory_followup.py`)

```
[LLM 답변 완료]
      │
      ▼
[Outlet 호출] body = { messages: [..., {role: "assistant", content: "생산 실적은..."}] }
      │
      ▼
[키워드 분류] "생산", "실적" 감지 → topic = "production"
      │
      ▼
[매핑 조회] production → ["불량률 TOP 3는?", "교대별 비교해줘", ...]
      │
      ▼
[메시지 수정] assistant 메시지 끝에 후속 질문 블록 추가
      │
      ▼
[반환] → Open WebUI가 수정된 메시지를 렌더링
```

### 주제 매핑 (8개)

| 주제 | 감지 키워드 | 후속 질문 |
|------|------------|----------|
| **생산** | 생산, 실적, 달성률, 목표 | 불량률 TOP 3는? / 교대별 비교 / 전주 대비 변화 / 제품별 비중 |
| **불량** | 불량, 결함, NG | 원인별 분석 / 설비별 현황 / 2주 추이 차트 / 정비 이력 |
| **설비** | 설비, 정지, 다운타임, 정비 | 정비 이력 / 파라미터 이상치 / 설비별 불량 / 가동률 추이 |
| **품질** | 품질, 검사, QC | 유형별 집계 / 합격률 비교 / 품질 추이 / 자재 수율 |
| **교대** | 교대, 주간, 야간, 잔업 | 교대별 불량률 / 야간 생산성 / 교대별 추이 / 작업자 실적 |
| **추이** | 추이, 트렌드, 차트 | 라인별 분리 / 불량률 추이 / 전월 대비 / 가동률 추이 |
| **작업자** | 작업자, 성과 | 숙련도별 비교 / 투입 인원 / 불량률 비교 / 인원 배치 |
| **자재** | 자재, 수율 | 수율 낮은 라인 / 제품별 사용량 / 수율 추이 / 상관관계 |

### LLM 생성 vs 결정론적 매핑

| 특성 | LLM 생성 (기본) | Outlet 매핑 (우리 방식) |
|------|-----------------|----------------------|
| 속도 | 느림 (LLM 추가 호출) | 즉시 (키워드 매칭) |
| 예측 가능성 | 매번 다름 | 항상 동일 |
| 도메인 적합성 | 가끔 엉뚱한 질문 | 전문가가 설계한 질문 |
| 유지보수 | 프롬프트 수정 | Python 코드 수정 |
| 비용 | 토큰 소비 | 0 |

### 수정 방법

`factory_followup.py`의 `self.topic_rules` 리스트를 편집:

```python
{
    "id": "새주제",
    "keywords": ["키워드1", "키워드2"],
    "followups": [
        "후속 질문 1",
        "후속 질문 2",
        "후속 질문 3",
        "후속 질문 4",
    ],
},
```

수정 후 Open WebUI Functions 페이지에서 코드를 업데이트하면 즉시 반영.

---

## 9. 모델 프리셋과 시스템 프롬프트

### 모델 프리셋 (`open-webui/model_preset.json`)

Open WebUI의 "커스텀 모델" — 기본 모델을 감싸는 설정 래퍼:

```
"Factory MES 분석가" (프리셋)
    ├── Base Model: qwen2.5:14b
    ├── System Prompt: (공장 도메인 컨텍스트)
    ├── Temperature: 0.3 (정확성 중시)
    ├── Tools: MCP 15개 도구
    ├── Filter: factory_followup (Outlet)
    └── Prompt Suggestions: 시작 질문 칩 5개
```

### 시스템 프롬프트 구성

시스템 프롬프트는 **4개 섹션**으로 나뉜다:

**1. 도메인 컨텍스트** — LLM에게 "너는 누구인가"를 알려줌
```
당신은 자동차 공장 MES 데이터 분석 전문가입니다.
- 오늘 날짜: {{CURRENT_DATE}}
- 데이터 기간: 2026-01-05 ~ {{CURRENT_DATE}}
```

**2. 공장 정보** — 라인/제품/교대 매핑
```
- BODY: 차체라인 — 프레스·용접·조립
- PAINT: 도장라인 — 전착·중도·상도
...
- SONATA(소나타), AVANTE(아반떼), TUCSON(투싼), ...
- DAY: 주간 (06:00-14:00), NIGHT: 야간, OVERTIME: 잔업
```

**3. 응답 규칙** — 출력 형식 강제
```
- 항상 MCP 도구를 사용하여 최신 데이터 기반으로 답변
- 숫자 데이터는 마크다운 표 형태로 정리
- 달성률 90% 미만 → ⚠️ 주의
- 불량률 2% 이상 → 🚨 경고
```

**4. 시각화 규칙** — 차트 형식 지정
```
- 추이 데이터 → Vega-Lite 라인 차트
- 비교 데이터 → Vega-Lite 막대 차트
- 인과관계 → Mermaid 다이어그램
- "차트", "그래프" 키워드 시 자동 적용
```

### `{{CURRENT_DATE}}`
Open WebUI가 자동으로 오늘 날짜로 치환. LLM이 "오늘"이 언제인지 알 수 있게 함.

---

## 10. 저장 프롬프트 (/ 명령어)

채팅창에 `/`를 입력하면 자동완성되는 단축 명령어:

| 명령어 | 제목 | 확장되는 프롬프트 |
|--------|------|----------------|
| `/daily` | 일일 생산 보고 | 오늘 전체 라인의 생산 실적을 조회하고, 라인별 달성률 표 + 전체 요약을 제공해줘. 달성률 90% 미만 라인은 원인 분석도 포함해줘. |
| `/defect` | 불량 분석 | 이번 주 불량 통계를 유형별로 집계하고, 가장 빈번한 불량 유형 TOP 3의 발생 라인과 추이를 분석해줘. |
| `/shift` | 교대 비교 | 이번 달 교대별(주간/야간/잔업) 생산성을 비교 분석해줘. 달성률, 불량률 포함하고 차트로 시각화해줘. |
| `/trend` | 생산 추이 | 최근 2주간 일별 생산 추이를 전체 라인 합산으로 Vega-Lite 차트와 함께 보여줘. |
| `/morning` | 아침 브리핑 | 어제 전체 생산 실적 요약, 불량 발생 건, 설비 정지 이력을 종합 브리핑해줘. 핵심 수치는 표로 정리. |

### 동작 원리
```
사용자: /morning [Enter]
         ↓
Open WebUI: 저장된 프롬프트로 자동 확장
         ↓
실제 전송: "어제 전체 생산 실적 요약, 불량 발생 건, 설비 정지 이력을 종합 브리핑해줘. 핵심 수치는 표로 정리."
         ↓
LLM: get_daily_production_summary + get_defect_summary + get_equipment_downtime 체이닝
         ↓
종합 브리핑 응답
```

---

## 11. 시각화 (Vega-Lite + Mermaid)

Open WebUI는 마크다운 코드블록을 인라인 렌더링한다.

### Vega-Lite 차트

시스템 프롬프트에서 LLM에게 형식을 지시:

````
```vega-lite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "width": 500, "height": 300,
  "data": {"values": [
    {"날짜": "2026-03-01", "생산량": 1200},
    {"날짜": "2026-03-02", "생산량": 1350},
    ...
  ]},
  "mark": {"type": "line", "point": true},
  "encoding": {
    "x": {"field": "날짜", "type": "temporal"},
    "y": {"field": "생산량", "type": "quantitative"}
  }
}
```
````

Open WebUI가 이 코드블록을 감지 → 인터랙티브 차트로 렌더링.

### 차트 유형 선택 기준

| 데이터 특성 | 차트 유형 | 예시 |
|------------|---------|------|
| 시간에 따른 변화 | 라인 차트 | 생산 추이, 불량률 추이 |
| 항목 간 비교 | 막대 차트 | 라인별 생산량, 제품별 비교 |
| 인과관계/흐름 | Mermaid 다이어그램 | 불량 원인 → 설비 → 정비 |

### Mermaid 다이어그램

````
```mermaid
graph LR
    A[도장불량 급증] --> B[스프레이건 점검]
    B --> C[노즐 마모 발견]
    C --> D[노즐 교체 정비]
    D --> E[불량률 정상화]
```
````

---

## 12. DB 스키마와 시뮬레이션 데이터

### 테이블 요약 (14개)

#### 마스터 (5)

| 테이블 | 설명 | 건수 |
|--------|------|------|
| `PRODUCTION_LINES` | 5 라인 (BODY/PAINT/ASSEMBLY/ENGINE/QC) | 5 |
| `PRODUCTS` | 5 제품 (소나타/아반떼/투싼/그랜저/아이오닉5) | 5 |
| `EQUIPMENT` | 설비 20대 (ROBOT/PRESS/SPRAY/CONVEYOR/TESTER) | 20 |
| `WORKERS` | 작업자 30명 (JUNIOR/MIDDLE/SENIOR) | 30 |
| `SHIFTS` | 3교대 (주간 06-14/야간 14-22/잔업 22-06) | 3 |

#### 트랜잭션 (5)

| 테이블 | 설명 | 건수 |
|--------|------|------|
| `WORK_ORDERS` | 작업지시 (날짜+제품+라인+교대) | ~600 |
| `PRODUCTION_LOG` | 생산실적 (생산량+불량수+작업자) | ~1,500 |
| `DEFECT_RECORDS` | 불량상세 (유형+원인+심각도+설비) | ~1,600 |
| `EQUIPMENT_DOWNTIME` | 설비비가동 (사유+시간) | ~90 |
| `QUALITY_INSPECTIONS` | 품질검사 (유형+결과) | ~1,500 |

#### 분석 (4)

| 테이블 | 설명 | 건수 |
|--------|------|------|
| `PROCESS_PARAMS` | 공정파라미터 (온도/압력/속도) | 다수 |
| `MATERIAL_USAGE` | 자재사용 (계획 vs 실투입) | 다수 |
| `MAINTENANCE_HISTORY` | 정비이력 | ~70 |
| `DAILY_PRODUCTION_SUMMARY` | 일별요약 | 300 |

### 시뮬레이션 특성

`db/seed.py`가 60일간 현실적인 데이터를 생성:
- 주말 생산량 감소
- 야간/잔업 생산성 저하
- **도장 라인 2주차부터 불량률 스파이크** (노즐 마모 시나리오)
- 설비 고장은 랜덤 발생
- 작업자 숙련도에 따른 불량률 차이

---

## 13. 설치 및 실행 가이드

### 사전 요구사항
- Python 3.12+
- Docker Desktop
- Ollama (`brew install ollama`)
- qwen2.5:14b 모델 (`ollama pull qwen2.5:14b`)

### 1단계: MCP 서버 실행

```bash
cd factory-mcp

# 가상환경
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# DB 생성 (최초 1회)
python -m db.seed

# MCP 서버 시작
python mcp_server.py
# → FastMCP "Factory AI" running on http://0.0.0.0:8501
```

### 2단계: Open WebUI 실행

```bash
cd open-webui
docker compose up -d
# → factory-open-webui 컨테이너 시작
# → http://localhost:3009 접속 가능
```

### 3단계: Admin Panel 설정 (최초 1회)

→ 다음 섹션 참조

### 동작 확인

```bash
# MCP 서버 헬스체크
curl http://localhost:8501/mcp

# Ollama 확인
ollama list   # qwen2.5:14b 있는지

# Open WebUI 접속
open http://localhost:3009
```

---

## 14. Admin Panel 설정 (1회)

Docker 재시작 후 `http://localhost:3009`에서 관리자로 로그인하고 다음을 설정.
이 설정은 Docker 볼륨에 영구 저장되므로 **1번만 하면 된다**.

### 1. MCP 서버 연결

```
Admin Panel → Settings → Tools → "+" 버튼
URL: http://host.docker.internal:8501/mcp
→ 15개 도구 자동 등록됨
```

### 2. 모델 프리셋 생성

```
Admin Panel → Workspace → Models → "+" New Model
- 모델 이름: Factory MES 분석가
- 기본 모델: qwen2.5:14b
- 시스템 프롬프트: model_preset.json의 params.system 값 복사
- 도구: MCP 체크
```

시작 질문 칩 / Temperature / 필터 연결은 API로 설정 (UI에 없는 항목):
```bash
# model_preset.json 내용으로 API 호출
# → suggestion_prompts 5개 + temperature 0.3 + filterIds 설정
```

### 3. 저장 프롬프트 등록

```
Admin Panel → Workspace → Prompts → "+" 5번 반복
saved_prompts.json의 5개를 각각 등록:
- /daily, /defect, /shift, /trend, /morning
```

### 4. 기본 모델 설정

```
Admin Panel → Settings → Interface → Default Model
→ "Factory MES 분석가" 선택
```

---

## 15. 파일 맵

```
factory-mcp/
├── mcp_server.py              # MCP 서버 엔트리포인트 (:8501)
├── config.py                  # DB 설정 (SQLite/Oracle 전환)
├── factory.db                 # SQLite 데이터베이스 (생성됨)
├── requirements.txt           # Python 의존성 (fastmcp, python-dotenv)
│
├── tools/                     # MCP 도구 모듈
│   ├── __init__.py            # query, to_json, log_call 공통 유틸
│   ├── production.py          # 생산 도구 3개
│   ├── defect.py              # 불량 도구 4개
│   ├── equipment.py           # 설비 도구 4개
│   └── analytics.py           # 분석 도구 4개
│
├── db/                        # 데이터베이스 계층
│   ├── schema.sql             # 14 테이블 DDL + 마스터 INSERT
│   ├── seed.py                # 60일 시뮬레이션 데이터 생성
│   ├── connection.py          # 브릿지 패턴 (query/execute)
│   └── backends/              # SQLite / Oracle 백엔드
│
├── open-webui/                # Open WebUI 설정
│   ├── docker-compose.yml     # Docker 설정 (Ollama 직접 연결)
│   ├── model_preset.json      # 모델 프리셋 백업 (시스템 프롬프트 + 칩)
│   ├── saved_prompts.json     # 저장 프롬프트 5개 백업
│   └── factory_followup.py    # Outlet 필터 (후속 질문 자동 제안)
│
├── docs/                      # 문서
│   └── MANUAL.md              # ← 이 파일
│
├── CLAUDE.md                  # Claude Code 프로젝트 설명
└── README.md                  # GitHub 프로젝트 소개
```
