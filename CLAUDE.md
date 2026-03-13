# Factory MCP (Stage 1)

자동차 공장 MES 데이터 MCP 서버 — Open WebUI가 15개 도구를 직접 호출.

## 아키텍처
```
User → Open WebUI (:3006) → MCP Server (:8501) → SQLite (factory.db)
                               15개 @mcp.tool()
```

## 기술 스택
- Python 3.11+ / `.venv/`
- FastMCP (Streamable HTTP, :8501)
- SQLite / Oracle 듀얼 백엔드
- Docker: Open WebUI → Ollama (qwen2.5:14b, tool calling) → MCP

## 구조
```
mcp_server.py        # MCP 서버 (:8501, 15개 도구)
config.py            # DB 설정
db/
├── schema.sql       # 14 테이블 DDL + 마스터 INSERT
├── seed.py          # 60일 시뮬레이션 데이터
├── connection.py    # 브릿지 패턴 (query/execute)
└── backends/        # SQLite / Oracle 자동 전환
open-webui/
├── docker-compose.yml    # Open WebUI (Ollama 직접 연결)
├── model_preset.json     # "Factory MES 분석가" 모델 프리셋 백업
└── saved_prompts.json    # 저장 프롬프트 5개 백업 (/daily, /defect, /shift, /trend, /morning)
```

## 테이블 14개

### 마스터 (5)
| 테이블 | 설명 | 건수 |
|--------|------|------|
| PRODUCTION_LINES | 5 라인 (BODY/PAINT/ASSEMBLY/ENGINE/QC) | 5 |
| PRODUCTS | 5 제품 (소나타/아반떼/투싼/그랜저/아이오닉5) | 5 |
| EQUIPMENT | 설비 20대 (ROBOT/PRESS/SPRAY/CONVEYOR/TESTER) | 20 |
| WORKERS | 작업자 30명 (JUNIOR/MIDDLE/SENIOR) | 30 |
| SHIFTS | 3교대 (주간/야간/잔업) | 3 |

### 트랜잭션 (5)
| 테이블 | 설명 |
|--------|------|
| WORK_ORDERS | 작업지시 (~600) |
| PRODUCTION_LOG | 생산실적 (~1500) |
| DEFECT_RECORDS | 불량상세 (~1600) |
| EQUIPMENT_DOWNTIME | 설비비가동 (~90) |
| QUALITY_INSPECTIONS | 품질검사 (~1500) |

### 분석 (4)
| 테이블 | 설명 |
|--------|------|
| PROCESS_PARAMS | 공정파라미터 (온도/압력/속도) |
| MATERIAL_USAGE | 자재사용 (계획 vs 실투입) |
| MAINTENANCE_HISTORY | 정비이력 (~70) |
| DAILY_PRODUCTION_SUMMARY | 일별요약 (300) |

## 도구 15개

### 생산 (3)
1. `get_daily_production_summary` — 일별 라인별 생산/불량
2. `get_production_by_product` — 제품별 생산량
3. `get_achievement_rate` — 라인별 목표 달성률

### 불량 (4)
4. `get_defect_summary` — 라인별 불량 요약
5. `get_defect_by_type` — 유형별 불량 집계
6. `get_defect_by_cause` — 원인 TOP N
7. `get_defect_trend` — 일별/주별/월별 불량률 추이

### 설비 (4)
8. `get_defect_by_equipment` — 설비별 불량 현황
9. `get_equipment_downtime` — 비가동 현황
10. `get_maintenance_history` — 정비 이력
11. `get_process_params_anomaly` — 파라미터 이상치

### 기타 (4)
12. `get_quality_inspections` — 품질 검사 현황
13. `get_material_yield` — 자재 수율
14. `get_worker_performance` — 작업자별 실적
15. `get_period_comparison` — 두 기간 비교

## 데이터 시나리오
- 기간: 2026-01-05 ~ 2026-03-05 (60일)
- **도장 라인 불량 스파이크**: 2주차(1/19~)부터 불량률 급등 → 원인: 스프레이건 노즐 마모 (60%)
- 데모 질문: "도장 불량률이 왜 높아?" → defect_summary → defect_by_cause → "노즐 마모"

## 실행

### 초기 설정
```bash
./setup.sh             # 자동 설정 (venv + pip + DB seed)
./setup.sh --reset     # DB 재생성
```

### MCP 서버 시작
```bash
# macOS / Linux
.venv/bin/python mcp_server.py

# Windows (PowerShell)
.venv\Scripts\python.exe mcp_server.py

# Windows (CMD)
.venv\Scripts\python.exe mcp_server.py
```

## Open WebUI 연동
```bash
cd open-webui && docker compose up -d   # :3006
```

### Docker 재시작 후 Admin Panel 설정 (1회)
1. **MCP 연결**: Settings → Tools → "+" → URL: `http://host.docker.internal:8501/mcp` → 15개 도구 자동 등록
2. **모델 프리셋**: Workspace → Models → "+" → `model_preset.json` 내용 입력 (시스템 프롬프트 + 시작 질문 칩 5개)
3. **저장 프롬프트**: Workspace → Prompts → "+" → `saved_prompts.json`의 5개 등록
4. **기본 모델**: Settings → Interface → Default Model → "Factory MES 분석가" 선택

### 저장 프롬프트 (/ 명령어)
| 명령어 | 용도 |
|--------|------|
| `/daily` | 일일 생산 보고 |
| `/defect` | 불량 분석 |
| `/shift` | 교대 비교 |
| `/trend` | 생산 추이 차트 |
| `/morning` | 아침 브리핑 |

### 시각화
- 추이/트렌드 → Vega-Lite 라인 차트 (Open WebUI 인라인 렌더링)
- 비교 데이터 → Vega-Lite 막대 차트
- 인과관계/흐름 → Mermaid 다이어그램
- "차트", "그래프", "시각화", "추이" 키워드 시 자동 적용

## 데모 질문 예시
- "오늘 생산 현황 알려줘" → get_daily_production_summary
- "도장 라인 불량률이 왜 높아?" → get_defect_summary → get_defect_by_cause
- "전주 대비 생산량 비교해줘" → get_period_comparison
- "설비 정비 이력 보여줘" → get_maintenance_history
- "작업자별 실적 비교" → get_worker_performance
- "최근 2주 생산 추이 차트로" → get_defect_trend + Vega-Lite 차트
