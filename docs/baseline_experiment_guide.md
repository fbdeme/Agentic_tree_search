# Baseline Experiment Guide (v2)

비교 모델 실험을 위한 가이드 문서입니다. 이 문서를 읽고 각 방법론의 답변을 수집한 뒤, 기존 평가 파이프라인으로 평가하면 됩니다.

> **v2 변경사항 (2026-03-31)**
> 1. 공식 코드/라이브러리 사용 필수 (자체 구현 금지)
> 2. RAGAs 평가 필수 (`retrieved_contexts` 필수 필드로 승격)
> 3. 재현성 데이터 저장 필수 (context, 타이밍, 인덱스 파일)
> 4. 라이브러리 버전 고정 기록 필수
> 5. 인덱스 파일 보존 필수

---

## 1. 프로젝트 배경

### 1.1 연구 개요

이 프로젝트는 **GWM(Graph World Model) 기반 멀티모달 규제 문서 탐색 에이전트**입니다.

원자력 안전성 분석 보고서(FSAR)를 대상으로, 에이전트가 문서를 탐색하며 **동적 지식그래프(Dynamic Sub-KG)**를 구축하고, 이를 기반으로 규제 심사 질의에 답변합니다.

핵심 특징:
- **Vectorless**: 벡터 임베딩 없이 BM25 + LLM 추론으로 검색
- **Tool-based exploration**: browse/read/search 도구로 문서 탐색 (파일 시스템처럼)
- **Two-stage edge inference**: 자연어 설명 먼저 → 온톨로지 레이블 매핑 (9개 엣지 유형)
- **Vision RAG**: 그림은 VLM 이미지로, 표는 구조화 텍스트로 처리
- **Dual evaluation**: RAGAs + LLM-as-Judge 두 프레임워크로 평가

### 1.2 현재 결과 (GWM Agent v0.4.6)

| 지표 | 값 |
|------|-----|
| LLM-as-Judge Accuracy | **81.0%** (162/200) |
| RAGAs Faithfulness | **0.93** |
| RAGAs Context Recall | **0.93** |
| judgment + cross_document Accuracy | **94%** |

### 1.3 비교 실험의 목적

동일한 벤치마크(200문항)와 동일한 평가 프레임워크로 **LightRAG, GraphRAG, RAPTOR, HippoRAG**의 성능을 측정하여, GWM 방법론의 기여를 분리합니다.

---

## 2. 실험 환경 설정

### 2.1 레포지토리 클론

```bash
git clone https://github.com/fbdeme/Agentic_tree_search.git
cd Agentic_tree_search
```

### 2.2 가상환경 + 의존성

```bash
python -m venv .venv
source .venv/bin/activate

pip install openai networkx matplotlib python-dotenv ragas langchain-openai \
            langchain-anthropic mlflow pandas tqdm seaborn rank-bm25 PyMuPDF
```

### 2.3 API Keys

`.env` 파일을 프로젝트 루트에 생성:

```
OPENAI_API_KEY=sk-...          # GPT-4.1 (답변 생성) + GPT-4-turbo/4o (평가)
ANTHROPIC_API_KEY=sk-ant-...   # Claude Sonnet 4.5 (Allganize 평가)
```

### 2.4 소스 문서

`data/documents/` 디렉토리에 아래 PDF를 배치 (NRC 공개 문서):
- `NuScale FSAR Ch.01 (공개본).pdf` (352페이지)
- `NuScale FSAR Ch.05 (공개본).pdf` (160페이지)

### 2.5 벤치마크 데이터셋

이미 포함되어 있음: `data/qa_dataset/multihop_qa_benchmark_v2.json`
- 200문항
- 3축 분류: reasoning_type(factual/comparative/judgment) × complexity(single/multi/cross) × modality(text/table/image/composite)

---

## 3. 비교 대상 방법론

### 3.1 담당 배정

