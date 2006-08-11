# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005,2006 Async Open Source <http://www.async.com.br>
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
## Foundation, Inc., or visit: http://www.gnu.org/.
##
""" Base classes to manage product's informations """

import decimal

from kiwi.datatypes import currency
from kiwi.argcheck import argcheck
from sqlobject import (UnicodeCol, ForeignKey, MultipleJoin,
                       BoolCol, IntCol, BLOBCol)
from sqlobject.sqlbuilder import AND
from zope.interface import implements
from stoqdrivers.constants import TAX_ICMS, TAX_NONE, TAX_SUBSTITUTION

from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.runtime import get_current_branch
from stoqlib.exceptions import (StockError, SellError, DatabaseInconsistency,
                                StoqlibError)
from stoqlib.domain.columns import PriceCol, DecimalCol
from stoqlib.domain.person import PersonAdaptToBranch, Person
from stoqlib.domain.stock import AbstractStockItem
from stoqlib.domain.base import Domain, ModelAdapter
from stoqlib.domain.sellable import (AbstractSellable, AbstractSellableItem,
                                     SellableView)
from stoqlib.domain.interfaces import (ISellable, IStorable, IContainer,
                                       IDelivery, IBranch)

_ = stoqlib_gettext

Person # pyflakes

#
# Base Domain Classes
#


class ProductSupplierInfo(Domain):
    """
    Supplier information for a Product

    Each product can has more than one supplier.

    B{Important attributes}:
        - I{is_main_supplier}: defines if this object stores information
                               for the main supplier.
        - I{base_cost}: the cost which helps the purchaser to define the
                        main cost of a certain product. Each product can
                        have multiple suppliers and for each supplier a
                        base_cost is available. The purchaser in this case
                        must decide how to define the main cost based in
                        the base cost avarage of all suppliers.
        - I(icms): a Brazil-specific attribute that means
                   'Imposto sobre circulacao de mercadorias e prestacao '
                   'de servicos'
    """

    base_cost = PriceCol(default=0)
    notes = UnicodeCol(default='')
    is_main_supplier = BoolCol(default=False)
    # This is Brazil-specific information
    icms = DecimalCol(default=0)
    supplier =  ForeignKey('PersonAdaptToSupplier')
    product =  ForeignKey('Product')


    #
    # Auxiliary methods
    #

    def get_name(self):
        if not self.supplier:
            raise ValueError('This object must have a valid supplier '
                             'attribute')
        return self.supplier.get_adapted().name

class ProductRetentionHistory(Domain):
    """Class responsible to store information about product's retention."""

    quantity = DecimalCol(default=0)
    reason = UnicodeCol(default='')
    product = ForeignKey('Product')


class Product(Domain):
    """Class responsible to store basic products informations."""

    suppliers = MultipleJoin('ProductSupplierInfo')
    image = BLOBCol(default='')
    #
    # Facet hooks
    #

    def facet_IStorable_add(self, **kwargs):
        storable = ProductAdaptToStorable(self, **kwargs)
        storable.fill_stocks()
        return storable

    #
    # General Methods
    #

    def block(self, conn, quantity, branch, reason, product):
        storable = IStorable(self)
        storable.decrease_stock(quantity, branch)
        return ProductRetentionHistory(quantity=quantity, product=product,
                                       reason=reason, connection=conn)

    #
    # Acessors
    #

    def get_main_supplier_name(self):
        supplier_info = self.get_main_supplier_info()
        return supplier_info.get_name()

    def get_main_supplier_info(self):
        """
        Gets a list of main suppliers for a Product, the main supplier
        is the most recently selected supplier.

        @returns: main supplier info
        @rtype: ProductSupplierInfo or None if a product lacks
           a main suppliers
        """

        if not self.suppliers:
            return

        main_suppliers = [supplier for supplier in self.suppliers
                                       if supplier.is_main_supplier]
        # A Product can only have one main supplier.
        # FIXME: Investigate why we can have 0
        if len(main_suppliers) > 1:
            raise DatabaseInconsistency(
                "A Product should have one main supplier, "
                "but %d suppliers were found: %r" % (len(main_suppliers),
                                                     main_suppliers))
        return main_suppliers[0]


