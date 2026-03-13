"""
ReasoningModule: OpenAI GPT 기반 추론 모듈
- 새로 탐색된 노드에서 엔티티/주요 내용 추출
- 노드 간 관계(엣지) 추론
- 최종 답변 생성
"""

import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ReasoningModule:
    """GPT-4o-mini 기반 추론 모듈"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def _call(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """OpenAI API 호출 헬퍼"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    # -----------------------------------------------------------
    # 1. 다음 탐색 계획 수립
    # -----------------------------------------------------------
    def plan_next_search(self, question: str, kg_context: str, tree_summary: str) -> str:
        """
        현재 KG 상태와 문서 트리를 보고, 다음에 탐색할 섹션을 결정합니다.
        GWM의 Action 단계에 해당.
        """
        system = (
            "당신은 규제 문서를 체계적으로 탐색하는 AI 에이전트입니다. "
            "현재까지 수집한 증거(지식그래프)와 문서 구조(트리)를 분석하여, "
            "사용자의 질의에 답하기 위해 다음에 탐색해야 할 섹션을 결정하세요.\n"
            "응답은 반드시 다음 JSON 형식으로만 출력하세요:\n"
            '{"next_search_query": "탐색할 내용", '
            '"target_section": "탐색할 섹션 제목 또는 키워드", '
            '"reasoning": "이 섹션을 탐색하는 이유"}'
        )
        user = (
            f"[사용자 질의]\n{question}\n\n"
            f"[현재 지식그래프]\n{kg_context}\n\n"
            f"[문서 트리 구조 요약]\n{tree_summary}"
        )
        raw = self._call(system, user, max_tokens=512)
        # JSON 추출 시도
        try:
            # 마크다운 코드블록 제거
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            return json.loads(cleaned).get("next_search_query", raw)
        except Exception:
            return raw

    # -----------------------------------------------------------
    # 2. 노드 간 관계 추론
    # -----------------------------------------------------------
    def infer_relation(
        self,
        node_a_title: str,
        node_a_content: str,
        node_b_title: str,
        node_b_content: str,
        question: str,
    ) -> dict:
        """
        두 노드 간의 관계를 추론합니다.
        GWM의 Transition(KG 업데이트) 단계에서 엣지를 생성할 때 사용.

        Returns:
            {"relation": "SATISFIES", "confidence": 0.9, "reasoning": "..."}
        """
        VALID_RELATIONS = [
            "REFERENCES", "SUPPORTS", "CONTRADICTS",
            "SATISFIES", "VIOLATES", "IS_PREREQUISITE_OF",
            "LEADS_TO", "SPECIFIES", "NONE"
        ]

        system = (
            "당신은 원자력 규제 문서 분석 전문가입니다. "
            "두 문서 섹션 사이의 논리적 관계를 분석하세요.\n"
            f"가능한 관계 유형: {', '.join(VALID_RELATIONS)}\n"
            "- NONE: 두 섹션 사이에 의미 있는 관계가 없음\n"
            "응답은 반드시 다음 JSON 형식으로만 출력하세요:\n"
            '{"relation": "관계유형", "confidence": 0.0~1.0, '
            '"reasoning": "한국어로 관계 성립 근거를 2~3문장으로 설명"}'
        )
        user = (
            f"[분석 목적 질의]\n{question}\n\n"
            f"[섹션 A] {node_a_title}\n{node_a_content[:600]}\n\n"
            f"[섹션 B] {node_b_title}\n{node_b_content[:600]}"
        )
        raw = self._call(system, user, max_tokens=512)
        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            result = json.loads(cleaned)
            if result.get("relation") not in VALID_RELATIONS:
                result["relation"] = "REFERENCES"
            return result
        except Exception:
            return {"relation": "REFERENCES", "confidence": 0.5, "reasoning": raw}

    # -----------------------------------------------------------
    # 3. 최종 답변 생성
    # -----------------------------------------------------------
    def generate_answer(self, question: str, kg_context: str, trajectory: list[str]) -> str:
        """
        완성된 KG와 탐색 궤적을 컨텍스트로 최종 답변을 생성합니다.
        """
        trajectory_str = "\n".join(
            [f"  Hop {i+1}: {step}" for i, step in enumerate(trajectory)]
        )
        system = (
            "당신은 원자력 규제 심사 전문가 AI입니다. "
            "에이전트가 여러 문서 섹션을 탐색하며 구축한 지식그래프를 바탕으로, "
            "사용자 질의에 대한 정확하고 근거 있는 답변을 생성하세요.\n"
            "답변에는 반드시 다음을 포함하세요:\n"
            "1. 핵심 결론 (명확하게)\n"
            "2. 근거 노드와 관계 경로 인용\n"
            "3. 불확실한 사항이 있으면 명시\n"
            "한국어로 답변하세요."
        )
        user = (
            f"[사용자 질의]\n{question}\n\n"
            f"[탐색 궤적 (Trajectory)]\n{trajectory_str}\n\n"
            f"[구축된 지식그래프]\n{kg_context}"
        )
        return self._call(system, user, max_tokens=1500)

    # -----------------------------------------------------------
    # 4. 노드 요약 생성
    # -----------------------------------------------------------
    def summarize_node(self, title: str, content: str) -> str:
        """긴 섹션 내용을 2~3문장으로 요약"""
        system = "문서 섹션을 2~3문장으로 간결하게 한국어로 요약하세요."
        user = f"[섹션 제목] {title}\n\n[내용]\n{content[:2000]}"
        return self._call(system, user, max_tokens=200)
