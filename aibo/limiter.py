import asyncio
import time

from aiohttp import ClientSession

DEFAULT_RATE = 1
DEFAULT_MAX_TOKENS = 10


class RateLimitedSession(ClientSession):
    def __init__(
        self, rate=DEFAULT_RATE, max_tokens=DEFAULT_MAX_TOKENS, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.rate = rate  # request/sec
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.updated_at = time.monotonic()

    async def _wait_for_token(self):
        # token bucket algorithm
        while self.tokens <= 1:
            now = time.monotonic()
            delta = now - self.updated_at
            new_tokens = self.tokens + delta * self.rate
            if new_tokens >= 1:
                self.tokens = min(new_tokens, self.max_tokens)
                self.updated_at = now
            else:
                await asyncio.sleep(1 / self.rate)
        self.tokens -= 1

    async def _request(self, *args, **kwargs):
        await self._wait_for_token()
        return await super()._request(*args, **kwargs)
