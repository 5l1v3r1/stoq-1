# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005,2006 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
##
""" Database access methods """

# FIXME: Refactor this to other files

import os
import platform
import socket
import subprocess
import time

from kiwi.component import get_utility
from kiwi.log import Logger

from stoqlib.database.exceptions import SQLError
from stoqlib.database.interfaces import IDatabaseSettings
from stoqlib.lib.translation import stoqlib_gettext

_ = stoqlib_gettext
_system = platform.system()
log = Logger('stoqlib.db.database')


def drop_database(dbname, settings=None):
    """Drops a database.
    @param dbname: the name of the database to be dropped.
    @param settings: optionally provide seetings, so that you dont have to
    provide IDatabaseSettings before calling this function.
    """
    if not settings:
        settings = get_utility(IDatabaseSettings)
    conn = settings.get_default_connection()

    try:
        # Postgres is lovely, try again a few times
        # before showing an error
        for i in range(3):
            try:
                conn.dropDatabase(dbname, ifExists=True)
                log.info("Dropped database %s" % (dbname,))
                break
            except Exception, e:
                time.sleep(1)
        else:
            if conn.databaseExists(dbname):
                raise e
    finally:
        conn.close()


def clean_database(dbname):
    """Cleans a database. If the database does not exist, it will be created.
    @param dbname: name of the database.
    """
    log.info("Cleaning database %s" % (dbname,))

    try:
        drop_database(dbname)
    except Exception, e:
        raise e

    settings = get_utility(IDatabaseSettings)
    if settings.dbname == dbname:
        conn = settings.get_default_connection()
    else:
        conn = settings.get_connection()

    conn.createDatabase(dbname)
    conn.close()


#
# General routines
#


def execute_sql(filename):
    """Inserts Raw SQL commands into the database read from a file.
    @param filename: filename with SQL commands
    @returns: return code, 0 if succeeded, positive integer for failure
    @rtype: int
    """
    settings = get_utility(IDatabaseSettings)

    log.info("Executing SQL script %s" % filename)

    if settings.rdbms == 'postgres':
        # Okay, this might look crazy, but it's actually the only way
        # to execute many SQL statements in PostgreSQL and
        # 1) Stop immediatelly when an error occur
        # 2) Print the error message, the filename and the line number where
        #    the error occurred.
        # 3) Do not print anything on the output unless it's an warning or a
        #    an error
        args = ['psql']
        # -U needs to go in first or psql on windows get confused
        args.extend(settings.get_tool_args())
        args.extend(['-n', '-q'])

        kwargs = {}
        if _system == 'Windows':
            # Hide the console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
            # For some reason XP doesn't like interacting with
            # proceses via pipes
            read_from_pipe = False
        else:
            read_from_pipe = True

        # We have two different execution modes,
        # 1) open stdin (-) and write the data via a pipe,
        #    this allows us to also disable noticies and info messages,
        #    so that only warnings are printed, we also fail if a warning
        #    or error is printed
        # 2) Pass in the file normally to psql, no error reporting included
        if read_from_pipe:
            args.extend(['-f', '-'])
            args.extend(['--variable', 'ON_ERROR_STOP='])
        else:
            args.extend(['-f', filename])

        args.append(settings.dbname)
        log.debug('executing %s' % (' '.join(args), ))
        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                **kwargs)

        if read_from_pipe:
            # We don't want to see notices on the output, skip them,
            # this will make all reported line numbers offset by 1
            proc.stdin.write("SET SESSION client_min_messages TO 'warning';");

            data = open(filename).read()
            # Rename serial into bigserial, for 64-bit id columns
            data = data.replace('id serial', 'id bigserial')
        else:
            data = None
        stdout, stderr = proc.communicate(data)
        if read_from_pipe and stderr:
            raise SQLError(stderr[:-1])
        return proc.returncode
    else:
        raise NotImplementedError(settings.rdbms)


def start_shell(command=None, quiet=False):
    """Runs a database shell using the current settings

    @param command: tell psql to execute the command string
    @param quiet: sets psql quiet option (-q)
    """
    settings = get_utility(IDatabaseSettings)

    if settings.rdbms == 'postgres':
        args = ['psql']
        if command:
            args.extend(['-c', command])
        if quiet:
            args.append('-q')
        args.extend(settings.get_tool_args())
        args.append(settings.dbname)

        print 'Connecting to %s' % (
            settings.get_connection_uri(filter_password=True),)
        proc = subprocess.Popen(args)
        proc.wait()
    else:
        raise NotImplementedError(settings.rdbms)

