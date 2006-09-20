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
## Author(s):   Evandro Vale Miquelito     <evandro@async.com.br>
##              Henrique Romano            <henrique@async.com.br>
##
""" Payment management implementations."""

from datetime import datetime, date
from decimal import Decimal

from kiwi.argcheck import argcheck
from kiwi.datatypes import currency
from sqlobject.sqlbuilder import AND
from sqlobject import IntCol, DateTimeCol, UnicodeCol, ForeignKey
from zope.interface import implements

from stoqlib.database.runtime import get_current_branch
from stoqlib.database.columns import PriceCol, AutoIncCol
from stoqlib.exceptions import DatabaseInconsistency, StoqlibError
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.defaults import (get_method_names, get_all_methods_dict,
                                  METHOD_MONEY)
from stoqlib.domain.fiscal import (IssBookEntry, IcmsIpiBookEntry,
                                   AbstractFiscalBookEntry)
from stoqlib.domain.base import Domain, ModelAdapter, InheritableModelAdapter
from stoqlib.domain.payment.operation import PaymentOperation
from stoqlib.domain.interfaces import (IInPayment, IOutPayment, IPaymentGroup,
                                       ICheckPM, IBillPM, IContainer,
                                       IPaymentDevolution, IPaymentDeposit)

_ = stoqlib_gettext


#
# Domain Classes
#


class Payment(Domain):
    """ The payment representation in Stoq.

    B{Importante attributes}:
        - I{interest}: the absolute value for the interest associated with
                       this payment.
        - I{discount}: the absolute value for the discount associated with
                       this payment.
    """

    (STATUS_PREVIEW,
     STATUS_PENDING,
     STATUS_PAID,
     STATUS_REVIEWING,
     STATUS_CONFIRMED,
     STATUS_CANCELLED) = range(6)

    statuses = {STATUS_PREVIEW: _(u'Preview'),
                STATUS_PENDING: _(u'To Pay'),
                STATUS_PAID: _(u'Paid'),
                STATUS_REVIEWING: _(u'Reviewing'),
                STATUS_CONFIRMED: _(u'Confirmed'),
                STATUS_CANCELLED: _(u'Cancelled')}

    identifier = AutoIncCol('stoqlib_payment_identifier_seq')
    status = IntCol(default=STATUS_PREVIEW)
    open_date = DateTimeCol(default=datetime.now)
    due_date = DateTimeCol()
    paid_date = DateTimeCol(default=None)
    cancel_date = DateTimeCol(default=None)
    paid_value = PriceCol(default=0)
    base_value = PriceCol()
    value = PriceCol()
    interest = PriceCol(default=0)
    discount = PriceCol(default=0)
    description = UnicodeCol(default=None)
    payment_number = UnicodeCol(default=None)
    method = ForeignKey('AbstractPaymentMethodAdapter')
    # FIXME: Move to methods itself?
    method_details = ForeignKey('PaymentMethodDetails', default=None)
    group = ForeignKey('AbstractPaymentGroup')
    till = ForeignKey('Till')
    destination = ForeignKey('PaymentDestination')

    def _check_status(self, status, operation_name):
        assert self.status == status, ('Invalid status for %s '
                                       'operation: %s' % (operation_name,
                                       self.statuses[self.status]))

    #
    # SQLObject hooks
    #

    def _create(self, id, **kw):
        if not 'value' in kw:
            raise TypeError('You must provide a value argument')
        if not 'base_value' in kw or not kw['base_value']:
            kw['base_value'] = kw['value']
        Domain._create(self, id, **kw)

    #
    # Public API
    #

    def get_status_str(self):
        if not self.statuses.has_key(self.status):
            raise DatabaseInconsistency('Invalid status for Payment '
                                        'instance, got %d' % self.status)
        return self.statuses[self.status]

    def get_days_late(self):
        days_late = datetime.today() - self.due_date
        if days_late.days < 0:
            return 0
        else:
            return days_late.days

    def set_to_pay(self):
        """Set a STATUS_PREVIEW payment as STATUS_PENDING. This also means
        that this is valid payment and its owner actually can charge it
        """
        self._check_status(self.STATUS_PREVIEW, 'set_to_pay')
        self.status = self.STATUS_PENDING

    def pay(self, paid_date=None, paid_value=None):
        """Pay the current payment set its status as STATUS_PAID"""
        self._check_status(self.STATUS_PENDING, 'pay')
        paid_value = paid_value or (self.value - self.discount +
                                    self.interest)
        self.paid_value = paid_value
        self.paid_date = paid_date or datetime.now()
        self.status = self.STATUS_PAID

    def submit(self, submit_date=None):
        """The first stage of payment acquittance is submiting and mark a
        payment with STATUS_REVIEWING
        """
        self._check_status(self.STATUS_PAID, 'submit')
        conn = self.get_connection()
        operation = PaymentOperation(connection=conn,
                                     operation_date=submit_date)
        operation.addFacet(IPaymentDeposit, connection=conn)
        self.status = self.STATUS_REVIEWING

    def reject(self, reason, reject_date=None):
        """If there is some problems in the  first stage of payment
        acquittance we must call reject for it.
        """
        self._check_status(self.STATUS_REVIEWING, 'reject')
        conn = self.get_connection()
        operation = PaymentOperation(connection=conn,
                                     operation_date=reject_date)
        operation.addFacet(IPaymentDevolution, connection=conn, reason=reason)
        self.status = self.STATUS_PAID

    def cancel_till_entry(self):
        if self.status == Payment.STATUS_CANCELLED:
            raise StoqlibError("This payment is already cancelled")
        self._check_status(self.STATUS_PENDING, 'reverse selection')
        self.status = self.STATUS_CANCELLED
        payment = self.clone()
        description = (_('Cancellation of payment number %s')
                       % self.identifier)
        payment.description = description
        payment.value *= -1
        payment.due_date = datetime.now()

    def cancel(self):
        # TODO Check for till entries here and call cancel_till_entry if
        # it's possible. Bug 2598
        if self.status not in [Payment.STATUS_PREVIEW, Payment.STATUS_PENDING]:
            raise StoqlibError("Invalid status for cancel operation, "
                                "got %s" % self.get_status_str())
        self.status = self.STATUS_CANCELLED
        self.cancel_date = datetime.now()

    @argcheck(date)
    def get_payable_value(self, paid_date=None):
        """ Returns the calculated payment value with the daily penalty.
            Note that the payment group daily_penalty must be
            between 0 and 100.
        """
        if self.status in [self.STATUS_PREVIEW, self.STATUS_CANCELLED]:
            return self.value
        if self.status in [self.STATUS_PAID, self.STATUS_REVIEWING,
                           self.STATUS_CONFIRMED]:
            return self.paid_value
        if self.method.get_implemented_iface() in (ICheckPM, IBillPM):
            paid_date = paid_date or datetime.now()
            days = (paid_date - self.due_date).days
            if days <= 0:
                return self.value
            daily_penalty = self.method.daily_penalty / 100
            return self.value + days * (daily_penalty * self.value)
        else:
            return self.value

    def get_thirdparty(self):
        if self.method_details:
            return self.method_details.get_thirdparty()
        return self.method.get_thirdparty(self.group)

    def get_thirdparty_name(self):
        thirdparty = self.get_thirdparty()
        if thirdparty:
            return thirdparty.name
        return _(u'Anonymous')


