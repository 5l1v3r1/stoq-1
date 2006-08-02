# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005, 2006 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
##  Author(s):  Evandro Vale Miquelito  <evandro@async.com.br>
##              Henrique Romano         <henrique@async.com.br>
##              Johan Dahlin            <jdahlin@async.com.br>
##
"""Routines for parsing the configuration file"""

import binascii
import gettext
import optparse
import os
from ConfigParser import SafeConfigParser

from kiwi.environ import environ, EnvironmentError
from kiwi.argcheck import argcheck
from stoqlib.database import (DEFAULT_RDBMS, DatabaseSettings,
                              build_connection_uri,
                              check_database_connection)
from stoqlib.exceptions import (FilePermissionError, ConfigError,
                                NoConfigurationError)

_ = gettext.gettext
_config = None


class StoqConfig:
    config_template = \
"""
# This file is generated automatically by Stoq and should not be changed
# manually unless you know exactly what are you doing.


[General]
# Default file where status and errors are appended to. Comment this out
# to allow output to be sent to stderr/stdout
logfile=~/.%(DOMAIN)s/application.log

[Database]
# Choose here the relational database management system you would like to
# use. Available is: postgres
rdbms=%(RDBMS)s

# This is used by the client to find the server.
address=%(ADDRESS)s

# The port to connect to
port=%(PORT)s

# The name of Stoq database in rdbms.
dbname=%(DBNAME)s

# the test database name
testdb=%(TESTDB)s

# The database username in rdbms.
dbusername=%(DBUSERNAME)s"""

    sections = ['General', 'Database']
    # Only Postgresql database is supported right now
    rdbms = DEFAULT_RDBMS
    domain = 'stoq'
    datafile = 'data'

    def __init__(self, filename=None):
        if not filename:
            filename = self._get_config_file()

        self._config = SafeConfigParser()

        if filename:
            if not self._open_config(filename):
                filename = None

        self._filename = filename

    def _get_config_file(self):
        filename = self.domain + '.conf'
        configdir = self.get_config_directory()
        standard = os.path.join(configdir, filename)
        if os.path.exists(standard):
            return standard

        try:
            conf_file = environ.find_resource('config', filename)
        except EnvironmentError, e:
            return
        return conf_file

    def _open_config(self, filename):
        if not os.path.exists(filename):
            return False
        self._config.read(filename)

        for section in StoqConfig.sections:
            if not self._config.has_section(section):
                raise ConfigError(
                    "config file does not have section: %s" % section)
        return True

    def _store_password(self, password):
        configdir = self.get_config_directory()
        datafile = os.path.join(configdir, StoqConfig.datafile)
        if not os.path.exists(datafile):
            if not os.path.exists(configdir):
                try:
                    os.makedirs(configdir)
                    os.chmod(configdir, 0700)
                except OSError, e:
                    if e.errno == 13:
                        raise FilePermissionError(
                            "Could not " % configdir)
                    raise

        try:
            fd = open(datafile, "w")
        except OSError, e:
            if e.errno == 13:
                raise FilePermissionError("%s is not writable" % datafile)
            raise

        # obfuscate password to avoid it being easily identified when
        # editing file on screen. this is *NOT* encryption!
        fd.write(binascii.b2a_base64(password))
        fd.close()

    def _get_password(self, filename):
        if not os.path.exists(filename):
            return

        data = open(filename).read()
        return binascii.a2b_base64(data)

    def _check_permissions(self, origin, writable=False, executable=False):
        # Make sure permissions are correct on relevant files/directories
        exception = None
        if not os.access(origin, os.R_OK):
            exception = "%s is not readable."
        if writable and not os.access(origin, os.W_OK):
            exception = "%s is not writable."
        if executable and not os.access(origin, os.X_OK):
            exception = "%s is not executable."
        if exception:
            raise FilePermissionError(exception % origin)

    def _has_option(self, name, section='General'):
        return self._config.has_option(section, name)

    def _get_option(self, name, section='General'):
        if not section in StoqConfig.sections:
            raise ConfigError('Invalid section: %s' % section)

        if self._config.has_option(section, name):
            return self._config.get(section, name)

        raise NoConfigurationError('%s does not have option: %s' %
                                   (self._filename, name))

    def _get_rdbms_name(self):
        if not self._has_option('rdbms', section='Database'):
            return 'postgres'
        return self._get_option('rdbms', section='Database')

    def _get_address(self):
        return self._get_option('address', section='Database')

    def _get_port(self):
        if not self._has_option('port', section='Database'):
            return '5432'
        return self._get_option('port', section='Database')

    def _get_dbname(self):
        if not self._has_option('dbname', section='Database'):
            return self._get_username()
        return self._get_option('dbname', section='Database')

    def _get_username(self):
        if not self._has_option('dbusername', section='Database'):
            import pwd
            return pwd.getpwuid(os.getuid())[0]
        return self._get_option('dbusername', section='Database')

    #
    # Public API
    #

    def create(self):
        config_dir = self.get_config_directory()
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)
        self._filename = os.path.join(
            config_dir, StoqConfig.domain + '.conf')

        if not self._config.has_section('General'):
            self._config.add_section('General')

        if not self._config.has_section('Database'):
            self._config.add_section('Database')

    def flush(self):
        """
        Writes the current configuration data to disk.
        """
        fd = open(self._filename, 'w')
        self._config.write(fd)
        fd.close()

    def remove(self):
        self._check_permissions(self._filename)
        os.remove(self._filename)

    def get_config_directory(self):
        return os.path.join(os.getenv('HOME'), '.' + self.domain)

    @argcheck(DatabaseSettings)
    def install_default(self, config_data):
        password = config_data.password

        self._store_password(password)
        configdir = self.get_config_directory()
        filename = os.path.join(configdir, StoqConfig.domain + '.conf')
        fd = open(filename, 'w')
        config_dict = dict(DOMAIN=StoqConfig.domain,
                           RDBMS=StoqConfig.rdbms,
                           PORT=config_data.port,
                           ADDRESS=config_data.address,
                           DBNAME=config_data.dbname,
                           TESTDB=config_data.dbname,
                           DBUSERNAME=config_data.username)
        fd.write(StoqConfig.config_template % config_dict)
        fd.close()
        self._config.read(filename)
        self._filename = filename

    def use_test_database(self):
        self._config.set('Database', 'dbname',
                         self._get_option('testdb', section='Database'))

    def check_connection(self):
        """Checks the stored database rdbms settings and raises ConfigError
        if something is wrong
        """
        conn_uri = self.get_connection_uri()
        check_database_connection(conn_uri)


    #
    # Accessors
    #

    def get_password(self):
        """
        @returns: password or None if it is not set
        """

        configdir = self.get_config_directory()
        data_file = os.path.join(configdir, StoqConfig.datafile)
        return self._get_password(data_file)

    def get_connection_uri(self):
        rdbms = self._get_rdbms_name()
        dbname = self._get_option('dbname', section='Database')

        if self._has_option('dbusername', section='Database'):
            username = self._get_option('dbusername', section='Database')
        else:
            username = os.getlogin()
        return build_connection_uri(self._get_address(), self._get_port(),
                                    dbname, rdbms, username,
                                    self.get_password())

    def get_settings(self):
        return DatabaseSettings(self._get_rdbms_name(),
                                self._get_address(),
                                self._get_port(),
                                self._get_dbname(),
                                self._get_username(),
                                self.get_password())

    @argcheck(optparse.Values)
    def set_from_options(self, options):
        """
        Updates the configuration given a values instance
        @param options: a optparse.Values instance
        """

        if options.address:
            self._config.set('Database', 'address', options.address)
        if options.port:
            self._config.set('Database', 'port', options.port)
        if options.dbname:
            self._config.set('Database', 'dbname', options.dbname)
        if options.username:
            self._config.set('Database', 'dbusername', options.username)
        if options.password:
            self._store_password(options.password)



#
# General routines
#


def _setup_stoqlib(config):
    from stoqlib.database import register_db_settings

    register_db_settings(config.get_settings())

@argcheck(StoqConfig)
def register_config(config):
    global _config
    _config = config
    _setup_stoqlib(config=config)

def get_config():
    global _config
    return _config
