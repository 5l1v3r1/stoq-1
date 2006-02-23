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
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s): Henrique Romano           <henrique@async.com.br>
##            Evandro Vale Miquelito    <evandro@async.com.br>
##            Bruno Rafael Garcia       <brg@async.com.br>
##
""" Service item editor implementation """

from kiwi.datatypes import currency

from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.gui.base.editors import BaseEditor
from stoqlib.domain.service import ServiceSellableItem, Service
from stoqlib.domain.sellable import BaseSellableInfo
from stoqlib.gui.editors.sellable import SellableEditor
from stoqlib.domain.interfaces import ISellable

_ = stoqlib_gettext


class ServiceItemEditor(BaseEditor):
    model_name = _('Service')
    model_type = ServiceSellableItem
    gladefile = 'ServiceItemEditor'
    proxy_widgets = ('service_name_label',
                     'price',
                     'estimated_fix_date',
                     'notes')
    size = (500, 250)

    def __init__(self, conn, model):
        BaseEditor.__init__(self, conn, model)
        self.service_name_label.set_bold(True)

    #
    # BaseEditor hooks
    #

    def get_title_model_attribute(self, model):
        return model.sellable.base_sellable_info.description

    def setup_proxies(self):
        self.add_proxy(self.model, ServiceItemEditor.proxy_widgets)


class ServiceEditor(SellableEditor):
    model_name = 'Service'
    model_type = Service

    def setup_widgets(self):
        self.notes_lbl.set_text(_('Service details'))
        self.stock_total_lbl.hide()
        self.stock_lbl.hide()

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        model = Service(connection=conn)
        sellable_info = BaseSellableInfo(connection=conn,
                                         description='', price=currency(0))
        model.addFacet(ISellable, code='', base_sellable_info=sellable_info,
                       connection=conn)
        return model
