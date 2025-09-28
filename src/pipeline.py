# sentiment_scout/pipeline.py

from pathlib import Path
import json
from datetime import datetime
from .client import BagoodexClient


def run_queries(queries, raw_dir: Path, processed_dir: Path):
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    client = BagoodexClient()
    results = []

    # Timestamped filenames
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    raw_file = raw_dir / f"{timestamp}.jsonl"
    summary_file = processed_dir / f"{timestamp}_summary.json"

    with open(raw_file, "w") as rf:
        for q in queries:
            try:
                posts = client.search(q)

                for p in posts:
                    # Analyze headline
                    analysis = client.analyze_text(p.get("headline", ""))

                    # Merge search + analysis into one row
                    result = {
                        "query": q,
                        "platform": p.get("platform", "Other"),
                        "headline": p.get("headline", ""),
                        "link": p.get("url") or "",  # only use "url"
                        "likes": p.get("likes", 0),
                        "comments": p.get("comments", 0),
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "topic": analysis.get("topic", "other"),
                        "summary": analysis.get("summary", ""),
                        "error": p.get("error", None),
                    }
                    results.append(result)
                    rf.write(json.dumps(result) + "\n")

            except Exception as e:
                error_result = {
                    "query": q,
                    "platform": "Other",
                    "headline": "",
                    "link": "",
                    "likes": 0,
                    "comments": 0,
                    "sentiment": "neutral",
                    "topic": "other",
                    "summary": "",
                    "error": str(e),
                }
                results.append(error_result)
                rf.write(json.dumps(error_result) + "\n")

    with open(summary_file, "w") as sf:
        json.dump(results, sf, indent=2)

    return results, raw_file, summary_file
