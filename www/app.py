# -*- coding -*-

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time

from datetime import datetime


from aiohttp import web

from coroweb import add_routes, add_static


# 拦截器，记录请求日志
async def logger_factory(app, handler):
    async def logger(request):
        # 记录日志
        logging.info('Request : %s %s' % (request.method, request.path))
        # 继续处理请求
        return await handler(request)
    return logger


# 拦截器，处理响应
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html; charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html; charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # 默认返回
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain; charset=utf-8'
        return resp
    return response


# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
async def init(loop):
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    # add_routes(app, 'handlers')
    # add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('Server started at http://127.0.0.1:9000')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
