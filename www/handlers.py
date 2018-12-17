# -*- coding:utf-8 -*-

from aiohttp import web

from models import User, Blog, Comment, next_id
from coroweb import get, post
from apis import APIError, APIValueError, APIResourceNotFoundError, APIPermissionError, Page
from config import configs

import asyncio
import logging
import time
import re
import hashlib
import json
import markdown2

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


# 跳转到日志编辑页
@get('/view/manage/toBlogEdit')
def to_blog_edit():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/createBlog'
    }


@get('/view/manage/blogs')
def to_blog_manage(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
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


# 创建日志
@post('/api/createBlog')
async def create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,
                user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog


# 获取单条日志内容
@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    comments = await Comment.findall('blog_id=?', [id], orderBy='created_at desc')
    for comment in comments:
        comment.html_content = text2html(comment.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


# 获取日志列表
@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findnumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findall(orderBy='created_at', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)


# 根据字符串page页码，转换成int值
def get_page_index(page):
    p = 1
    try:
        p = int(page)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


# 将user信息放入cookie，生成session cookie值
def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


# 根据cookie判断用户是否合法登录用户
@asyncio.coroutine
async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
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


# 检查是否为管理员
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


# 将text内容转换成html
def text2html(content):
    lines = map(lambda s: '<p>%s</p>' % s.replace('<', '&lt;').replace('>', '&gt;'),
                filter(lambda s: s.strip() != '', content.split('\n')))
    return ''.join(lines)
