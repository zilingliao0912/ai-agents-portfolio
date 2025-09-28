"""
Social Media Agent v7
- Part 1: Generate viral content (caption + meme text + template choice)
- Part 2: Generate meme image from chosen template
- Part 3: Upload meme to Catbox
- Part 4: Post caption + Catbox image link to Twitter (X)
"""

import os
import json
import requests
from transformers import pipeline
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import tweepy
import random
from dotenv import load_dotenv
load_dotenv()

# -----------------------
# Input: Issue Object
# -----------------------
with open("social_media_input.json", "r") as f:
    issue = json.load(f)

# ✅ Ensure buzzwords exists (fallback to topic split if missing)
if "buzzwords" not in issue:
    issue["buzzwords"] = issue.get("topic", "").split() if "topic" in issue else ["solana"]

TEMPLATES = ["thinking", "drake_hotline", "wojak_crying", "disaster_girl", "galaxy_brain"]

# -----------------------
# Part 1: Content Agent
# -----------------------
#generator = pipeline("text2text-generation", model="google/flan-t5-small")
import torch
from transformers import pipeline


generator = pipeline(
    "text-generation",
    model="gpt2-medium",
    device=0 if torch.backends.mps.is_available() else -1
)


def generate_meme_content(issue_obj):
    # ✅ guarantee buzzwords exists
    buzzwords = issue_obj.get("buzzwords") or issue_obj.get("topic", "").split() or ["solana"]
    buzz = ", ".join(buzzwords)

    prompt = f"""
        You are a senior AI social media content creator. 
        Generate content for a viral meme about Solana.

        Requirements:
        - Be witty, creative, and think outside the box. Make it funny, punchy, and viral — like a tweet that could hit 1M views.
        - Captions must be short (under 200 characters).
        - Must be safe for a public audience: no sexual, racial, political, or offensive jokes.
        - Humor should be light, friendly, and relatable.
        - The visual background template will be randomly chosen later (ignore recommending one).
        - make it sound like a snappy TikTok caption or Twitter meme
        
        Context:
        User type: {issue_obj.get('user_type', 'Unknown')}
        Topic: {issue_obj.get('topic', '')}
        Buzzwords: {buzz}
        Sentiment: {issue_obj.get('sentiment', 'Neutral')}
        ...
"""

    result = generator(
        prompt,
        max_length=120,
        do_sample=True,
        top_k=50,
        top_p=0.95,
        temperature=1.2,
        num_return_sequences=1
    )
    text = result[0]["generated_text"].strip()

    content = {
        "viral_caption": text[:180],  # make sure it's short enough
        "meme_text_top": issue_obj.get("topic", "SOLANA").upper(),
        "meme_text_bottom": " / ".join(issue_obj.get("buzzwords", [])),
        "style": "funny, ironic",
        "recommended_template": random.choice(TEMPLATES)
    }


    # try:
    #     content = json.loads(result[0]["generated_text"])
    # except:
    #     content = {
    #         "viral_caption": result[0]["generated_text"][:180],
    #         "meme_text_top": issue_obj.get("topic", "SOLANA").upper(),
    #         "meme_text_bottom": " / ".join(issue_obj.get("buzzwords", [])),
    #         "style": "funny, ironic",
    #     }

    # ✅ Always randomize template
    #content["recommended_template"] = random.choice(TEMPLATES)
    return content

# -----------------------
# Part 2: Visual Agent
# -----------------------

def create_meme_from_content(content_json, filename="meme.png"):
    template = content_json.get("recommended_template", "thinking")
    if template == "wojak_crying":
        bg_path = "wojak_crying.webp"
    else:
        bg_path = f"{template}.jpg"

    try:
        img = Image.open(bg_path).convert("RGB")
    except:
        img = Image.new("RGB", (800, 600), color=(20, 20, 20))

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Impact.ttf", 48)
    except:
        font = ImageFont.load_default()

    def draw_text_with_outline(text, pos, font, fill="white", outline="black", width=3):
        x, y = pos
        for dx in [-width, 0, width]:
            for dy in [-width, 0, width]:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    draw_text_with_outline(content_json["meme_text_top"], (20, 20), font)
    draw_text_with_outline(content_json["meme_text_bottom"], (20, img.height - 100), font)

    img.save(filename)
    print(f"✅ Meme saved with template {template}: {filename}")
    return filename

# -----------------------
# Part 3: Upload to Catbox
# -----------------------
def upload_to_catbox(filepath):
    url = "https://catbox.moe/user/api.php"
    with open(filepath, "rb") as f:
        resp = requests.post(url, data={"reqtype": "fileupload"}, files={"fileToUpload": f})
    if resp.status_code == 200:
        return resp.text.strip()
    else:
        raise Exception(f"Upload failed: {resp.text}")

# -----------------------
# Part 4: Twitter Posting
# -----------------------
def post_to_twitter(caption, img_url):
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    tweet_text = f"{caption}\n\n{img_url}"
    resp = client.create_tweet(text=tweet_text)
    print("🐦 Posted:", resp)

# -----------------------
# Run Agent
# -----------------------
if __name__ == "__main__":
    content = generate_meme_content(issue)
    print("\n🎯 Generated Content:")
    print(json.dumps(content, indent=2))

    filename = f"meme_{datetime.now().strftime('%Y%m%d')}.png"
    create_meme_from_content(content, filename=filename)
    print(f"💬 Viral Caption:\n{content['viral_caption']}")

    img_url = upload_to_catbox(filename)
    print(f"🌐 Uploaded Meme URL: {img_url}")

    # Uncomment to post
    # post_to_twitter(content["viral_caption"], img_url)