class ProductStockReference(Domain):
    """Stock informations for products.

    B{Important attributes}:
        - I{logic_quantity}: Represents the current quantity of a product
                             in the warehouse reserved for this store.
                             For example: you can have decentralized
                             servers, in this case the quantity of the
                             product in the stock will be shared between the
                             stores, or a centralized server wich contains
                             all the product.
    """

    quantity = DecimalCol(default=0)
    logic_quantity = DecimalCol(default=0)
    branch =  ForeignKey('PersonAdaptToBranch')
    product_item =  ForeignKey('ProductSellableItem')


class ProductSellableItem(AbstractSellableItem):
    """Class responsible to store basic products informations."""

    implements(IContainer)

    #
    # IContainer implementation
    #

    def add_item(self, item):
        raise NotImplementedError('This method should be replaced by '
                                  'add_stock_reference')

    def get_items(self):
        conn = self.get_connection()
        return ProductStockReference.selectBy(connection=conn,
                                              product_item=self)

    def remove_item(self, item):
        conn = self.get_connection()
        if not isinstance(item, ProductStockReference):
            raise TypeError("Item should be of type ProductStockReference,"
                            " got %r" % type(item))
        ProductStockReference.delete(item.id, connection=conn)

    #
    # Basic methods
    #

    def sell(self, branch, order_product=False):
        conn = self.get_connection()
        sparam = sysparam(conn)
        if not (branch and
                branch.id == get_current_branch(conn).id or
                branch.id == sparam.CURRENT_WAREHOUSE.id):
            msg = ("Stock still doesn't support sales for "
                   "branch companies different than the "
                   "current one or the warehouse")
            raise SellError(msg)

        if order_product and not sparam.ACCEPT_ORDER_PRODUCTS:
            msg = _("This company doesn't allow order products")
            raise SellError(msg)

        if not self.sellable.can_be_sold():
            msg = '%r is already sold' % self.sellable
            raise SellError(msg)

        if order_product:
            # TODO waiting for bug 2469
            raise StoqlibError("Order products is not a valid feature yet")
        adapted = self.sellable.get_adapted()
        storable = IStorable(adapted)
        # Update the stock
        storable.decrease_stock(self.quantity, branch)

        # The function get_full_balance returns the current amount of items in the
        # stock. If get_full_balance == 0 we have no more stock for this product
        # and we need to set it as sold.
        logic_qty = storable.get_logic_balance()
        balance = storable.get_full_balance() - logic_qty
        if not balance:
            self.sellable.sell()

    def cancel(self, branch):
        conn = self.get_connection()
        adapted = self.sellable.get_adapted()
        storable = IStorable(adapted)
        # Update the stock
        storable.increase_stock(self.quantity, branch)

    #
    # General methods
    #

    def get_quantity_delivered(self):
        # Avoiding circular imports here
        from stoqlib.domain.service import ServiceSellableItem
        conn = self.get_connection()
        q1 = AbstractSellableItem.q.saleID == self.sale.id
        q2 = AbstractSellableItem.q.id == ServiceSellableItem.q.id
        query = AND(q1, q2)
        services = AbstractSellableItem.select(query, connection=conn)
        if not services.count():
            return decimal.Decimal('0.0')
        delivered_qty = decimal.Decimal('0.0')
        for service in services:
            delivery = IDelivery(service)
            if not delivery:
                continue
            item = delivery.get_item_by_sellable(self.sellable)
            if not item:
                continue
            delivered_qty += item.quantity
        return delivered_qty

    def has_been_totally_delivered(self):
        return self.get_quantity_delivered() == self.quantity


    def add_stock_reference(self, branch, quantity=0,
                            logic_quantity=0):
        conn = self.get_connection()
        return ProductStockReference(connection=conn, quantity=quantity,
                                     logic_quantity=logic_quantity,
                                     branch=branch, product_item=self)


