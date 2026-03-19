"""
ReasoningModule: OpenAI GPT-based reasoning module
- Extract entities/key content from newly explored nodes
- Infer relationships (edges) between nodes
- Generate final answers
"""

import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ReasoningModule:
    """GPT-4.1 based reasoning module"""

    def __init__(self, model: str = "gpt-4.1"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def _call(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """OpenAI API call helper"""
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
    # 1. Plan next search
    # -----------------------------------------------------------
    def plan_next_search(self, question: str, kg_context: str, tree_summary: str) -> dict:
        """
        Analyze current KG state and document tree to decide:
        1) Whether the collected evidence is sufficient to answer the query
        2) If not, which section to explore next

        Returns:
            {"sufficient": bool, "next_search_query": str, "reasoning": str}
        """
        system = (
            "You are an AI agent that systematically explores regulatory documents. "
            "Analyze the evidence collected so far (knowledge graph) and the document structure (tree).\n\n"
            "First, judge whether the current evidence is SUFFICIENT to fully answer the user's query. "
            "Consider: Are all key facts, numerical values, and regulatory references found? "
            "Are there obvious gaps or missing cross-references?\n\n"
            "If sufficient, set sufficient=true. If not, determine which section to explore next.\n"
            "Respond ONLY in the following JSON format:\n"
            '{"sufficient": true/false, '
            '"next_search_query": "content to search for (empty string if sufficient)", '
            '"reasoning": "why evidence is sufficient OR why this section should be explored next"}'
        )
        user = (
            f"[User Query]\n{question}\n\n"
            f"[Current Knowledge Graph]\n{kg_context}\n\n"
            f"[Document Tree Structure Summary]\n{tree_summary}"
        )
        raw = self._call(system, user, max_tokens=512)
        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            result = json.loads(cleaned)
            return {
                "sufficient": result.get("sufficient", False),
                "next_search_query": result.get("next_search_query", ""),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception:
            return {"sufficient": False, "next_search_query": raw, "reasoning": ""}

    # -----------------------------------------------------------
    # 2. Infer relations between nodes
    # -----------------------------------------------------------
    # Structural edge labels (document connectivity)
    STRUCTURAL_LABELS = ["REFERENCES", "SPECIFIES"]

    # Semantic edge labels (regulatory judgment)
    SEMANTIC_LABELS = [
        "SATISFIES", "VIOLATES", "SUPPORTS", "CONTRADICTS",
        "LEADS_TO", "IS_PREREQUISITE_OF",
    ]

    ALL_LABELS = STRUCTURAL_LABELS + SEMANTIC_LABELS + ["SEMANTIC", "NONE"]

    def infer_relation(
        self,
        node_a_title: str,
        node_a_content: str,
        node_b_title: str,
        node_b_content: str,
        question: str,
    ) -> dict:
        """
        Two-stage edge inference: description first, then label.

        Stage 1: LLM describes the relationship in natural language.
        Stage 2: LLM maps the description to an ontology label.

        This avoids the "default to REFERENCES" problem where LLM
        picks the safest label under classification pressure.

        Returns:
            {"relation": str, "description": str, "confidence": float}
        """
        system = (
            "You are an expert in nuclear regulatory document analysis.\n\n"
            "STEP 1: Describe the relationship between Section A and Section B "
            "in ONE concrete sentence. Focus on HOW they are related in the "
            "context of the analysis question. Be specific — mention what "
            "information connects them (e.g., design values, regulatory limits, "
            "causal effects, prerequisites).\n\n"
            "STEP 2: Based on your description, classify the relationship into "
            "one of the following labels:\n"
            "  Structural:\n"
            "    REFERENCES — A cites or cross-references B\n"
            "    SPECIFIES — A provides details/specifications for B's general description\n"
            "  Semantic (regulatory judgment):\n"
            "    SATISFIES — A (design result) meets B (regulatory requirement)\n"
            "    VIOLATES — A (design result) fails to meet B (requirement)\n"
            "    SUPPORTS — A provides evidence that strengthens B's claim\n"
            "    CONTRADICTS — A provides evidence that conflicts with B\n"
            "    LEADS_TO — A (cause/event) leads to B (consequence/state)\n"
            "    IS_PREREQUISITE_OF — A must be understood/verified before B\n"
            "  Other:\n"
            "    SEMANTIC — meaningful relationship that doesn't fit above types\n"
            "    NONE — no meaningful relationship\n\n"
            "Respond ONLY in JSON:\n"
            '{"description": "one sentence describing the relationship", '
            '"relation": "LABEL", "confidence": 0.0~1.0}'
        )
        user = (
            f"[Analysis Question]\n{question}\n\n"
            f"[Section A] {node_a_title}\n{node_a_content[:600]}\n\n"
            f"[Section B] {node_b_title}\n{node_b_content[:600]}"
        )
        raw = self._call(system, user, max_tokens=512)
        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            result = json.loads(cleaned)
            if result.get("relation") not in self.ALL_LABELS:
                result["relation"] = "SEMANTIC"
            return {
                "relation": result.get("relation", "SEMANTIC"),
                "description": result.get("description", ""),
                "confidence": result.get("confidence", 0.5),
                # Keep backward compat: reasoning = description
                "reasoning": result.get("description", ""),
            }
        except Exception:
            return {"relation": "SEMANTIC", "description": raw,
                    "confidence": 0.5, "reasoning": raw}

    # -----------------------------------------------------------
    # 3. Generate final answer
    # -----------------------------------------------------------
    def generate_answer(
        self,
        question: str,
        kg_context: str,
        trajectory: list[str],
        reference_images: list[str] | None = None,
    ) -> str:
        """
        Generate a final answer using the completed KG, exploration trajectory,
        and optionally referenced Figure/Table images (VLM).

        Args:
            reference_images: List of base64-encoded JPEG images of referenced
                              Figures/Tables from the document.
        """
        trajectory_str = "\n".join(
            [f"  Hop {i+1}: {step}" for i, step in enumerate(trajectory)]
        )

        system = (
            "You are an expert AI for nuclear regulatory review. "
            "Based on the knowledge graph constructed by the agent through exploring multiple document sections, "
            "generate an accurate and evidence-based answer to the user's query.\n"
        )
        if reference_images:
            system += (
                "You are also provided with images of referenced Figures and Tables from the document. "
                "Use these visual materials to provide a more accurate and complete answer.\n"
            )
        system += (
            "Your answer must:\n"
            "1. State the core conclusion directly\n"
            "2. Quote or paraphrase the specific evidence from the knowledge graph that supports your conclusion "
            "(include the exact values, terms, and node IDs)\n"
            "3. Mention any uncertainties explicitly\n"
            "Ground every claim in the provided context. Do not add information not found in the knowledge graph.\n"
            "Be concise. Answer in English. Keep your answer under 300 words."
        )

        user_text = (
            f"[User Query]\n{question}\n\n"
            f"[Exploration Trajectory]\n{trajectory_str}\n\n"
            f"[Constructed Knowledge Graph]\n{kg_context}"
        )

        if reference_images:
            # Use vision API with images
            from src.utils.vision import build_vision_content

            if reference_images:
                user_text += f"\n\n[Referenced Figures/Tables: {len(reference_images)} image(s) attached below]"

            content = build_vision_content(user_text, reference_images)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
                max_tokens=800,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        else:
            return self._call(system, user_text, max_tokens=800)

    # -----------------------------------------------------------
    # 4. Generate node summary
    # -----------------------------------------------------------
    def summarize_node(self, title: str, content: str) -> str:
        """Summarize a long document section in 2-3 sentences"""
        system = "Summarize the document section concisely in 2-3 sentences in English."
        user = f"[Section Title] {title}\n\n[Content]\n{content[:2000]}"
        return self._call(system, user, max_tokens=200)
