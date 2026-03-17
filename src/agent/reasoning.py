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
    def infer_relation(
        self,
        node_a_title: str,
        node_a_content: str,
        node_b_title: str,
        node_b_content: str,
        question: str,
    ) -> dict:
        """
        Infer the logical relationship between two nodes.
        Used during the GWM Transition (KG update) step to create edges.

        Returns:
            {"relation": "SATISFIES", "confidence": 0.9, "reasoning": "..."}
        """
        VALID_RELATIONS = [
            "REFERENCES", "SUPPORTS", "CONTRADICTS",
            "SATISFIES", "VIOLATES", "IS_PREREQUISITE_OF",
            "LEADS_TO", "SPECIFIES", "NONE"
        ]

        system = (
            "You are an expert in nuclear regulatory document analysis. "
            "Analyze the logical relationship between two document sections.\n"
            f"Possible relation types: {', '.join(VALID_RELATIONS)}\n"
            "- NONE: No meaningful relationship between the two sections\n"
            "Respond ONLY in the following JSON format:\n"
            '{"relation": "RELATION_TYPE", "confidence": 0.0~1.0, '
            '"reasoning": "Explain the basis for this relationship in 2-3 sentences"}'
        )
        user = (
            f"[Analysis Purpose Query]\n{question}\n\n"
            f"[Section A] {node_a_title}\n{node_a_content[:600]}\n\n"
            f"[Section B] {node_b_title}\n{node_b_content[:600]}"
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
            "Your answer must include:\n"
            "1. Core conclusion (stated clearly)\n"
            "2. Key evidence citations with node IDs\n"
            "3. Explicit mention of any uncertainties\n"
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
