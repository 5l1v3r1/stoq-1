# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2008 Async Open Source <http://www.async.com.br>
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
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
##
""" Sale wizard definition """


import gtk

from kiwi.argcheck import argcheck
from kiwi.component import get_utility
from kiwi.datatypes import currency, ValidationError
from kiwi.python import Settable

from stoqlib.database.exceptions import IntegrityError
from stoqlib.database.runtime import new_transaction, finish_transaction
from stoqlib.domain.events import CreatePaymentEvent
from stoqlib.enums import CreatePaymentStatus
from stoqlib.exceptions import StoqlibError
from stoqlib.lib.interfaces import IPluginManager
from stoqlib.lib.message import warning
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.lib.parameters import sysparam
from stoqlib.gui.base.wizards import WizardEditorStep, BaseWizard, BaseWizardStep
from stoqlib.gui.base.dialogs import run_dialog
from stoqlib.gui.editors.fiscaleditor import CfopEditor
from stoqlib.gui.editors.noteeditor import NoteEditor
from stoqlib.gui.editors.personeditor import ClientEditor, TransporterEditor
from stoqlib.gui.interfaces import IDomainSlaveMapper
from stoqlib.gui.slaves.cashchangeslave import CashChangeSlave
from stoqlib.gui.slaves.paymentmethodslave import SelectPaymentMethodSlave
from stoqlib.gui.slaves.paymentslave import register_payment_slaves
from stoqlib.gui.slaves.saleslave import SaleDiscountSlave
from stoqlib.gui.wizards.personwizard import run_person_role_dialog
from stoqlib.domain.fiscal import CfopData
from stoqlib.domain.person import Person, ClientView
from stoqlib.domain.payment.method import PaymentMethod
from stoqlib.domain.payment.operation import register_payment_operations
from stoqlib.domain.payment.renegotiation import PaymentRenegotiation
from stoqlib.domain.sale import Sale
from stoqlib.domain.interfaces import ISalesPerson, ITransporter

N_ = _ = stoqlib_gettext


#
# Wizard Steps
#

class PaymentMethodStep(BaseWizardStep):
    gladefile = 'HolderTemplate'
    slave_holder = 'place_holder'

    def __init__(self, wizard, previous, conn, model, method, outstanding_value=None):
        self._method_name = method
        self._method_slave = None
        self.model = model

        if outstanding_value is None:
            outstanding_value = currency(0)
        self._outstanding_value = outstanding_value

        BaseWizardStep.__init__(self, conn, wizard, previous)

        register_payment_slaves()
        self._create_ui()

    def _create_ui(self):
        slave = self._create_slave(self._method_name)
        self._attach_slave(slave)

    def _create_slave(self, method):
        dsm = get_utility(IDomainSlaveMapper)
        slave_class = dsm.get_slave_class(method)
        assert slave_class
        method = self.conn.get(method)
        slave = slave_class(self.wizard, self, self.conn, self.model,
                            method, outstanding_value=self._outstanding_value)
        self._method_slave = slave
        return slave

    def _attach_slave(self, slave):
        if self.get_slave(self.slave_holder):
            self.detach_slave(self.slave_holder)
        self.attach_slave(self.slave_holder, slave)

    #
    # WizardStep hooks
    #

    def validate_step(self):
        return self._method_slave.finish()

    def has_next_step(self):
        return False

    def post_init(self):
        self._method_slave.update_view()


