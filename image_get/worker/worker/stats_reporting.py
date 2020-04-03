import time
"""
Reports the status of image processing jobs by publishing statistics to Redis.

Description of keys:

We want to know what proportion of requests failed over several time intervals.
These are tracked through window functions:
status60s:{domain} - Events that occurred in the last 60 seconds
status1hr:{domain} - Events that occurred in the last hour
status12hr:{domain} - Events that occurred in the last 12 hours

We also want to know the overall progress of the crawl and have a general
idea of which domains are having problems:
resize_errors - Number of errors that have occurred across all domains
resize_errors:{domain} - Number of errors that have occurred for a domain
num_resized - Number of successfully resized images
num_resized:{domain} - Number of successfully resized images for a domain

known_tlds - A set listing every TLD workers have encountered. The crawl 
monitor uses this set to determine which domains need to be watched. It will
not be possible to make requests to domains that are not in this list.

Domains are formatted as the TLD and suffix.
Valid example: status60s:staticflickr.com
Invalid example: status60s:https://staticflickr.com
"""

STATUS_60s = 'status60s:'
STATUS_1HR = 'status1hr:'
STATUS_12HR = 'status12hr:'

LAST_50_REQUESTS = 'statuslast50req:'

# Window intervals in seconds
ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
TWELVE_HOURS = ONE_HOUR * 12

WINDOW_PAIRS = [
    (STATUS_60s, ONE_MINUTE),
    (STATUS_1HR, ONE_HOUR),
    (STATUS_12HR, TWELVE_HOURS)
]

ERROR_COUNT = 'resize_errors'
TLD_ERRORS = 'resize_errors:'

SUCCESS_COUNT = 'num_resized'
TLD_SUCCESS = 'num_resized:'

SUCCEEDED = 1
FAILED = 0

KNOWN_TLDS = 'known_tlds'


class StatsManager:
    def __init__(self, redis):
        self.redis = redis
        self.known_tlds = set()

    @staticmethod
    async def _record_window_samples(pipe, domain, success):
        """ Insert a status into all sliding windows. """
        now = time.monotonic()
        for stat_key, interval in WINDOW_PAIRS:
            key = f'{stat_key}{domain}'
            await pipe.zadd(key, now, success)
            # Delete events from outside the window
            await pipe.zremrangebyscore(key, '-inf', now - interval)

    @staticmethod
    async def _record_last_50_requests_sample(pipe, domain, status):
        """ Insert a status into the list holding the last 50 requests."""
        await pipe.rpush(f'{LAST_50_REQUESTS}{domain}', status)
        await pipe.ltrim(f'{LAST_50_REQUESTS}{domain}', -50, -1)

    async def record_error(self, tld, code=None):
        """
        :param tld: The domain key for the associated URL.
        :param code: An optional status code.
        """
        domain = f'{tld.domain}.{tld.suffix}'
        async with await self.redis.pipeline() as pipe:
            await pipe.incr(ERROR_COUNT)
            await pipe.incr(f'{TLD_ERRORS}{domain}')
            affect_rate_limiting = True
            if code:
                await pipe.incr(f'{TLD_ERRORS}{domain}:{code}')
                if code == 404 or code == 'UnidentifiedImageError':
                    affect_rate_limiting = False
            if affect_rate_limiting:
                await self._record_window_samples(pipe, domain, FAILED)
            await pipe.execute()

    async def record_success(self, tld):
        domain = f'{tld.domain}.{tld.suffix}'
        async with await self.redis.pipeline() as pipe:
            await pipe.incr(SUCCESS_COUNT)
            await pipe.incr(f'{TLD_SUCCESS}{domain}')
            await self._record_window_samples(pipe, domain, SUCCEEDED)
            await pipe.execute()

    async def update_tlds(self, tld):
        """
        If a TLD hasn't been seen before, add it to the set in Redis.
        """
        if tld not in self.known_tlds:
            self.known_tlds.add(tld)
            await self.redis.sadd(KNOWN_TLDS, tld)