| 방법론 | 논문 | 핵심 특징 | 담당 |
|--------|------|---------|------|
| **LightRAG** | Guo et al. (2024) | 이중 레벨(entity + topic) 그래프 검색 | TBD |
| **GraphRAG** | Edge et al. (2024) | 커뮤니티 기반 글로벌/로컬 검색 | TBD |
| **RAPTOR** | Sarthi et al. (2024) | 재귀적 트리 요약 + 클러스터링 | TBD |
| **HippoRAG** | Gutierrez et al. (2024) | 해마 기반 연상 메모리 + KG | TBD |

### 3.2 각 방법론이 구현해야 하는 것

```
입력:
  1. NuScale FSAR Ch.01 + Ch.05 (PDF 파일)
  2. 질문 200개 (multihop_qa_benchmark_v2.json)

출력 (모두 필수):
  1. predictions JSON 파일 (아래 스키마, retrieved_contexts 포함)
  2. LLM-as-Judge 평가 결과
  3. RAGAs 평가 결과
  4. 인덱스 파일 (재현용)
  5. 구현 노트 (라이브러리 버전, 인덱싱 시간/비용 포함)

평가:
  기존 파이프라인 사용 (본인이 직접 돌리거나, 결과 파일만 push)
```

---

## 4. 공정한 비교를 위한 규칙

### 4.1 반드시 통일해야 하는 것

| 항목 | 값 | 이유 |
|------|-----|------|
| **공식 코드 사용** | 아래 4.4절 참조 | 자체 구현은 구현 차이가 결과를 오염시킴 |
| **생성 LLM** | `gpt-4.1` | 모델 성능 차이가 방법론 비교를 오염시킴 |
| **Temperature** | `0` 또는 `0.1` | 재현성 |
| **답변 길이** | 1-2 문장 (max_tokens=300) | GWM과 동일 조건 |
| **데이터셋** | `multihop_qa_benchmark_v2.json` 전체 200문항 | 동일 벤치마크 |
| **소스 문서** | 동일 PDF 2개 | 동일 정보 접근 |
| **평가 프레임워크** | LLM-as-Judge + RAGAs 모두 | 이중 평가로 결과 신뢰도 확보 |

### 4.2 방법론별로 달라도 되는 것

| 항목 | 설명 |
|------|------|
| **인덱싱 방법** | 벡터 DB, KG 구축, 트리 요약 등 각 방법론 고유의 사전 처리 |
| **검색 방법** | 벡터 유사도, 그래프 순회, 키워드 매칭 등 |
| **임베딩 모델** | text-embedding-3-small 등 (사용 시 명시) |
| **Chunk 크기** | 각 방법론의 권장 설정 사용 |

### 4.3 답변 생성 프롬프트

**모든 방법론에서 동일한 프롬프트를 사용하세요:**

```python
system_prompt = (
    "You are an expert AI for nuclear regulatory review. "
    "Based on the provided context, answer the user's question. "
    "Answer in 1-2 sentences ONLY. "
    "State the direct answer with specific values, then cite the source. "
    "Do NOT add uncertainty statements, background, or methodology. "
    "Do NOT add information not found in the provided context. "
    "Answer in English."
)
```

이 프롬프트는 GWM 에이전트의 `generate_answer()`와 동일합니다. 검색된 context를 user message에 포함하고, 위 system prompt로 답변을 생성하세요.

### 4.4 공식 코드/라이브러리 사용 규칙

**반드시 각 방법론의 공식 구현을 사용하세요. 자체 재구현은 금지합니다.**

논문의 공정한 비교를 위해, 리뷰어가 "구현 차이가 결과를 좌우한 것 아닌가"라는 의문을 제기하지 못하도록 공식 코드를 사용해야 합니다.

| 방법론 | 설치 방법 | 비고 |
|--------|----------|------|
| **LightRAG** | `pip install lightrag-hku` | PyPI 패키지 |
| **GraphRAG** | `pip install graphrag` | PyPI 패키지 (Python ≥3.11) |
| **RAPTOR** | 공식 레포 clone 후 코드 통합 (아래 참조) | PyPI 없음, 패키지 구조가 아님 |
| **HippoRAG** | `pip install hipporag` | PyPI 패키지 (Python ≥3.10) |

