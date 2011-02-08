# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2007 Async Open Source <http://www.async.com.br>
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
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
""" Main gui definition for admin application.  """

import gettext

import pango
from kiwi.enums import SearchFilterPosition
from kiwi.ui.objectlist import Column, SearchColumn
from kiwi.ui.search import ComboSearchFilter

from stoqlib.database.orm import AND
from stoqlib.database.runtime import (new_transaction, finish_transaction,
                                      get_current_branch)
from stoqlib.domain.person import Person, PersonAdaptToUser, UserView
from stoqlib.domain.profile import UserProfile
from stoqlib.domain.invoice import InvoiceLayout
from stoqlib.gui.dialogs.clientcategorydialog import ClientCategoryDialog
from stoqlib.gui.dialogs.devices import DeviceSettingsDialog
from stoqlib.gui.dialogs.paymentcategorydialog import PaymentCategoryDialog
from stoqlib.gui.dialogs.paymentmethod import PaymentMethodsDialog
from stoqlib.gui.dialogs.pluginsdialog import PluginManagerDialog
from stoqlib.gui.dialogs.sintegradialog import SintegraDialog
from stoqlib.gui.editors.invoiceeditor import (InvoiceLayoutDialog,
                                               InvoicePrinterDialog)
from stoqlib.gui.editors.personeditor import UserEditor
from stoqlib.gui.editors.sellableeditor import SellableTaxConstantsDialog
from stoqlib.gui.search.fiscalsearch import CfopSearch, FiscalBookEntrySearch
from stoqlib.gui.search.parametersearch import ParameterSearch
from stoqlib.gui.search.personsearch import (EmployeeRoleSearch,
                                             EmployeeSearch,
                                             BranchSearch)
from stoqlib.gui.search.profilesearch import UserProfileSearch
from stoqlib.gui.search.stationsearch import StationSearch
from stoqlib.gui.search.taxclasssearch import TaxTemplatesSearch
from stoqlib.gui.wizards.personwizard import run_person_role_dialog
from stoqlib.lib.defaults import ALL_ITEMS_INDEX
from stoqlib.lib.message import info

from stoq.gui.application import SearchableAppWindow, VersionChecker

_ = gettext.gettext


