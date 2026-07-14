"""MatchPipeline: exclusions → semantic similarity → requirement boost → threshold.

Deterministic given embeddings; every decision carries human-readable reasons
persisted on the job row (FR-4.7). Embeddings are cached on the rows and only
recomputed when text/model changes.
"""
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSettings, Job, Keyword
from app.matching.embedders import Embedder, cosine
from app.matching.rules import (
    check_exclusions,
    check_requirements,
    has_early_career_signal,
    is_early_career_keyword,
)

# An include keyword only becomes a *reason* above this similarity.
REASON_SIMILARITY = 0.45


@dataclass
class MatchStats:
    processed: int = 0
    matched: int = 0
    excluded: int = 0
    unmatched: int = 0


def job_embed_text(job: Job) -> str:
    parts = [job.title]
    if job.location:
        parts.append(job.location)
    return " · ".join(parts)


async def _ensure_keyword_embeddings(
    session: AsyncSession, embedder: Embedder, keywords: list[Keyword]
) -> None:
    stale = [k for k in keywords if not k.embedding or k.embedding_model != embedder.model_name]
    if not stale:
        return
    vectors = await embedder.embed([k.term for k in stale])
    for kw, vec in zip(stale, vectors, strict=True):
        kw.embedding = vec
        kw.embedding_model = embedder.model_name
    await session.flush()


async def match_jobs(
    session: AsyncSession, embedder: Embedder, jobs: list[Job]
) -> MatchStats:
    keywords = (
        (await session.execute(select(Keyword).where(Keyword.enabled))).scalars().all()
    )
    includes = [k for k in keywords if k.kind == "include"]
    requirements = [k.term for k in keywords if k.kind == "requirement"]
    excludes = [k.term for k in keywords if k.kind == "exclude"]
    app = (await session.execute(select(AppSettings))).scalar_one()

    # Enforce the early-career gate only when the user actually targets it
    # (i.e. has intern/grad/new-grad-type include keywords). "Role" keywords
    # drive the semantic score; "level" keywords express the gate.
    role_includes = [k for k in includes if not is_early_career_keyword(k.term)]
    enforce_early_career = any(is_early_career_keyword(k.term) for k in includes)
    scored_includes = role_includes or includes

    await _ensure_keyword_embeddings(session, embedder, includes)

    stats = MatchStats()
    # Embed all jobs needing vectors in one batch.
    to_embed = [
        j for j in jobs if not j.embedding  # job text is immutable (hash identity)
    ]
    if to_embed:
        vectors = await embedder.embed([job_embed_text(j) for j in to_embed])
        for job, vec in zip(to_embed, vectors, strict=True):
            job.embedding = vec

    for job in jobs:
        stats.processed += 1

        # 1. Hard exclusions (senior terms + years-of-experience, title + desc).
        exclusion_hits = check_exclusions(job.title, excludes, job.description_snippet)
        if exclusion_hits:
            job.status = "excluded"
            job.match_score = None
            job.match_reasons = [{"term": t, "kind": "exclude"} for t in exclusion_hits]
            stats.excluded += 1
            continue

        # 2. Early-career gate: an internship monitor requires an intern/grad
        #    signal. Drops senior/architect/generic-IT roles that merely look
        #    like software work to the embedder.
        if enforce_early_career and not has_early_career_signal(
            job.title, job.description_snippet
        ):
            job.status = "unmatched"
            job.match_score = None
            job.match_reasons = [{"term": "not an early-career role", "kind": "gate"}]
            stats.unmatched += 1
            continue

        # 3. Semantic score vs role keywords + requirement boost.
        sims = [
            (k.term, cosine(job.embedding or [], k.embedding or []))
            for k in scored_includes
            if k.embedding
        ]
        sims.sort(key=lambda pair: pair[1], reverse=True)
        base = sims[0][1] if sims else 0.0

        req_hits = check_requirements(
            requirements, job.title, job.location, job.description_snippet
        )
        boost = min(app.requirement_boost * len(req_hits), 0.15)
        score = base + boost

        reasons: list[dict[str, object]] = [
            {"term": term, "kind": "include", "similarity": round(sim, 3)}
            for term, sim in sims[:4]
            if sim >= REASON_SIMILARITY
        ]
        reasons += [{"term": t, "kind": "requirement"} for t in req_hits]

        job.match_score = round(score, 4)
        job.match_reasons = reasons
        if score >= app.match_threshold:
            job.status = "matched"
            stats.matched += 1
        else:
            job.status = "unmatched"
            stats.unmatched += 1

    await session.commit()
    logger.info(
        "match run: {} processed / {} matched / {} excluded / {} unmatched",
        stats.processed, stats.matched, stats.excluded, stats.unmatched,
    )
    return stats
