# -*- coding:utf-8 -*-

from models import User
from coroweb import get, post


@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }
