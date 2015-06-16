#!/usr/bin/env python

"""API to map MAC addresses to hostnames"""

from contextlib import contextmanager, closing
from subprocess import Popen, PIPE
from sqlite3 import connect
from bottle import route, run, request
from json import dumps
import re
import os
import configparser

__author__ = "Enrico Bacis"
__email__ = "enrico.bacis@gmail.com"

# Added by Emiliano Vavassori <syntaxerrormmm-AT-gmail.com>
# Configuring script for usage as service - using ini file
config = ConfigParser.ConfigParser()
config.read('/etc/mac2hostname.ini')

# Will create a PID file to be used with init.d script
pid = os.getpid()
op = open(config.get('General', 'PIDFile'), 'w')
op.write("%s" % pid)
op.close()

@contextmanager
def getcursor(db = config.get('General', 'Database')):
    with connect(db) as connection:
        with closing(connection.cursor()) as cursor:
            yield cursor

def init_tables():
    with getcursor() as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS client (id INT PRIMARY KEY,'
                       'hostname TEXT NOT NULL UNIQUE, mac TEXT UNIQUE)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idxmac ON client(mac)')

def normalizemac(mac):
    return ':'.join(x.zfill(2) for x in mac.split(':')).upper()

def gethostname(mac, base=None):
    mac, base = normalizemac(mac), base or 'lab'
    with getcursor() as cursor:
        (newid,) = cursor.execute('SELECT COALESCE(MAX(id)+1, 1) FROM client').fetchone()
        cursor.execute('INSERT OR IGNORE INTO client VALUES (%s, "%s-%s", "%s")' % (newid, base, newid, mac))
        (hostname,) = cursor.execute('SELECT hostname FROM client WHERE mac = "%s"' % mac)
    return hostname

def getmac(ip):
    Popen(['ping', '-c1', '-t2', ip], stdout=PIPE).communicate()
    arp = Popen(['arp', '-n', ip], stdout=PIPE).communicate()[0]
    return re.search(r'(([\da-fA-F]{1,2}\:){5}[\da-fA-F]{1,2})', arp).group(1)

@route('/hosts')
def hosts():
    with getcursor() as cursor:
        return dumps([dict((meta[0], data)
                      for meta, data in zip(cursor.description, row))
                      for row in cursor.execute('SELECT hostname, mac FROM client ORDER BY id')], indent=4)

@route('/mac2hostname')
def mac2hostname():
    mac, base = request.query.mac, request.query.base
    if not mac:
        return 'Usage: GET /mac2hostname?mac=XX_XX_XX_XX_XX_XX[&base=YYY]'
    return gethostname(mac, base)

@route('/whatsmyhostname')
def whatsmyhostname():
    ip = request.query.ip or request['REMOTE_ADDR']
    return gethostname(getmac(ip), request.query.base)

if __name__ == '__main__':
    init_tables()
    run(
        host = config.get('General', 'BindAddress'),
        port = int(config.get('General', 'Port'))
    )

