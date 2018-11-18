# -*- coding:utf-8 -*-

from models import User
from coroweb import get, post


@get('/')
async def index():
    users = await User.findall()
    return {
        '__template__': 'test.html',
        'users': users
    }