def test_local_database():
    """Check and see if we postgres running locally"""
    if _system == 'Windows':
        # Windows uses local sockets, just try and see if a connection
        # can be established
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', 5432))
        except socket.error:
            return False
        return True
    else:
        # default location for unix socket files is /tmp,
        # ubuntu/debian patches that to /var/run/postgresl
        for pgdir in ['/tmp', '/var/run/postgresql']:
            if (not os.path.exists(pgdir) and
                not os.path.isdir(pgdir)):
                continue

            # Check for the default unix socket which
            # we will later use to create a database user
            fname = os.path.join(pgdir, '.s.PGSQL.5432')
            if os.path.exists(fname):
                return True
        return False

def test_connection():
    """Test database connectivity for using command line tools
    @returns: True for success, False if connection fails
    @rtype: bool
    """
    settings = get_utility(IDatabaseSettings)

    log.info("Testing database connectivity using command line tools")

    if settings.rdbms == 'postgres':
        args = ['psql', '-n', '-q',
                '--variable', 'ON_ERROR_STOP=',
                '-c', 'SELECT 1;']
        args.extend(settings.get_tool_args())
        args.append(settings.dbname)

        log.debug('executing %s' % (' '.join(args), ))
        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)

        retval = proc.wait()
        return retval == 0
    else:
        raise NotImplementedError(settings.rdbms)


def dump_database(filename):
    """Dump the contents of the current database
    @param filename: filename to write the database dump to
    """
    settings = get_utility(IDatabaseSettings)
    log.info("Dumping database to %s" % filename)

    if settings.rdbms == 'postgres':
        args = ['pg_dump', '-Fc', '-E', 'UTF-8']
        if filename is not None:
            args.extend(['-f', filename])
        args.extend(settings.get_tool_args())
        args.append(settings.dbname)

        log.debug('executing %s' % (' '.join(args), ))
        proc = subprocess.Popen(args)
        return proc.wait() == 0
    else:
        raise NotImplementedError(settings.rdbms)


def rename_database(src, dest):
    """Renames a database.
    @param src: the name of the database we want to rename.
    @param dest: the new database name.
    """
    settings = get_utility(IDatabaseSettings)

    log.info("Renaming %s database to %s" % (src, dest))

    settings.dbname = dest
    conn = settings.get_default_connection()
    conn.renameDatabase(src, dest)
    conn.close()


def restore_database(dump):
    """Restores the current database.
    @param dump: a database dump file to be used to restore the database.
    """
    settings = get_utility(IDatabaseSettings)

    log.info("Restoring database %s using %s" % (settings.dbname, dump))

    if settings.rdbms == 'postgres':
        # This will create a new database
        newname = "%s__backup_%s" % (settings.dbname,
                                     time.strftime("%Y%m%d_%H%M"))
        clean_database(newname)

        args = ['pg_restore', '-d', newname]
        args.extend(settings.get_tool_args())
        args.append(dump)

        log.debug('executing %s' % (' '.join(args), ))

        proc = subprocess.Popen(args, stderr=subprocess.PIPE)
        retcode = proc.wait()
        return newname
    else:
        raise NotImplementedError(settings.rdbms)


def dump_table(table, filename=None):
    """Dump the contents of a table.
    Note this does not include the schema itself, just the data.
    To get the data call stdout.read() on the returned object.
    @param table: table to write
    @param proc: a subprocess.Popen instance
    """
    settings = get_utility(IDatabaseSettings)

    log.info("Dumping table to %s" % table)

    if settings.rdbms == 'postgres':
        args = ['pg_dump', '-E', 'UTF-8', '-a', '-t', table]
        if filename is not None:
            args.extend(['-f', filename])
        args.extend(settings.get_tool_args())
        args.append(settings.dbname)

        log.debug('executing %s' % (' '.join(args), ))
        return subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                env=dict(LANG='C'))
    else:
        raise NotImplementedError(settings.rdbms)


def query_server_time(conn):
    settings = get_utility(IDatabaseSettings)
    conn = settings.get_default_connection()

    if settings.rdbms == 'postgres':
        return conn.queryAll("SELECT NOW();")[0][0]
    else:
        raise NotImplementedError
