# sentiment_scout/client.py

import requests
import json
from pathlib import Path
import re
from .config import AIMLAPI_KEY, BASE_URL, MAX_TOKENS
# from .config import AIMLAPI_KEY, BASE_URL, MAX_TOKENS
try:
    from .config import AIMLAPI_KEY, BASE_URL, MAX_TOKENS  # when run as module
except ImportError:
    from config import AIMLAPI_KEY, BASE_URL, MAX_TOKENS   # when run as script




RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)
LAST_RESPONSE_PATH = RAW_DIR / "last_response.json"


class GPT5Client:
    def __init__(self):
        self.chat_url = f"{BASE_URL}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {AIMLAPI_KEY}",
            "Content-Type": "application/json",
        }

    def _safe_request(self, payload: dict) -> dict:
        try:
            resp = requests.post(self.chat_url, headers=self.headers, json=payload, timeout=60)
            data = resp.json()
            LAST_RESPONSE_PATH.write_text(json.dumps({"payload": payload, "response": data}, indent=2))
            resp.raise_for_status()
            return data
        except Exception as e:
            return {"error": str(e)}

    def search(self, query: str) -> list:
        """
        Use bagoodexto pull the top 5 most relevant/engaging posts.
        Output enriched with sentiment, buzzwords, and topics for leadership preview.
        """
        prompt = (
            "You are a senior Solana ecosystem market research analyst.\n"
            f"Task: For the query '{query}', return the **top 5 posts** across the web.\n"
            "For each post, analyze and output:\n"
            "- platform (Reddit, X/Twitter, LinkedIn, or Other)\n"
            "- headline (short title)\n"
            "- url (string)\n"
            "- buzzwords (list of 3–5 key words/phrases)\n"
            "- sentiment (positive, neutral, negative)\n"
            "- topic (payments, DeFi, NFT/gaming, or custom)\n"
            "- summary (1–2 sentences)\n"
        )

        payload = {
            "model": "bagoodex/bagoodex-search-v1",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(MAX_TOKENS, 800),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "social_posts",
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "platform": {"type": "string"},
                                "headline": {"type": "string"},
                                "url": {"type": "string"},
                                "buzzwords": {"type": "array", "items": {"type": "string"}},
                                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                                "topic": {"type": "string"},
                                "summary": {"type": "string"}
                            },
                            "required": ["platform", "headline", "url", "sentiment", "topic", "summary"]
                        }
                    }
                }
            }
        }

        data = self._safe_request(payload)
        if "error" in data:
            return [{"platform": "Unknown", "query": query, "error": data["error"]}]

        raw_msg = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "")

        try:
            posts = json.loads(raw_msg)
            if not isinstance(posts, list):
                posts = [posts]
        except Exception:
            return [{"platform": "Unknown", "query": query, "error": f"Parse error: {raw_msg[:200]}"}]

        return posts[:5]
