def process_emails(emails: list):
    """
    Process and categorize emails using AI summarization.
    Replace this logic with Google Gemini or your own model.
    """
    summarized = []
    for email in emails:
        summary = {
            "from": email['from'],
            "subject": email['subject'],
            "summary": f"Auto-summary of: {email['snippet'][:50]}..."  # placeholder
        }
        summarized.append(summary)
    return summarized