class BaseMethodSelectionStep(object):
    """Base class for method selection when doing client sales

    Classes using this base class should have a select_method_holder EventBox
    and a cash_change_holder EventBox in the glade file
    """

    #
    #   Private API
    #

    @argcheck(PaymentMethod)
    def _update_next_step(self, method):
        if method and method.method_name == 'money':
            self.wizard.enable_finish()
            self.cash_change_slave.enable_cash_change()
        else:
            self.wizard.disable_finish()
            self.cash_change_slave.disable_cash_change()

    def _get_total_amount(self):
        if isinstance(self.model, Sale):
            return self.model.get_total_sale_amount()
        elif isinstance(self.model, PaymentRenegotiation):
            return self.model.total
        else:
            raise TypeError

    #
    #   Public API
    #

    def get_selected_method(self):
        return self.pm_slave.get_selected_method()

    def setup_cash_payment(self, total=None):
        money_method = PaymentMethod.get_by_name(self.conn, 'money')
        total = total or self._get_total_amount()
        return money_method.create_inpayment(self.model.group, total)

    #
    # WizardStep hooks
    #

    def setup_slaves(self):
        methods = SelectPaymentMethodSlave.AVAILABLE_METHODS
        self.pm_slave = SelectPaymentMethodSlave(available_methods=methods)
        self.pm_slave.connect('method-changed', self.on_payment_method_changed)
        self.attach_slave('select_method_holder', self.pm_slave)

        self.cash_change_slave = CashChangeSlave(self.conn, self.model)
        self.attach_slave('cash_change_holder', self.cash_change_slave)
        self.cash_change_slave.received_value.connect(
            'activate', lambda entry: self.wizard.go_to_next())

    def next_step(self):
        selected_method = self.get_selected_method()
        if selected_method.method_name == 'money':
            if not self.cash_change_slave.can_finish():
                warning(_(u"Invalid value, please verify if it was "
                          "properly typed."))
                self.cash_change_slave.received_value.select_region(
                    0, len(self.cash_change_slave.received_value.get_text()))
                self.cash_change_slave.received_value.grab_focus()
                return self

            # We have to modify the payment, so the fiscal printer can
            # calculate and print the payback, if necessary.
            payment = self.setup_cash_payment().get_adapted()
            total = self.cash_change_slave.get_received_value()
            payment.base_value = total

            # Return None here means call wizard.finish, which is exactly
            # what we need
            return None
        elif selected_method.method_name == 'store_credit':
            client = self.client.read()
            credit = client.remaining_store_credit
            total = self._get_total_amount()

            if credit < total:
                warning(_(u"Client %s does not have enought credit left.") % \
                        client.person.name)
                return self

            step_class = PaymentMethodStep
        else:
            step_class = PaymentMethodStep

        retval = CreatePaymentEvent.emit(selected_method, self.model,
                                         self.conn)

        # None means no one catched this event
        if retval is None or retval == CreatePaymentStatus.UNHANDLED:
            return step_class(self.wizard, self, self.conn, self.model, selected_method)

        # finish the wizard
        if retval == CreatePaymentStatus.SUCCESS:
            return None

        # returning self to stay on this step
        return self

    #
    #   Callbacks
    #

    def on_payment_method_changed(self, slave, method_name):
        self._update_next_step(method_name)


