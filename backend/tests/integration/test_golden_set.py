"""Golden-set semantic matching test (docs/12 §3.2) — runs the REAL local
embedder, so it's an integration test (downloads the MiniLM model on first run;
skipped automatically if sentence-transformers isn't installed).

Gate: ≥90% agreement with the labeled set.
"""
import pytest

pytest.importorskip("sentence_transformers")

from app.matching.embedders import LocalEmbedder, cosine  # noqa: E402

INCLUDE_KEYWORDS = [
    "Software Engineer", "Software Development Engineer", "Backend",
    "Machine Learning", "Intern", "Graduate", "New Grad", "University", "Student",
]
THRESHOLD = 0.55

# (job title, should_match) — must-match pairs from the brief + hard negatives.
GOLDEN: list[tuple[str, bool]] = [
    # Brief's canonical examples
    ("Software Development Engineer Intern", True),
    ("Software Engineer Internship", True),
    ("University Hiring - Campus Program", True),
    ("Graduate Program - Engineering", True),
    ("New Grad Software Engineer", True),
    # Common real-world variants
    ("SDE Intern - 2027", True),
    ("Software Engineering Intern", True),
    ("Backend Developer Intern", True),
    ("Machine Learning Engineer, Early Career", True),
    ("Intern - Platform Engineering", True),
    ("Student Software Developer", True),
    ("Campus Hire - Software Engineer", True),
    ("Software Engineer I (University Grad)", True),
    ("Applied ML Intern", True),
    # Must NOT match (irrelevant functions)
    ("Sales Development Representative", False),
    ("Legal Counsel", False),
    ("Product Marketing Manager", False),
    ("Executive Assistant", False),
    ("Financial Analyst", False),
    ("Recruiter, Talent Acquisition", False),
    ("Truck Driver", False),
    ("Warehouse Associate", False),
]


@pytest.fixture(scope="module")
def embeddings():
    embedder = LocalEmbedder()
    import asyncio

    texts = INCLUDE_KEYWORDS + [t for t, _ in GOLDEN]
    vectors = asyncio.run(embedder.embed(texts))
    kw_vecs = vectors[: len(INCLUDE_KEYWORDS)]
    title_vecs = vectors[len(INCLUDE_KEYWORDS) :]
    return kw_vecs, title_vecs


def test_golden_set_agreement(embeddings):
    kw_vecs, title_vecs = embeddings
    correct = []
    wrong = []
    for (title, expected), vec in zip(GOLDEN, title_vecs, strict=True):
        score = max(cosine(vec, kv) for kv in kw_vecs)
        predicted = score >= THRESHOLD
        (correct if predicted == expected else wrong).append((title, expected, round(score, 3)))
    agreement = len(correct) / len(GOLDEN)
    assert agreement >= 0.9, f"golden-set agreement {agreement:.0%}; misses: {wrong}"
