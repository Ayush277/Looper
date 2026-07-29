from app.notifications.base import Digest, DigestJob
from app.notifications.senders import TG_LIMIT, _tg_escape, render_digest_telegram


def make_digest(n: int) -> Digest:
    return Digest(
        subject="x",
        jobs=[
            DigestJob(
                company=f"Company {i}",
                title=f"Software Engineer Intern (2027) #{i}",
                location="Bengaluru, India",
                posted_at="2026-07-28",
                apply_url=f"https://example.com/jobs/{i}",
                reasons=["Intern", "Software Engineer", "India"],
            )
            for i in range(n)
        ],
        scanned_companies=14,
        scan_time="08:00 UTC",
    )


class TestTelegramEscaping:
    def test_markdown_syntax_chars_escaped(self):
        assert _tg_escape("C++ (Backend) - 2027!") == r"C\+\+ \(Backend\) \- 2027\!"

    def test_plain_text_untouched(self):
        assert _tg_escape("Software Engineer") == "Software Engineer"


class TestTelegramRendering:
    def test_single_message_for_small_digest(self):
        chunks = render_digest_telegram(make_digest(3))
        assert len(chunks) == 1
        assert "3 new matches" in chunks[0]
        assert "https://example.com/jobs/0" in chunks[0]

    def test_singular_wording(self):
        assert "1 new match*" in render_digest_telegram(make_digest(1))[0]

    def test_splits_when_over_telegram_limit(self):
        chunks = render_digest_telegram(make_digest(60))
        assert len(chunks) > 1
        assert all(len(c) <= 4096 for c in chunks), "every chunk must fit Telegram's cap"

    def test_every_job_survives_chunking(self):
        joined = "".join(render_digest_telegram(make_digest(60)))
        for i in range(60):
            assert f"https://example.com/jobs/{i}" in joined

    def test_chunks_stay_under_soft_limit(self):
        for c in render_digest_telegram(make_digest(40)):
            assert len(c) <= TG_LIMIT + 400
