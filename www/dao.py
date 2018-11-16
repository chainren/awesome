# -*- coding:utf-8 -*-

import orm
import asyncio
import logging

from models import User

logging.basicConfig(level=logging.INFO)

async def test():
    logging.info('test add user')
    await orm.create_pool(loop, host='localhost', port=3306, user='root', password='root', db='awesome')

    u = User(name='Test', email='test@123.com', passwd='1234567890', image='about:blank')

    await u.save()


loop = asyncio.get_event_loop()
loop.run_until_complete(test())