class AdminApp(SearchableAppWindow):

    app_name = _('Administrative')
    app_icon_name = 'stoq-admin-app'
    gladefile = "admin"
    search_table = UserView
    search_label = _('matching:')

    def __init__(self, app):
        SearchableAppWindow.__init__(self, app)
        self._update_view()
        self._version_checker = VersionChecker(self.conn, self)
        self._version_checker.check_new_version()

    def create_filters(self):
        # FIXME: Convert the query to a Viewable so we can add name
        self.set_text_field_columns(['username'])
        status_filter = ComboSearchFilter(_('Show users with status'),
                                          self._get_status_values())
        self.executer.add_filter_query_callback(
            status_filter, self._get_status_query)
        self.add_filter(status_filter, position=SearchFilterPosition.TOP)

    def get_columns(self):
        return [SearchColumn('username', title=_('Login Name'), sorted=True,
                              data_type=str, width=150, searchable=True),
                SearchColumn('profile_name', title=_('Profile'),
                             data_type=str, width=150, expand=True,
                             ellipsize=pango.ELLIPSIZE_END),
                SearchColumn('name', title=_('Name'), data_type=str,
                             width=300),
                Column('status_str', title=_('Status'), data_type=str)]

    #
    # Private
    #

    def _get_status_values(self):
        items = [(v, k) for k, v in PersonAdaptToUser.statuses.items()]
        items.insert(0, (_('Any'), ALL_ITEMS_INDEX))
        return items

    def _get_status_query(self, state):
        query = None
        if state.value == PersonAdaptToUser.STATUS_ACTIVE:
            query = PersonAdaptToUser.q.is_active == True
        elif state.value == PersonAdaptToUser.STATUS_INACTIVE:
            query = PersonAdaptToUser.q.is_active == False

        return query

    def _update_view(self):
        has_selected = self.results.get_selected() is not None
        self.edit_button.set_sensitive(has_selected)

    def _edit_user(self):
        trans = new_transaction()
        user = trans.get(self.results.get_selected().user)
        model =  run_person_role_dialog(UserEditor, self, trans, user)
        finish_transaction(trans, model)
        trans.close()

    def _add_user(self):
        trans = new_transaction()
        model = run_person_role_dialog(UserEditor, self, trans)
        if finish_transaction(trans, model):
            self.refresh()
        trans.close()

    def _run_invoice_printer_dialog(self):
        if not InvoiceLayout.select(connection=self.conn):
            info(_(
                "You must create at least one invoice layout before adding an"
                "invoice printer"))
            return

        self.run_dialog(InvoicePrinterDialog, self.conn)

    def _run_payment_categories_dialog(self):
        trans = new_transaction()
        model = self.run_dialog(PaymentCategoryDialog, trans)
        finish_transaction(trans, model)
        trans.close()

    def _run_client_categories_dialog(self):
        trans = new_transaction()
        model = self.run_dialog(ClientCategoryDialog, trans)
        finish_transaction(trans, model)
        trans.close()

    #
    # Callbacks
    #

    def _on_fiscalbook_action_clicked(self, button):
        self.run_dialog(FiscalBookEntrySearch, self.conn, hide_footer=True)

    def _on_new_user_action_clicked(self, button):
        self._add_user()

    def on_results__double_click(self, results, user):
        self._edit_user()

    def on_results__selection_changed(self, results, user):
        self._update_view()

    def on_add_button__clicked(self, button):
        self._add_user()

    def on_edit_button__clicked(self, button):
        self._edit_user()

    def on_taxes__activate(self, action):
        self.run_dialog(SellableTaxConstantsDialog, self.conn)

    def on_sintegra__activate(self, action):
        branch = get_current_branch(self.conn)

        if branch.manager is None:
            info(_(
                "You must define a manager to this branch before you can create"
                " a sintegra archive"))
            return

        self.run_dialog(SintegraDialog, self.conn)

    def on_BranchSearch__activate(self, action):
        self.run_dialog(BranchSearch, self.conn, hide_footer=True)

    def on_BranchStationSearch__activate(self, action):
        self.run_dialog(StationSearch, self.conn, hide_footer=True)

    def on_CfopSearch__activate(self, action):
        self.run_dialog(CfopSearch, self.conn, hide_footer=True)

    def on_EmployeeSearch__activate(self, action):
        self.run_dialog(EmployeeSearch, self.conn, hide_footer=True)

    def on_EmployeeRole__activate(self, action):
        self.run_dialog(EmployeeRoleSearch, self.conn)

    def on_UserProfile__activate(self, action):
        self.run_dialog(UserProfileSearch, self.conn)

    def on_about_menu__activate(self, action):
        self._run_about()

    def on_devices_setup__activate(self, action):
        self.run_dialog(DeviceSettingsDialog, self.conn)

    def on_system_parameters__activate(self, action):
        self.run_dialog(ParameterSearch, self.conn)

    def on_invoice_printers__activate(self, action):
        self._run_invoice_printer_dialog()

    def on_invoices__activate(self, action):
        self.run_dialog(InvoiceLayoutDialog, self.conn)

    def on_PaymentMethod__activate(self, action):
        self.run_dialog(PaymentMethodsDialog, self.conn)

    def on_payment_categories__activate(self, action):
        self._run_payment_categories_dialog()

    def on_client_categories__activate(self, action):
        self._run_client_categories_dialog()

    def on_Plugins__activate(self, action):
        self.run_dialog(PluginManagerDialog, self.conn)

    def on_TaxTemplates__activate(self, action):
        self.run_dialog(TaxTemplatesSearch, self.conn)
