# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2006 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s):   Johan Dahlin   <jdahlin@async.com.br>
##

""" Stoqlib Interfaces """

from zope.interface import Attribute
from zope.interface.interface import Interface

class CookieError(Exception):
    pass

class ICookieFile(Interface):
    def get():
        """
        Fetch the cookie or raise CookieError if a problem occurred

        @returns: (username, password)
        @rtype: tuple
        """

    def store(username, password):
        """
        Stores a username and password

        @param username: username
        @param password: password
        """

    def clear():
        """
        Resets the cookie
        """

class ICurrentBranch(Interface):
    """
    This is a mainly a marker for the current branch which is expected
    to implement L{stoqlib.domain.interfaces.IBranch}
    It's mainly used by get_current_branch()
    """

class ICurrentBranchStation(Interface):
    """
    This is a mainly a marker for the current branch station.
    It's mainly used by get_current_station()
    """

class ICurrentUser(Interface):
    """
    This is a mainly a marker for the current user.
    It's mainly used by get_current_user()
    """

    username = Attribute('Username')
    password = Attribute('Password')
    profile = Attribute('A profile represents a colection of information '
                        'which represents what this user can do in the '
                        'system')

class IApplicationDescriptions(Interface):
    """Get a list of application names, useful for launcher programs
    """

    def get_application_names():
        """@returns: a list of application names"""

    def get_descriptions():
        """@returns: a list of tuples with some important Stoq application
        informations. Each tuple has the following data:
        * Application name
        * Application full name
        * Application icon name
        """


class IDatabaseSettings(Interface):
    """
    This is an interface to describe all important database settings
    """

    rdbms = Attribute('name identifying the database type')
    dbname = Attribute('name identifying the database name')
    address = Attribute('database address')
    port = Attribute('database port')

    def get_connection_uri():
        """@returns: a SQLObject connection URI"""
