# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005, 2006 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##              Johan Dahlin                <jdahlin@async.com.br>
##
##
""" Database startup routines"""

import gettext
import optparse
import socket

from kiwi.argcheck import argcheck
from kiwi.component import provide_utility
from sqlobject import sqlhub
from stoqlib.database.admin import ensure_admin_user, initialize_system
from stoqlib.database.migration import schema_migration
from stoqlib.database.runtime import get_connection
from stoqlib.domain.person import BranchStation
from stoqlib.exceptions import DatabaseError
from stoqlib.lib.interfaces import (ICurrentBranch, ICurrentBranchStation,
                                    IApplicationDescriptions)
from stoqlib.lib.message import error

from stoq.lib.configparser import register_config, StoqConfig

_ = gettext.gettext

def set_branch_by_stationid(conn):
    name = socket.gethostname()
    stations = BranchStation.select(
        BranchStation.q.name == name, connection=conn)
    if stations.count() == 0:
        error(_("The computer <u>%s</u> is not registered in Stoq") % name,
              _("To solve this, open the administrator application "
                "and register this computer."))
    station = stations[0]

    if not station.is_active:
        error(_("The computer <u>%s</u> is not active in Stoq") % name,
              _("To solve this, open the administrator application "
                "and re-activate this computer."))

    provide_utility(ICurrentBranchStation, station)
    provide_utility(ICurrentBranch, station.branch)

def setup(config, options=None, register_station=True, check_schema=True):
    """
    Loads the configuration from arguments and configuration file.

    @param config: a StoqConfig instance
    @param options: a Optionparser instance
    @param register_station: if we should register the branch station.
    @param check_schema: if we should check the schema
    """

    # NOTE: No GUI calls are allowed in here
    #       If you change anything here, you need to verify that all
    #       callsites are still working properly.
    #       bin/debug
    #       bin/stoq
    #       bin/stoqdbadmin
    #       python stoq/tests/runtest.py

    if options:
        if options.verbose:
            # FIXME: Set KIWI_LOG
            pass

        config.set_from_options(options)

    register_config(config)

    from stoq.lib.applist import ApplicationDescriptions
    provide_utility(IApplicationDescriptions, ApplicationDescriptions())

    try:
        conn = get_connection()
    except DatabaseError, e:
        error(e.short, e.msg)

    if register_station:
        set_branch_by_stationid(conn)
    if check_schema:
        if not schema_migration.check_updated(conn):
            error(_("Database schema error"),
                  _("The database schema has changed, but the database has "
                    "not been updated. Run 'stoqdbadmin updateschema` to"
                    "update the schema  to the latest available version."))

    if options and options.debug:
        conn.debug = True
    sqlhub.threadConnection = conn

def clean_database(config, options=None):
    """Clean the database
    @param config: a StoqConfig instance
    @param options: a Optionparser instance
    """
    if not options:
        password = ''
        verbose = False
    else:
        password = options.password
        verbose = options.verbose

    password = password or config.get_password()
    initialize_system(verbose=verbose)
    ensure_admin_user(password)

def get_option_parser():
    """
    Get the option parser used to parse arguments on the command line
    @returns: an optparse.OptionParser
    """

    # Note: only generic command line options here, specific ones
    #       should be added at callsite

    parser = optparse.OptionParser()

    group = optparse.OptionGroup(parser, 'General')
    group.add_option('-f', '--filename',
                      action="store",
                      type="string",
                      dest="filename",
                      default=None,
                      help='Use this file name for config file')
    group.add_option('-v', '--verbose',
                     action="store_true",
                     dest="verbose",
                     default=False)
    group.add_option('', '--debug',
                     action="store_true",
                     dest="debug")
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, 'Database access')
    group.add_option('-d', '--dbname',
                      action="store",
                      dest="dbname",
                      help='Database name to use')
    group.add_option('-H', '--hostname',
                      action="store",
                      dest="address",
                      help='Database address to connect to')
    group.add_option('-p', '--port',
                      action="store",
                      dest="port",
                      help='Database port')
    group.add_option('-u', '--username',
                      action="store",
                      dest="username",
                      help='Database username')
    group.add_option('-w', '--password',
                     action="store",
                     type="str",
                     dest="password",
                     help='user password',
                     default='')
    parser.add_option_group(group)
    return parser

@argcheck(StoqConfig, bool)
def create_examples(config, utilities=False):
    """Create example database for a given config file"""
    from stoqlib.domain.examples.createall import create
    create(utilities=utilities)
