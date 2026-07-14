from app.shared.hashing import canonical_url_path, job_content_hash, normalize_text

CID = "11111111-1111-1111-1111-111111111111"


class TestNormalizeText:
    def test_lowercase_punct_whitespace(self):
        assert normalize_text("  Software   Engineer, Intern! ") == "software engineer intern"

    def test_idempotent(self):
        once = normalize_text("SDE-II (Backend)")
        assert normalize_text(once) == once

    def test_none_and_empty(self):
        assert normalize_text(None) == ""
        assert normalize_text("   ") == ""


class TestCanonicalUrlPath:
    def test_strips_query_fragment_www_and_trailing_slash(self):
        assert (
            canonical_url_path("https://www.careers.x.com/jobs/123/?utm_source=li#top")
            == "careers.x.com/jobs/123"
        )

    def test_host_case_insensitive(self):
        assert canonical_url_path("https://Careers.X.com/A") == "careers.x.com/A"


class TestJobContentHash:
    def test_stable_across_tracking_params_and_case(self):
        a = job_content_hash(CID, "SDE Intern", "Bangalore", "https://x.com/j/1?utm=a")
        b = job_content_hash(CID, "sde  intern", "BANGALORE", "https://www.x.com/j/1/")
        assert a == b

    def test_sensitive_to_title_location_url(self):
        base = job_content_hash(CID, "SDE Intern", "Bangalore", "https://x.com/j/1")
        assert base != job_content_hash(CID, "SDE Intern II", "Bangalore", "https://x.com/j/1")
        assert base != job_content_hash(CID, "SDE Intern", "Hyderabad", "https://x.com/j/1")
        assert base != job_content_hash(CID, "SDE Intern", "Bangalore", "https://x.com/j/2")

    def test_sensitive_to_company(self):
        other = "22222222-2222-2222-2222-222222222222"
        assert job_content_hash(CID, "SDE Intern", None, "https://x.com/j/1") != job_content_hash(
            other, "SDE Intern", None, "https://x.com/j/1"
        )

    def test_is_sha256_hex(self):
        h = job_content_hash(CID, "T", None, "https://x.com/j")
        assert len(h) == 64 and int(h, 16) >= 0
