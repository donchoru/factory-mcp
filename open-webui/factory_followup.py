"""
title: Factory MES 후속 질문
description: 공장 MES 답변 주제를 분류하고, 미리 정의된 후속 질문을 칩으로 제안합니다.
author: dongcheol
version: 0.1.0
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    """답변 후 주제 기반 후속 질문을 자동 제안하는 Outlet 필터."""

    class Valves(BaseModel):
        enabled: bool = Field(default=True, description="필터 활성화 여부")

    def __init__(self):
        self.valves = self.Valves()

        # 주제별 키워드 → 후속 질문 매핑
        self.topic_rules = [
            {
                "id": "production",
                "keywords": ["생산", "실적", "달성률", "목표", "생산량", "production", "actual", "target"],
                "followups": [
                    "불량률 TOP 3 라인은 어디야?",
                    "교대별 생산성 비교해줘",
                    "전주 대비 생산량 변화는?",
                    "제품별 생산 비중 보여줘",
                ],
            },
            {
                "id": "defect",
                "keywords": ["불량", "불량률", "결함", "defect", "reject", "NG"],
                "followups": [
                    "불량 원인별로 분석해줘",
                    "설비별 불량 현황은?",
                    "최근 2주 불량률 추이 차트로 보여줘",
                    "정비 이력 조회해줘",
                ],
            },
            {
                "id": "equipment",
                "keywords": ["설비", "정지", "비가동", "가동", "다운타임", "downtime", "정비"],
                "followups": [
                    "정비 이력 보여줘",
                    "공정 파라미터 이상치 확인해줘",
                    "설비별 불량 현황은?",
                    "이번 달 가동률 추이 차트로",
                ],
            },
            {
                "id": "quality",
                "keywords": ["품질", "검사", "합격", "불합격", "QC", "inspection"],
                "followups": [
                    "불량 유형별 집계해줘",
                    "라인별 합격률 비교",
                    "최근 품질 추이 차트로",
                    "자재 수율 확인해줘",
                ],
            },
            {
                "id": "shift",
                "keywords": ["교대", "주간", "야간", "잔업", "shift", "DAY", "NIGHT"],
                "followups": [
                    "교대별 불량률 비교해줘",
                    "야간 생산성이 낮은 라인은?",
                    "이번 주 교대별 추이 차트로",
                    "작업자별 실적 비교해줘",
                ],
            },
            {
                "id": "trend",
                "keywords": ["추이", "트렌드", "차트", "그래프", "변화", "trend"],
                "followups": [
                    "라인별로 나눠서 추이 보여줘",
                    "불량률 추이도 같이 보여줘",
                    "전월 대비 비교 분석해줘",
                    "설비 가동률 추이도 확인",
                ],
            },
            {
                "id": "worker",
                "keywords": ["작업자", "인원", "성과", "worker", "performance"],
                "followups": [
                    "숙련도별 생산성 비교해줘",
                    "라인별 투입 인원 현황은?",
                    "작업자별 불량률 비교",
                    "교대별 인원 배치 현황",
                ],
            },
            {
                "id": "material",
                "keywords": ["자재", "수율", "투입", "material", "yield"],
                "followups": [
                    "자재 수율 낮은 라인은?",
                    "제품별 자재 사용량 비교",
                    "이번 주 자재 수율 추이",
                    "불량과 자재 수율 상관관계",
                ],
            },
        ]

        # 기본 후속 질문 (매칭 안 될 때)
        self.default_followups = [
            "오늘 전체 라인 생산 현황 알려줘",
            "이번 주 불량률 TOP 3 분석해줘",
            "설비 정지 이력 조회해줘",
            "교대별 생산성 비교해줘",
        ]

    def _classify(self, text: str) -> list[str]:
        """텍스트에서 키워드 매칭으로 주제를 분류. 복수 주제 가능."""
        text_lower = text.lower()
        matched = []
        for rule in self.topic_rules:
            for kw in rule["keywords"]:
                if kw.lower() in text_lower:
                    matched.append(rule["id"])
                    break
        return matched

    def _get_followups(self, topics: list[str]) -> list[str]:
        """주제들에서 후속 질문을 수집 (중복 제거, 최대 4개)."""
        seen = set()
        result = []
        for topic_id in topics:
            for rule in self.topic_rules:
                if rule["id"] == topic_id:
                    for q in rule["followups"]:
                        if q not in seen:
                            seen.add(q)
                            result.append(q)
        return result[:4] if result else self.default_followups[:4]

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        # 마지막 어시스턴트 메시지 + 마지막 유저 메시지에서 주제 분류
        context_text = ""
        for msg in reversed(messages):
            if msg.get("role") in ("assistant", "user"):
                context_text += " " + msg.get("content", "")
            if len(context_text) > 2000:
                break

        topics = self._classify(context_text)
        followups = self._get_followups(topics)

        # Open WebUI가 인식하는 형태로 후속 질문 주입
        # 방법 1: 마지막 메시지의 info.followups 필드
        last_msg = messages[-1]
        if last_msg.get("role") == "assistant":
            if "info" not in last_msg:
                last_msg["info"] = {}
            last_msg["info"]["followups"] = followups

            # 방법 2: 메시지 콘텐츠 끝에 구조화된 블록 추가 (fallback)
            suggestion_block = "\n\n---\n💡 **다음 질문 제안:**\n"
            for i, q in enumerate(followups, 1):
                suggestion_block += f"- {q}\n"
            last_msg["content"] = last_msg.get("content", "") + suggestion_block

        return body
