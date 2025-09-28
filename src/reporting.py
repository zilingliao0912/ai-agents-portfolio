from pathlib import Path
from datetime import datetime

def make_report(results, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use full timestamp down to seconds
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = output_dir / f"daily_report_{timestamp}.md"

    # Add header
    pretty_date = datetime.now().strftime("%B %d, %Y %H:%M:%S")
    lines = [f"# Sentiment Scout Daily Report\n", f"### Generated: {pretty_date}\n"]

    platforms = sorted(set(r.get("platform", "Unknown") for r in results))

    for platform in platforms:
        lines.append(f"## {platform}")

        # Show errors first
        for r in [x for x in results if x.get("platform") == platform and x.get("error")]:
            lines.append(f"- **Query**: {r.get('query', '')}")
            lines.append(f"- **Error**: {r.get('error', '')}")
            lines.append("")

        # Then table for valid rows
        valid_rows = [x for x in results if x.get("platform") == platform and not x.get("error")]
        if valid_rows:
            lines.append("| Headline | Topic | Sentiment | Likes | Comments | Link |")
            lines.append("|----------|-------|-----------|-------|----------|------|")
            for r in valid_rows[:5]:
                link = f"[Link]({r['link']})" if r.get("link") else ""
                lines.append(
                    f"| {r.get('headline','')} | {r.get('topic','other')} | "
                    f"{r.get('sentiment','neutral')} | {r.get('likes','')} | "
                    f"{r.get('comments','')} | {link} |"
                )
            lines.append("")

    report_file.write_text("\n".join(lines))
    return report_file