- 공식 라이브러리의 API를 통해 인덱싱/검색/답변 생성을 수행
- 생성 LLM만 `gpt-4.1`로 교체하고, 나머지 파라미터는 각 라이브러리의 기본값 또는 논문 권장값 사용
- 라이브러리 버그로 인한 최소한의 패치(예: 호환성 수정)는 허용하되, **구현 노트에 무엇을 왜 수정했는지 반드시 기록**
- 사용한 라이브러리 **버전을 정확히 기록** (예: `lightrag-hku==1.4.12`, `hipporag==2.0.0a4`)

---

## 5. 출력 형식 (Predictions JSON)

### 5.1 스키마

```json
{
  "method": "lightrag",
  "model": "gpt-4.1",
  "timestamp": "2026-03-27T10:00:00",
  "total": 200,
  "library_version": "lightrag-hku==1.4.12",
  "results": [
    {
      "id": "Q001",
      "question": "What is the total net electrical output...",
      "expected_answer": "The total net electrical output...",
      "generated_answer": "The total net electrical output of a full 12-module NuScale plant is approximately 570 MWe.",
      "retrieved_contexts": [
        "Chapter 1, Section 1.1: The NuScale Power Plant design ...",
        "Table 1.3-1: Key parameters include ..."
      ],
      "reasoning_type": "factual",
      "complexity": "single_evidence",
      "question_type": "text_only",
      "n_chunks_retrieved": 5,
      "retrieval_time_sec": 1.2,
      "generation_time_sec": 3.5
    }
  ]
}
```

### 5.2 필수 필드

| 필드 | 설명 |
|------|------|
| `id` | 질문 ID (Q001~Q200) — 벤치마크에서 그대로 복사 |
| `question` | 질문 텍스트 — 벤치마크에서 그대로 복사 |
| `expected_answer` | 기대 정답 — 벤치마크에서 그대로 복사 |
| `generated_answer` | **방법론이 생성한 답변** |
| `retrieved_contexts` | **검색된 context 텍스트 리스트** (RAGAs 평가에 필수) |
| `reasoning_type` | factual / comparative / judgment — 벤치마크에서 복사 |
| `complexity` | single_evidence / multi_evidence / cross_document — 복사 |
| `question_type` | text_only / table_only / image_only / composite — 복사 |

### 5.3 필수 재현성 필드

| 필드 | 설명 |
|------|------|
| `n_chunks_retrieved` | 검색된 chunk/node 수 |
| `retrieval_time_sec` | 검색 소요 시간 (초) |
| `generation_time_sec` | 답변 생성 소요 시간 (초) |
| `error` | 에러 발생 시 메시지 (정상이면 생략 가능) |

### 5.4 메타데이터 필수 필드 (JSON 최상위)

| 필드 | 설명 |
|------|------|
| `method` | 방법론명 (예: `lightrag`) |
| `model` | 생성 LLM (예: `gpt-4.1`) |
| `library_version` | 라이브러리 버전 (예: `lightrag-hku==1.4.12`) |
| `timestamp` | 실행 시각 |
| `total` | 총 문항 수 |

### 5.5 파일 저장 위치

각 방법론별 폴더에 저장합니다:

```
benchmark/results/
  gwm/                    # GWM Agent (기존 결과)
    pred_gwm_v046_*.json
    judge_gwm_v046_*.json
  lightrag/               # ← 여기에 저장
    pred.json             # 답변 + retrieved_contexts (필수)
    judge.json            # LLM-as-Judge 결과 (필수)
    ragas.json            # RAGAs 평가 결과 (필수)
    note.md               # 구현 노트 (필수)
    index/                # 인덱스 파일 (필수, 재현용)
  graphrag/               # ← 동일 구조
  raptor/                 # ← 동일 구조
  hipporag/               # ← 동일 구조
```

병렬로 분할 실행한 경우 `pred_1.json ~ pred_8.json`처럼 번호를 붙여도 됩니다.

