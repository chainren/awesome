# -*- coding:utf-8 -*-

import orm
import asyncio

from models import User


def test():
    yield from orm.create_pool(user='root', password='root', database='awesome')

    u = User(name='Test', email='test@123.com', passwd='1234567890', image='about:blank')

    #yield from u.save()


if __name__ == 'main':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    loop.close()



