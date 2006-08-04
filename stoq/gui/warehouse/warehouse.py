# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005 Async Open Source <http://www.async.com.br>
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
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##
""" Main gui definition for warehouse application.  """

import gettext
import decimal

import gtk
from kiwi.ui.widgets.list import Column, SummaryLabel
from stoqlib.exceptions import DatabaseInconsistency
from stoqlib.database import finish_transaction
from stoqlib.lib.runtime import new_transaction, get_current_branch
from stoqlib.lib.message import warning
from stoqlib.lib.defaults import ALL_ITEMS_INDEX, ALL_BRANCHES
from stoqlib.lib.parameters import sysparam
from stoqlib.gui.wizards.receivingwizard import ReceivingOrderWizard
from stoqlib.gui.search.receivingsearch import PurchaseReceivingSearch
from stoqlib.gui.dialogs.productstockdetails import ProductStockHistoryDialog
from stoqlib.gui.dialogs.productretention import ProductRetentionDialog
from stoqlib.reporting.product import ProductReport
from stoqlib.domain.person import Person
from stoqlib.domain.sellable import SellableView
from stoqlib.domain.interfaces import ISellable, IBranch, IStorable
from stoqlib.domain.product import (Product, ProductFullStockView,
                                    ProductAdaptToSellable)

from stoq.gui.application import SearchableAppWindow

_ = gettext.gettext


class WarehouseApp(SearchableAppWindow):
    app_name = _('Warehouse')
    app_icon_name = 'stoq-warehouse-app'
    gladefile = "warehouse"
    searchbar_table = SellableView
    searchbar_result_strings = (_('product'), _('products'))
    searchbar_labels = (_('Matching:'),)
    filter_slave_label = _('Show products at:')
    klist_selection_mode = gtk.SELECTION_MULTIPLE
    klist_name = 'products'

    def __init__(self, app):
        SearchableAppWindow.__init__(self, app)
        self.table = Product.getAdapterClass(ISellable)
        self._setup_widgets()
        self._update_widgets()

    def _setup_widgets(self):
        value_format = '<b>%s</b>'
        self.summary_label = SummaryLabel(klist=self.products,
                                          column='stock',
                                          label=_('<b>Stock Total:</b>'),
                                          value_format=value_format)
        self.summary_label.show()
        self.list_vbox.pack_start(self.summary_label, False)

    def get_filter_slave_items(self):
        items = [(o.get_adapted().name, o)
                  for o in Person.iselect(IBranch, connection=self.conn)]
        if not items:
            raise DatabaseInconsistency('You should have at least one '
                                        'branch on your database.'
                                        'Found zero')
        items.append(ALL_BRANCHES)
        return items

    def _update_widgets(self, *args):
        has_stock = len(self.products) > 0
        self.retention_button.set_sensitive(has_stock)
        one_selected = len(self.products.get_selected_rows()) == 1
        self.history_button.set_sensitive(one_selected)
        self.retention_button.set_sensitive(one_selected)
        self.print_button.set_sensitive(has_stock)
        self._update_stock_total()

    def on_searchbar_activate(self, slave, objs):
        SearchableAppWindow.on_searchbar_activate(self, slave, objs)
        self._update_widgets()

    def _update_stock_total(self):
        self.summary_label.update_total()

    def _update_filter_slave(self, slave):
        self.searchbar.search_items()
        self._update_stock_total()

    def get_on_filter_slave_status_changed(self):
        return self._update_filter_slave

    def get_columns(self):
        return [Column('code', title=_('Code'), sorted=True,
                       data_type=int, format='%03d', width=120),
                Column('description', title=_("Description"),
                       data_type=str, expand=True),
                Column('supplier_name', title=('Supplier'),
                       data_type=str, width=170),
                Column('stock', title=_('Quantity'),
                       data_type=decimal.Decimal, width=90),
                Column('unit', title=_("Unit"), data_type=str,
                       width=70)]
    #
    # Hooks
    #

    def get_filterslave_default_selected_item(self):
        return get_current_branch(self.conn)

    def get_extra_query(self):
        """Hook called by SearchBar"""
        branch = self.filter_slave.get_selected_status()
        if branch != ALL_ITEMS_INDEX:
            self.set_searchtable(SellableView)
            return SellableView.q.branch_id == branch.id
        self.set_searchtable(ProductFullStockView)

    #
    # Callbacks
    #

    def on_products__selection_changed(self, *args):
        self._update_widgets()

    def _on_receive_action_clicked(self, *args):
        conn = new_transaction()
        model = self.run_dialog(ReceivingOrderWizard, conn)
        finish_transaction(conn, model)

    def on_stock_transfer_action_clicked(self, *args):
        # TODO To be implemented
        pass

    def on_retention_button__clicked(self, button):
        sellable_view = self.products.get_selected_rows()[0]
        product = Product.get(sellable_view.product_id,
                              connection=self.conn)
        storable = IStorable(product, connection=self.conn)
        warehouse = sysparam(self.conn).CURRENT_WAREHOUSE
        warehouse_branch = IBranch(warehouse.get_adapted(),
                                   connection=self.conn)
        if (not storable
            or not storable.get_full_balance(warehouse_branch)):
            warning(_(u"You must have at least one item "
                      "in stock to perfom this action."))
            return
        model = self.run_dialog(ProductRetentionDialog, self.conn, product)
        if not finish_transaction(self.conn, model, keep_transaction=True):
            return
        sellable_view.sync()
        self.products.update(sellable_view)

    def on_receiving_search_action_clicked(self, *args):
        self.run_dialog(PurchaseReceivingSearch, self.conn)

    def on_print_button__clicked(self, button):
        products = self.products.get_selected_rows() or self.products
        self.searchbar.print_report(ProductReport, products)

    def on_history_button__clicked(self, button):
        selected = self._klist.get_selected_rows()
        if len(selected) != 1:
            raise ValueError("You should have only one selected item at "
                             "this point")
        sellable = ProductAdaptToSellable.get(selected[0].id,
                                              connection=self.conn)
        self.run_dialog(ProductStockHistoryDialog, self.conn, sellable)
