# import os
# import json
# import requests
# from dotenv import load_dotenv
# from datetime import datetime
# import pandas as pd
# import argparse

# import itertools, snscrape.modules.reddit as s

# def fetch_live_posts(limit=5):
#     posts = []
#     for p in itertools.islice(s.RedditSearchScraper("Solana").get_items(), limit):
#         posts.append({
#             "issue_text": p.title,
#             "platform": "Reddit",
#             "timestamp": p.date.strftime("%Y-%m-%d %H:%M:%S"),
#             "engagement_score": getattr(p, "score", 0)
#         })
#     return posts

# # ------------------------
# # Env
# # ------------------------
# load_dotenv()
# AIML_API_KEY = os.getenv("AIML_API_KEY")
# AIML_API_URL = "https://api.aimlapi.com/v1/chat/completions"
# MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini-search-preview")

# if not AIML_API_KEY:
#     print("⚠️ AIML_API_KEY not found in environment. API calls will fail unless you use --dry-run.")

# # ------------------------
# # Prompts (exact per your spec)
# # ------------------------
# SIGNAL_SCOUT_PROMPT = """You are Signal Scout. Convert Solana-related posts into JSON objects.

# Schema:
# {
#   "issue_text": "...",
#   "summary": "...",          # 1-sentence pain point
#   "user_type": "...",        # Retail Investor | Wallet User | Developer
#   "platform": "...",         # Reddit | Twitter
#   "topic": "...",            # main keyword
#   "buzzwords": ["..."],
#   "sentiment": "...",        # Positive | Neutral | Negative
#   "lifecycle_stage": "...",  # Acquisition | Onboarding | Participation | General
#   "engagement_score": 0,
#   "timestamp": "YYYY-MM-DD HH:MM:SS"
# }

# Rules:
# - Always return JSON.
# - Infer lifecycle: Acquisition=wallet setup/fees, Onboarding=SDK/docs, Participation=staking/NFTs/network, else General.
# - If unclear, user_type="Retail Investor".
# - engagement_score=0 if unknown.
# - Be concise.

# Example:
# Input: "Phantom wallet keeps crashing on swaps."
# Output:
# {
#   "issue_text": "Phantom wallet keeps crashing on swaps.",
#   "summary": "Phantom crashes during swaps, blocking retail users.",
#   "user_type": "Wallet User",
#   "platform": "Reddit",
#   "topic": "phantom",
#   "buzzwords": ["phantom", "wallet", "crash", "swap"],
#   "sentiment": "Negative",
#   "lifecycle_stage": "Participation",
#   "engagement_score": 0,
#   "timestamp": "2025-09-19 12:00:00"
# }
# """

# PRIORITIZER_PROMPT = """You are the Prioritizer Agent. Your job: pick the Top 3 most important Solana issues from a list of max 10 JSON issues.

# Input: up to 10 issue objects from Signal Scout.

# Rules:
# - Rank by: (1) engagement_score (high → important), (2) sentiment (Negative > Neutral > Positive), (3) lifecycle_stage (Acquisition > Onboarding > Participation > General).
# - Return exactly 3 issues.
# - If fewer than 3 issues given, return all.
# - Keep original JSON fields, add "rank": 1, 2, or 3.
# - Output as a JSON array only.
# """

# # ------------------------
# # AIML API helper
# # ------------------------

# def _aiml_call(system_prompt: str, user_content: str, max_tokens: int = 1000):
#     headers = {"Authorization": f"Bearer {AIML_API_KEY}", "Content-Type": "application/json"}
#     payload = {
#         "model": MODEL_NAME,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_content},
#         ],
#         "max_tokens": max_tokens,
#     }

#     try:
#         r = requests.post(AIML_API_URL, headers=headers, json=payload, timeout=30)
#     except requests.RequestException as e:
#         print("⚠️ Network/API error:", e)
#         return [{"raw_output": str(e)}]

#     print("DEBUG status:", r.status_code)
#     print("DEBUG body:", r.text[:400])

#     try:
#         r.raise_for_status()
#     except requests.HTTPError as e:
#         print("⚠️ API returned error:", e)
#         return [{"raw_output": r.text}]

#     data = r.json()
#     content = data["choices"][0]["message"]["content"]

#     # Strip code fences if model wrapped JSON in ```json ... ```
#     s = content.strip()
#     if s.startswith("```"):
#         s = s.strip("` \n")
#         if s.startswith("json"):
#             s = s[4:] if s.startswith("json\n") else s[3:]
#         s = s.strip()

#     # Try parsing JSON directly
#     try:
#         parsed = json.loads(s)
#     except json.JSONDecodeError:
#         # Rescue: grab substring starting from first {
#         if "{" in s:
#             try:
#                 s2 = s[s.index("{"):]
#                 parsed = json.loads(s2)
#             except Exception:
#                 parsed = [{"raw_output": content}]
#         else:
#             parsed = [{"raw_output": content}]

