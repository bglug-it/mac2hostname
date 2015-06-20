#!/usr/bin/env python

"""A service to provide consistent naming based on MAC address and role."""
__author__ = 'Enrico Bacis'
__email__ = 'enrico.bacis@gmail.com'

from contextlib import contextmanager, closing
from subprocess import Popen, PIPE
from sqlite3 import connect
from bottle import Bottle, request
from json import dumps
from ConfigParser import ConfigParser
import re
import os
import sys

class MyApp:
  def __init__(self, configfile = '/etc/mac2hostname.ini'):
    if not os.path.isfile(configfile):
      print "Cannot find main file, %s. Exiting." % configfile
      sys.exit(1)

    # Loads configurations
    config = ConfigParser()
    config.read(configfile)
    # Populates private properties with configuration
    self.__dbfile = config.get('Daemon', 'Database') if config.has_option('Daemon', 'Database') else '/var/lib/mac2hostname/mac2hostname.db'
    self.__logdir = config.get('Daemon', 'LogDir') if config.has_option('Daemon', 'LogDir') else '/var/log/mac2hostname'
    self.__pidfile = config.get('Daemon', 'PIDFile') if config.has_option('Daemon', 'PIDFile') else '/var/run/mac2hostname/mac2hostname.pid'
    self.__bindaddress = config.get('Daemon', 'BindAddress') if config.has_option('Daemon', 'BindAddress') else '127.0.0.1'
    self.__port = config.getint('Daemon', 'Port') if config.has_option('Daemon',
    'Port') else 8080
    self.__defaultbase = config.get('NameSettings', 'Base') if config.has_option('NameSettings', 'Base') else 'client'
    self.__defaultrole = config.get('NameSettings', 'Role') if config.has_option('NameSettings', 'Role') else 'client'
    self.__namedigits = config.get('NameSettings', 'Digits') if config.has_option('NameSettings', 'Digits') else '2'
    self.__ip = False
    self.__mac = False
    self.__role = False
    self.__app = Bottle()
    # Applies routes
    self.__route()
    # Assures table creation
    self.__init_tables()

  # Private methods
  def __route(self):
    self.__app.get('/mac2hostname', callback=self.mac2hostname)
    self.__app.get('/whatsmyhostname', callback=self.whatsmyhostname)
    self.__app.get('/hosts', callback=self.hosts)
    self.__app.get('/ansible_inventory', callback=self.ansible_inventory)

  def __init_tables(self):
    with self.__getcursor() as cursor:
      cursor.execute('CREATE TABLE IF NOT EXISTS client (id INT PRIMARY KEY,'
                       'hostname TEXT NOT NULL UNIQUE, mac TEXT UNIQUE, role TEXT)')
      cursor.execute('CREATE INDEX IF NOT EXISTS idxmac ON client(mac)')

  def __getmac(self):
    if not self.__ip:
      return False

    Popen(['ping', '-c1', '-t2', self.__ip], stdout=PIPE).communicate()
    arp = Popen(['arp', '-n', self.__ip], stdout=PIPE).communicate()[0]
    self.__mac = re.search(r'(([\da-fA-F]{1,2}\:){5}[\da-fA-F]{1,2})', arp).group(1).lower()
    return True
    
  def __normalizemac(self, mac):
    return ':'.join(x.zfill(2) for x in mac.split('_')).lower()

  def __gethostname(self):
    # If called with ip parameter, comes from whatsmyhostname
    if self.__ip:
      self.__getmac()

    # At this point, the mac is set.
    with self.__getcursor() as cursor:
      (newid,) = cursor.execute('SELECT COALESCE(MAX(id) + 1, 1) FROM client').fetchone()
      # Constucts the hostname format
      formatstring = '%s-%0' + self.__namedigits + 'd'
      data = (newid, formatstring % (self.__defaultbase, newid), self.__mac, self.__role)
      # Since MAC is Unique, this fails with the same MAC address
      cursor.execute('INSERT OR IGNORE INTO client VALUES (?, ?, ?, ?)', data)
      (hostname,) = cursor.execute('SELECT hostname FROM client WHERE mac = "%s"' % self.__mac).fetchone()
      return hostname

  def __ping(self, obj):
    ping = Popen(['ping', '-c1', '-t2', obj])
    if ping == 0:
      return True

    return False

  @contextmanager
  def __getcursor(self):
    with connect(self.__dbfile) as connection:
      with closing(connection.cursor()) as cursor:
        yield cursor

  # Instance methods AKA routes
  def mac2hostname(self):
    # Ensure required parameters have been passed
    if not request.query.mac:
      return "Usage: GET /mac2hostname?mac=XX_XX_XX_XX_XX_XX[&base=YYY][&role=ZZZ]"
    # Sets up variables for possible parameters
    self.__mac = self.__normalizemac(request.query.mac)
    self.__base = request.query.base or self.__defaultbase
    self.__role = request.query.role or self.__defaultrole
    return self.__gethostname()

  def whatsmyhostname(self):
    # No required parameters
    self.__ip = request.query.ip or request['REMOTE_ADDR']
    self.__role = request.query.role or self.__defaultrole
    return self.__gethostname()

  def hosts(self):
    # Default where clause: no where specifications
    where = ''
    # If a role parameter is passed, list the hosts for that role
    if request.query.role: 
      where = "WHERE role = '%s'" % request.query.role
    with self.__getcursor() as cursor:
      return dumps([dict((meta[0], data)
        for meta, data in zip(cursor.description, row))
          for row in cursor.execute('SELECT role, hostname, mac FROM client '
              + where + 'ORDER BY role ASC, hostname ASC')], indent=4)

  def ansible_inventory(self):
    retval = {} # Empty dictionary, for now
    # Manages the case when first script is called with --host <hostname>
    # For the moment, do not pass any variables.
    if request.query.host:
      return retval
    with self.__getcursor() as cursor:
      available_roles = [row[0] for row in cursor.execute('SELECT DISTINCT role from client ORDER BY role ASC')]
      for role in available_roles:
        entries = []
        for row in cursor.execute('SELECT hostname FROM client WHERE role = "%s" ORDER BY hostname ASC' % role):
          #if self.__ping(row[0]):
            entries.append(row[0])
        retval[role] = entries

    # Returns JSON data
    return dumps(retval)

  def start(self):
    # Opens up a PID file
    pid = os.getpid()
    pidfile = open(self.__pidfile, 'w')
    pidfile.write('%s' % pid)
    pidfile.close()

    # Runs Bottle, at last.
    self.__app.run(host=self.__bindaddress, port=self.__port)

# Main body
if __name__ == '__main__':
  cfgfile = '/etc/mac2hostname.ini'
  if len(sys.argv) > 1:
    cfgfile = sys.argv[1]
  app = MyApp(cfgfile)
  app.start()
