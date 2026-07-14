"""Seed the database with the brief's defaults. Idempotent — safe to rerun.

Run: python -m app.db.seed  (or `make seed`)
"""
import asyncio

from loguru import logger
from sqlalchemy import select

from app.db.engine import SessionFactory
from app.db.models import AppSettings, Company, DiscoveryQuery, Keyword, Schedule
from app.shared.logging import setup_logging

# name -> careers URL (None = rely on API adapters / probing / discovery)
COMPANIES: dict[str, str | None] = {
    "Google": "https://www.google.com/about/careers/applications/jobs/results",
    "Microsoft": "https://jobs.careers.microsoft.com/global/en/search",  # + custom adapter
    "Amazon": "https://www.amazon.jobs/en/search",  # + custom adapter
    "Adobe": "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced",
    "Salesforce": "https://careers.salesforce.com/en/jobs/",
    "Atlassian": "https://www.atlassian.com/company/careers/all-jobs",
    "Oracle": "https://careers.oracle.com/jobs/",
    "Cisco": "https://careers.cisco.com/global/en/search-results",
    "Nvidia": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "Visa": "https://corporate.visa.com/en/jobs.html",
    "Uber": "https://www.uber.com/us/en/careers/list/",
    "Rubrik": None,  # auto-discovered on Greenhouse by the ATS prober
    "LinkedIn": "https://careers.linkedin.com",
    "Intuit": "https://jobs.intuit.com/search-jobs",
}

KEYWORDS: dict[str, list[str]] = {
    "include": [
        "Software Engineer", "Software Development Engineer", "Backend", "Platform",
        "Infrastructure", "AI Engineer", "Machine Learning", "University", "Student",
        "Intern", "Graduate", "New Grad",
    ],
    "requirement": [
        "2027", "Batch 2027", "Expected Graduation 2027", "Final Year", "India",
        "Remote", "Bangalore", "Hyderabad", "Pune",
    ],
    "exclude": [
        "Senior", "Principal", "Manager", "Staff", "Experienced", "5+ Years",
    ],
}

SCHEDULE_HOURS = [8, 14, 20]


async def seed() -> None:
    async with SessionFactory() as session:
        existing = {
            c.name: c
            for c in (await session.execute(select(Company))).scalars().all()
        }
        for name, url in COMPANIES.items():
            company = existing.get(name)
            if company is None:
                session.add(Company(name=name, careers_url=url))
            elif company.careers_url is None and url:
                company.careers_url = url

        existing_keywords = {
            (term, kind)
            for term, kind in (
                await session.execute(select(Keyword.term, Keyword.kind))
            ).all()
        }
        for kind, terms in KEYWORDS.items():
            for term in terms:
                if (term, kind) not in existing_keywords:
                    session.add(Keyword(term=term, kind=kind))

        existing_hours = set(
            (await session.execute(select(Schedule.hour))).scalars().all()
        )
        for hour in SCHEDULE_HOURS:
            if hour not in existing_hours:
                session.add(Schedule(hour=hour, minute=0))

        if (await session.execute(select(AppSettings))).scalar_one_or_none() is None:
            session.add(AppSettings(id=1))

        default_query = "Software Engineer Intern · India"
        if (
            await session.execute(
                select(DiscoveryQuery).where(DiscoveryQuery.name == default_query)
            )
        ).scalar_one_or_none() is None:
            session.add(
                DiscoveryQuery(
                    name=default_query,
                    keywords=["software engineer intern", "SDE intern 2027"],
                    country="India",
                    locations=["Bangalore", "Hyderabad", "Pune", "Remote"],
                )
            )

        await session.commit()
    logger.info("Seed complete.")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(seed())
