# Agentic Tree Search: GWM 기반 다중 모달 규제 문서 탐색 에이전트

GWM(Graph World Model)의 State-Action-Transition 루프를 실제 구현하고,
**PageIndex 오픈소스**를 환경(World)으로 활용하는 실험 프레임워크입니다.

## 핵심 아키텍처

```
[사용자 질의]
      ↓
┌─────────────────────────── GWM Agent ─────────────────────────────┐
│  State (Short-term Memory)          Action (Exploration)           │
│  ┌──────────────────────┐           ┌────────────────────────────┐ │
│  │   Dynamic Sub-KG     │ ←──────── │   PageIndex Tree Search   │ │
│  │   (NetworkX DiGraph) │           │   (Agentic Retrieval)     │ │
│  └──────────────────────┘           └────────────────────────────┘ │
│                    ↑                                                │
│          Transition (GPT 관계 추론 → 엣지 생성)                    │
└───────────────────────────────────────────────────────────────────┘
      ↓ (4-hop 반복 후)
[최종 답변 + KG 시각화]
```

## 빠른 시작

```bash
# 1. 가상환경 활성화
source .venv/bin/activate

# 2. 실험 실행 (시뮬레이션 트리 사용)
python experiments/run_experiment.py

# 3. 결과 확인
open experiments/results/  # PNG + JSON

# 4. 실제 PDF → PageIndex 트리 생성
cd pageindex_core
python run_pageindex.py --pdf_path ../experiments/your_doc.pdf
```

## 프로젝트 구조

```
Agentic_tree_search/
├── pageindex_core/          # PageIndex 오픈소스 (GitHub 클론)
│   └── run_pageindex.py     # PDF → Tree JSON 생성
│
├── src/
│   ├── state/knowledge_graph.py    # Dynamic Sub-KG (G_t)
│   ├── environment/pageindex_env.py # World (PageIndex 트리 탐색)
│   ├── agent/
│   │   ├── gwm_agent.py            # GWM State-Action-Transition
│   │   └── reasoning.py            # GPT-4.1 추론 모듈
│   └── utils/visualize.py          # KG 시각화
│
└── experiments/
    ├── sample_fsar_tree.json       # NuScale FSAR 시뮬레이션 트리
    ├── run_experiment.py           # 실험 실행 스크립트
    └── results/                    # 출력 (PNG, JSON)
```

## 실험 시나리오

| 실험 | 질의 요약 | 기대 홉 수 |
|------|-----------|-----------|
| 1 | RCP 정지 사고 PCT vs. Tech Specs 한계치 | 4 hop |
| 2 | LOCA 10 CFR 50.46 3중 수락 기준 | 4 hop |

## PageIndex 오픈소스 사용법

```bash
cd pageindex_core
# .env에 CHATGPT_API_KEY=sk-... 설정됨
python run_pageindex.py --pdf_path /path/to/fsar.pdf --model gpt-4.1
```

생성된 트리 JSON을 `experiments/run_experiment.py`에서 로드하여 사용합니다.
