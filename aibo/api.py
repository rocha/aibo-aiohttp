import asyncio
import logging
import os

from aiohttp import web

from aibo.limiter import RateLimitedSession

API_TOKEN = os.getenv("API_TOKEN", "")
EVENT_SECURITY_TOKEN = os.getenv("EVENT_SECURITY_TOKEN", "")
DEVICE_ID = os.getenv("DEVICE_ID", "")

BASE_URL = "https://public.api.aibo.com/v1"
BASE_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

MAX_REQUESTS_PER_MINUTE = 1000 / 60
DEFAULT_EXECUTE_RETRIES = 4
DEFAULT_EXECUTE_RETRY_SLEEP = 5

logger = logging.getLogger(__name__)

# /devices
# /devices/{id}/capabilities/{function}/execute
# /executions/{id} ACCEPTED IN_PROGRESS SUCCEEDED FAILED (CANNOTSTART INTERRUPT ABORT TIMEOUT)
# /oauth2/{token|revoke}


class Execution:
    def __init__(self, eid, capability, retries, wait_time):
        self.eid = eid
        self.capability = capability
        self.retries = retries
        self.wait_time = wait_time


class API:
    def __init__(self, device_id=DEVICE_ID):
        rate = MAX_REQUESTS_PER_MINUTE / 60
        self.session = RateLimitedSession(
            rate=rate, max_tokens=10, headers=BASE_HEADERS
        )
        self.device_id = device_id
        self.event_callbacks = []

    async def get_devices(self):
        logger.debug("get devices")
        path = BASE_URL + "/devices"
        async with self.session.get(path) as response:
            return await response.json()

    async def post_capability(self, capability, payload):
        base, aid = BASE_URL, self.device_id
        path = f"{base}/devices/{aid}/capabilities/{capability}/execute"
        async with self.session.post(path, json=payload) as response:
            return await response.json()

    async def get_execution(self, execution_id):
        path = f"{BASE_URL}/executions/{execution_id}"
        async with self.session.get(path) as response:
            return await response.json()

    async def execute(
        self,
        capability,
        arguments=None,
        retries=DEFAULT_EXECUTE_RETRIES,
        wait_time=DEFAULT_EXECUTE_RETRY_SLEEP,
    ):
        payload = {}
        if arguments:
            payload["arguments"] = arguments

        logger.debug("post %s", capability)

        response = await self.post_capability(capability, payload)
        if response.get("status") == "ACCEPTED":
            execution = Execution(
                response["executionId"], capability, retries, wait_time
            )
            response = await self._wait_execution(execution)
        elif "error" in response:
            logger.error(response)

        return response

    async def _wait_execution(self, execution):
        response = {"capability": execution.capability, "executionId": execution.eid}

        await asyncio.sleep(1)

        count = 0
        while count < execution.retries:
            logger.debug(
                "get %s %s/%s", execution.capability, count + 1, execution.retries
            )

            res = await self.get_execution(execution.eid)

            has_error = "error" in res
            finished = res.get("status") in {"SUCCEEDED", "FAILED"}
            if finished or has_error:
                response.update(res)
                break

            count += 1

            # don't sleep on the last cycle
            if count < execution.retries:
                await asyncio.sleep(execution.wait_time)

        if "status" not in response and "error" not in response:
            response.update({"status": "FAILED", "result": "TIMEOUT"})

        if response.get("status") != "SUCCEEDED":
            logger.error(response)
        else:
            logger.debug(response)

        return response

    async def web_event_handler(self, request):
        headers = request.headers
        if headers.get("X-Security-Token", "") != EVENT_SECURITY_TOKEN:
            return web.HTTPUnauthorized()

        response = {}
        data = await request.json()

        if data["eventId"] == "endpoint_verification":
            response["challenge"] = data["challenge"]
        else:
            for callback in self.event_callbacks:
                await callback(data)

        return web.json_response(response)

    def add_event_callback(self, callback):
        self.event_callbacks.append(callback)

    async def close(self):
        await self.session.close()
