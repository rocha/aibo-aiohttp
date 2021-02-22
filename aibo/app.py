import asyncio
import logging
import time
from datetime import datetime
from pprint import pformat, pprint

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_jinja2 import template

from aibo.api import API

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@routes.get("/")
@template("index.html")
async def index(request):
    now = datetime.now()
    state = pformat(request.app["aibo"])
    return {"time": now, "state": state}


@routes.get("/status")
async def get_status(request):
    status = request.app["aibo"]
    return web.json_response(status)


@routes.get("/ws")
async def websocket(request):
    ws = web.WebSocketResponse()

    await ws.prepare(request)
    request.app["ws"].append(ws)

    try:
        async for msg in ws:
            print("msg:", pformat(msg))
            if msg.type == aiohttp.WSMsgType.ERROR:
                print(ws.exception())
    finally:
        request.app["ws"].remove(ws)

    return ws


async def client_session_ctx(app):
    app["ws"] = []
    app["aibo"] = {}
    app["tasks"] = []
    app["api"] = API()

    app.router.add_routes([web.post("/", app["api"].web_event_handler)])

    yield

    for task in app["tasks"]:
        task.cancel()
    await app["api"].close()


async def on_startup(app):
    api = app["api"]

    api.add_event_callback(lambda e: send_ws_event(app, e))

    task = asyncio.create_task(api.get_devices())
    task.add_done_callback(lambda t: pprint(t.result().get("devices", [])))

    create_update_task(app, "posture_status", 10)
    create_update_task(app, "name_called_status", 10)
    create_update_task(app, "sleepy_status", 30)
    create_update_task(app, "hungry_status", 30)
    create_update_task(app, "body_touched_status", 30)
    create_update_task(app, "voice_command_status", 30)
    create_update_task(app, "found_objects_status", 30)


async def init():
    app = web.Application()

    loader = jinja2.FileSystemLoader("./aibo/templates")
    aiohttp_jinja2.setup(app, loader=loader)

    routes.static("/", "./aibo/static")
    app.add_routes(routes)

    app.cleanup_ctx.append(client_session_ctx)

    app.on_startup.append(on_startup)

    return app


async def send_ws_event(app, event_data, ws=None):
    sockets = app["ws"] if ws is None else [ws]
    for s in sockets:
        if s.closed:
            app["ws"].remove(s)
        else:
            try:
                await s.send_json(event_data)
            except ValueError:
                logger.error("Invalid data")


def create_update_task(app, capability, wait_time):
    app["aibo"][capability] = {}
    task = asyncio.create_task(update_status(app, capability, wait_time))
    app["tasks"].append(task)
    return task


async def update_status(app, capability, wait_time):
    api = app["api"]
    app["aibo"][capability] = None
    while True:
        response = await api.execute(capability)
        if response.get("status") == "SUCCEEDED":
            new_status = response["result"].get(capability, None)
        else:
            new_status = None

        old_status = app["aibo"][capability]
        app["aibo"][capability] = new_status

        if new_status != old_status:
            event = {
                "deviceId": api.device_id,
                "data": {capability: new_status},
                "eventId": capability,
                "timestamp": int(time.time() * 1000),
            }
            await send_ws_event(app, event)

        await asyncio.sleep(wait_time)
