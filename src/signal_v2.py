# signal.py
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import argparse
import pandas as pd
import subprocess

# ------------------------
# Env
# ------------------------
load_dotenv()
PROVIDER = os.getenv("PROVIDER", "llama")  # aimlapi | openai | llama
AIML_API_KEY = os.getenv("AIML_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Endpoints
AIML_API_URL = "https://api.aimlapi.com/v1/chat/completions"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# ------------------------
# Prompts
# ------------------------
SIGNAL_SCOUT_PROMPT = """You are Signal Scout. Convert Solana-related posts into JSON objects.

Schema:
{ "issue_text": "...", "summary": "...", "user_type": "...", "platform": "...",
  "topic": "...", "buzzwords": ["..."], "sentiment": "...",
  "lifecycle_stage": "...", "engagement_score": 0, "timestamp": "YYYY-MM-DD HH:MM:SS"
}
"""

PRIORITIZER_PROMPT = """You are the Prioritizer Agent. Rank top 3 issues from a list.
Rules: rank by engagement_score > sentiment (Neg>Neu>Pos) > lifecycle_stage.
Return exactly 3 issues with all fields + add "rank": 1–3. JSON array only.
"""

# ------------------------
# Model Router
# ------------------------
def model_call(system_prompt, user_content, max_tokens=800):
    """Route to AIML, OpenAI, or local LLaMA. Fallback to sample file if fails."""
    try:
        if PROVIDER == "aimlapi":
            headers = {"Authorization": f"Bearer {AIML_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "bagoodex/bagoodex-search-v1",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": max_tokens,
            }
            r = requests.post(AIML_API_URL, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]

        elif PROVIDER == "openai":
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": max_tokens,
            }
            r = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]

        elif PROVIDER == "llama":
            result = subprocess.run(
                ["ollama", "run", "llama3", f"{system_prompt}\n\nUser: {user_content}"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")
            content = result.stdout.strip()

        else:
            raise ValueError(f"Unsupported PROVIDER={PROVIDER}")

        # cleanup
        s = content.strip()
        if s.startswith("```"):
            s = s.strip("` \n")
            if s.lower().startswith("json"):
                s = s.split("\n", 1)[1]
        return json.loads(s)

    except Exception as e:
        print(f"⚠️ Model provider failed ({e}). Falling back to sample dataset...")
        # fallback: load from reddit_posts.json
        try:
            with open("reddit_posts.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError("❌ No model response and no fallback dataset found.")

# ------------------------
# Agents
# ------------------------
def signal_scout(query="Solana reddit posts"):
    return model_call(SIGNAL_SCOUT_PROMPT, query)

def prioritizer(issues):
    return model_call(PRIORITIZER_PROMPT, json.dumps(issues))

# ------------------------
# CLI
# ------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="Solana reddit posts")
    args = parser.parse_args()

    print(f"⚡ Fetching issues for query: {args.query} (provider={PROVIDER})")
    structured = signal_scout(args.query)
    ranked = prioritizer(structured)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pd.DataFrame(structured).to_csv(f"signal_structured_{ts}.csv", index=False)
    pd.DataFrame(ranked).to_csv(f"signal_ranked_{ts}.csv", index=False)

    # Save top issue for social media agent
    if ranked:
        with open("social_media_input.json", "w") as f:
            json.dump(ranked[0], f, indent=2)

    print("✅ Pipeline complete. Structured + ranked issues saved.")
    print(json.dumps(ranked, indent=2))
