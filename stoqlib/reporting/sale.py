# -*- coding: utf-8 -*-
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
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##  Author(s):  Henrique Romano         <henrique@async.com.br>
##              Evandro Miquelito       <evandro@async.com.br>
##
##
""" Sales report implementation """

from kiwi.datatypes import currency

from stoqlib.domain.sale import SaleView
from stoqlib.reporting.base.tables import ObjectTableColumn as OTC
from stoqlib.reporting.base.flowables import RIGHT
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.validators import (get_formatted_price, format_quantity,
                                    format_phone_number)
from stoqlib.lib.defaults import ALL_ITEMS_INDEX
from stoqlib.reporting.template import BaseStoqReport, SearchResultsReport
from stoqlib.lib.translation import stoqlib_gettext

_ = stoqlib_gettext

class SaleOrderReport(BaseStoqReport):
    report_name = _("Sale Order")

    def __init__(self, filename, sale_order):
        self.order = sale_order
        BaseStoqReport.__init__(self, filename, SaleOrderReport.report_name,
                                do_footer=True)
        self._identify_client()
        self.add_blank_space()
        self._setup_items_table()

    def _identify_client(self):
        if not self.order.client:
            return
        person = self.order.client.get_adapted()
        text = "<b>%s:</b> %s" % (_("Client"), person.name)
        if person.phone_number:
            phone_str = ("<b>%s:</b> %s" %
                         (_("Phone"), format_phone_number(person.phone_number)))
            text += " %s" % phone_str
        self.add_paragraph(text)

    def _get_table_columns(self):
        # XXX Bug #2430 will improve this part
        return [OTC(_("Code"), lambda obj: obj.sellable.get_code_str(),
                    truncate=True, width=80),
                OTC(_("Item"),
                    lambda obj: obj.sellable.base_sellable_info.description,
                    truncate=True, width=130),
                OTC(_("Quantity"), lambda obj: obj.get_quantity_unit_string(),
                    width=70, align=RIGHT),
                OTC(_("Price"), lambda obj: get_formatted_price(obj.price),
                    width=90, align=RIGHT),
                OTC(_("Total"),
                    lambda obj: get_formatted_price(obj.get_total()),
                    width=100, align=RIGHT)]

    def _setup_items_table(self):
        # XXX Bug #2430 will improve this part
        items_qty = self.order.get_items_total_quantity()
        total_value = get_formatted_price(self.order.get_items_total_value())
        if items_qty > 1:
            items_text = _("%s items") % format_quantity(items_qty)
        else:
            items_text = _("%s item") % format_quantity(items_qty)
        summary = ["", "", items_text, "", total_value]
        self.add_object_table(list(self.order.get_items()),
                              self._get_table_columns(), summary_row=summary)

    #
    # BaseReportTemplate hooks
    #

    def get_title(self):
        return (_("Sale Order on %s, with due date of %d days")
                % (self.order.open_date.strftime("%x"),
                   sysparam(self.conn).MAX_SALE_ORDER_VALIDITY))

class SalesReport(SearchResultsReport):
    # This should be properly verified on BaseStoqReport. Waiting for
    # bug 2517
    obj_type = SaleView
    report_name = _("Sales Report")
    main_object_name = _("sales")
    filter_format_string = _("with status <u>%s</u>")

    def __init__(self, filename, sale_list, status=None, *args, **kwargs):
        self.sale_list = sale_list
        self._landscape_mode = status and status == ALL_ITEMS_INDEX
        SearchResultsReport.__init__(self, filename, sale_list,
                                     SalesReport.report_name,
                                     landscape=self._landscape_mode,
                                     *args, **kwargs)
        self._setup_sales_table()

    def _get_columns(self):
        # XXX Bug #2430 will improve this part
        person_col_width = 140
        if self._landscape_mode:
            person_col_width += 84
        columns = [OTC(_("Number"), lambda obj: obj.order_number, width=50,
                       align=RIGHT),
                   OTC(_("Date"), lambda obj: obj.get_open_date_as_string(),
                       width=70, align=RIGHT),
                   OTC(_("Client"),
                       data_source=lambda obj: obj.get_client_name(),
                       width=person_col_width),
                   OTC(_("Salesperson"), lambda obj: obj.salesperson_name,
                       width=person_col_width, truncate=True),
                   OTC(_("Total"), lambda obj: get_formatted_price(obj.total),
                       width=80, align=RIGHT)]
        if self._landscape_mode:
            columns.insert(-1, OTC(_("Status"),
                                   lambda obj: (obj.get_status_name()),
                                   width=80))
        return columns

    def _setup_sales_table(self):
        total = sum([sale.total
                         for sale in self.sale_list], currency(0))
        total_str = _("Total %s") % get_formatted_price(total)
        summary_row = ["", "", "", "", total_str]
        if self._landscape_mode:
            summary_row.insert(-1, "")
        self.add_object_table(self.sale_list, self._get_columns(),
                              summary_row=summary_row)
