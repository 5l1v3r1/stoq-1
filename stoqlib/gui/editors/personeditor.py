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
## Author(s): Henrique Romano             <henrique@async.com.br>
##            Evandro Vale Miquelito      <evandro@async.com.br>
##            Ariqueli Tejada Fonseca     <aritf@async.com.br>
##            Bruno Rafael Garcia         <brg@async.com.br>
##
""" Person editors definition """

import datetime
from decimal import Decimal

from sqlobject.sqlbuilder import func, AND
from kiwi.datatypes import ValidationError
from kiwi.ui.widgets.list import Column

from stoqlib.database.runtime import get_connection
from stoqlib.exceptions import DatabaseInconsistency
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.gui.wizards.paymentmethodwizard import PaymentMethodDetailsWizard
from stoqlib.gui.base.lists import AdditionListSlave
from stoqlib.gui.base.editors import SimpleEntryEditor, BaseEditor
from stoqlib.gui.templates.persontemplate import BasePersonRoleEditor
from stoqlib.gui.slaves.paymentmethodslave import FinanceDetailsSlave
from stoqlib.gui.slaves.clientslave import ClientStatusSlave
from stoqlib.gui.slaves.credproviderslave import CreditProviderDetailsSlave
from stoqlib.gui.slaves.employeeslave import (EmployeeDetailsSlave,
                                      EmployeeStatusSlave,
                                      EmployeeRoleSlave,
                                      EmployeeRoleHistorySlave)
from stoqlib.gui.slaves.userslave import (UserDetailsSlave, UserStatusSlave,
                                     PasswordEditorSlave, LoginInfo)
from stoqlib.gui.slaves.supplierslave import SupplierDetailsSlave
from stoqlib.gui.slaves.transporterslave import TransporterDataSlave
from stoqlib.gui.slaves.branchslave import BranchDetailsSlave
from stoqlib.domain.payment.methods import (PaymentMethodDetails,
                                            FinanceDetails)
from stoqlib.domain.person import EmployeeRole, Person
from stoqlib.domain.interfaces import (IClient, ICreditProvider, IEmployee,
                                       ISupplier, ITransporter, IUser,
                                       ICompany, IIndividual, IBranch)

_ = stoqlib_gettext


class ClientEditor(BasePersonRoleEditor):
    model_name = _('Client')
    title = _('New Client')
    model_iface = IClient
    gladefile = 'BaseTemplate'

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        client = IClient(person)
        return client or person.addFacet(IClient, connection=conn)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        self.status_slave = ClientStatusSlave(self.conn, self.model,
                                              visual_mode=self.visual_mode)
        self.main_slave.attach_person_slave(self.status_slave)


class UserEditor(BasePersonRoleEditor):
    model_name = _('User')
    title = _('New User')
    model_iface = IUser
    gladefile = 'BaseTemplate'
    USER_TAB_POSITION = 0

    def __init__(self, conn, model=None, role_type=None, person=None,
                 visual_mode=False):
        BasePersonRoleEditor.__init__(self, conn, model, role_type, person,
                                      visual_mode=visual_mode)


    #
    # BaseEditorSlaves Hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        user = IUser(person)
        return user or person.addFacet(IUser, connection=conn, username="",
                                       password="", profile=None)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        user_status = UserStatusSlave(self.conn, self.model)
        self.main_slave.attach_person_slave(user_status)
        passwd_fields = not self.edit_mode
        self.user_details = UserDetailsSlave(self.conn, self.model,
            show_password_fields=passwd_fields,
            visual_mode=self.visual_mode)
        tab_text = _('User Details')
        self.main_slave._person_slave.attach_custom_slave(self.user_details,
                                                          tab_text)
        tab_child = self.main_slave._person_slave.custom_tab
        notebook = self.main_slave._person_slave.person_notebook
        notebook.reorder_child(tab_child, position=self.USER_TAB_POSITION)
        notebook.set_current_page(self.USER_TAB_POSITION)

    def validate_confirm(self):
        return self.user_details.validate_confirm()

    def on_confirm(self):
        self.main_slave.on_confirm()
        self.user_details.on_confirm()
        return self.model


