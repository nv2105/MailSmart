# app/services/formatter.py

def format_digest(summary_dict: dict) -> str:
    """
    Takes summarizer output {summary_of_emails, actions} and returns readable digest text.
    """
    summaries = summary_dict.get("summary_of_emails", [])
    actions = summary_dict.get("actions", [])

    out = []
    out.append("📩 MailSmart Daily Digest\n" + "─" * 30)

    out.append(f"✅ Total emails: {len(summaries)}")
    out.append(f"⭐ Important emails: {min(5, len(summaries))} shown below\n")

    # Summaries
    out.append("🔹 Top Summaries:")
    for s in summaries[:5]:
        out.append(f"- {s}")

    # Actions
    if actions:
        out.append("\n📌 Suggested Actions:")
        for a in actions:
            out.append(f"- {a['action']} ({a['name']})")

    return "\n".join(out)
