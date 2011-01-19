# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2009 Async Open Source <http://www.async.com.br>
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
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##  Author(s):      Evandro Vale Miquelito  <evandro@async.com.br>
##                  Johan Dahlin            <jdahlin@async.com.br>
##
""" Base classes for application's GUI """

import datetime
import gettext
import os

import gtk
from kiwi.component import get_utility
from kiwi.enums import SearchFilterPosition
from kiwi.environ import environ
from stoqlib.database.orm import ORMObjectQueryExecuter
from stoqlib.database.runtime import (get_current_user, new_transaction,
                                      finish_transaction, get_connection)
from stoqlib.lib.interfaces import ICookieFile
from stoqlib.lib.message import yesno, info
from stoqlib.lib.parameters import sysparam
from stoqlib.gui.base.application import BaseApp, BaseAppWindow
from stoqlib.gui.base.search import StoqlibSearchSlaveDelegate
from stoqlib.gui.dialogs.csvexporterdialog import CSVExporterDialog
from stoqlib.gui.printing import print_report
from stoqlib.gui.introspection import introspect_slaves
from stoqlib.gui.slaves.userslave import PasswordEditor
from stoqlib.domain.person import PersonAdaptToCompany
from stoqlib.domain.interfaces import IBranch

import stoq


_ = gettext.gettext


class App(BaseApp):

    def __init__(self, window_class, config, options, runner):
        self.config = config
        self.options = options
        self.runner = runner
        self.window_class = window_class
        BaseApp.__init__(self, window_class)


class AppWindow(BaseAppWindow):
    """ Base class for the main window of applications.

    @cvar app_name: This attribute is used when generating titles for
                    applications.  It's also useful if we get a list of
                    available applications with the application names
                    translated. This list is going to be used when
                    creating new user profiles.

    @cvar klist_name: The name of the kiwi list instance used by our
                       application
    @cvar klist_selection_mode: The selection mode for the kiwi list

    """

    app_icon_name = None
    klist_name = 'klist'
    klist_selection_mode = gtk.SELECTION_BROWSE
    search = None

    def __init__(self, app):
        self.conn = new_transaction()
        BaseAppWindow.__init__(self, app)
        self.user_menu_label = get_current_user(self.conn
                                    ).username.capitalize()
        self._klist = getattr(self, self.klist_name)
        if not len(self._klist.get_columns()):
            self._klist.set_columns(self.get_columns())
        self._klist.set_selection_mode(self.klist_selection_mode)
        if app.options.debug:
            self._create_debug_menu()
        self._create_user_menu()
        self.setup_focus()
        self._check_examples_database()

    def _check_examples_database(self):
        async_comp = PersonAdaptToCompany.selectOneBy(
                            cnpj='03.852.995/0001-07',
                            connection=self.conn)
        if not async_comp:
            return

        async_branch = IBranch(async_comp.person, None)
        if not async_branch:
            return

        msg = _(u'<b>You are using the examples database.</b>')
        label = gtk.Label(msg)
        label.set_use_markup(True)

        button = gtk.Button(_(u'Remove examples'))
        button.connect('clicked', self._on_remove_examples__clicked)

        if hasattr(gtk, 'InfoBar'):
            bar = gtk.InfoBar()
            bar.get_content_area().add(label)
            bar.add_action_widget(button, 0)
            bar.set_message_type(gtk.MESSAGE_WARNING)

            bar.show_all()
        else:
            bar = gtk.EventBox()
            hbox = gtk.HBox()

            hbox.pack_start(label)
            hbox.pack_start(button, False, False, 6)

            bar.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
            bar.add(hbox)
            bar.show_all()

        self.main_vbox.pack_start(bar, False, False, 0)
        self.main_vbox.reorder_child(bar, 1)

    def _store_cookie(self, *args):
        u = get_current_user(self.conn)
        # XXX: encrypt and ask for password it again
        get_utility(ICookieFile).store(u.username, u.password)
        if hasattr(self, 'user_menu'):
            self._reset_user_menu()

    def _clear_cookie(self, *args):
        get_utility(ICookieFile).clear()
        if hasattr(self, 'user_menu'):
            self._reset_user_menu()

    def _change_password(self):
        trans = new_transaction()
        user = get_current_user(trans)
        retval = self.run_dialog(PasswordEditor, trans, user)
        finish_transaction(trans, retval)

    def _reset_user_menu(self):
        assert self.user_menu
