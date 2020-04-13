import concurrent.futures
import pytest
import time
import asyncio
from crawl_monitor.rate_limit import rate_limit_regulator, compute_crawl_rate,\
    MAX_CRAWL_RPS, MIN_CRAWL_RPS, MAX_CRAWL_SIZE
from test.mocks import FakeRedis, FakeAioSession, FakeAioResponse


def test_crawl_rates():
    low_crawl = compute_crawl_rate(1)
    assert low_crawl == MIN_CRAWL_RPS
    big_crawl = compute_crawl_rate(1000000000)
    assert big_crawl == MAX_CRAWL_RPS
    medium_crawl = compute_crawl_rate(MAX_CRAWL_SIZE / 2)
    tolerance = 1
    assert abs(medium_crawl - (MAX_CRAWL_RPS / 2)) < tolerance


@pytest.fixture
def source_fixture():
    """ Mocks the /v1/sources endpoint response. """
    return [
        {
            "source_name": "example",
            "image_count": 5000000,
            "display_name": "Example",
            "source_url": "example.com"
        }
    ]


async def run_regulator(regulator_task):
    try:
        await asyncio.wait_for(regulator_task, timeout=1)
    except concurrent.futures.TimeoutError:
        # expected
        pass


def create_mock_regulator(sources):
    response = FakeAioResponse(status=200, body=sources)
    session = FakeAioSession(response=response)
    redis = FakeRedis()
    regulator_task = asyncio.create_task(rate_limit_regulator(session, redis))
    return redis, regulator_task


@pytest.mark.asyncio
async def test_rate_regulation(source_fixture):
    sources = source_fixture
    redis, regulator_task = create_mock_regulator(sources)
    await run_regulator(regulator_task)
    assert redis.store['currtokens:example'] > 1


@pytest.mark.asyncio
async def test_error_circuit_breaker(source_fixture):
    sources = source_fixture
    redis, regulator_task = create_mock_regulator(sources)
    redis.store['statuslast50req:example'] = [b'500'] * 51
    await run_regulator(regulator_task)
    assert b'example' in redis.store['halted']


@pytest.mark.asyncio
async def test_temporary_halts(source_fixture):
    sources = source_fixture
    redis, regulator_task = create_mock_regulator(sources)
    one_second_ago = time.monotonic() - 1
    error_key = 'status60s:example'
    redis.store[error_key] = []
    for _ in range(3):
        redis.store[error_key].append(
            (one_second_ago, bytes(f'500:{one_second_ago}', 'utf-8'))
        )
    for _ in range(8):
        redis.store[error_key].append(
            (one_second_ago, bytes(f'200:{one_second_ago}', 'utf-8'))
        )
    await run_regulator(regulator_task)
    assert b'example' in redis.store['temp_halted']
