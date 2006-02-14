# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005, 2006 Async Open Source <http://www.async.com.br>
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
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Henrique Romano             <henrique@async.com.br>
##              Evandro Vale Miquelito      <evandro@async.com.br>
##              Bruno Rafael Garcia         <brg@async.com.br>
##
""" Editors definitions for products"""

import gettext

from kiwi.datatypes import ValidationError
from kiwi.ui.widgets.list import Column
from kiwi.utils import gsignal

from stoqlib.gui.base.lists import SimpleListDialog
from stoqlib.gui.base.editors import BaseEditor, BaseEditorSlave
from stoqlib.gui.base.dialogs import run_dialog
from stoqlib.domain.person import Person
from stoqlib.domain.sellable import BaseSellableInfo
from stoqlib.domain.product import ProductSupplierInfo, Product
from stoqlib.domain.interfaces import ISellable, IStorable, ISupplier
from stoqlib.gui.editors.sellable import SellableEditor
from stoqlib.lib.validators import get_price_format_str
from stoqlib.lib.parameters import sysparam

_ = lambda msg: gettext.dgettext('stoqlib', msg)


#
# Slaves
#


class ProductSupplierSlave(BaseEditorSlave):
    """ A basic slave for suppliers selection.  This slave emits the
    'cost-changed' signal when the supplier's product cost has
    changed.
    """
    gladefile = 'ProductSupplierSlave'
    proxy_widgets = 'supplier_lbl',
    model_type = Product

    gsignal("cost-changed")

    def on_supplier_button__clicked(self, button):
        self.edit_supplier()
 
    def edit_supplier(self):
        main_supplier = self.model.get_main_supplier_info()
        if not main_supplier:
            current_cost = 0.0
        else:
            current_cost =  main_supplier.base_cost
        result = run_dialog(ProductSupplierEditor, self, self.conn, self.model)
        if not result:
            return
        if result.base_cost != current_cost:
            self.emit("cost-changed")
        self.proxy.update('main_supplier_info.name')

    def setup_proxies(self):
        self.proxy = self.add_proxy(self.model,
                                    ProductSupplierSlave.proxy_widgets)

#
# Editors
#


class ProductSupplierEditor(BaseEditor):
    model_name = _('Product Suppliers')
    model_type = Product
    gladefile = 'ProductSupplierEditor'

    proxy_widgets = ('supplier_combo',
                     'base_cost',
                     'icms',
                     'notes')

    def __init__(self, conn, model=None):
        BaseEditor.__init__(self, conn, model)
        # XXX: Waiting fix for bug #2043
        self.new_supplier_button.set_sensitive(False)

    def set_widget_formats(self):
        self.base_cost.set_data_format(get_price_format_str())
        self.icms.set_data_format(get_price_format_str())

    def setup_combos(self):
        supplier_list = Person.iselect(ISupplier, connection=self.conn)
        items = [(obj.get_adapted().name, obj) for obj in supplier_list]

        assert items, ("There is no suppliers in database!")

        self.supplier_combo.prefill(items)

    def list_suppliers(self):
        cols = [Column('name', title=_('Supplier name'),
                       data_type=str, width=350),
                Column('base_cost', title=_('Base Cost'),
                       data_type=float, width=120)]

        run_dialog(SimpleListDialog, self, cols, self.model.suppliers)

    def update_model(self):
        selected_supplier = self.supplier_combo.get_selected_data()

        # Kiwi proxy already sets the supplier attribute to new selected
        # supplier, so we need revert this and set the correct supplier:
        self.prod_supplier_proxy.model.supplier = self._last_supplier
        
        self._last_supplier = selected_supplier
        is_valid_model = self.prod_supplier_proxy.model.base_cost

        if is_valid_model:
            self.prod_supplier_proxy.model.product = self.model

        for supplier_info in self.model.suppliers:
            if supplier_info.supplier is selected_supplier:
                model = supplier_info
                break
        else:
            model = ProductSupplierInfo(connection=self.conn, product=None,
                                        supplier=selected_supplier)
        self.prod_supplier_proxy.new_model(model)

        # updating the field for the widget validation works fine
        self.prod_supplier_proxy.update('base_cost')

    #
    # BaseEditor hooks
    #

    def get_title(self, *args):
        return _('Add supplier information')

    def setup_proxies(self):
        self.setup_combos()

        model = self.model.get_main_supplier_info()
        if not model:
            supplier = sysparam(self.conn).SUGGESTED_SUPPLIER
            model = ProductSupplierInfo(connection=self.conn, product=None, 
                                        is_main_supplier=True,
                                        supplier=supplier)
        self.set_widget_formats()

        self.prod_supplier_proxy = self.add_proxy(model, 
                                                  self.proxy_widgets)

        # XXX:  GTK don't allow me get the supplier selected in the combo
        # *when* the 'changed' signal is emitted, i.e, when the 'changed'
        # callback is called, the model already have the new value selected
        # by user, so I need to store in a local attribute the last model
        # selected.
        self._last_supplier = model.supplier

    def update_main_supplier_references(self, main_supplier):
        if not self.model.suppliers:
            return

        for s in self.model.suppliers:
            if s is main_supplier:
                s.is_main_supplier = True
                continue

            s.is_main_supplier = False

    def on_confirm(self):
        current_supplier = self.prod_supplier_proxy.model
        is_valid_model = current_supplier and current_supplier.base_cost
        if not current_supplier or not is_valid_model:
            return

        current_supplier.product = self.model
        self.update_main_supplier_references(current_supplier)
        return current_supplier

    #
    # Kiwi handlers
    # 

    def on_supplier_list_button__clicked(self, button):
        self.list_suppliers()

    def on_supplier_combo__changed(self, *args):
        self.update_model()

    def on_base_cost__validate(self, entry, value):
        if not value or value <= 0.0:
            return ValidationError("Value must be greater than zero.")


class ProductEditor(SellableEditor):
    model_name = _('Product')
    model_type = Product

    def setup_slaves(self):
        supplier_slave = ProductSupplierSlave(self.conn, self.model)
        supplier_slave.connect("cost-changed",
                               self._on_supplier_slave__cost_changed)
        self.attach_slave('product_supplier_holder', supplier_slave)

    def setup_widgets(self):
        self.notes_lbl.set_text(_('Product details'))
        self.stock_total_lbl.show()
        self.stock_lbl.show()

    def create_model(self, conn):
        model = Product(connection=conn)
        sellable_info = BaseSellableInfo(connection=conn)

        model.addFacet(ISellable, base_sellable_info=sellable_info,
                       connection=conn)
        model.addFacet(IStorable, connection=conn)
        supplier = sysparam(conn).SUGGESTED_SUPPLIER
        supplier_info = ProductSupplierInfo(connection=conn,
                                            is_main_supplier=True,
                                            supplier=supplier,
                                            product=model)
        return model

    #
    # Callbacks
    #

    def _on_supplier_slave__cost_changed(self, slave):
        if not self.sellable_proxy.model.cost and self.model.suppliers:
           base_cost = self.model.get_main_supplier_info().base_cost
           self.sellable_proxy.model.cost = base_cost or 0.0
           self.sellable_proxy.update('cost')

        if self.sellable_proxy.model.base_sellable_info.price:
           return
        cost = self.sellable_proxy.model.cost or 0.0
        markup = self.sellable_proxy.model.get_suggested_markup() or 0.0
        price = cost + ((markup / 100) * cost)
        self.sellable_proxy.model.base_sellable_info.price = price
        self.sellable_proxy.update('price')
