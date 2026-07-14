from app.matching.rules import check_exclusions, check_requirements

EXCLUDES = ["Senior", "Principal", "Manager", "Staff", "Experienced", "5+ Years"]
REQS = ["2027", "Final Year", "India", "Remote", "Bangalore", "Hyderabad"]


class TestExclusions:
    def test_seniority_words_hit(self):
        assert check_exclusions("Senior Software Engineer", EXCLUDES) == ["Senior"]
        assert check_exclusions("Staff ML Engineer", EXCLUDES) == ["Staff"]
        assert check_exclusions("Engineering Manager", EXCLUDES) == ["Manager"]

    def test_years_variants_hit(self):
        for title in (
            "SDE III (7+ years)",
            "Backend Engineer - 5 years experience",
            "Engineer (4-6 yrs)",
            "Developer with at least 3 years",
        ):
            assert check_exclusions(title, EXCLUDES), title

    def test_intern_titles_pass(self):
        for title in (
            "Software Engineering Intern, 2027",
            "SDE Intern",
            "New Grad Software Engineer",
            "2 year rotational program",  # < 3 years is not seniority
        ):
            assert check_exclusions(title, EXCLUDES) == [], title

    def test_no_substring_false_positives(self):
        # "Seniority" contains "Senior" but is not the word; "Staffing" != "Staff"
        assert check_exclusions("Staffing Coordinator Intern", EXCLUDES) == []


class TestRequirements:
    def test_direct_hits(self):
        hits = check_requirements(REQS, "SWE Intern 2027", "Hyderabad, India", None)
        assert set(hits) == {"2027", "India", "Hyderabad"}

    def test_alias_bengaluru_matches_bangalore(self):
        hits = check_requirements(["Bangalore"], "Intern", "Bengaluru, KA, India", None)
        assert hits == ["Bangalore"]

    def test_alias_batch_2027(self):
        hits = check_requirements(["2027"], "SDE Intern", None, "Open to batch 2027 students")
        assert hits == ["2027"]

    def test_snippet_searched(self):
        hits = check_requirements(["Final Year"], "Intern", None, "Must be in final year")
        assert hits == ["Final Year"]

    def test_no_hits(self):
        assert check_requirements(REQS, "Software Intern", "Seattle, WA", None) == []