#     # Unwrap dicts like {"issues": [...]} or {"items": [...]}
#     if isinstance(parsed, dict):
#         if "issues" in parsed and isinstance(parsed["issues"], list):
#             return parsed["issues"]
#         if "items" in parsed and isinstance(parsed["items"], list):
#             return parsed["items"]
#         return [parsed]

#     return parsed

# # ------------------------
# # Agents
# # ------------------------
# def signal_scout_api(raw_posts):
#     """Calls AIML to convert raw posts -> structured issues."""
#     return _aiml_call(SIGNAL_SCOUT_PROMPT, json.dumps(raw_posts))

# def prioritizer_api(issues):
#     """Calls AIML to rank structured issues -> Top 3."""
#     return _aiml_call(PRIORITIZER_PROMPT, json.dumps(issues))

# # ------------------------
# # Dry-run local stubs (no tokens)
# # ------------------------
# def signal_scout_local(raw_posts):
#     """Heuristic/local version of Signal Scout (no API)."""
#     out = []
#     for p in raw_posts:
#         text = p.get("text") or p.get("issue_text") or ""
#         platform = p.get("platform", "Twitter")
#         ts = p.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         engagement = p.get("engagement") or p.get("engagement_score") or 0

#         t = text.lower()
#         if any(k in t for k in ["sdk", "docs", "debug"]):
#             stage = "Onboarding"
#             user = "Developer" if "dev" in t or "developer" in t else "Retail Investor"
#         elif any(k in t for k in ["setup", "fees", "create account"]):
#             stage = "Acquisition"
#             user = "Retail Investor"
#         elif any(k in t for k in ["staking", "nft", "swap", "network down", "crash"]):
#             stage = "Participation"
#             user = "Wallet User" if "wallet" in t or "phantom" in t else "Retail Investor"
#         else:
#             stage = "General"
#             user = "Retail Investor"

#         sentiment = "Negative" if any(k in t for k in ["crash", "down", "terrible", "confusing", "bug"]) else "Neutral"
#         words = [w.strip(".,!?") for w in text.split() if len(w.strip(".,!?")) > 2]
#         topic = words[0].lower() if words else "general"
#         buzz = list(dict.fromkeys([w.lower() for w in words]))[:5]

#         out.append({
#             "issue_text": text,
#             "summary": (text[:140] + "...") if len(text) > 140 else text,
#             "user_type": user,
#             "platform": platform,
#             "topic": topic,
#             "buzzwords": buzz,
#             "sentiment": sentiment,
#             "lifecycle_stage": stage,
#             "engagement_score": int(engagement) if isinstance(engagement, (int, float, str)) else 0,
#             "timestamp": ts,
#         })
#     return out

# def prioritizer_local(issues):
#     """Deterministic local ranking (no API), following your rules."""
#     # sentiment order: Negative > Neutral > Positive
#     s_rank = {"Negative": 2, "Neutral": 1, "Positive": 0}
#     # lifecycle order: Acquisition > Onboarding > Participation > General
#     l_rank = {"Acquisition": 3, "Onboarding": 2, "Participation": 1, "General": 0}

#     def score(i):
#         es = int(i.get("engagement_score", 0))
#         sr = s_rank.get(i.get("sentiment"), 0)
#         lr = l_rank.get(i.get("lifecycle_stage"), 0)
#         return (es, sr, lr)

#     sorted_issues = sorted(issues, key=score, reverse=True)
#     top = sorted_issues[:3] if len(sorted_issues) >= 3 else sorted_issues
#     for idx, item in enumerate(top, start=1):
#         item["rank"] = idx
#     return top

# # ------------------------
# # CLI
# # ------------------------

# # ------------------------
# # CLI
# # ------------------------

# # ------------------------
# # CLI
# # ------------------------
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--dry-run", action="store_true", help="No API calls; use local Signal Scout + local Prioritizer")
#     parser.add_argument("--input-file", type=str, help="Path to JSON file of raw posts (list of {text,platform,timestamp,engagement})")
#     args = parser.parse_args()

#     # Load raw posts
#     raw_posts = []
#     # Load raw posts
#     if args.input_file and os.path.exists(args.input_file):
#         with open(args.input_file, "r") as f:
#             raw_posts = json.load(f)
#     else:
#         print("⚡ Fetching live Reddit data for 'Solana' ...")
#         raw_posts = fetch_live_posts(limit=5)

#     if not raw_posts:
#         print("❌ No input posts provided. System did not run.")
#         exit(1)


#     # Run pipeline
#     if args.dry_run:
#         print("⚠️ Dry-run: using local Signal Scout + local Prioritizer (no tokens).")
#         structured = signal_scout_local(raw_posts)
#         ranked = prioritizer_local(structured)
#     else:
#         structured = signal_scout_api(raw_posts)
#         if not structured:
#             print("❌ Signal Scout returned no structured issues. System did not run.")
#             exit(1)
#         ranked = prioritizer_api(structured)
#         if not ranked:
#             print("❌ Prioritizer returned no ranked issues. System did not run.")
#             exit(1)