---

## 6. 평가 실행 방법

### 6.1 LLM-as-Judge (필수)

```bash
source .venv/bin/activate

python -m benchmark.llm_judge benchmark/results/lightrag/pred.json \
  --output benchmark/results/lightrag/judge.json
```

3개 evaluator가 순차 실행됩니다:
1. **Tonic AI** (GPT-4-turbo): Similarity 0-5, ≥4 → O
2. **MLflow** (GPT-4o): Similarity + Correctness 1-5, both≥4 → O (2표)
3. **Allganize** (Claude Sonnet 4.5): Correctness 0/1, =1 → O

4표 majority vote → 최종 O/X → Accuracy

예상 시간: 200문항 × ~30초 = **~100분**
예상 비용: ~$13 (GPT-4-turbo + GPT-4o + Claude Sonnet)

### 6.2 RAGAs (필수)

**`retrieved_contexts`가 pred.json에 포함되어 있어야 합니다.**

```bash
# 베이스라인용 RAGAs 평가
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate_baseline_ragas.py \
  --pred benchmark/results/lightrag/pred.json \
  --output benchmark/results/lightrag/ragas.json
```

측정 지표:
- **Faithfulness**: 답변이 검색된 context에 근거하는지 (환각 여부)
- **Context Recall**: 정답에 필요한 정보가 검색된 context에 포함되어 있는지

예상 시간: 200문항 × ~15초 = **~50분**
예상 비용: ~$5

> 기존 GWM용 `experiments/evaluate.py`는 에이전트를 실행하며 KG를 구축하므로 베이스라인에는 사용할 수 없습니다. 별도 스크립트 `experiments/evaluate_baseline_ragas.py`를 사용하세요.

### 6.3 결과 확인

```bash
# LLM-as-Judge 결과
python3 -c "
import json
with open('benchmark/results/lightrag/judge.json') as f:
    data = json.load(f)
print(f'Accuracy: {data[\"summary\"][\"accuracy\"]*100:.1f}%')
for rt in ['factual','comparative','judgment']:
    stats = data['by_reasoning_type'].get(rt, {})
    print(f'  {rt}: {stats.get(\"accuracy\",0)*100:.1f}%')
"

# RAGAs 결과
python3 -c "
import json
with open('benchmark/results/lightrag/ragas.json') as f:
    data = json.load(f)
for metric in ['faithfulness', 'context_recall']:
    print(f'{metric}: {data[\"summary\"][metric]:.4f}')
"
```

---

## 7. Git 작업 흐름

### 7.1 브랜치 전략

```bash
# 메인에서 브랜치 생성
git checkout -b baseline/{방법론명}

# 예시
git checkout -b baseline/lightrag
```

### 7.2 커밋할 파일

```
benchmark/results/{방법론명}/pred.json    # 답변 + context (필수)
benchmark/results/{방법론명}/judge.json   # LLM-as-Judge 결과 (필수)
benchmark/results/{방법론명}/ragas.json   # RAGAs 결과 (필수)
benchmark/results/{방법론명}/note.md      # 구현 노트 (필수)
benchmark/results/{방법론명}/index/       # 인덱스 파일 (필수, 재현용)
```

### 7.3 구현 노트에 포함할 내용 (필수)

```markdown
# {방법론명} Baseline 구현 노트

## 환경
- LLM: gpt-4.1
- 라이브러리: {패키지명}=={버전} (예: lightrag-hku==1.4.12)
- Python: {버전}
- 임베딩: text-embedding-3-small (해당 시)
- Chunk size: 512 tokens (해당 시)

## 공식 코드 수정 사항
- (라이브러리 버그 패치 등이 있으면 기록, 없으면 "없음")

## 인덱싱
- 방법: ...
- 소요 시간: ...분
- 인덱스 크기: ...MB
- 인덱스 파일 위치: benchmark/results/{방법론명}/index/

## 검색 설정
- Top-K: ...
- 기타 파라미터: ...

## 결과
- LLM-as-Judge Accuracy: ...%
- RAGAs Faithfulness: ...
- RAGAs Context Recall: ...
- 특이사항: ...
```

