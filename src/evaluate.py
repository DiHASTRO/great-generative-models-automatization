import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.models import ReviewAnalysis
from src.one_shot import analyze_one_shot
from src.workflow import analyze_workflow


FALLBACK_ONE_SHOT = ReviewAnalysis(
    overall_sentiment="neutral",
    aspects=[],
    summary="",
    business_recommendation="",
)

FALLBACK_WORKFLOW = ReviewAnalysis(
    overall_sentiment="neutral",
    aspects=[],
    summary="Не удалось выполнить анализ.",
    business_recommendation="Требуется ручная проверка.",
)


@dataclass
class RunResult:
    case_id: int
    architecture: str
    success: bool
    latency_s: float
    llm_calls: int
    total_tokens: int
    sentiment_acc: float
    aspect_f1: float
    error: Optional[str] = None


def sentiment_accuracy(pred: ReviewAnalysis, expected: str) -> float:
    return 1.0 if pred.overall_sentiment == expected else 0.0


def aspect_f1(pred: ReviewAnalysis, expected_aspects: List[str]) -> float:
    if not expected_aspects and not pred.aspects:
        return 1.0
    if not expected_aspects or not pred.aspects:
        return 0.0

    pred_names = [a.name.lower().strip() for a in pred.aspects]
    exp_names = [e.lower().strip() for e in expected_aspects]

    def match(e: str, p: str) -> bool:
        return e in p or p in e

    tp = 0
    used_pred = set()
    for e in exp_names:
        for i, p in enumerate(pred_names):
            if i not in used_pred and match(e, p):
                tp += 1
                used_pred.add(i)
                break

    precision = tp / len(pred_names) if pred_names else 0.0
    recall = tp / len(exp_names) if exp_names else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def run_one_shot(
    review_text: str,
) -> tuple[ReviewAnalysis, float, int, int, bool, Optional[str]]:
    start = time.perf_counter()
    try:
        result, tokens = analyze_one_shot(review_text)
        return result, time.perf_counter() - start, 1, tokens, True, None
    except Exception as e:
        return (
            FALLBACK_ONE_SHOT,
            time.perf_counter() - start,
            1,
            0,
            False,
            f"{type(e).__name__}: {e}",
        )


def run_workflow(
    review_text: str,
) -> tuple[ReviewAnalysis, float, int, int, bool, Optional[str]]:
    start = time.perf_counter()
    try:
        result, tokens = analyze_workflow(review_text)
        return result, time.perf_counter() - start, 2, tokens, True, None
    except Exception as e:
        return (
            FALLBACK_WORKFLOW,
            time.perf_counter() - start,
            2,
            0,
            False,
            f"{type(e).__name__}: {e}",
        )


def main() -> None:
    data_path = Path(__file__).resolve().parent.parent / "data" / "test_cases.json"
    cases = json.loads(data_path.read_text(encoding="utf-8"))

    results: List[RunResult] = []

    for case in cases:
        cid = case["id"]
        text = case["text"]
        expected_sent = case["expected_sentiment"]
        expected_aspects = case.get("expected_aspects", [])

        pred_os, lat_os, calls_os, tok_os, succ_os, err_os = run_one_shot(text)
        if err_os:
            print(f"[one-shot case {cid}] {err_os}")
        results.append(
            RunResult(
                case_id=cid,
                architecture="one-shot",
                success=succ_os,
                latency_s=lat_os,
                llm_calls=calls_os,
                total_tokens=tok_os,
                sentiment_acc=sentiment_accuracy(pred_os, expected_sent),
                aspect_f1=aspect_f1(pred_os, expected_aspects),
                error=err_os,
            )
        )

        pred_wf, lat_wf, calls_wf, tok_wf, succ_wf, err_wf = run_workflow(text)
        if err_wf:
            print(f"[workflow case {cid}] {err_wf}")
        results.append(
            RunResult(
                case_id=cid,
                architecture="workflow",
                success=succ_wf,
                latency_s=lat_wf,
                llm_calls=calls_wf,
                total_tokens=tok_wf,
                sentiment_acc=sentiment_accuracy(pred_wf, expected_sent),
                aspect_f1=aspect_f1(pred_wf, expected_aspects),
                error=err_wf,
            )
        )

        print(f"\ncase {cid}: expected={expected_sent!r}")
        print(
            f"  one-shot pred: {pred_os.overall_sentiment!r}, "
            f"aspects={[a.name for a in pred_os.aspects]}"
        )
        print(
            f"  workflow pred: {pred_wf.overall_sentiment!r}, "
            f"aspects={[a.name for a in pred_wf.aspects]}"
        )

    def agg(arch: str) -> Dict[str, float]:
        subset = [r for r in results if r.architecture == arch]
        n = len(subset) or 1
        return {
            "success_rate": sum(r.success for r in subset) / n,
            "sentiment_acc": sum(r.sentiment_acc for r in subset) / n,
            "aspect_f1": sum(r.aspect_f1 for r in subset) / n,
            "avg_latency_s": sum(r.latency_s for r in subset) / n,
            "avg_llm_calls": sum(r.llm_calls for r in subset) / n,
            "avg_tokens": sum(r.total_tokens for r in subset) / n,
        }

    summary = {
        "one-shot": agg("one-shot"),
        "workflow": agg("workflow"),
    }

    print("\n=== СВОДКА ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    out = Path(__file__).resolve().parent.parent / "results_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nСводка сохранена в {out}")


if __name__ == "__main__":
    main()
