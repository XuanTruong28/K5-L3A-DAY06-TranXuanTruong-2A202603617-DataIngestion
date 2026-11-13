"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def _is_evidence_hit(question: dict[str, Any], hit: dict[str, Any]) -> bool:
    """Kiểm tra xem chunk có thuộc đúng trang gold và chứa bằng chứng evidence không."""
    gold_page = int(question.get("gold_page", -1))
    hit_page = int(hit.get("page", -2))

    if gold_page != hit_page:
        return False

    evidence = question.get("evidence_quote", "").strip().lower()
    chunk_text = hit.get("text", "").lower()

    if not evidence or not chunk_text:
        return False

    # Kiểm tra trực tiếp đoạn trích
    if evidence in chunk_text:
        return True

    # Chuẩn hóa khoảng trắng để kiểm tra
    clean_ev = " ".join(evidence.split())
    clean_chunk = " ".join(chunk_text.split())
    if clean_ev in clean_chunk:
        return True

    # Kiểm tra cụm 5 từ đầu tiên của bằng chứng
    words = clean_ev.split()
    if len(words) >= 4:
        anchor = " ".join(words[:4])
        if anchor in clean_chunk:
            return True

    return False


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace."""
    hit_at_1 = 1 if (len(hits) > 0 and _is_evidence_hit(question, hits[0])) else 0
    hit_at_3 = 1 if any(_is_evidence_hit(question, h) for h in hits[:3]) else 0

    return {
        "question_id": question["id"],
        "split": question["split"],
        "type": question.get("type", "direct"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer", ""),
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
        "filter": question.get("filter"),
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "top_hits": [
            {
                "rank": idx + 1,
                "chunk_id": h.get("chunk_id"),
                "page": h.get("page"),
                "score": h.get("score"),
                "is_hit": _is_evidence_hit(question, h),
                "text_snippet": h.get("text", "")[:200]
            }
            for idx, h in enumerate(hits[:3])
        ]
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    dev_traces = [t for t in traces if t["split"] == "dev"]
    test_traces = [t for t in traces if t["split"] == "test"]

    def calc_metrics(subset: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(subset)
        if total == 0:
            return {"total": 0, "hit1_count": 0, "hit1_rate": 0.0, "hit3_count": 0, "hit3_rate": 0.0}
        h1 = sum(t["hit_at_1"] for t in subset)
        h3 = sum(t["hit_at_3"] for t in subset)
        return {
            "total": total,
            "hit1_count": h1,
            "hit1_rate": round(h1 / total * 100, 2),
            "hit3_count": h3,
            "hit3_rate": round(h3 / total * 100, 2)
        }

    return {
        "dev": calc_metrics(dev_traces),
        "test": calc_metrics(test_traces),
        "overall": calc_metrics(traces)
    }