class SalesPersonStep(BaseMethodSelectionStep, WizardEditorStep):
    """ An abstract step which allows to define a salesperson, the sale's
    discount and surcharge, when it is needed.
    """
    gladefile = 'SalesPersonStep'
    model_type = Sale
    proxy_widgets = ('total_lbl',
                     'subtotal_lbl',
                     'salesperson',
                     'client',
                     'transporter',)

    invoice_widgets = ('invoice_number',)
    cfop_widgets = ('cfop',)

    def __init__(self, wizard, conn, model, payment_group,
                 invoice_model):
        self.invoice_model = invoice_model

        self.payment_group = payment_group
        WizardEditorStep.__init__(self, conn, wizard, model)
        BaseMethodSelectionStep.__init__(self)
        self.update_discount_and_surcharge()

    #
    # Private API
    #

    def _update_totals(self):
        for field_name in ('total_sale_amount', 'sale_subtotal'):
            self.proxy.update(field_name)
        self.cash_change_slave.update_total_sale_amount()

    def _update_widgets(self):
        has_client = bool(self.client.read())
        self.pm_slave.method_set_sensitive('store_credit', has_client)
        self.pm_slave.method_set_sensitive('bill', has_client)

    def _fill_clients_combo(self):
        clients = ClientView.get_active_clients(self.conn)
        max_results = sysparam(self.conn).MAX_SEARCH_RESULTS
        clients = clients[:max_results]
        items = [(c.name, c.client) for c in clients]
        self.client.prefill(sorted(items))
        self.client.set_sensitive(len(items))

    def _fill_transporter_combo(self):
        table = Person.getAdapterClass(ITransporter)
        transporters = table.get_active_transporters(self.conn)
        items = [(t.person.name, t) for t in transporters]
        self.transporter.prefill(items)
        self.transporter.set_sensitive(len(items))

    def _fill_cfop_combo(self):
        cfops = [(cfop.get_description(), cfop)
                    for cfop in CfopData.select(connection=self.conn)]
        self.cfop.prefill(cfops)

    def _create_client(self):
        trans = new_transaction()
        client = run_person_role_dialog(ClientEditor, self, trans, None)
        rv = finish_transaction(trans, client)
        client = self.conn.get(client)
        trans.close()
        if not client:
            return
        if len(self.client) == 0:
            self._fill_clients_combo()
            return
        clients = self.client.get_model_items().values()
        if client in clients:
            if client.is_active:
                self.client.update(client)
            else:
                # remove client from combo
                self.client.select_item_by_data(client)
                iter = self.client.get_active_iter()
                model = self.client.get_model()
                model.remove(iter)
                # just in case the inactive client was selected before.
                self.client.select_item_by_position(0)
        elif client.is_active:
            self.client.append_item(client.person.name, client)
            self.client.select(client)
        self._update_widgets()

    #
    # Public API
    #

    def update_discount_and_surcharge(self):
        # Here we need avoid to reset sale data defined when creating the
        # Sale in the POS application, i.e, we should not reset the
        # discount and surcharge if they are already set (this is the
        # case when CONFIRM_SALES_ON_TILL parameter is enabled).
        if not sysparam(self.conn).CONFIRM_SALES_ON_TILL:
            self.model.discount_value = currency(0)
            self.model.surcharge_value = currency(0)

    def setup_widgets(self):
        # Only quotes have expire date.
        self.expire_date.hide()
        self.expire_label.hide()

        # Hide operation nature widgets
        self.operation_nature.hide()
        self.nature_lbl.hide()

        # if the NF-e plugin is active, the client is mandantory in this
        # wizard (in this situation, we have only quote sales).
        if self.model.status == Sale.STATUS_QUOTE:
            manager = get_utility(IPluginManager)
            assert manager

            mandatory_client = manager.is_active('nfe')
            self.client.set_property('mandatory', mandatory_client)

        salespersons = Person.iselect(ISalesPerson, connection=self.conn)
        items = [(s.person.name, s) for s in salespersons]
        self.salesperson.prefill(items)
        if not sysparam(self.conn).ACCEPT_CHANGE_SALESPERSON:
            self.salesperson.set_sensitive(False)
        else:
            self.salesperson.grab_focus()
        self._fill_clients_combo()
        self._fill_transporter_combo()
        if sysparam(self.conn).ASK_SALES_CFOP:
            self._fill_cfop_combo()
        else:
            self.cfop_lbl.hide()
            self.cfop.hide()
            self.create_cfop.hide()

        # the maximum number allowed for an invoice is 999999999.
        self.invoice_number.set_adjustment(
            gtk.Adjustment(lower=1, upper=999999999, step_incr=1))

        if not self.model.invoice_number:
            # we need to use a new transaction, so any query will not count
            # the current sale object.
            trans = new_transaction()
            new_invoice_number = Sale.get_last_invoice_number(trans) + 1
            trans.close()
            self.invoice_model.invoice_number = new_invoice_number
        else:
            new_invoice_number = self.model.invoice_number
            self.invoice_model.invoice_number = new_invoice_number
            self.invoice_number.set_sensitive(False)

        self.invoice_model.original_invoice = new_invoice_number

    #
    # WizardStep hooks
    #

    def post_init(self):
        self.wizard.payment_group.clear_unused()
        self.register_validate_function(self.wizard.refresh_next)
        self._update_next_step(self.get_selected_method())

        if hasattr(self, 'cash_change_slave'):
            self.cash_change_slave.received_value.grab_focus()

        self.force_validation()

    def setup_slaves(self):
        BaseMethodSelectionStep.setup_slaves(self)
        self.pm_slave.method_set_sensitive('store_credit',
                                           bool(self.client.read()))
        self.pm_slave.method_set_sensitive('bill',
                                           bool(self.client.read()))

        self.discount_slave = SaleDiscountSlave(self.conn, self.model,
                                                self.model_type)
        self.discount_slave.connect('discount-changed',
                                    self.on_discount_slave_changed)
        slave_holder = 'discount_surcharge_slave'
        if self.get_slave(slave_holder):
            self.detach_slave(slave_holder)
        self.attach_slave(slave_holder, self.discount_slave)

    def setup_proxies(self):
        self.setup_widgets()
        self.proxy = self.add_proxy(self.model,
                                    SalesPersonStep.proxy_widgets)
        self.invoice_proxy = self.add_proxy(self.invoice_model,
                                            self.invoice_widgets)
        if self.model.client:
            self.client.set_sensitive(False)
            self.create_client.set_sensitive(False)
        if sysparam(self.conn).ASK_SALES_CFOP:
            self.add_proxy(self.model, SalesPersonStep.cfop_widgets)

    #
    # Callbacks
    #

    def on_client__changed(self, entry):
        self._update_widgets()

    def on_create_client__clicked(self, button):
        self._create_client()

    def on_create_transporter__clicked(self, button):
        trans = new_transaction()
        transporter = trans.get(self.model.transporter)
        model =  run_person_role_dialog(TransporterEditor, self, trans,
                                        transporter)
        rv = finish_transaction(trans, model)
        trans.close()
        if rv:
            self._fill_transporter_combo()
            self.transporter.select(model)

    def on_discount_slave_changed(self, slave):
        self._update_totals()

    def on_notes_button__clicked(self, *args):
        run_dialog(NoteEditor, self, self.conn, self.model, 'notes',
                   title=_("Additional Information"))

    def on_create_cfop__clicked(self, widget):
        cfop = run_dialog(CfopEditor, self, self.conn, None)
        if cfop:
            self.cfop.append_item(cfop.get_description(), cfop)
            self.cfop.select_item_by_data(cfop)

    def on_invoice_number__validate(self, widget, value):
        if value <= 0:
            return ValidationError(_(u'Invoice number should be positive.'))
        if value > 999999999:
            return ValidationError(_(u'Invoice number should be lesser '
                                      'than 999999999.'))
        # we need to use a new transaction or the selectOneBy will also
        # include the current object.
        trans = new_transaction()
        exists = Sale.selectOneBy(invoice_number=value, connection=trans)
        if exists:
            return ValidationError(_(u'Invoice number already used.'))
        trans.close()


