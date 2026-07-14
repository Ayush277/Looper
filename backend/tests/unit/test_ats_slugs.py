from app.scraping.extractors.ats import _slug_candidates


class TestSlugCandidates:
    def test_no_url_allows_name_guessing(self):
        assert "rubrik" in _slug_candidates("Rubrik", None)

    def test_own_domain_url_disables_name_guessing(self):
        # Regression: name-guessed Greenhouse slug returned a squatter test board.
        slugs = _slug_candidates("LinkedIn", "https://careers.linkedin.com/jobs")
        assert slugs == []

    def test_ats_url_slug_extracted_and_name_guessing_kept(self):
        slugs = _slug_candidates("Acme", "https://boards.greenhouse.io/acmeinc")
        assert slugs[0] == "acmeinc"
        assert "acme" in slugs

    def test_workday_tenant_extracted(self):
        slugs = _slug_candidates("Nvidia", "https://nvidia.wd5.myworkdayjobs.com/Site")
        assert "nvidia" in slugs
