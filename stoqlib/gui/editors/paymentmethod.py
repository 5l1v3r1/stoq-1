# -*- coding: utf-8 -*-
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
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##
""" Editors for payment method management.  """


from stoqlib.domain.payment.methods import AbstractPaymentMethodAdapter
from stoqlib.domain.payment.destination import PaymentDestination
from stoqlib.gui.slaves.paymentmethod import CheckBillSettingsSlave
from stoqlib.gui.base.editors import BaseEditor
from stoqlib.lib.translation import stoqlib_gettext


_ = stoqlib_gettext


class PaymentMethodEditor(BaseEditor):
    model_name = _('Payment Method')
    size = (450, 200)
    gladefile = 'PaymentMethodEditor'
    proxy_widgets = ('destination', )

    def __init__(self, conn, model):
        """
        @param conn: an sqlobject Transaction instance
        @param model: an adapter of PaymentMethod which means a subclass of
                      AbstractPaymentMethodAdapter
        """
        self.model_type = AbstractPaymentMethodAdapter
        BaseEditor.__init__(self, conn, model)

    def _setup_widgets(self):
        destinations = PaymentDestination.select(connection=self.conn)
        items = [(d.get_description(), d) for d in destinations]
        self.destination.prefill(items)

    #
    # BaseEditor Hooks
    #

    def get_title_model_attribute(self, model):
        return model.description

    def setup_proxies(self):
        self._setup_widgets()
        self.add_proxy(self.model, PaymentMethodEditor.proxy_widgets)


class CheckBillMethodEditor(PaymentMethodEditor):

    def setup_slaves(self):
        slave = CheckBillSettingsSlave(self.conn, self.model)
        self.attach_slave('slave_holder', slave)
