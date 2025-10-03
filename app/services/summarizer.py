# app/services/summarizer.py
import os
import json
import re
import traceback
from datetime import datetime, timezone
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv()

from app.services.vector_store import upsert_emails
from app.services.gmail_service import get_emails_from_last_24_hours

# Perplexity client
from perplexity import Perplexity
PERPLEXITY_CLIENT = Perplexity(api_key=os.environ.get("PERPLEXITY_API_KEY"))

# Config
PROMPT_PATH = os.getenv("PROMPT_PATH", "prompts/summarizer_prompt.txt")
LOG_DIR = os.getenv("LOG_DIR", "logs")
CHUNK_SIZE = int(os.getenv("EMAIL_CHUNK_SIZE", 5) or 5)
ESSENTIAL_PATH = "config/essential.json"
MAX_EMAIL_FETCH = int(os.getenv("MAX_EMAIL_FETCH", 20))

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Local fallback
HF_LOCAL_MODEL = os.getenv("HF_LOCAL_MODEL", "sshleifer/distilbart-cnn-12-6")

# === Utilities ===
def load_prompt() -> str:
    if not os.path.exists(PROMPT_PATH):
        raise FileNotFoundError("Prompt file missing: " + PROMPT_PATH)
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def load_essential_senders() -> List[str]:
    if not os.path.exists(ESSENTIAL_PATH):
        return []
    try:
        with open(ESSENTIAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("senders", [])
    except Exception:
        return []

def ensure_essential(emails: List[Dict]) -> List[Dict]:
    essential = load_essential_senders()
    return [e for e in emails if any(s.lower() in e.get("from", "").lower() for s in essential)]

def get_email_unique_key(email: Dict) -> str:
    return f"{email.get('id')}_{email.get('from')}_{email.get('subject')}"

def safe_parse_json_from_text(text: str) -> Dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    # Fallback: simple summary list
    lines = text.strip().splitlines()
    summary_points = []
    actions = []
    for line in lines[:20]:
        clean = line.strip()
        if len(clean) > 10:
            summary_points.append(clean[:300])
    return {"summary_of_emails": summary_points or ["No summary available"], "actions": actions}

def chunk_text(text: str, chunk_words: int = 600) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i+chunk_words]) for i in range(0, len(words), chunk_words)]

# === API Calls ===
def call_perplexity(prompt: str) -> Dict:
    """Call Perplexity API via official client."""
    try:
        completion = PERPLEXITY_CLIENT.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": prompt}]
        )
        text = completion.choices[0].message.content
        return {"choices": [{"message": {"content": text}}]}
    except Exception as e:
        print("⚠️ Perplexity API call failed:", e)
        traceback.print_exc()
        return {"choices": [{"message": {"content": "Perplexity failed"}}]}

def call_gemini(prompt: str) -> Dict:
    if not GEMINI_API_KEY:
        return {"choices": [{"message": {"content": "Gemini API key missing"}}]}
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            model = genai.GenerativeModel("gemini-flash-latest")
        except Exception:
            model = genai.GenerativeModel("gemini-pro-latest")
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp))
        return {"choices": [{"message": {"content": text}}]}
    except Exception as e:
        print("⚠️ Gemini call failed:", e)
        traceback.print_exc()
        return {"choices": [{"message": {"content": "Gemini failed"}}]}

def call_transformers_local(text: str) -> Dict:
    try:
        from transformers import pipeline
        summarizer = pipeline(
            "summarization",
            model=HF_LOCAL_MODEL,
            device=-1
        )
        pieces = []
        for chunk in chunk_text(text):
            out = summarizer(chunk, max_length=200, min_length=30, truncation=True)
            pieces.append(out[0].get("summary_text", str(out)))
        return {"choices": [{"message": {"content": "\n\n".join(pieces)}}]}
    except Exception as e:
        print("⚠️ Local summarizer failed:", e)
        traceback.print_exc()
        return {"choices": [{"message": {"content": "Local summarizer failed"}}]}

# === Backend Controller ===
def summarize_with_backends(prompt: str) -> Dict:
    for name, func in [
        ("Perplexity", call_perplexity),
        ("Gemini", call_gemini),
        ("Local", call_transformers_local)
    ]:
        try:
            res = func(prompt)
            content = res["choices"][0]["message"]["content"]
            if not content or "failed" in content.lower():
                continue
            print(f"✅ {name} produced usable summary on attempt 1")
            return safe_parse_json_from_text(content)
        except Exception as e:
            print(f"⚠️ {name} exception:", e)
            traceback.print_exc()
    return {"summary_of_emails": ["Error producing summary"], "actions": []}

# === Summarize Emails ===
def summarize_emails(emails: List[Dict]) -> Dict:
    if not emails:
        return {"summary_of_emails": [], "actions": []}
    prompt_template = load_prompt()
    summaries = []

    for i in range(0, len(emails), CHUNK_SIZE):
        chunk = emails[i:i+CHUNK_SIZE]
        emails_text = "\n\n---\n\n".join([
            f"From: {e.get('from')}\nSubject: {e.get('subject')}\n{e.get('snippet')}"
            for e in chunk
        ])
        for text_chunk in chunk_text(emails_text):
            prompt = prompt_template.replace("{emails_text}", text_chunk)
            summaries.append(summarize_with_backends(prompt))

    merged = {"summary_of_emails": [], "actions": []}
    for s in summaries:
        merged["summary_of_emails"].extend(s.get("summary_of_emails", []))
        merged["actions"].extend(s.get("actions", []))
    return merged

# === Direct Summarize from payload ===
def summarize_emails_direct(emails: list):
    return summarize_emails(emails)

# === Full Daily Pipeline ===
def run_rag_daily(max_results: int = None) -> Dict:
    if max_results is None:
        max_results = MAX_EMAIL_FETCH  # fallback to env value
    emails = get_emails_from_last_24_hours(max_results=max_results)
    if not emails:
        return {"summary_of_emails": [], "actions": []}

    essential_emails = ensure_essential(emails)
    combined = emails + essential_emails
    unique_dict = {get_email_unique_key(e): e for e in combined}
    all_emails = list(unique_dict.values())

    try:
        upsert_emails(all_emails)
    except Exception as e:
        print("⚠️ Qdrant upsert failed:", e)

    summary = summarize_emails(all_emails)

    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(LOG_DIR, f"summary_{ts}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"time": ts, "summary": summary, "count": len(all_emails)}, f, indent=2)
    except Exception as e:
        print("⚠️ Failed to save summary log:", e)

    return summary

