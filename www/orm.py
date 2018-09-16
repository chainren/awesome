# -*- coding:utf-8 -*-

import asyncio
import logging;

logging.basicConfig(level=logging.INFO)
import aiomysql


# 创建连接池
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('Create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password = kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


# select 方法
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global  __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('Rows returned:%s' %len(rs))
        return rs


# insert,update,delete通用方法
@asyncio.coroutine
def execute(sql, args):
    log(sql, args)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            effected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return effected


# 输出日志
def log(sql, args):
    logging.info('SQL: %s, args: %s' % (sql, args))