### 7.4 Push

```bash
git add benchmark/results/{방법론명}/
git commit -m "Add {방법론명} baseline: Accuracy XX.X%, Faith X.XX, CR X.XX"
git push origin baseline/{방법론명}
```

이후 Pull Request를 생성하면 메인에 머지합니다.

---

## 8. 방법론별 구현 힌트

### 8.1 LightRAG

```
논문: Guo et al., "LightRAG: Simple and Fast RAG" (2024)
GitHub: https://github.com/HKUDS/LightRAG
설치: pip install lightrag-hku

핵심:
- PDF → 텍스트 추출 → 엔티티/관계 추출 → 그래프 구축
- 이중 레벨 검색: low-level (엔티티) + high-level (토픽)
- 벡터 DB 필요 (nano-vectordb 또는 FAISS)

주의:
- 생성 LLM을 gpt-4.1로 통일
- 인덱싱에 사용하는 LLM도 기록 (보통 gpt-4o-mini)
- 검색 결과에서 retrieved_contexts를 반드시 추출하여 저장
```

### 8.2 GraphRAG

```
논문: Edge et al., "From Local to Global" (2024)
GitHub: https://github.com/microsoft/graphrag
설치: pip install graphrag  (Python ≥3.11 필요)

핵심:
- PDF → 텍스트 추출 → 엔티티/관계 추출 → 커뮤니티 탐지 → 요약
- Local search (관련 엔티티 주변) + Global search (커뮤니티 요약)
- 사전 인덱싱 비용 높음

주의:
- settings.yaml에서 LLM을 gpt-4.1로 설정
- 인덱싱 시간과 비용 반드시 기록
- 검색 결과에서 retrieved_contexts를 반드시 추출하여 저장
```

### 8.3 RAPTOR

```
논문: Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval" (2024)
GitHub: https://github.com/parthsarthi03/raptor
설치: PyPI 패키지 없음, pip install 불가

RAPTOR는 공식 레포가 패키지 구조가 아니라 pip 설치가 안 됩니다.
공식 레포(https://github.com/parthsarthi03/raptor)의 코드를 clone하여
핵심 로직(클러스터링, 트리 구축, 검색)을 가져와 통합하세요.

코드 위치: baseline_experiment/raptor/
스크립트: baseline_experiment/scripts/

핵심:
- 텍스트 → chunk → 클러스터링(UMAP+GMM) → 요약 → 재귀적 트리 구축
- 검색 시 트리의 적절한 레벨에서 요약 선택
- 임베딩 기반 유사도 검색

주의:
- 공식 레포의 알고리즘을 충실히 따를 것 (클러스터링, 트리 구축 로직)
- 변경한 부분은 구현 노트에 반드시 기록 (예: LLM 교체, 임베딩 모델 교체)
- 트리 구축에 LLM 호출 많음 (요약 생성)
- collapse_tree vs tree_traversal 두 가지 검색 모드 중 선택
- 검색 결과에서 retrieved_contexts를 반드시 추출하여 저장
```

### 8.4 HippoRAG

```
논문: Gutierrez et al., "HippoRAG: Neurobiologically Inspired Long-Term Memory for LLMs" (2024)
GitHub: https://github.com/OSU-NLP-Group/HippoRAG
설치: pip install hipporag  (Python ≥3.10 필요)

핵심:
- 해마(Hippocampus) 기반 연상 메모리 모델
- 오프라인 인덱싱: 텍스트 → 엔티티 추출 → KG 구축
- 온라인 검색: 패턴 분리 → 패턴 완성 → 관련 passage 검색

주의:
- OpenIE 기반 엔티티/관계 추출
- Colbert 또는 Contriever 기반 passage 검색
- 의존성이 복잡할 수 있음 — 별도 venv 권장
- 검색 결과에서 retrieved_contexts를 반드시 추출하여 저장
```

---