#         label = self.user_menu.children()[0]
#         username = runtime.get_current_user().username
#         if self.app.config.check_cookie():
#             self.clear_cookie_menuitem.set_sensitive(1)
#             self.save_cookie_menuitem.set_sensitive(0)
#             star = " [$]"
#         else:
#             # A fixed width to avoid changes in the menu width
#             star = "    "
#             self.clear_cookie_menuitem.set_sensitive(0)
#             self.save_cookie_menuitem.set_sensitive(1)
#         label.set_text("user: %s%s" % (username, star))

    def _read_resource(self, domain, name):
        try:
            license = environ.find_resource(domain, name)
            return file(license)
        except EnvironmentError:
            import gzip
            license = environ.find_resource(domain, name + '.gz')
            return gzip.GzipFile(license)

    def _run_about(self, *args):
        about = gtk.AboutDialog()
        about.set_name(stoq.program_name)
        about.set_version(stoq.version)
        about.set_website(stoq.website)
        release_date = stoq.release_date
        about.set_comments('Release Date: %s' %
                           datetime.datetime(*release_date).strftime('%x'))
        about.set_copyright('Copyright (C) 2005-2010 Async Open Source')

        # Logo
        icon_file = environ.find_resource('pixmaps', 'stoq_logo.png')
        logo = gtk.gdk.pixbuf_new_from_file(icon_file)
        about.set_logo(logo)

        # License

        fp = self._read_resource('docs', 'COPYING')
        about.set_license(fp.read())

        # Authors & Contributors
        fp = self._read_resource('docs', 'AUTHORS')
        lines = [a.strip() for a in fp.readlines()]
        lines.append('') # separate authors from contributors
        fp = self._read_resource('docs', 'CONTRIBUTORS')
        lines.extend([c.strip() for c in fp.readlines()])
        about.set_authors(lines)

        about.run()
        about.destroy()

    def _create_user_menu(self):
        ui_string = """<ui>
          <menubar name="menubar">
            <menu action="UserMenu">
              <menuitem action="StoreCookie"/>
              <menuitem action="ClearCookie"/>
              <menuitem action="ChangePassword"/>
              <separator/>
              <menuitem action="ChangeUser"/>
              <menuitem action="ChangeApplication"/>
            </menu>
          </menubar>
        </ui>"""

        actions = [
            ('UserMenu', None, _('%s User') % self.user_menu_label),
            ('StoreCookie', gtk.STOCK_SAVE, _('_Store'), '<control>k',
             _('Store a cookie'), self.on_StoreCookie__activate),
            ('ClearCookie',     gtk.STOCK_CLEAR, _('_Clear'), '<control>e',
             _('Clear the cookie'), self.on_ClearCookie__activate),
            ('ChangePassword', gtk.STOCK_REFRESH, _('Chan_ge Password'),
              '<control>g', _('Change the password'),
              self.on_ChangePassword__activate),
            ('ChangeUser',    gtk.STOCK_REFRESH, _('C_hange User'), '<control>h',
             _('Change user'), self.on_ChangeUser__activate),
            ('ChangeApplication',    gtk.STOCK_REFRESH, _('Change Application'),
             'F5', _('Change application'), self._on_ChangeApplication__activate),
            ]

        ag = gtk.ActionGroup('UsersMenuActions')
        ag.add_actions(actions)

        self.uimanager.insert_action_group(ag, 0)
        self.uimanager.add_ui_from_string(ui_string)

        user_menu = self.uimanager.get_widget('/menubar/UserMenu')
        user_menu.set_right_justified(True)

        if sysparam(self.conn).DISABLE_COOKIES:
            self._clear_cookie()
            store_cookie = self.uimanager.get_widget('/menubar/UserMenu/StoreCookie')
            store_cookie.hide()
            clear_cookie = self.uimanager.get_widget('/menubar/UserMenu/ClearCookie')
            clear_cookie.hide()

    def _create_debug_menu(self):
        ui_string = """<ui>
          <menubar name="menubar">
            <menu action="DebugMenu">
              <menuitem action="Introspect"/>
            </menu>
          </menubar>
        </ui>"""
        actions = [
            ('DebugMenu', None, _('Debug')),
            ('Introspect', None, _('Introspect slaves'),
             None, None, self.on_Introspect_activate),
            ]

        ag = gtk.ActionGroup('DebugMenuActions')
        ag.add_actions(actions)
        self.uimanager.insert_action_group(ag, 0)
        self.uimanager.add_ui_from_string(ui_string)

    def print_report(self, report_class, *args, **kwargs):
        filters = self.search.get_search_filters()
        if filters:
            kwargs['filters'] = filters

        print_report(report_class, *args, **kwargs)

    #
    # Public API
    #

    def get_columns(self):
        raise NotImplementedError('You should define this method on parent')

    def setup_focus(self):
        """Define this method on child when it's needed."""
        pass

    def get_title(self):
        # This method must be redefined in child when it's needed
        return _('Stoq - %s') % self.app_name

    def can_change_application(self):
        """Define if we can change the current application or not.

        @returns: True if we can change the application, False otherwise.
        """
        return True

    def can_close_application(self):
        """Define if we can close the current application or not.

        @returns: True if we can close the application, False otherwise.
        """
        return True

    #
    # BaseAppWindow
    #

    def shutdown_application(self, *args):
        if self.can_close_application():
            if self.search:
                self.search.save_columns()
            self.app.shutdown()
        # We must return True here or the window will be hidden.
        return True

    #
    # Callbacks
    #

    def _on_quit_action__clicked(self, *args):
        self.shutdown_application()

    def on_StoreCookie__activate(self, action):
        self._store_cookie()

    def on_ClearCookie__activate(self, action):
        self._clear_cookie()

    def on_ChangePassword__activate(self, action):
        self._change_password()

    def on_ChangeUser__activate(self, action):
        self.app.runner.relogin()

    def _on_ChangeApplication__activate(self, action):
        if not self.can_change_application():
            return

        runner = self.app.runner
        appname = runner.choose()
        if appname:
            runner.run(appname)

    def on_Introspect_activate(self, action):
        window = self.get_toplevel()
        introspect_slaves(window)

    def _on_remove_examples__clicked(self, button):
        if not self.can_close_application():
            return
        if yesno(_(u'This will delete the current database and '
                    'configuration. Are you sure?'),
                 gtk.RESPONSE_NO,_(u"Cancel"),  _(u"Remove")):
             return

        info(_('Please, start stoq again to configure new database'))


        stoqdir = os.path.join(os.environ['HOME'], '.stoq')
        flag_file = os.path.join(stoqdir, 'remove_examples')
        open(flag_file, 'w').write('')

        self.shutdown_application()


