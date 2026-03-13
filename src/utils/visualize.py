"""
KG 시각화 유틸리티 - NetworkX + matplotlib
"""

import os
import json
import matplotlib
matplotlib.use('Agg')  # GUI 없이 파일로 저장
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path


# 관계 타입별 색상
EDGE_COLORS = {
    "REFERENCES":        "#6C8EBF",
    "SUPPORTS":          "#82B366",
    "CONTRADICTS":       "#FF4444",
    "SATISFIES":         "#00AA00",
    "VIOLATES":          "#CC0000",
    "IS_PREREQUISITE_OF":"#9673A6",
    "LEADS_TO":          "#D6AB00",
    "SPECIFIES":         "#00897B",
}

# Hop 번호별 노드 색상
HOP_COLORS = {
    0: "#E1D5E7",
    1: "#DAE8FC",
    2: "#D5E8D4",
    3: "#FFF2CC",
    4: "#FFE6CC",
    5: "#F8CECC",
}


def visualize_kg(kg, output_path: str = "experiments/kg_output.png") -> str:
    """
    DynamicSubKG를 시각화하여 PNG로 저장.
    
    Returns:
        저장된 파일 경로
    """
    G = kg.graph

    if len(G.nodes) == 0:
        print("[Visualize] 노드가 없어 시각화를 건너뜁니다.")
        return ""

    os.makedirs(Path(output_path).parent, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    fig.patch.set_facecolor("#1E1E2E")
    ax.set_facecolor("#1E1E2E")

    # 레이아웃
    pos = nx.spring_layout(G, seed=42, k=2.5)

    # 노드 색상 (hop 기반)
    node_colors = []
    for nid in G.nodes:
        hop = G.nodes[nid].get("hop", 0)
        node_colors.append(HOP_COLORS.get(hop, "#CCCCCC"))

    # 노드 그리기
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=2500,
        alpha=0.9,
    )

    # 노드 레이블 (짧게)
    labels = {
        nid: G.nodes[nid].get("title", nid)[:20] + ("..." if len(G.nodes[nid].get("title", nid)) > 20 else "")
        for nid in G.nodes
    }
    nx.draw_networkx_labels(
        G, pos, labels=labels, ax=ax,
        font_size=8, font_color="#111111", font_weight="bold",
    )

    # 엣지 (관계별로 그룹화하여 색상 적용)
    edge_groups: dict[str, list] = {}
    for u, v, data in G.edges(data=True):
        rel = data.get("relation", "REFERENCES")
        if rel not in edge_groups:
            edge_groups[rel] = []
        edge_groups[rel].append((u, v))

    for rel, edges in edge_groups.items():
        color = EDGE_COLORS.get(rel, "#888888")
        nx.draw_networkx_edges(
            G, pos, edgelist=edges, ax=ax,
            edge_color=color, width=2.5,
            arrows=True, arrowsize=20,
            connectionstyle="arc3,rad=0.1",
        )

    # 엣지 레이블
    edge_labels = {
        (u, v): data.get("relation", "")
        for u, v, data in G.edges(data=True)
    }
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, ax=ax,
        font_size=7, font_color="#FFFFFF",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#333355", alpha=0.7),
    )

    # 범례 (Hop 색상 기준)
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=HOP_COLORS[i], label=f"Hop {i}")
        for i in sorted(HOP_COLORS.keys())
        if any(G.nodes[n].get("hop", 0) == i for n in G.nodes)
    ]
    if legend_elements:
        ax.legend(handles=legend_elements, loc="upper left",
                  facecolor="#2D2D3F", labelcolor="white", fontsize=9)

    # 제목
    ax.set_title(
        f"GWM Dynamic Sub-KG  |  {len(G.nodes)} nodes, {len(G.edges)} edges\n"
        f"Q: {kg.question[:80]}",
        color="white", fontsize=11, pad=12,
    )
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#1E1E2E")
    plt.close()
    print(f"[Visualize] KG 시각화 저장: {output_path}")
    return output_path


def save_kg_json(kg, output_path: str = "experiments/kg_output.json") -> str:
    """KG를 JSON으로 저장"""
    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kg.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"[Visualize] KG JSON 저장: {output_path}")
    return output_path