#
# Wizards for sales
#

class ConfirmSaleWizard(BaseWizard):
    """A wizard used when confirming a sale order. It means generate
    payments, fiscal data and update stock
    """
    size = (600, 400)
    first_step = SalesPersonStep
    title = _("Sale Checkout")

    def __init__(self, conn, model):
        self._check_payment_group(model, conn)
        register_payment_operations()

        # invoice_model is a Settable so avoid bug 4218, where more
        # than one checkout may try to use the same invoice number.
        self.invoice_model = Settable(invoice_number=None,
                                     original_invoice=None)
        first_step = self.first_step(self, conn, model, self.payment_group,
                                     self.invoice_model)
        BaseWizard.__init__(self, conn, first_step, model)

        if not sysparam(self.conn).CONFIRM_SALES_ON_TILL:
            # This was added to allow us to work even if an error
            # happened while adding a payment, where we already order
            # but cannot confirm and are thrown back to the main
            # POS interface
            if self.model.can_order():
                self.model.order()

    def _check_payment_group(self, model, conn):
        if not isinstance(model, Sale):
            raise StoqlibError("Invalid datatype for model, it should be "
                               "of type Sale, got %s instead" % model)
        self.payment_group = model.group

    def _invoice_changed(self):
        return (self.invoice_model.invoice_number !=
                    self.invoice_model.original_invoice)


    #
    # BaseWizard hooks
    #

    def finish(self):
        self.retval = True
        invoice_number = self.invoice_model.invoice_number

        # Workaround for bug 4218: If the invoice is was already used by
        # another transaction (another cashier), try using the next one
        # available, or show a warning if the number was manually set.
        while True:
            try:
                self.conn.savepoint('before_set_invoice_number')
                self.model.invoice_number = invoice_number
            except IntegrityError:
                self.conn.rollback_to_savepoint('before_set_invoice_number')
                if self._invoice_changed():
                    warning(_(u"The invoice number %s is already used. "
                       "Confirm the sale again to chose another one.") %
                       invoice_number)
                    self.retval = False
                    break
                else:
                    invoice_number += 1
            else:
                break
        self.close()
