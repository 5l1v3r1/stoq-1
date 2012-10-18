# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2012 Async Open Source <http://www.async.com.br>
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

import datetime

from stoqlib.domain.receiving import ReceivingOrder, ReceivingOrderItem
from stoqlib.gui.uitestutils import GUITest
from stoqlib.gui.search.receivingsearch import PurchaseReceivingSearch


class TestReceivingOrderSearch(GUITest):
    def testReceivingOrderSearch(self):
        self.clean_domain([ReceivingOrderItem, ReceivingOrder])

        supplier_a = self.create_supplier('Mark')
        purchase_order_a = self.create_purchase_order(supplier=supplier_a)
        order_a = self.create_receiving_order(purchase_order=purchase_order_a)

        supplier_b = self.create_supplier('Dominique')
        purchase_order_b = self.create_purchase_order(supplier=supplier_b)
        order_b = self.create_receiving_order(purchase_order=purchase_order_b)

        order_a.purchase.identifier = 81954
        order_a.receival_date = datetime.datetime(2012, 1, 1)

        order_b.purchase.identifier = 78526
        order_b.receival_date = datetime.datetime(2012, 2, 2)

        search = PurchaseReceivingSearch(self.trans)

        search.search.refresh()
        self.check_search(search, 'receiving-no-filter')

        search.search.search._primary_filter.entry.set_text('dom')
        search.search.refresh()
        self.check_search(search, 'receiving-string-filter')