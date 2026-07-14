from app.matching.rules import (
    check_exclusions,
    check_requirements,
    has_early_career_signal,
    is_early_career_keyword,
)

EXCLUDES = ["Senior", "Principal", "Manager", "Staff", "Experienced", "5+ Years"]
REQS = ["2027", "Final Year", "India", "Remote", "Bangalore", "Hyderabad"]


class TestExclusions:
    def test_seniority_words_hit(self):
        assert "Senior" in check_exclusions("Senior Software Engineer", EXCLUDES)
        assert "Staff" in check_exclusions("Staff ML Engineer", EXCLUDES)
        assert "Manager" in check_exclusions("Engineering Manager", EXCLUDES)

    def test_builtin_senior_terms_without_user_config(self):
        # Architect/Lead/Principal excluded even if user didn't list them.
        assert check_exclusions("Corporate IT Architect", [])
        assert check_exclusions("Software Engineering Lead", [])
        assert check_exclusions("Architect, AI Data Platform & Engineering", [])

    def test_years_variants_hit_incl_ranges(self):
        for title, snip in (
            ("SDE III", "requires 7+ years of experience"),
            ("Backend Engineer", "5 years experience required"),
            ("Software Engineer", "2-5 years of experience"),   # the reported bug
            ("Developer", "at least 3 years experience"),
        ):
            assert check_exclusions(title, EXCLUDES, snip), (title, snip)

    def test_intern_titles_pass(self):
        for title in (
            "Software Engineering Intern, 2027",
            "SDE Intern",
            "New Grad Software Engineer",
        ):
            assert check_exclusions(title, EXCLUDES) == [], title

    def test_no_substring_false_positives(self):
        assert check_exclusions("Staffing Coordinator Intern", EXCLUDES) == []


class TestEarlyCareerGate:
    def test_intern_grad_signals_pass(self):
        for title in (
            "Software Engineering Intern",
            "New Grad Software Engineer",
            "Software Development Graduate, 2027",
            "University Hire - Backend",
            "Campus Recruit SDE",
            "2027 Software Dev Engineer Intern",
        ):
            assert has_early_career_signal(title, None), title

    def test_senior_generic_roles_have_no_signal(self):
        for title in (
            "Corporate IT Architect",
            "ML Services Software Development Engineer",
            "Information Security Systems Engineer",
            "Applied AI Engineer - VLSI Design",
        ):
            assert not has_early_career_signal(title, None), title

    def test_signal_from_description(self):
        assert has_early_career_signal(
            "Software Engineer", "This is an internship for current students"
        )

    def test_no_false_signal_from_common_description_words(self):
        # "university" / "student" in requirements prose must not falsely qualify.
        assert not has_early_career_signal(
            "Software Engineer", "Bachelor's from a university; 4 years experience"
        )

    def test_keyword_classification(self):
        assert is_early_career_keyword("Intern")
        assert is_early_career_keyword("New Grad")
        assert is_early_career_keyword("University")
        assert not is_early_career_keyword("Software Engineer")
        assert not is_early_career_keyword("Backend")


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