class PasswordEditor(BaseEditor):
    gladefile = 'PasswordEditor'
    model_type = LoginInfo
    proxy_widgets = ('current_password',)

    def __init__(self, conn, user, visual_mode=False):
        self.user = user
        self.old_password = self.user.password
        BaseEditor.__init__(self, conn, visual_mode=visual_mode)
        self._setup_widgets()

    def _setup_widgets(self):
        self.password_slave.set_password_labels(_('New Password:'),
                                                _('Retype New Password:'))

    #
    # BaseEditorSlave Hooks
    #

    def get_title(self, model):
        title = _('Change "%s" Password') % self.user.username
        return title

    def create_model(self, conn):
        return LoginInfo()

    def setup_slaves(self):
        self.password_slave = PasswordEditorSlave(self.conn, self.model,
                                                  visual_mode=self.visual_mode)
        self.attach_slave('password_holder', self.password_slave)

    def setup_proxies(self):
        self.proxy = self.add_proxy(self.model,
                                    PasswordEditor.proxy_widgets)

    def validate_confirm(self):
        if self.model.current_password != self.old_password:
            msg = _(u"Password doesn't match with the stored one")
            self.current_password.set_invalid(msg)
            return False
        if not self.password_slave.validate_confirm():
            return False
        return True

    def on_confirm(self):
        self.password_slave.on_confirm()
        self.user.password = self.model.new_password
        return self.user


class CreditProviderEditor(BasePersonRoleEditor):
    model_name = _('Credit Provider')
    title = _('New Credit Provider')
    model_iface = ICreditProvider
    gladefile = 'BaseTemplate'
    provtype = None

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        credprovider = ICreditProvider(person)
        if credprovider:
            return credprovider
        if self.provtype is None:
            raise ValueError('Subclasses of CreditProviderEditor must '
                             'define a provtype attribute')
        return person.addFacet(ICreditProvider, short_name='',
                               provider_type=self.provtype,
                               open_contract_date=datetime.datetime.today(),
                               connection=conn)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        klass = CreditProviderDetailsSlave
        self.details_slave = klass(self.conn, self.model,
                                   visual_mode=self.visual_mode)
        slave = self.main_slave.get_person_slave()
        slave.attach_slave('person_status_holder', self.details_slave)


class CardProviderEditor(CreditProviderEditor):

    provtype = Person.getAdapterClass(ICreditProvider).PROVIDER_CARD

    def _get_columns(self):
        return [Column('description', _('Payment Type'), data_type=unicode,
                       expand=True, sorted=True),
                Column('destination_name', _('Destination'),
                       data_type=unicode, width=90),
                Column('commission', _('Commission (%)'),
                       data_type=Decimal, width=120),
                Column('is_active', _('Active'), data_type=bool,
                       editable=True)]

    def setup_slaves(self):
        CreditProviderEditor.setup_slaves(self)
        items = PaymentMethodDetails.selectBy(providerID=self.model.id,
                                              connection=self.conn)
        addlist = AdditionListSlave(self.conn, self._get_columns(),
                                    PaymentMethodDetailsWizard,
                                    list(items))
        addlist.register_editor_kwargs(credprovider=self.model)
        addlist.connect('before-delete-items', self.before_delete_items)
        addlist.klist.connect('cell-edited', self.on_cell_edited)
        slave = self.main_slave.get_person_slave()
        slave.attach_custom_slave(addlist, _("Payment Types"))
    #
    # Callbacks
    #

    def before_delete_items(self, slave, items):
        for item in items:
            table = type(item)
            table.delete(item.id, connection=self.conn)

    def on_cell_edited(self, klist, obj, attr):
        conn = obj.get_connection()
        conn.commit()


class FinanceProviderEditor(CreditProviderEditor):

    provtype = Person.getAdapterClass(ICreditProvider).PROVIDER_FINANCE

    def setup_slaves(self):
        CreditProviderEditor.setup_slaves(self)
        query = PaymentMethodDetails.q.providerID == self.model.id
        items = FinanceDetails.select(query, connection=self.conn)
        qty = items.count()
        if not qty:
            item = FinanceDetails(connection=self.conn,
                                  provider=self.model, destination=None)
        elif qty == 1:
            item = items[0]
        else:
            raise DatabaseInconsistency("You should have only one "
                                        "FinanceDetails  instance for "
                                        "this provider, got %d instead"
                                        % qty)
        finance_slave = FinanceDetailsSlave(self.conn, item)
        slave = self.main_slave.get_person_slave()
        slave.attach_custom_slave(finance_slave, _("Finance Details"))


