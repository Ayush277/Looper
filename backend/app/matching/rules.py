"""Rule layer of the match pipeline (docs/03 FR-4).

Three guarantees, in priority order:
  1. Hard exclusions (seniority words + years-of-experience) — never emailed.
  2. Early-career gate — this is an *internship* monitor, so a job must carry an
     intern/grad/new-grad/campus signal (in title or description) to qualify.
     Without it, generic-software-role matches (senior SWE, architect, IT) are
     dropped even when semantically similar to an include keyword.
  3. Requirement boosts (2027, India, Bangalore…) — enrich score & reasons.
"""
import re

# ── Seniority exclusions ────────────────────────────────────────────────
# Built-in senior terms are excluded even if the user didn't list them —
# an internship is never a Senior/Staff/Principal/Architect/Lead/Manager role.
BUILTIN_SENIOR = [
    "senior", "sr.", "staff", "principal", "lead", "architect", "manager",
    "director", "head of", "vp", "vice president", "distinguished", "fellow",
    "experienced", "expert",
]

# Years-of-experience: match "5+ years", "2-5 years", "3 to 7 yrs", using the
# HIGH end of any range. Interns/new-grads don't require prior experience.
_YEARS = re.compile(
    r"(\d{1,2})\s*(?:\+|(?:-|–|to)\s*(\d{1,2}))?\s*\+?\s*(?:years?|yrs?)",
    re.I,
)
EXPERIENCE_MIN_YEARS = 2  # a role wanting ≥2 yrs experience is not early-career

# ── Early-career signals ────────────────────────────────────────────────
# Strong signals are trustworthy anywhere (title or description).
_STRONG = (
    r"intern(ships?)?|co-?op|new[\s-]?grad(uate)?s?|campus\s+(hire|recruit)|"
    r"graduate\s+(program|trainee|scheme|engineer|analyst|associate)|grad\s+program|"
    r"early[\s-]?career|entry[\s-]?level|fresher|apprentice(ship)?|"
    r"(class|batch)\s+(of\s+)?20\d\d|20\d\d\s*[/,&]\s*20\d\d|20\d\d\s+grad"
)
# Weak signals are only trusted in the TITLE (too common in description prose,
# e.g. "university degree required", "current students").
_WEAK = r"graduate|junior|jr\.?|trainee|university\s+(hire|grad)|student"

STRONG_RE = re.compile(rf"(?<!\w)(?:{_STRONG})", re.I)
WEAK_RE = re.compile(rf"(?<!\w)(?:{_WEAK})", re.I)

# Include-keyword terms that express *level* rather than *role*. When the user
# has any of these, the early-career gate is enforced.
EARLY_CAREER_TERMS = {
    "intern", "internship", "graduate", "new grad", "new-grad", "newgrad",
    "university", "student", "campus", "fresher", "trainee", "entry level",
    "apprentice", "co-op", "coop",
}


def _word_match(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text.lower()) is not None


def _max_years(text: str) -> int:
    best = 0
    for m in _YEARS.finditer(text):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        best = max(best, hi)
    return best


def has_early_career_signal(title: str, snippet: str | None) -> bool:
    """True if the job reads as an internship / new-grad / entry-level role."""
    if STRONG_RE.search(title) or WEAK_RE.search(title):
        return True
    return bool(snippet and STRONG_RE.search(snippet))


def is_early_career_keyword(term: str) -> bool:
    t = term.lower()
    return any(k in t for k in EARLY_CAREER_TERMS)


# ── India location gate ─────────────────────────────────────────────────
# Cities/states/country tokens that mark a job as India-based. Bare "remote"
# is intentionally excluded — remote-anywhere is usually not India-specific.
INDIA_TOKENS = [
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "gurugram", "gurgaon",
    "mumbai", "new delhi", "delhi", "noida", "chennai", "kolkata", "ahmedabad",
    "jaipur", "kochi", "cochin", "chandigarh", "indore", "coimbatore", "nagpur",
    "visakhapatnam", "vizag", "mysore", "mysuru", "trivandrum",
    "thiruvananthapuram", "karnataka", "telangana", "maharashtra", "haryana",
    "tamil nadu", "kerala", "uttar pradesh", "gujarat",
]
_INDIA_RE = re.compile(rf"(?<!\w)(?:{'|'.join(INDIA_TOKENS)})(?!\w)", re.I)

INDIA_KEYWORD_TERMS = {
    "india", *[t for t in INDIA_TOKENS if t not in ("india",)],
}


def is_india_location(title: str, location: str | None, snippet: str | None) -> bool:
    text = " ".join(p for p in [title, location, snippet] if p)
    return bool(_INDIA_RE.search(text))


def is_india_keyword(term: str) -> bool:
    return term.lower() in INDIA_KEYWORD_TERMS


def check_exclusions(
    title: str, exclude_terms: list[str], snippet: str | None = None
) -> list[str]:
    """Exclusion terms hit by this job (empty = passes).

    Checks user-supplied exclude keywords + built-in senior terms against the
    title, and a years-of-experience threshold against title + description.
    Experience/seniority is skipped only when the title itself is clearly an
    intern posting (so a rare "Intern — gain 3 years of experience" isn't lost).
    """
    hits: list[str] = []
    for term in [*exclude_terms, *BUILTIN_SENIOR]:
        if _word_match(term.rstrip("+ ."), title):
            hits.append(term)

    title_is_intern = bool(STRONG_RE.search(title))
    if not title_is_intern:
        years = _max_years(f"{title}  {snippet or ''}")
        if years >= EXPERIENCE_MIN_YEARS and (
            "experience" in (title + " " + (snippet or "")).lower()
        ):
            hits.append(f"{years}+ years experience")

    # De-dup while preserving order.
    return list(dict.fromkeys(hits))


def check_requirements(
    requirement_terms: list[str], title: str, location: str | None, snippet: str | None
) -> list[str]:
    """Requirement terms found in the job's text fields."""
    text = " ".join(p for p in [title, location, snippet] if p)
    hits = []
    for term in requirement_terms:
        candidates = [term, *ALIASES.get(term.lower(), [])]
        if any(_word_match(c, text) for c in candidates):
            hits.append(term)
    return hits


# Location / batch aliases so portal wording variations still match.
ALIASES: dict[str, list[str]] = {
    "bangalore": ["bengaluru"],
    "bengaluru": ["bangalore"],
    "2027": ["batch 2027", "class of 2027", "graduating 2027", "expected graduation 2027"],
    "remote": ["work from home", "wfh", "anywhere"],
}