class SearchableAppWindow(AppWindow):
    """
    Base class for applications which main interface consists of a list

    @cvar search_table: The we will query on to perform the search
    @cvar search_label: Label left of the search entry
    """

    search_table = None
    search_label = _('Search:')
    klist_name = 'results'

    def __init__(self, app):
        if self.search_table is None:
            raise TypeError("%r must define a search_table attribute" % self)

        self.executer = ORMObjectQueryExecuter(get_connection())
        self.executer.set_table(self.search_table)

        self.search = StoqlibSearchSlaveDelegate(self.get_columns(),
                                     restore_name=self.__class__.__name__)
        self.search.enable_advanced_search()
        self.search.set_query_executer(self.executer)
        self.results = self.search.search.results
        self.set_text_field_label(self.search_label)

        AppWindow.__init__(self, app)

        self.attach_slave('search_holder', self.search)

        self.create_filters()

        self.search.focus_search_entry()

    #
    # Public API
    #

    def set_searchtable(self, search_table):
        """
        @param search_table:
        """
        self.executer.set_table(search_table)
        self.search_table = search_table

    def add_filter(self, search_filter, position=SearchFilterPosition.BOTTOM,
                   columns=None, callback=None):
        """
        See L{SearchSlaveDelegate.add_filter}
        """
        self.search.add_filter(search_filter, position, columns, callback)

    def set_text_field_columns(self, columns):
        """
        See L{SearchSlaveDelegate.set_text_field_columns}
        """
        self.search.set_text_field_columns(columns)

    def set_text_field_label(self, label):
        """
        @param label:
        """
        search_filter = self.search.get_primary_filter()
        search_filter.set_label(label)

    def refresh(self):
        """
        See L{kiwi.ui.search.SearchSlaveDelegate.refresh}
        """
        self.search.refresh()

    def clear(self):
        """
        See L{kiwi.ui.search.SearchSlaveDelegate.clear}
        """
        self.search.clear()

    def export_csv(self):
        """Runs a dialog to export the current search results to a CSV file.
        """
        self.run_dialog(CSVExporterDialog, self, self.search_table,
                        self.results)

    #
    # Hooks
    #

    def create_filters(self):
        pass
    #
    # Callbacks
    #

    def on_ExportCSV__activate(self, action):
        self.export_csv()

