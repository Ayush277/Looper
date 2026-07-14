"""Rule layer of the match pipeline (docs/03 FR-4).

Hard exclusions guarantee the precision floor: a job hitting one is stored as
`excluded` and can never be emailed, regardless of semantic score.
Requirement hits never gate a match — they boost the score and enrich reasons.
"""
import re

# "5+ years", "7-10 yrs", "at least 4 years", "minimum of 6 years"
YEARS_PATTERN = re.compile(
    r"\b(?:at\s+least\s+|minimum\s+(?:of\s+)?)?(\d{1,2})\s*(?:-\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?)\b",
    re.I,
)
SENIORITY_MIN_YEARS = 3

# Location aliases so "Bangalore" matches portals that write "Bengaluru".
ALIASES: dict[str, list[str]] = {
    "bangalore": ["bengaluru"],
    "bengaluru": ["bangalore"],
    "2027": ["batch 2027", "class of 2027", "graduating 2027", "expected graduation 2027"],
    "remote": ["work from home", "wfh", "anywhere"],
}


def _word_match(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text.lower()) is not None


def check_exclusions(title: str, exclude_terms: list[str]) -> list[str]:
    """Return the exclusion terms hit by this title (empty = passes)."""
    hits = [t for t in exclude_terms if _word_match(t.rstrip("+ "), title)]
    for m in YEARS_PATTERN.finditer(title):
        if int(m.group(1)) >= SENIORITY_MIN_YEARS:
            hits.append(m.group(0).strip())
            break
    return hits


def check_requirements(
    requirement_terms: list[str], title: str, location: str | None, snippet: str | None
) -> list[str]:
    """Return requirement terms found in the job's text fields."""
    text = " ".join(p for p in [title, location, snippet] if p)
    hits = []
    for term in requirement_terms:
        candidates = [term, *ALIASES.get(term.lower(), [])]
        if any(_word_match(c, text) for c in candidates):
            hits.append(term)
    return hits