## 9. 기록해야 하는 비용/효율 지표

| 지표 | 설명 | GWM 참고값 |
|------|------|-----------|
| 사전 인덱싱 시간 | PDF → 인덱스 구축 | 0분 (vectorless) |
| 사전 인덱싱 LLM 호출 | 인덱싱에 사용된 API 호출 수 | 0 |
| 사전 인덱싱 비용 | API 비용 | $0 |
| 문항당 평균 시간 | 질문 → 답변 소요 | ~100초 |
| 문항당 평균 LLM 호출 | 검색+생성에 사용된 API 호출 | ~20회 |
| 200문항 총 비용 | API 비용 | ~$25 |

---

## 10. FAQ

**Q: PDF에서 텍스트를 어떻게 추출하나요?**
A: 각 방법론의 권장 방식을 사용하세요. 대부분 PyMuPDF, PyPDF2, 또는 자체 파서를 사용합니다. GWM은 PyMuPDF `page.get_text()`를 사용합니다.

**Q: 테이블과 이미지는 어떻게 처리하나요?**
A: 각 방법론의 방식대로 처리하세요. 처리 못하는 경우 텍스트만으로 답변해도 됩니다. 어떻게 처리했는지 구현 노트에 기록해주세요.

**Q: 200문항 중 일부만 먼저 테스트할 수 있나요?**
A: 네. `--start 1 --end 10` 등으로 범위 지정 가능. 파일럿(5~10문항)으로 먼저 검증 후 전체를 돌리는 것을 권장합니다.

**Q: 답변에 인용(citation)을 포함해야 하나요?**
A: 포함해도 되고 안 해도 됩니다. 평가 시 `remove_citations()` 함수가 자동으로 인용을 제거합니다.

**Q: 에러가 발생한 문항은 어떻게 하나요?**
A: `generated_answer` 필드에 에러 메시지를 기록하고, `error` 필드를 추가하세요. 평가 시 해당 문항은 X(오답)로 처리됩니다.

**Q: Claude Code를 사용해서 구현해도 되나요?**
A: 네. 이 레포를 clone한 상태에서 Claude Code를 사용하면 `CLAUDE.md`와 `docs/` 파일들이 자동으로 컨텍스트에 포함되어 프로젝트 구조를 이해한 상태로 작업할 수 있습니다.

**Q: 공식 라이브러리에 버그가 있어서 수정해야 하는데요?**
A: 최소한의 패치는 허용됩니다. 단, **무엇을 왜 수정했는지 구현 노트에 반드시 기록**하세요. 알고리즘 자체를 변경하는 수정은 금지입니다.

**Q: RAPTOR는 PyPI 패키지가 없는데요?**
A: `pip install git+https://github.com/parthsarthi03/raptor.git`으로 공식 레포에서 직접 설치하세요. 자체 재구현은 금지입니다.

**Q: retrieved_contexts는 어떤 형태로 저장하나요?**
A: 문자열 리스트(`list[str]`)로 저장하세요. 각 문자열은 검색된 하나의 chunk/passage/node의 텍스트입니다. RAGAs가 이 형태를 기대합니다.

---

## 11. 체크리스트

```
[ ] 레포 clone + 환경 설정
[ ] .env에 API Keys 추가
[ ] 소스 PDF 배치 (data/documents/)
[ ] 공식 라이브러리 설치 (자체 구현 금지)
[ ] 라이브러리 버전 기록
[ ] 인덱싱 수행 + 인덱스 파일 보존
[ ] 파일럿 테스트 (5~10문항, retrieved_contexts 포함 확인)
[ ] 전체 200문항 답변 수집 → pred.json (retrieved_contexts 포함 필수)
[ ] LLM-as-Judge 평가 실행 → judge.json
[ ] RAGAs 평가 실행 → ragas.json
[ ] 구현 노트 작성 → note.md (라이브러리 버전, 패치 내역, 인덱싱 시간/비용)
[ ] 인덱스 파일 → index/ 폴더에 저장
[ ] 브랜치에 push + PR 생성
```
