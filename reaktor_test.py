#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging.config, threading, time
import reaktor


DEBUG, DEVEL = True, True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'simple': {
            'format': '%(message)s'
        },
        'extended': {
            'format': '[%(levelname)s %(asctime)s %(process)d][%(filename)s:%(lineno)d][%(module)s]\t%(message)s'
        },
    },

    'handlers': {
        'console': {
            'level':     'DEBUG',
            'class':     'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level':     'DEBUG',
            'class':     'logging.FileHandler',
            'filename':  'log.asc',
            'formatter': 'extended',
        },
    },

    'loggers': {
        'reaktor': {
            'level':      'DEBUG'   if DEBUG else 'INFO',
            'handlers':  ['console' if DEVEL else 'file',],
            'propagate': True,
        },
        'txtr': {
            'level':      'DEBUG'   if DEBUG else 'INFO',
            'handlers':  ['console' if DEVEL else 'file',],
            'propagate': True,
        },
        'txtrapp': {
            'level':      'DEBUG'   if DEBUG else 'INFO',
            'handlers':  ['console' if DEVEL else 'file',],
            'propagate': True,
        },
    },
}
logging.config.dictConfig(LOGGING)


threads = 5
running = True


def run():
    global running

    r = reaktor.Reaktor()
    count = 0
    res1 = r.WSContentCategoryMgmt.getCatalogContentCategoryRoots("nobody")
    try:
        while running:
            res2 = r.WSContentCategoryMgmt.getCatalogContentCategoryRoots("nobody")
            if not str(res1) == str(res2):
                raise "new answer %s" % res2
            count += 1
            print count
    except Exception, err:
        print err
    running = False


if __name__ == "__main__":

    reaktor.REAKTOR_HOST = u"staging.txtr.com"
    reaktor.REAKTOR_PORT = 80
    reaktor.REAKTOR_SSL  = False
    reaktor.REAKTOR_PATH = u"/json/rpc?v=2"

    for i in range(threads):
        t = threading.Thread(target = run)
        t.daemon = True
        t.start()

    while running:
        time.sleep(500)

