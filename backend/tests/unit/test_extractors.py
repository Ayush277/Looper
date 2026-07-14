from app.scraping.extractors.html_heuristic import extract_html_jobs
from app.scraping.extractors.jsonld import extract_jsonld_jobs

JSONLD_PAGE = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"JobPosting","title":"Software Engineering Intern, 2027",
  "url":"https://x.com/jobs/123","datePosted":"2026-07-10",
  "identifier":{"@type":"PropertyValue","value":9911},
  "jobLocation":{"@type":"Place","address":{"addressLocality":"Bangalore","addressCountry":"IN"}},
  "description":"<p>Work on <b>backend</b> systems.</p>"},
 {"@type":"Organization","name":"XCorp"}
]}
</script>
<script type="application/ld+json">not even json</script>
</head><body></body></html>
"""

HTML_LIST_PAGE = """
<html><body>
<nav><a href="/careers/">All jobs</a><a href="/about">About</a></nav>
<ul class="openings">
 <li><a href="/jobs/1001">SDE Intern</a> <span>Bangalore, India</span></li>
 <li><a href="/jobs/1002">Machine Learning Intern</a> <span>Hyderabad</span></li>
 <li><a href="/jobs/1003">Platform Engineer, New Grad</a> <span>Remote</span></li>
 <li><a href="/jobs/1003">Platform Engineer, New Grad</a> <span>Remote (dup)</span></li>
</ul>
<footer><a href="/jobs/rss">Subscribe</a></footer>
</body></html>
"""


class TestJsonLd:
    def test_extracts_posting_from_graph(self):
        jobs = extract_jsonld_jobs(JSONLD_PAGE, "https://x.com/careers")
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Software Engineering Intern, 2027"
        assert job.apply_url == "https://x.com/jobs/123"
        assert job.location == "Bangalore, IN"
        assert job.external_id == "9911"
        assert str(job.posted_at) == "2026-07-10"
        assert "backend systems" in (job.description_snippet or "")

    def test_ignores_invalid_json_and_non_postings(self):
        assert extract_jsonld_jobs("<html><body>plain</body></html>", "u") == []


class TestHtmlHeuristic:
    def test_extracts_dense_cluster_relative_urls_and_dedups(self):
        jobs = extract_html_jobs(HTML_LIST_PAGE, "https://x.com/careers")
        titles = {j.title for j in jobs}
        assert titles == {"SDE Intern", "Machine Learning Intern", "Platform Engineer, New Grad"}
        assert all(j.apply_url.startswith("https://x.com/jobs/") for j in jobs)

    def test_nav_noise_not_extracted(self):
        jobs = extract_html_jobs(HTML_LIST_PAGE, "https://x.com/careers")
        assert not any(j.title in ("All jobs", "About", "Subscribe") for j in jobs)

    def test_sparse_page_returns_empty(self):
        page = '<html><body><a href="/jobs/1">One Job</a></body></html>'
        assert extract_html_jobs(page, "https://x.com") == []

    def test_category_pages_without_ids_rejected(self):
        # Regression: Amazon/Atlassian/Intuit category navs were extracted as "jobs".
        page = """
        <html><body><ul>
         <li><a href="/careers/engineering">Engineering</a></li>
         <li><a href="/careers/sales">Sales</a></li>
         <li><a href="/careers/all-teams">All Teams</a></li>
         <li><a href="/content/en/job-categories">Job Categories</a></li>
        </ul></body></html>
        """
        assert extract_html_jobs(page, "https://x.com") == []
