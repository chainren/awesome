# -*- coding:utf-8 -*-

from aiohttp import web

from models import User, Blog, next_id
from coroweb import get, post
from apis import APIError, APIValueError, APIResourceNotFoundError, APIPermissionError
from config import configs

import logging
import time
import re
import hashlib
import json

logging.basicConfig(level=logging.INFO)

# 邮箱正则
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# sha1算法正则
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
# session coke名称
SESSION_COOKE = 'awesome_session'

_COOKIE_KEY = configs.session.get('secret')


@get('/')
async def index():
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, ' \
              'sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/api/users')
async def get_users():
    users = await User.findall(orderBy='created_at desc')
    for u in users:
        u.password = '******'
    return dict(users=users)


# 跳转注册页面
@get('/view/toRegister')
def to_register():
    return {
        '__template__': 'register.html'
    }


# 跳转到登录页面
@get('/view/toSignin')
def to_signin():
    return {
        '__template__': 'signin.html'
    }


# 用户注册方法
@post('/api/register')
async def user_register(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findall('email=?', [email])
    if len(users) > 0:
        raise APIError('register failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='')
    await user.save()
    # 设置session cookie
    resp = web.Response()
    resp.set_cookie(SESSION_COOKE, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    resp.content_type = 'application/json'
    resp.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return resp


# 用户登录
@post('/api/signin')
async def user_login(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findall('email=?', [email])
    if len(users) <= 0:
        raise APIValueError('email', 'Email not exists.')
    user = users[0]
    # 验证密码
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        return APIValueError('passwd', 'Invalid password.')
    # 验证通过，设置cookie
    resp = web.Response()
    resp.set_cookie(SESSION_COOKE, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    resp.content_type = 'application/json'
    resp.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return resp


# 退出登录
@get('/api/siginout')
def signout(request):
    referer = request.handers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(SESSION_COOKE, '-deleted-', max_age=0, httponly=True)
    logging.info('User signed out.')
    return r


# 将user信息放入cookie，生成session cookie值
def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


# 根据cookie判断用户是否合法登录用户
async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.strip('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None
