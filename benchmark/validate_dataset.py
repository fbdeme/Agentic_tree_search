# -*- coding: utf-8 -*-
"""GWM Benchmark 데이터셋 검증 스크립트.

200문항 데이터셋의 스키마, 분포, evidence 정합성을 검사합니다.

Usage:
    python -m benchmark.validate_dataset
    python -m benchmark.validate_dataset --dataset QADATASET/multihop_qa_benchmark_v2.json --strict
"""

import json
import argparse
from collections import Counter
from pathlib import Path

from benchmark.config import (
    BENCHMARK_V2_PATH,
    REASONING_TYPES,
    COMPLEXITY_LEVELS,
    QUESTION_TYPES,
    REQUIRED_FIELDS,
    EVIDENCE_REQUIRED_FIELDS,
)


def load_benchmark(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(questions: list[dict]) -> list[str]:
    """필수 필드 존재 여부 및 Enum 유효성 검증"""
    errors = []
    for q in questions:
        qid = q.get("id", "UNKNOWN")

        # 필수 필드
        for field in REQUIRED_FIELDS:
            if field not in q:
                errors.append(f"[{qid}] 필수 필드 누락: {field}")

        # Enum 유효성
        if q.get("reasoning_type") not in REASONING_TYPES:
            errors.append(f"[{qid}] 잘못된 reasoning_type: {q.get('reasoning_type')}")
        if q.get("complexity") not in COMPLEXITY_LEVELS:
            errors.append(f"[{qid}] 잘못된 complexity: {q.get('complexity')}")
        if q.get("question_type") not in QUESTION_TYPES:
            errors.append(f"[{qid}] 잘못된 question_type: {q.get('question_type')}")

        # 빈 필드
        if not q.get("question", "").strip():
            errors.append(f"[{qid}] question이 비어있음")
        if not q.get("expected_answer", "").strip():
            errors.append(f"[{qid}] expected_answer가 비어있음")
        if not q.get("answer_keywords"):
            errors.append(f"[{qid}] answer_keywords가 비어있음")

    return errors


def validate_id_uniqueness(questions: list[dict]) -> list[str]:
    """ID 중복 검사"""
    ids = [q.get("id") for q in questions]
    dupes = [qid for qid, count in Counter(ids).items() if count > 1]
    return [f"중복 ID 발견: {qid}" for qid in dupes]


def validate_distribution(questions: list[dict], declared: dict) -> list[str]:
    """선언된 분포 vs 실제 카운트 비교"""
    errors = []

    # reasoning_type × complexity matrix
    if "distribution" in declared:
        # distribution 키 형식: "factual_single", "factual_multi", "factual_cross"
        cx_short = {
            "single_evidence": "single",
            "multi_evidence": "multi",
            "cross_document": "cross",
        }
        for rt in REASONING_TYPES:
            for cx in COMPLEXITY_LEVELS:
                actual = sum(
                    1 for q in questions
                    if q.get("reasoning_type") == rt and q.get("complexity") == cx
                )
                key = f"{rt}_{cx_short[cx]}"
                expected = declared["distribution"].get(key, 0)
                if actual != expected:
                    errors.append(
                        f"분포 불일치 [{rt}/{cx}]: 선언={expected}, 실제={actual}"
                    )

    # question_type
    if "question_type_distribution" in declared:
        for qt, expected in declared["question_type_distribution"].items():
            actual = sum(1 for q in questions if q.get("question_type") == qt)
            if actual != expected:
                errors.append(
                    f"question_type 분포 불일치 [{qt}]: 선언={expected}, 실제={actual}"
                )

    return errors


def validate_evidence(questions: list[dict]) -> list[str]:
    """Evidence 완전성 및 정합성 검증"""
    errors = []

    for q in questions:
        qid = q.get("id", "UNKNOWN")
        evidence = q.get("ground_truth_evidence", [])
        complexity = q.get("complexity", "")
        qtype = q.get("question_type", "")

        if not evidence:
            errors.append(f"[{qid}] ground_truth_evidence가 비어있음")
            continue

        # evidence 필드 검사
        for i, ev in enumerate(evidence):
            for field in EVIDENCE_REQUIRED_FIELDS:
                if field not in ev or not ev[field]:
                    errors.append(f"[{qid}] evidence[{i}] 필드 누락/비어있음: {field}")

        # cross_document: 양쪽 챕터 포함 확인
        if complexity == "cross_document":
            docs = {ev.get("source_document") for ev in evidence}
            if not ("Ch.01" in docs and "Ch.05" in docs):
                errors.append(
                    f"[{qid}] cross_document인데 양쪽 챕터 미포함: {docs}"
                )

        # question_type vs source_type 정합성
        source_types = {ev.get("source_type") for ev in evidence}
        if qtype == "table_only" and "table" not in source_types:
            errors.append(f"[{qid}] table_only인데 table evidence 없음")
        if qtype == "image_only" and not (source_types & {"image", "figure"}):
            errors.append(f"[{qid}] image_only인데 image/figure evidence 없음")

    return errors


def detect_duplicates(questions: list[dict], threshold: float = 0.85) -> list[str]:
    """질문 텍스트 중복 탐지 (Jaccard 유사도)"""
    warnings = []

    def _tokenize(text: str) -> set[str]:
        return set(text.lower().split())

    for i in range(len(questions)):
        tokens_i = _tokenize(questions[i].get("question", ""))
        for j in range(i + 1, len(questions)):
            tokens_j = _tokenize(questions[j].get("question", ""))
            if not tokens_i or not tokens_j:
                continue
            jaccard = len(tokens_i & tokens_j) / len(tokens_i | tokens_j)
            if jaccard > threshold:
                warnings.append(
                    f"유사 질문 감지 (Jaccard={jaccard:.2f}): "
                    f"{questions[i]['id']} ↔ {questions[j]['id']}"
                )

    return warnings


def run_validation(dataset_path: str, strict: bool = False) -> bool:
    """전체 검증 실행"""
    print(f"\n{'='*60}")
    print(f"GWM Benchmark 데이터셋 검증")
    print(f"  파일: {dataset_path}")
    print(f"{'='*60}\n")

    data = load_benchmark(dataset_path)
    questions = data.get("questions", [])
    print(f"총 문항 수: {len(questions)}")

    all_errors = []
    all_warnings = []

    # 1. 스키마 검증
    print("\n[1/5] 스키마 검증...")
    errs = validate_schema(questions)
    all_errors.extend(errs)
    print(f"  → {len(errs)}건 오류")

    # 2. ID 중복
    print("[2/5] ID 고유성 검증...")
    errs = validate_id_uniqueness(questions)
    all_errors.extend(errs)
    print(f"  → {len(errs)}건 오류")

    # 3. 분포 검증
    print("[3/5] 분포 매트릭스 검증...")
    errs = validate_distribution(questions, data)
    all_errors.extend(errs)
    print(f"  → {len(errs)}건 오류")

    # 4. Evidence 검증
    print("[4/5] Evidence 정합성 검증...")
    errs = validate_evidence(questions)
    all_errors.extend(errs)
    print(f"  → {len(errs)}건 오류")

    # 5. 중복 탐지
    print("[5/5] 중복 질문 탐지...")
    warns = detect_duplicates(questions)
    all_warnings.extend(warns)
    print(f"  → {len(warns)}건 경고")

    # 분포 요약
    print(f"\n{'─'*60}")
    print("분포 요약:")
    rt_counts = Counter(q.get("reasoning_type") for q in questions)
    cx_counts = Counter(q.get("complexity") for q in questions)
    qt_counts = Counter(q.get("question_type") for q in questions)
    print(f"  reasoning_type: {dict(rt_counts)}")
    print(f"  complexity:     {dict(cx_counts)}")
    print(f"  question_type:  {dict(qt_counts)}")

    # 결과 출력
    print(f"\n{'='*60}")
    if all_errors:
        print(f"오류 {len(all_errors)}건:")
        for e in all_errors:
            print(f"  ❌ {e}")
    if all_warnings:
        print(f"\n경고 {len(all_warnings)}건:")
        for w in all_warnings:
            print(f"  ⚠️  {w}")

    if not all_errors and not all_warnings:
        print("✅ 모든 검증 통과!")
    elif not all_errors:
        print(f"\n✅ 오류 없음 (경고 {len(all_warnings)}건)")
    else:
        print(f"\n❌ 오류 {len(all_errors)}건 발견")

    passed = len(all_errors) == 0 if not strict else (len(all_errors) == 0 and len(all_warnings) == 0)
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GWM Benchmark 데이터셋 검증")
    parser.add_argument(
        "--dataset", default=str(BENCHMARK_V2_PATH),
        help="데이터셋 JSON 경로",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="경고도 실패로 처리",
    )
    args = parser.parse_args()

    passed = run_validation(args.dataset, args.strict)
    raise SystemExit(0 if passed else 1)