class EmployeeEditor(BasePersonRoleEditor):
    model_name = _('Employee')
    title = _('New Employee')
    model_iface = IEmployee
    gladefile = 'BaseTemplate'

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        if ICompany(person):
            person.addFacet(IIndividual, connection=self.conn)
        employee = IEmployee(person)
        return employee or person.addFacet(IEmployee, connection=conn,
                                           role=None)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        if not self.individual_slave:
            raise ValueError('This editor must have an individual slave')
        self.details_slave = EmployeeDetailsSlave(self.conn, self.model,
                                                  visual_mode=self.visual_mode)
        custom_tab_label = _('Employee Data')
        slave = self.individual_slave
        slave._person_slave.attach_custom_slave(self.details_slave,
                                                custom_tab_label)
        self.status_slave = EmployeeStatusSlave(self.conn, self.model,
                                                visual_mode=self.visual_mode)
        slave.attach_person_slave(self.status_slave)
        self.role_slave = EmployeeRoleSlave(self.conn, self.model,
                                            edit_mode=self.edit_mode,
                                            visual_mode=self.visual_mode)
        slave._person_slave.attach_role_slave(self.role_slave)
        history_tab_label = _("Role History")
        history_slave = EmployeeRoleHistorySlave(self.model)
        slave._person_slave.attach_extra_slave(history_slave,
                                               history_tab_label)

    def on_confirm(self):
        self.individual_slave.on_confirm()
        self.role_slave.on_confirm()
        return self.model



class EmployeeRoleEditor(SimpleEntryEditor):
    model_type = EmployeeRole
    model_name = _('Employee Role')
    size = (330, 130)

    def __init__(self, conn, model, visual_mode=False):
        SimpleEntryEditor.__init__(self, conn, model, attr_name='name',
                                   name_entry_label=_('Role Name:'),
                                   visual_mode=visual_mode)

    #
    # BaseEditor Hooks
    #

    def get_title_model_attribute(self, model):
        return model.name

    #
    # BaseEditorSlave Hooks
    #

    def create_model(self, conn):
        return EmployeeRole(connection=conn, name='')

    def on_cancel(self):
        # XXX This will prevent problems in case that you can't
        # update the connection.
        if not self.edit_mode:
            self.model_type.delete(self.model.id, connection=self.conn)

    #
    # Kiwi handlers
    #

    def on_name_entry__validate(self, widget, value):
        conn = get_connection()
        q1 = func.UPPER(EmployeeRole.q.name) == value.upper()
        q2 = EmployeeRole.q.id != self.model.id
        query = AND(q1, q2)
        if EmployeeRole.select(query, connection=conn):
            return ValidationError('This role already exists!')


class SupplierEditor(BasePersonRoleEditor):
    model_name = _('Supplier')
    title = _('New Supplier')
    model_iface = ISupplier
    gladefile = 'BaseTemplate'

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        supplier = ISupplier(person)
        return supplier or person.addFacet(ISupplier, connection=conn)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        self.details_slave = SupplierDetailsSlave(self.conn, self.model)
        slave = self.main_slave.get_person_slave()
        slave.attach_slave('person_status_holder', self.details_slave)


class TransporterEditor(BasePersonRoleEditor):
    model_name = _('Transporter')
    title = _('New Transporter')
    model_iface = ITransporter
    gladefile = 'BaseTemplate'

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        transporter = ITransporter(person)
        if transporter:
            return transporter
        return person.addFacet(ITransporter, connection=conn)

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        self.details_slave = TransporterDataSlave(self.conn,
                                                  self.model)
        slave = self.main_slave.get_person_slave()
        slave.attach_slave('person_status_holder', self.details_slave)

class BranchEditor(BasePersonRoleEditor):
    model_name = _('Branch')
    title = _('New Branch')
    model_iface = IBranch
    gladefile = 'BaseTemplate'

    #
    # BaseEditor hooks
    #

    def create_model(self, conn):
        person = BasePersonRoleEditor.create_model(self, conn)
        branch = IBranch(person)
        model =  branch or person.addFacet(IBranch, connection=conn)
        model.manager = Person(connection=self.conn, name="")
        return model

    def setup_slaves(self):
        BasePersonRoleEditor.setup_slaves(self)
        self.status_slave = BranchDetailsSlave(self.conn, self.model)
        self.main_slave.attach_person_slave(self.status_slave)
