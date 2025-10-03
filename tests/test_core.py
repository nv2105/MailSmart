import pytest
from app.main import load_summaries
from app.services.gmail_service import get_emails_from_last_24_hours

def test_load_summaries_structure():
    summaries = load_summaries()
    assert isinstance(summaries, list)
    if summaries:
        s = summaries[0]
        assert "run_time" in s
        assert "total_emails" in s
        assert "important_emails" in s

@pytest.mark.skip(reason="Requires live Gmail credentials")
def test_get_emails_from_last_24_hours():
    emails = get_emails_from_last_24_hours(max_results=5)
    assert isinstance(emails, list)
    if emails:
        e = emails[0]
        assert "from" in e
        assert "subject" in e
        assert "snippet" in e
        assert "id" in e
