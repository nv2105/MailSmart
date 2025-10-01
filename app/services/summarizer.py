# app/services/summarizer.py
import os, requests
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PROMPT_FILE = "prompts/summarizer_prompt.txt"

def load_prompt_template() -> str:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def summarize_emails(emails: list) -> dict:
    """
    Summarizes emails into categories + action items using Groq LLM.
    Prompt is loaded from external file for easy editing.
    """

    if not emails:
        return {"summary_of_emails": [], "actions": []}

    input_text = "\n\n".join(
        [f"From: {e['from']}\nSubject: {e['subject']}\n{e['snippet']}" for e in emails]
    )

    # Load base prompt
    base_prompt = load_prompt_template()

    # Inject dynamic email content into prompt
    final_prompt = f"{base_prompt}\n\nEmails:\n{input_text}"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()

    try:
        output = result["choices"][0]["message"]["content"]
        return eval(output)  # could replace with json.loads(output) if always valid JSON
    except Exception as e:
        return {"summary_of_emails": ["⚠️ Summarization failed"], "actions": [], "error": str(e)}
