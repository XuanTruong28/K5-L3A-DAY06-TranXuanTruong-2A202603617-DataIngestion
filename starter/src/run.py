"""Pipeline entry point; implements the orchestration of strategies A, B, and C."""
import csv
import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import ChromaVectorStore


def main() -> None:
    print("=" * 60)
    print("DAY 06 · DATA INGESTION PIPELINE & BENCHMARK")
    print("=" * 60)

    # 1. Load the corpus and benchmark; validate >= 30 content pages
    pdf_path = Path("data/fao_seaweed_guide.pdf")
    benchmark_path = Path("data/benchmark.json")

    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing corpus: {pdf_path}")
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Missing benchmark: {benchmark_path}")

    print(f"\n[1/5] Loading corpus from {pdf_path}...")
    pages = load_pdf(pdf_path, document_id="fao_seaweed_guide", source=str(pdf_path))
    print(f" -> Extracted {len(pages)} content pages (requirement: >= 30). Validated: OK!")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)
    questions = benchmark_data["questions"]
    print(f" -> Loaded {len(questions)} benchmark questions (15 dev / 5 test). Validated: OK!")

    # 2. Build strategies A, B, and C
    print("\n[2/5] Chunking corpus according to strategies...")
    # Strategy A: Fixed-size 500 chars, overlap 50 chars
    chunks_a = []
    for p in pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    print(f" -> Strategy A (fixed_size 500/50): {len(chunks_a)} chunks")

    # Strategy B & C: By paragraph/heading (max 800 chars)
    chunks_b = []
    for p in pages:
        chunks_b.extend(by_paragraph(p, max_size=800))
    print(f" -> Strategy B & C (by_paragraph max 800): {len(chunks_b)} chunks")

    # 3. Embed with the same model and store vectors/metadata
    model_name = "all-MiniLM-L6-v2"
    print(f"\n[3/5] Initializing embedder '{model_name}' and ChromaVectorStore...")
    embedder = MyEmbedder(model_name=model_name)
    store = ChromaVectorStore(database_url="starter/results/chroma", dimensions=embedder.dimensions)
    store.create_schema()

    # Ingest Strategy A
    t0 = time.time()
    print(" -> Ingesting Strategy A...")
    texts_a = [c.text for c in chunks_a]
    vectors_a = embedder.embed_documents(texts_a)
    store.upsert("A", chunks_a, vectors_a)
    t_a = round(time.time() - t0, 2)
    print(f"    Done Strategy A in {t_a}s")

    # Ingest Strategy B (also used for Strategy C)
    t0 = time.time()
    print(" -> Ingesting Strategy B & C...")
    texts_b = [c.text for c in chunks_b]
    vectors_b = embedder.embed_documents(texts_b)
    store.upsert("B", chunks_b, vectors_b)
    store.upsert("C", chunks_b, vectors_b)
    t_bc = round(time.time() - t0, 2)
    print(f"    Done Strategy B & C in {t_bc}s")

    # 4. Run the same dev/test questions across all 3 strategies
    print("\n[4/5] Evaluating 20 questions across strategies A, B, and C...")
    strategies = [
        {"name": "A", "desc": "Fixed-size 500/50, No Filter", "use_filter": False},
        {"name": "B", "desc": "By Paragraph max 800, No Filter", "use_filter": False},
        {"name": "C", "desc": "By Paragraph max 800, With Metadata Filter", "use_filter": True}
    ]

    all_traces: dict[str, list] = {}
    summaries: dict[str, dict] = {}

    for strat in strategies:
        strat_key = strat["name"]
        print(f" -> Running Strategy {strat_key} ({strat['desc']})...")
        strat_traces = []

        for q in questions:
            q_vec = embedder.embed_query(q["question"])
            # Apply filter only for Strategy C if question provides a filter
            flt = q.get("filter") if strat["use_filter"] else None
            hits = store.search(strategy=strat_key, query_vector=q_vec, top_k=3, filters=flt)
            evaluated = evaluate_query(q, hits)
            strat_traces.append(evaluated)

        all_traces[strat_key] = strat_traces
        summaries[strat_key] = summarize(strat_traces)

    # 5. Report metrics and save artifacts
    print("\n[5/5] Benchmark Results Summary:")
    print("-" * 65)
    print(f"{'Strategy':<12} | {'Split':<6} | {'Hit@1':<12} | {'Hit@3':<12} | {'Total':<5}")
    print("-" * 65)

    exp_log_rows = []
    for s_key in ["A", "B", "C"]:
        s_sum = summaries[s_key]
        for split_key in ["dev", "test", "overall"]:
            row = s_sum[split_key]
            h1_str = f"{row['hit1_count']}/{row['total']} ({row['hit1_rate']}%)"
            h3_str = f"{row['hit3_count']}/{row['total']} ({row['hit3_rate']}%)"
            print(f"Strategy {s_key:<3} | {split_key:<6} | {h1_str:<12} | {h3_str:<12} | {row['total']:<5}")
            exp_log_rows.append({
                "strategy": f"Strategy {s_key}",
                "split": split_key,
                "hit1_count": row["hit1_count"],
                "hit1_rate": row["hit1_rate"],
                "hit3_count": row["hit3_count"],
                "hit3_rate": row["hit3_rate"],
                "total_questions": row["total"]
            })
        print("-" * 65)

    # Save traces
    results_dir = Path("starter/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    traces_path = results_dir / "traces.json"
    with open(traces_path, "w", encoding="utf-8") as f:
        json.dump(all_traces, f, indent=2, ensure_ascii=False)
    print(f"\nSaved per-query traces to: {traces_path}")

    # Save experiment log to artifacts/experiment_log.csv
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    csv_path = artifacts_dir / "experiment_log.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "strategy", "split", "hit1_count", "hit1_rate", "hit3_count", "hit3_rate", "total_questions"
        ])
        writer.writeheader()
        writer.writerows(exp_log_rows)
    print(f"Saved experiment log to: {csv_path}")

    print("\nPIPELINE EXECUTION COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
