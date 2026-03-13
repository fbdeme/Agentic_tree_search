"""
실험 실행 스크립트: GWM 기반 다중 홉 규제 문서 탐색 에이전트

사용법:
    cd /Users/jeonmingyu/workspace_2026/Agentic_tree_search
    source .venv/bin/activate
    python experiments/run_experiment.py

PageIndex 오픈소스로 직접 PDF → 트리 생성 후 실험하려면:
    cd pageindex_core
    python run_pageindex.py --pdf_path ../experiments/your_doc.pdf
    # → tests/results/ 에 JSON 저장됨
    # 그 후 위 스크립트에서 tree_path를 해당 JSON으로 변경
"""

import sys
import os
import json
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.gwm_agent import GWMAgent
from src.utils.visualize import visualize_kg, save_kg_json


def load_fsar_tree(tree_path: str) -> tuple[str, list]:
    """샘플 FSAR 트리 JSON 로드"""
    with open(tree_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["doc_id"], data["tree"], data.get("doc_name", "FSAR")


def run_experiment(question: str, doc_ids: list[str], env: PageIndexEnvironment, exp_name: str):
    """단일 실험 실행"""
    print(f"\n{'#'*70}")
    print(f"# 실험: {exp_name}")
    print(f"{'#'*70}")

    agent = GWMAgent(
        environment=env,
        model="gpt-4o-mini",
        max_hops=4,
        top_k=2,
    )

    start = time.time()
    result = agent.run(question=question, doc_ids=doc_ids)
    elapsed = time.time() - start

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"⏱️  실행 시간: {elapsed:.1f}초")
    print(f"\n📊 최종 지식그래프 상태:")
    print(f"   {result['kg']}")

    print(f"\n🗺️  탐색 궤적 (Trajectory):")
    for step in result["trajectory"]:
        print(f"   {step}")

    print(f"\n💡 최종 답변:")
    print("-" * 60)
    print(result["answer"])
    print("-" * 60)

    # 시각화 & 저장
    safe_name = exp_name.replace(" ", "_").replace("/", "_")[:30]
    kg_img_path = str(ROOT / f"experiments/results/kg_{safe_name}.png")
    kg_json_path = str(ROOT / f"experiments/results/kg_{safe_name}.json")

    visualize_kg(result["kg"], output_path=kg_img_path)
    save_kg_json(result["kg"], output_path=kg_json_path)

    return result


def main():
    print("🚀 GWM 기반 다중 모달 규제 문서 탐색 에이전트 실험")
    print("=" * 60)

    # ── 환경 설정 ────────────────────────────────────────────────
    env = PageIndexEnvironment(model="gpt-4o-mini")

    # 샘플 FSAR 트리 로드 (사전 생성된 트리 JSON)
    tree_path = ROOT / "experiments/sample_fsar_tree.json"
    with open(tree_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_id = data["doc_id"]
    doc_name = data.get("doc_name", "FSAR")
    tree = data["tree"]

    # 환경에 문서 등록
    env.register_tree(doc_id=doc_id, tree=tree, doc_name=doc_name)
    print(f"\n✅ 환경 설정 완료: {env.doc_count}개 문서, {env.node_count}개 노드 캐싱")

    doc_ids = [doc_id]

    # ── 실험 1: 냉각재 펌프 정지 사고 + 피복재 온도 제한치 만족 여부 ──
    q1 = (
        "원자로 냉각재 펌프(RCP) 정지 사고 시 발생하는 핵연료 피복재 최고 온도(PCT)가 "
        "기술 지침서(Chapter 16)에서 규정한 안전 한계치를 만족하는가? "
        "해당 근거 섹션과 수치를 함께 제시하시오."
    )
    result1 = run_experiment(q1, doc_ids, env, "RCP정지_PCT_규제만족")

    print(f"\n{'='*70}\n")

    # ── 실험 2: LOCA 시나리오 3중 만족 여부 (피복재 온도 + 산화율 + 냉각가능성) ──
    q2 = (
        "냉각재 상실 사고(LOCA) 시나리오에서 10 CFR 50.46의 세 가지 수락 기준 "
        "(핵연료 피복재 온도 2,200°F, 최대 국부 산화율 17%, 냉각가능성 유지)이 "
        "모두 만족되는지 FSAR 분석 결과를 기반으로 종합 평가하시오."
    )
    result2 = run_experiment(q2, doc_ids, env, "LOCA_3중기준_평가")

    print(f"\n{'='*70}")
    print("✅ 모든 실험 완료. 결과는 experiments/results/ 폴더를 확인하세요.")
    print("   - PNG: KG 시각화")
    print("   - JSON: KG 구조 데이터")


if __name__ == "__main__":
    os.makedirs(ROOT / "experiments/results", exist_ok=True)
    main()