class ProductStockItem(AbstractStockItem):
    """Class that makes a reference to the product stock of a
    certain branch company."""

    storable = ForeignKey('ProductAdaptToStorable')


#
# Adapters
#


class ProductAdaptToSellable(AbstractSellable):
    """A product implementation as a sellable facet."""

    sellableitem_table = ProductSellableItem
    tax_type = IntCol(default=TAX_ICMS)
    tax_value = PriceCol(default=0)

    tax_type_names = {
        TAX_ICMS: _("Aliquot"),
        TAX_SUBSTITUTION: _("Substitution"),
        TAX_NONE: _("Exempt"),
        }

    def _create(self, id, **kw):
        if not 'tax_type' in kw:
            kw['tax_type'] = TAX_ICMS
        if not 'tax_value' in kw:
            param = sysparam(self.get_connection())
            if kw['tax_type'] == TAX_ICMS:
                kw['tax_value'] = param.ICMS_TAX
            else:
                kw['tax_value'] = param.SUBSTITUTION_TAX
        AbstractSellable._create(self, id, **kw)

Product.registerFacet(ProductAdaptToSellable, ISellable)

class ProductAdaptToStorable(ModelAdapter):
    """A product implementation as a storable facet."""

    implements(IStorable, IContainer)

    retention = MultipleJoin('ProductRetentionHistory')

    #
    # IContainer implementation
    #

    def add_item(self, item):
        raise NotImplementedError('This method should be replaced '
                                  'by add_stock_item')


    def get_items(self):
        raise NotImplementedError('This method should be replaced '
                                  'by get_stocks')

    def remove_item(self, item):
        conn = self.get_connection()
        if not isinstance(item, ProductStockItem):
            raise TypeError("Item should be of type ProductStockItem, got "
                            % type(item))
        ProductStockItem.delete(item.id, connection=conn)

    #
    # IStorable implementation
    #

    def fill_stocks(self):
        conn = self.get_connection()
        branch_companies = PersonAdaptToBranch.select(connection=conn)
        for branch in branch_companies:
            self.add_stock_item(branch)

    def increase_stock(self, quantity, branch=None):
        stocks = self.get_stocks(branch)
        for stock_item in stocks:
            stock_item.quantity += quantity
        conn = self.get_connection()
        adapted = self.get_adapted()
        sellable = ISellable(adapted)
        if sellable.is_sold():
            sellable.set_available()

    def increase_logic_stock(self, quantity, branch=None):
        self._check_logic_quantity()
        stocks = self.get_stocks(branch)
        for stock_item in stocks:
            stock_item.logic_quantity += quantity

    def check_rejected_stocks(self, stocks, quantity, check_logic=False):
        for stock_item in stocks:
            if check_logic:
                base_qty = stock_item.logic_quantity
            else:
                base_qty = stock_item.quantity
            if base_qty < quantity:
                msg = ('Quantity to decrease is greater than available '
                       'stock.')
                raise StockError(msg)

    def decrease_stock(self, quantity, branch=None):
        if not self._has_qty_available(quantity, branch):
            # Of course that here we must use the logic quantity balance
            # as an addition to our main stock
            logic_qty = self.get_logic_balance(branch)
            balance = self.get_full_balance(branch) - logic_qty
            logic_sold_qty = quantity - balance
            quantity -= logic_sold_qty
            self.decrease_logic_stock(logic_sold_qty, branch)

        stocks = self.get_stocks(branch)
        self.check_rejected_stocks(stocks, quantity)

        for stock_item in stocks:
            stock_item.quantity -= quantity

    def decrease_logic_stock(self, quantity, branch=None):
        self._check_logic_quantity()
        rejected = []

        stocks = self.get_stocks(branch)
        self.check_rejected_stocks(stocks, quantity, check_logic=True)

        for stock_item in stocks:
            stock_item.logic_quantity -= quantity

    def get_full_balance(self, branch=None):
        """ Get the stock balance and the logic balance."""
        stocks = self.get_stocks(branch)
        if not stocks.count():
            raise StockError, 'Invalid stock references for %s' % self
        value = decimal.Decimal('0.0')
        has_logic_qty = sysparam(self.get_connection()).USE_LOGIC_QUANTITY
        for stock_item in stocks:
            value += stock_item.quantity
            if has_logic_qty:
                value += stock_item.logic_quantity
        return value

    def get_logic_balance(self, branch=None):
        stocks = self.get_stocks(branch)
        assert stocks.count() >= 1
        values = [stock_item.logic_quantity for stock_item in stocks]
        return sum(values, decimal.Decimal('0.0'))

    def get_average_stock_price(self):
        total_cost = decimal.Decimal('0.0')
        total_qty = decimal.Decimal('0.0')
        for stock_item in self.get_stocks():
            total_cost += stock_item.stock_cost
            total_qty += stock_item.quantity

        if total_cost and not total_qty:
            msg = ('%s has inconsistent stock information: Quantity = 0 '
                   'and TotalCost= %f')
            raise StockError(msg % (self.get_adapted(), total_cost))
        if not total_qty:
            return currency(0)
        return currency(total_cost / total_qty)

    def _has_qty_available(self, quantity, branch):
        logic_qty = self.get_logic_balance(branch)
        balance = self.get_full_balance(branch) - logic_qty
        qty_ok = quantity <= balance
        logic_qty_ok = quantity <= self.get_full_balance(branch)
        has_logic_qty = sysparam(self.get_connection()).USE_LOGIC_QUANTITY
        if not qty_ok and not (has_logic_qty and logic_qty_ok):
            msg = ('Quantity to sell is greater than the available '
                   'stock.')
            raise StockError(msg)
        return qty_ok

    #
    # Accessors
    #

    def get_full_balance_string(self, branch=None, full_balance=None):
        full_balance = full_balance or self.get_full_balance(branch)
        adapted = self.get_adapted()
        conn = self.get_connection()
        sellable = ISellable(adapted)
        return u"%s %s" % (full_balance, sellable.get_unit_description())

    def get_full_balance_for_current_branch(self):
        conn = self.get_connection()
        branch = IBranch(sysparam(conn).CURRENT_WAREHOUSE.get_adapted())
        return self.get_full_balance(branch)

    #
    # General methods
    #


    def _check_logic_quantity(self):
        if not sysparam(self.get_connection()).USE_LOGIC_QUANTITY:
            msg = ("This company doesn't allow logic quantity "
                   "operations.")
            raise StockError(msg)

    def has_stock_by_branch(self, branch):
        """Returns True if there is at least one item on stock for the
        given branch or False if not.
        This method also considers the logic stock
        """
        stock = self.get_stocks(branch)
        qty = stock.count()
        if not qty == 1:
            raise DatabaseInconsistency("You should have only one stock "
                                        "item for this branch, got %d"
                                        % qty)
        stock = stock[0]
        return stock.quantity + stock.logic_quantity > 0

    def add_stock_item(self, branch, stock_cost=0.0, quantity=0.0,
                       logic_quantity=0.0):
        conn = self.get_connection()
        return ProductStockItem(connection=conn, branch=branch,
                                stock_cost=stock_cost, quantity=quantity,
                                logic_quantity=logic_quantity,
                                storable=self)

    @argcheck(Person.getAdapterClass(IBranch))
    def get_stocks(self, branch=None):
        conn = self.get_connection()
        table, parent = ProductStockItem, AbstractStockItem
        q1 = table.q.id == parent.q.id
        q2 = table.q.storableID == self.id
        if not branch:
            query = AND(q1, q2)
        else:
            q3 = parent.q.branchID == branch.id
            query = AND(q1, q2, q3)
        return table.select(query, connection=conn)


Product.registerFacet(ProductAdaptToStorable, IStorable)


#
# Views
#

class ProductFullStockView(SellableView):
    """Stores general informations about products and the stock total in
    all branch companies"
    """

#
# Auxiliary functions
#


def storables_set_branch(conn, branch):
    """A method that must be called always when a new branch company is
    created. It creates a new stock reference for all the products.
    """
    for storable in ProductAdaptToStorable.select(connection=conn):
        storable.add_stock_item(branch)
