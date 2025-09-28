# manager.py
"""
Manager Pipeline
- Runs Signal Agent (signal_v2.py)
- Picks top issue
- Runs Social Media Agent (social_media.py)
- Ends with a post on Twitter
"""

import subprocess, glob, pandas as pd, json

def run_signal_agent():
    print("🚀 Running Signal Agent...")
    subprocess.run(
        ["python", "signal_v2.py", "--query", "Solana reddit posts"],
        check=True
    )
    # Get latest ranked file
    latest = sorted(glob.glob("signal_ranked_*.csv"))[-1]
    print(f"📂 Using ranked file: {latest}")
    df = pd.read_csv(latest)
    top_issue = df.iloc[0].to_dict()
    with open("social_media_input.json", "w") as f:
        json.dump(top_issue, f, indent=2)
    print("✅ Saved top issue to social_media_input.json")

def run_social_media_agent():
    print("🚀 Running Social Media Agent...")
    subprocess.run(["python", "social_media.py"], check=True)

if __name__ == "__main__":
    run_signal_agent()
    run_social_media_agent()
    print("🎉 Full pipeline complete — issue scraped, meme generated, and posted to Twitter!")
