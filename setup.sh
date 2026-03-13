#!/bin/bash
# ============================================================
# Factory MCP — 초기 설정 스크립트
# MES 데이터 MCP 서버 (:8501)
#
# 사용법:
#   chmod +x setup.sh
#   ./setup.sh              # 기본 설정
#   ./setup.sh --reset      # DB 재생성 (factory.db)
# ============================================================

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

print_step() { echo -e "\n${BLUE}[$1/4]${NC} ${BOLD}$2${NC}"; }
print_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}!${NC} $1"; }
print_err()  { echo -e "  ${RED}✗${NC} $1"; }

RESET=false
for arg in "$@"; do
    case $arg in
        --reset)  RESET=true ;;
        --help|-h)
            echo "Factory MCP 초기 설정"
            echo ""
            echo "사용법: ./setup.sh [옵션]"
            echo ""
            echo "옵션:"
            echo "  --reset   기존 DB 삭제 후 재생성 (60일 시뮬레이션 데이터)"
            echo "  --help    이 도움말 표시"
            exit 0
            ;;
    esac
done

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     Factory MCP — MES 분석 서버 설정     ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"

# ── Step 1: Python 확인 ──
print_step 1 "Python 환경 확인"

PYTHON=""
for cmd in python3.11 python3.12 python3.13 python3; do
    if command -v $cmd &>/dev/null; then
        ver=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo $ver | cut -d. -f1)
        minor=$(echo $ver | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    print_err "Python 3.11 이상이 필요합니다."
    exit 1
fi
print_ok "Python: $($PYTHON --version)"

# ── Step 2: 가상환경 ──
print_step 2 "가상환경 설정"

if [ -d ".venv" ]; then
    print_ok "기존 가상환경 사용: .venv/"
else
    $PYTHON -m venv .venv
    print_ok "가상환경 생성: .venv/"
fi

source .venv/bin/activate
print_ok "가상환경 활성화 완료"

# ── Step 3: 패키지 설치 ──
print_step 3 "패키지 설치"

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
print_ok "$(pip list 2>/dev/null | wc -l | tr -d ' ')개 패키지 설치 완료"

# ── Step 4: DB 초기화 ──
print_step 4 "데이터베이스 초기화"

DB_FILE="factory.db"

if [ "$RESET" = true ] && [ -f "$DB_FILE" ]; then
    rm -f "$DB_FILE"
    print_warn "기존 DB 삭제: $DB_FILE"
fi

if [ -f "$DB_FILE" ] && [ "$RESET" = false ]; then
    print_ok "기존 DB 사용: $DB_FILE (재생성: ./setup.sh --reset)"
else
    python -m db.seed
    print_ok "DB 생성 완료: $DB_FILE (60일 시뮬레이션 데이터)"
    echo ""
    echo -e "  ${GREEN}테이블 14개:${NC}"
    echo "    마스터 5개 (라인, 제품, 설비, 작업자, 교대)"
    echo "    트랜잭션 5개 (작업지시, 생산, 불량, 비가동, 검사)"
    echo "    분석 4개 (파라미터, 자재, 정비, 일별요약)"
fi

# ── 완료 ──
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║            설정 완료!                    ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}실행 방법:${NC}"
echo ""
echo -e "  ${YELLOW}# macOS / Linux${NC}"
echo "  .venv/bin/python mcp_server.py"
echo ""
echo -e "  ${YELLOW}# Windows (PowerShell)${NC}"
echo '  .venv\Scripts\python.exe mcp_server.py'
echo ""
echo -e "${BOLD}접속:${NC}"
echo -e "  MCP 엔드포인트  →  ${GREEN}http://localhost:8501/mcp${NC}"
echo ""
echo -e "${BOLD}도구 15개:${NC}"
echo "  생산(3): daily_summary, by_product, achievement_rate"
echo "  불량(4): defect_summary, by_type, by_cause, trend"
echo "  설비(4): by_equipment, downtime, maintenance, params_anomaly"
echo "  분석(4): quality, material_yield, worker_perf, period_comparison"
echo ""