#     # Save both steps with timestamp (to the second)
#         # Save both steps with timestamp (to the second)
#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     scout_csv = f"signal_scout_structured_{ts}.csv"
#     top3_csv = f"prioritized_issues_{ts}.csv"

#     pd.DataFrame(structured).to_csv(scout_csv, index=False)
#     pd.DataFrame(ranked).to_csv(top3_csv, index=False)

#     print(f"✅ Saved: {scout_csv}")
#     print(f"✅ Saved: {top3_csv}")

#     # -------------------------------
#     # Format Top 1 Issue for Social Media Agent
#     # -------------------------------
#     def format_for_social_media(issue):
#         return {
#             "user_type": issue.get("user_type", "End User"),
#             "platform": issue.get("platform", "Twitter"),
#             "topic": issue.get("topic", issue.get("summary", "General Issue")),
#             "buzzwords": issue.get("buzzwords", []),
#             "sentiment": issue.get("sentiment", "Neutral"),
#             "lifecycle_stage": issue.get("lifecycle_stage", "Issue"),
#             "engagement_score": issue.get("engagement_score", 0),
#             "timestamp": issue.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#         }

#     if ranked:
#         top_issue = format_for_social_media(ranked[0])
#         with open("social_media_input.json", "w") as f:
#             json.dump(top_issue, f, indent=2)
#         print("🚀 Social Media Agent input saved: social_media_input.json")
#         print("Example issue:", json.dumps(top_issue, indent=2))
#     else:
#         print("⚠️ No ranked issues to pass to Social Media Agent.")


# signal_agent.py
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import argparse
import pandas as pd

# ------------------------
# Env
# ------------------------
load_dotenv()
AIML_API_KEY = os.getenv("AIML_API_KEY")
API_URL = "https://api.aimlapi.com/v1/chat/completions"
MODEL_NAME = "bagoodex/bagoodex-search-v1"   # web-enabled search model

if not AIML_API_KEY:
    print("❌ AIML_API_KEY not found in .env")
    exit(1)

# ------------------------
# Prompts
# ------------------------
SIGNAL_SCOUT_PROMPT = """You are Signal Scout. Convert Solana-related posts into JSON objects.

Schema:
{
  "issue_text": "...",
  "summary": "...",          # 1-sentence pain point
  "user_type": "...",        # Retail Investor | Wallet User | Developer
  "platform": "...",         # Reddit | Twitter
  "topic": "...",            # main keyword
  "buzzwords": ["..."],
  "sentiment": "...",        # Positive | Neutral | Negative
  "lifecycle_stage": "...",  # Acquisition | Onboarding | Participation | General
  "engagement_score": 0,
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}

Rules:
- Always return JSON.
- Infer lifecycle: Acquisition=wallet setup/fees, Onboarding=SDK/docs, Participation=staking/NFTs/network, else General.
- If unclear, user_type="Retail Investor".
- engagement_score=0 if unknown.
- Be concise.
"""

PRIORITIZER_PROMPT = """You are the Prioritizer Agent. Your job: pick the Top 3 most important Solana issues from a list of max 10 JSON issues.

Input: up to 10 issue objects from Signal Scout.

Rules:
- Rank by: (1) engagement_score (high → important), (2) sentiment (Negative > Neutral > Positive), (3) lifecycle_stage (Acquisition > Onboarding > Participation > General).
- Return exactly 3 issues.
- If fewer than 3 issues given, return all.
- Keep original JSON fields, add "rank": 1, 2, or 3.
- Output as a JSON array only.
"""

# ------------------------
# AIML API helper
# ------------------------
def aiml_call(system_prompt, user_content, max_tokens=1000):
    headers = {
        "Authorization": f"Bearer {AIML_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]

    # cleanup: strip ```json fences if present
    s = content.strip()
    if s.startswith("```"):
        s = s.strip("` \n")
        if s.lower().startswith("json"):
            s = s.split("\n", 1)[1]
    try:
        return json.loads(s)
    except:
        return [{"raw_output": content}]

# ------------------------
# Agents
# ------------------------
def signal_scout(query="Solana reddit posts"):
    return aiml_call(SIGNAL_SCOUT_PROMPT, query)

def prioritizer(issues):
    return aiml_call(PRIORITIZER_PROMPT, json.dumps(issues))

# ------------------------
# CLI
# ------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="Solana reddit posts",
                        help="What to search (default: Solana reddit posts)")
    args = parser.parse_args()

    print(f"⚡ Fetching issues for query: {args.query}")
    structured = signal_scout(args.query)
    if not structured:
        print("❌ No structured issues returned")
        exit(1)

    ranked = prioritizer(structured)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pd.DataFrame(structured).to_csv(f"signal_scout_structured_{ts}.csv", index=False)
    pd.DataFrame(ranked).to_csv(f"prioritized_issues_{ts}.csv", index=False)

    print("✅ Saved structured + ranked issues")
    print(json.dumps(ranked, indent=2))