class AbstractPaymentGroup(InheritableModelAdapter):
    """A base class for payment group adapters. """

    (STATUS_PREVIEW,
     STATUS_OPEN,
     STATUS_CLOSED,
     STATUS_CANCELLED) = range(4)

    statuses = {STATUS_PREVIEW: _(u"Preview"),
                STATUS_OPEN: _(u"Open"),
                STATUS_CLOSED: _(u"Closed"),
                STATUS_CANCELLED: _(u"Cancelled")}

    implements(IPaymentGroup, IContainer)

    status = IntCol(default=STATUS_OPEN)
    open_date = DateTimeCol(default=datetime.now)
    close_date = DateTimeCol(default=None)
    cancel_date = DateTimeCol(default=None)
    default_method = IntCol(default=METHOD_MONEY)
    installments_number = IntCol(default=1)
    interval_type = IntCol(default=None)
    intervals = IntCol(default=None)

    def _create_till_entry(self, value, description, till):
        from stoqlib.domain.till import TillEntry
        conn = self.get_connection()
        return TillEntry(connection=conn,
                         description=description, value=value, till=till,
                         payment_group=self)

    #
    # IPaymentGroup implementation
    #

    #
    # FIXME: We should to remove all these methods without implementation, so
    # we can ensure that interface are properly implemented in subclasses.
    #
    def get_thirdparty(self):
        raise NotImplementedError

    def set_thirdparty(self, person):
        raise NotImplementedError

    def get_group_description(self):
        """Returns a small description for the payment group which will be
        used in payment descriptions
        """
        raise NotImplementedError

    def update_thirdparty_status(self):
        raise NotImplementedError

    def get_balance(self):
        # FIXME: Move sum to SQL statement
        return sum([s.value for s in self.get_items()])

    # FIXME: Use None instead of datetime.now() as a default argument
    def add_payment(self, value, description, method, destination=None,
                    due_date=datetime.now()):
        """Create a new payment and add it to the group"""
        from stoqlib.domain.till import Till
        conn = self.get_connection()
        destination = destination or sysparam(conn).DEFAULT_PAYMENT_DESTINATION
        till = Till.get_current(conn)
        return Payment(due_date=due_date, value=value, till=till,
                       description=description, group=self, method=method,
                       destination=destination, connection=conn)

    #
    # IContainer implementation
    #

    @argcheck(Payment)
    def add_item(self, payment):
        payment.group = self

    @argcheck(Payment)
    def remove_item(self, payment):
        Payment.delete(payment.id, connection=self.get_connection())

    def get_items(self):
        return Payment.selectBy(group=self,
                                connection=self.get_connection())

    #
    # Fiscal methods
    #

    def _create_fiscal_entry(self, table, cfop, invoice_number, **kwargs):
        conn = self.get_connection()
        drawee = self.get_thirdparty()
        branch = get_current_branch(conn)
        return table(connection=conn, invoice_number=invoice_number,
                     cfop=cfop, drawee=drawee, branch=branch,
                     date=datetime.now(), payment_group=self, **kwargs)

    def create_icmsipi_book_entry(self, cfop, invoice_number, icms_value,
                                  ipi_value=Decimal("0.0")):
        self._create_fiscal_entry(IcmsIpiBookEntry, cfop, invoice_number,
                                  icms_value=icms_value, ipi_value=ipi_value)

    def create_iss_book_entry(self, cfop, invoice_number, iss_value):
        self._create_fiscal_entry(IssBookEntry, cfop, invoice_number,
                                  iss_value=iss_value)

    def revert_fiscal_entry(self, invoice_number):
        conn = self.get_connection()
        entries = AbstractFiscalBookEntry.selectBy(payment_groupID=self.id,
                                                   connection=conn)
        if entries.count() > 1:
            raise DatabaseInconsistency("You should have only one fiscal "
                                        "entry per payment group")
        if not entries.count():
            return
        entries[0].reverse_entry(invoice_number)

    #
    # Public API
    #

    def cancel(self, invoice_number):
        if self.status == AbstractPaymentGroup.STATUS_CANCELLED:
            raise StoqlibError("This payment group is already cancelled")
        for payment in self.get_unpaid_payments():
            payment.cancel()
        self.status = AbstractPaymentGroup.STATUS_CANCELLED
        self.cancel_date = datetime.now()
        self.revert_fiscal_entry(invoice_number)

    @argcheck(Decimal, unicode, object)
    def create_debit(self, value, description, till):
        value = - abs(value)
        return self._create_till_entry(value, description, till)

    @argcheck(Decimal, unicode, object)
    def create_credit(self, value, description, till):
        value = abs(value)
        return self._create_till_entry(value, description, till)

    def get_paid_payments(self):
        # FIXME: Logic in SQL
        statuses = (Payment.STATUS_PAID, Payment.STATUS_REVIEWING,
                    Payment.STATUS_CONFIRMED)
        return [p for p in self.get_items() if p.status in statuses]

    def get_unpaid_payments(self):
        # FIXME: Logic in SQL
        statuses = Payment.STATUS_PREVIEW, Payment.STATUS_PENDING
        return [p for p in self.get_items() if p.status in statuses]

    def get_total_paid(self):
        # FIXME: Move sum to SQL statement
        paid_values = [payment.paid_value
                            for payment in self.get_paid_payments()]
        return sum(paid_values, currency(0))

    def set_method(self, method_iface):
        items = get_all_methods_dict().items()
        method = [method_id for method_id, iface in items
                        if method_iface is iface]
        if len(method) != 1:
            raise TypeError('Invalid method_class argument, got type %s'
                            % method_iface)
        self.default_method = method[0]

    def get_till_entries(self):
        from stoqlib.domain.till import TillEntry
        return TillEntry.selectBy(payment_groupID=self.id,
                                  connection=self.get_connection())

    def setup_inpayments(self):
        payment_cout = self.get_items().count()
        till_entries_count = self.get_till_entries().count()
        if not (payment_cout or till_entries_count):
            raise ValueError('You must have at least one payment for each '
                             'payment group')
        self.installments_number = payment_cout
        self.set_payments_to_pay()

    def confirm_money_payments(self):
        from stoqlib.domain.payment.methods import PMAdaptToMoneyPM
        for payment in self.get_items():
            if not isinstance(payment.method, PMAdaptToMoneyPM):
                continue
            payment.pay()

    def set_payments_to_pay(self):
        """Checks if all the payments have STATUS_PREVIEW and set them as
        STATUS_PENDING
        """
        for payment in self.get_items():
            payment.set_to_pay()

    def check_close(self):
        """Verifies if the payment group can be closed and close it.

        @returns: the close status, True if it has been closed or
                 False if not.
        """
        if not self.status == AbstractPaymentGroup.STATUS_OPEN:
            raise ValueError("The status for this payment group should be "
                             "opened, got %s" % self.get_status_string())
        payments = self.get_items()
        statuses = [Payment.STATUS_CONFIRMED, Payment.STATUS_CANCELLED]
        for payment in payments:
            if payment.status not in statuses:
                return False
        self.status = AbstractPaymentGroup.STATUS_CLOSED
        return True

    def clear_preview_payments(self, ignore_method_iface=None):
        """Delete payments of preview status associated to the current
        payment_group. It can happen if user open and cancel this wizard.
        Notes:
            ignore_method_iface = a payment method interface which is
                                  ignored in the search for payments
        """
        conn = self.get_connection()
        q1 = Payment.q.status == Payment.STATUS_PREVIEW
        q2 = Payment.q.groupID == self.id
        if ignore_method_iface:
            base_method = sysparam(conn).BASE_PAYMENT_METHOD
            method = ignore_method_iface(base_method)
            q3 = Payment.q.methodID != method.id
            query = AND(q1, q2, q3)
        else:
            query = AND(q1, q2)
        payments = Payment.select(query, connection=conn)
        conn = self.get_connection()
        for payment in payments:
            inpayment = IInPayment(payment)
            if not inpayment:
                continue
            payment.method.delete_inpayment(inpayment)

    #
    # Accessors
    #

    def get_status_string(self):
        if not self.status in AbstractPaymentGroup.statuses.keys():
            raise DatabaseInconsistency("Invalid status, got %d"
                                        % self.status)
        return self.statuses[self.status]

    def get_default_payment_method(self):
        """This hook must be redefined in a subclass when it's necessary"""
        return self.default_method

    def get_default_payment_method_name(self):
        """This hook must be redefined in a subclass when it's necessary"""
        method_names = get_method_names()
        if not self.default_method in method_names.keys():
            raise DatabaseInconsistency('Invalid payment method, got %d'
                                        % self.default_method)
        return method_names[self.default_method]

    def get_method_id_by_iface(self, iface):
        methods = get_all_methods_dict()
        if not iface in methods.values():
            raise ValueError('Invalid interface, got %s' % iface)
        method_data = [method_id for method_id, m_iface in methods.items()
                            if m_iface is iface]
        qty = len(method_data)
        if not qty == 1:
            raise ValueError('It should have only one item on method_data '
                             'list, got %d instead' % qty)
        return method_data[0]


#
# Adapters for Payment class
#


class PaymentAdaptToInPayment(ModelAdapter):

    implements(IInPayment)

    # TODO: Unused
    def receive(self):
        payment = self.get_adapted()
        if not payment.status == Payment.STATUS_PENDING:
            raise ValueError("This payment is already received.")
        payment.pay()
        payment.group.update_thirdparty_status()
        # TODO we must also add new till entries here

Payment.registerFacet(PaymentAdaptToInPayment, IInPayment)


class PaymentAdaptToOutPayment(ModelAdapter):

    implements(IOutPayment)

    def pay(self):
        payment = self.get_adapted()
        if not payment.status == Payment.STATUS_PENDING:
            raise ValueError("This payment is already paid.")
        payment.pay()
        # TODO we must also add new till entries here

Payment.registerFacet(PaymentAdaptToOutPayment, IOutPayment)

class CashAdvanceInfo(Domain):
    employee = ForeignKey("PersonAdaptToEmployee")
    payment = ForeignKey("Payment")
    open_date = DateTimeCol(default=datetime.now)

