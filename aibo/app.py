import asyncio
from datetime import datetime
from pprint import pprint, pformat
import logging

import aiohttp
from aiohttp import web
import aiohttp_jinja2
from aiohttp_jinja2 import template
import jinja2

from aibo.api import API

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@routes.get('/')
@template('index.html')
async def index(request):
    now = datetime.now()
    state = pformat(request.app['aibo'])
    return {'time': now, 'state': state}


@routes.get('/ws')
async def websocket(request):
    ws = web.WebSocketResponse()

    await ws.prepare(request)
    request.app['ws'].append(ws)
    await send_status(request.app, ws)

    try:
        async for msg in ws:
            print('msg:', pformat(msg))
            if msg.type == aiohttp.WSMsgType.ERROR:
                print(ws.exception())
    finally:
        request.app['ws'].remove(ws)

    return ws


async def client_session_ctx(app):
    app['ws'] = []
    app['aibo'] = {}
    app['tasks'] = []
    app['api'] = API()

    app.router.add_routes([web.post('/', app['api'].web_event_handler)])

    yield

    for task in app['tasks']:
        task.cancel()
    await app['api'].close()


async def on_startup(app):
    api = app['api']

    api.add_event_callback(lambda e: send_event(app, e))

    task = asyncio.create_task(api.get_devices())
    task.add_done_callback(lambda t: pprint(t.result().get('devices', [])))

    create_update_task(app, 'posture_status', 10)
    create_update_task(app, 'sleepy_status', 30)
    create_update_task(app, 'hungry_status', 30)


async def init():
    app = web.Application()

    aiohttp_jinja2.setup(app,
                         loader=jinja2.FileSystemLoader('./aibo/templates'))

    routes.static('/', './aibo/static')
    app.add_routes(routes)

    app.cleanup_ctx.append(client_session_ctx)

    app.on_startup.append(on_startup)

    return app


async def send_ws(app, data, ws=None):
    sockets = app['ws'] if ws is None else [ws]
    for s in sockets:
        if s.closed:
            app['ws'].remove(s)
        else:
            try:
                await s.send_json(data)
            except ValueError:
                logger.error('Invalid data')


async def send_status(app, ws=None):
    data = {
        'type': 'status',
        'status': app['aibo'],
        'time': str(datetime.now())
    }
    await send_ws(app, data, ws)


async def send_event(app, event):
    data = {'type': 'event', 'event': event, 'time': str(datetime.now())}
    await send_ws(app, data)


def create_update_task(app, capability, wait_time):
    app['aibo'][capability] = {}
    task = asyncio.create_task(update_status(app, capability, wait_time))
    app['tasks'].append(task)
    return task


async def update_status(app, capability, wait_time):
    while True:
        response = await app['api'].execute(capability)

        if response.get('status') == 'SUCCEEDED':
            app['aibo'].update(response['result'])
        else:
            app['aibo'][capability] = {}

        await send_status(app)

        await asyncio.sleep(wait_time)
