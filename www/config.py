# -*- coding:utf-8 -*-

import config_default

configs = config_default.configs


# 合并配置
def merge(default, override):
    r = {}
    for k, v in default.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


class ConfigDict(dict):
    def __init__(self, names=(), values=(), **kw):
        super(ConfigDict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, item):
        try:
            return self[item]
        except:
            raise AttributeError(r"'ConfigDict' object has no attribute '%s'" % item)

    def __setattr__(self, key, value):
        self[key] = value


# 将配置项转入ConfigDict实例中
def toconfigdict(conf):
    d = ConfigDict()
    for k, v in conf.items():
        if isinstance(v, dict):
            toconfigdict(v)
        d[k] = v
    return d


try:
    import config_prod
    configs = merge(configs, config_prod.configs)
except ImportError:
    pass


configs = toconfigdict(configs)
