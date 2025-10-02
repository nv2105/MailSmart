# app/services/summarizer.py
import os
import json
import re
import requests
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import List, Dict
from huggingface_hub import InferenceApi


load_dotenv()

from app.services.vector_store import upsert_emails
from app.services.gmail_service import get_emails_from_last_24_hours

# === Config ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PROMPT_PATH = os.getenv("PROMPT_PATH", "prompts/summarizer_prompt.txt")
LOG_DIR = os.getenv("LOG_DIR", "logs")
RAG_TOPK = int(os.getenv("RAG_TOPK", 5))
ESSENTIAL_PATH = "config/essential.json"  # essential senders list
CHUNK_SIZE = int(os.getenv("EMAIL_CHUNK_SIZE", 5))  # For LLM batching
HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-2-7b-chat-hf")  # or Llama-3 if available

# === Utilities ===
def load_prompt() -> str:
    """Load summarizer prompt template."""
    if not os.path.exists(PROMPT_PATH):
        raise FileNotFoundError("Prompt file missing: " + PROMPT_PATH)
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_essential_senders() -> List[str]:
    """Load essential senders from config."""
    if not os.path.exists(ESSENTIAL_PATH):
        return []
    try:
        with open(ESSENTIAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("senders", [])
    except Exception:
        return []


def ensure_essential(emails: List[Dict]) -> List[Dict]:
    """Return all essential emails from list, based on config/essential.json"""
    essential = load_essential_senders()
    essentials_found = [
        e for e in emails if any(s.lower() in e.get("from", "").lower() for s in essential)
    ]
    return essentials_found


def get_email_unique_key(email: Dict) -> str:
    """Generate a unique key for deduplication."""
    return f"{email.get('id')}_{email.get('from')}_{email.get('subject')}"


# === Hugging Face LLaMA API Backend ===
def call_hf_llama(prompt: str) -> Dict:
    """Call Hugging Face Inference API for LLaMA."""
    if not HF_API_KEY:
        raise ValueError("HF_API_KEY not set in .env")
    try:
        hf = InferenceApi(repo_id=HF_MODEL, token=HF_API_KEY)
        output = hf(inputs=prompt)
        # output could be dict or str depending on model
        text = output if isinstance(output, str) else output.get("generated_text", str(output))
        return {"choices": [{"message": {"content": text}}]}
    except Exception as e:
        print("⚠️ Hugging Face LLaMA API failed:", e)
        traceback.print_exc()
        return {"choices": [{"message": {"content": "HF LLaMA backend failed"}}]}

# === LLM Backends ===
def call_groq(prompt: str) -> Dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 700
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def call_gemini(prompt: str) -> Dict:
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
    except Exception:
        traceback.print_exc()
        return {"choices": [{"message": {"content": "Gemini backend failed"}}]}


def safe_parse_json_from_text(text: str) -> Dict:
    """Try parsing JSON, else fallback to heuristic summary."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # fallback heuristic
    lines = text.strip().splitlines()
    summary_points = []
    actions = []
    for line in lines[:10]:
        if len(line.strip()) > 10:
            summary_points.append(line.strip()[:200])
    return {"summary_of_emails": summary_points or ["No summary available"], "actions": actions}


def summarize_with_backends(prompt: str) -> Dict:
    """Try HF LLaMA -> Groq -> Gemini."""
    for backend, func in [("HF LLaMA", call_hf_llama), ("Groq", call_groq), ("Gemini", call_gemini)]:
        try:
            if (backend == "HF LLaMA" and not HF_API_KEY) or \
               (backend == "Groq" and not GROQ_API_KEY) or \
               (backend == "Gemini" and not GEMINI_API_KEY):
                continue
            res = func(prompt)
            content = res["choices"][0]["message"]["content"]
            parsed = safe_parse_json_from_text(content)
            return parsed
        except Exception as e:
            print(f"⚠️ {backend} failed:", e)
            traceback.print_exc()
    return {"summary_of_emails": ["Error producing summary"], "actions": []}



# === Public Summarizer ===
def summarize_emails(emails: List[Dict]) -> Dict:
    """Summarize emails using available backends, chunked if necessary."""
    prompt_template = load_prompt()
    summaries = []
    for i in range(0, len(emails), CHUNK_SIZE):
        chunk = emails[i:i + CHUNK_SIZE]
        emails_text = "\n\n---\n\n".join([
            f"From: {e.get('from')}\nSubject: {e.get('subject')}\n{e.get('snippet')}"
            for e in chunk
        ])
        prompt = prompt_template.replace("{emails_text}", emails_text)
        summaries.append(summarize_with_backends(prompt))
    # merge summaries
    merged_summary = {"summary_of_emails": [], "actions": []}
    for s in summaries:
        merged_summary["summary_of_emails"].extend(s.get("summary_of_emails", []))
        merged_summary["actions"].extend(s.get("actions", []))
    return merged_summary


def summarize_emails_direct(emails: List[Dict]) -> Dict:
    """Direct summarization wrapper."""
    if not emails:
        return {"summary_of_emails": [], "actions": []}
    return summarize_emails(emails)


# === Full RAG Daily Pipeline ===
def run_rag_daily(max_results: int = 20) -> Dict:
    """Fetch emails, index, and summarize for daily RAG pipeline."""
    emails = get_emails_from_last_24_hours(max_results=max_results)
    if not emails:
        return {"summary_of_emails": [], "actions": []}

    # always include essential emails
    essential_emails = ensure_essential(emails)
    combined_emails = emails + essential_emails

    # deduplicate based on unique key
    unique_dict = {get_email_unique_key(e): e for e in combined_emails}
    all_emails = list(unique_dict.values())

    # index into Qdrant
    try:
        upsert_emails(all_emails)
    except Exception as e:
        print("⚠️ Qdrant upsert failed:", e)
        traceback.print_exc()

    # generate summary
    summary = summarize_emails(all_emails)

    # save log
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(LOG_DIR, f"summary_{ts}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"time": ts, "summary": summary, "count": len(all_emails)}, f, indent=2)
    except Exception as e:
        print("⚠️ Failed to save summary log:", e)
        traceback.print_exc()

    return summary