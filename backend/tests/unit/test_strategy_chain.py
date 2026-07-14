import pytest

from app.scraping import strategies
from app.scraping.fetcher import Fetcher
from app.scraping.strategies import run_strategy_chain
from app.scraping.types import FetchError, RawJob, Strategy

JOB = RawJob(title="SDE Intern", apply_url="https://x.com/jobs/1")


def make_chain(monkeypatch, behaviors: dict[Strategy, object]) -> None:
    async def wrap(result):  # noqa: ANN001
        if isinstance(result, Exception):
            raise result
        return result

    chain = [
        (strat, (lambda r: (lambda f, n, u: wrap(r)))(behaviors.get(strat, [])))
        for strat, _ in strategies.CHAIN
    ]
    monkeypatch.setattr(strategies, "CHAIN", chain)


@pytest.fixture
def fetcher():
    return Fetcher(respect_robots=False)


async def test_first_success_wins(monkeypatch, fetcher):
    make_chain(monkeypatch, {Strategy.CAREERS_PAGE: [JOB]})
    outcome = await run_strategy_chain(fetcher, "X", "https://x.com")
    assert outcome.ok and outcome.strategy_used == "careers_page"
    assert len(outcome.attempts) == 1


async def test_falls_through_failures_and_records_attempts(monkeypatch, fetcher):
    make_chain(
        monkeypatch,
        {
            Strategy.CAREERS_PAGE: FetchError("u", "HTTP 403"),
            Strategy.JOB_API: [JOB, JOB],
        },
    )
    outcome = await run_strategy_chain(fetcher, "X", "https://x.com")
    assert outcome.strategy_used == "job_api"
    assert [a.strategy for a in outcome.attempts] == ["careers_page", "job_api"]
    assert outcome.attempts[0].error == "HTTP 403"


async def test_preferred_strategy_tried_first(monkeypatch, fetcher):
    make_chain(monkeypatch, {Strategy.JOB_API: [JOB]})
    outcome = await run_strategy_chain(fetcher, "X", "https://x.com", preferred="job_api")
    assert outcome.strategy_used == "job_api"
    assert outcome.attempts[0].strategy == "job_api"
    assert len(outcome.attempts) == 1


async def test_total_failure_reports_all_attempts(monkeypatch, fetcher):
    make_chain(monkeypatch, {})  # every strategy returns []
    outcome = await run_strategy_chain(fetcher, "X", "https://x.com")
    assert not outcome.ok
    assert len(outcome.attempts) == 5


async def test_unexpected_exception_does_not_kill_chain(monkeypatch, fetcher):
    make_chain(
        monkeypatch,
        {Strategy.CAREERS_PAGE: RuntimeError("boom"), Strategy.JOB_API: [JOB]},
    )
    outcome = await run_strategy_chain(fetcher, "X", "https://x.com")
    assert outcome.strategy_used == "job_api"
