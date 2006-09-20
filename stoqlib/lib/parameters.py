# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
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
##
## Author(s):    Evandro Vale Miquelito     <evandro@async.com.br>
##               Henrique Romano            <henrique@async.com.br>
##
""" Parameters and system data for applications"""

from kiwi.datatypes import currency
from kiwi.argcheck import argcheck
from kiwi.log import Logger
from kiwi.python import namedAny, ClassInittableObject

from stoqlib.database.database import finish_transaction
from stoqlib.database.runtime import new_transaction
from stoqlib.domain.parameter import ParameterData
from stoqlib.domain.interfaces import (ISupplier, IBranch, ICompany,
                                       ISellable, IMoneyPM, ICheckPM, IBillPM,
                                       ICardPM, IFinancePM,
                                       IGiftCertificatePM)
from stoqlib.exceptions import DatabaseInconsistency
from stoqlib.lib.translation import stoqlib_gettext

_ = stoqlib_gettext


log = Logger('stoqlib.parameters')

class ParameterDetails:
    def __init__(self, group, short_desc, long_desc):
        self.group = group
        self.short_desc = short_desc
        self.long_desc = long_desc

_parameter_info = dict(
    MAIN_COMPANY=ParameterDetails(
    _(u'General'),
    _(u'Main Company'),
    _(u'The main company which is the owner of all other branch companies')),

    DEFAULT_SALESPERSON_ROLE=ParameterDetails(
    _(u'Sales'),
    _(u'Default Salesperson Role'),
    _(u'Defines which of the employee roles existent in the system is the '
      'salesperson role')),

    SUGGESTED_SUPPLIER=ParameterDetails(
    _(u'Purchase'),
    _(u'Suggested Supplier'),
    _(u'The supplier suggested when we are adding a new product in the '
      'system')),

    DEFAULT_BASE_CATEGORY=ParameterDetails(
    _(u'Purchase'),
    _(u'Default Base Sellable Category'),
    _(u'A default base sellable category which we always get as a '
      'suggestion when adding a new Sellable on the system')),

    DEFAULT_PAYMENT_DESTINATION=ParameterDetails(
    _(u'Financial'),
    _(u'Default Payment Destination'),
    _(u'A default payment destination which will be used for all the '
      'created payments until the user change the destination of each '
      'payment method.')),

    BASE_PAYMENT_METHOD=ParameterDetails(
    _(u'Financial'),
    _(u'Base Payment Method'),
    _(u'The base payment method which can easily be converted to '
      'other methods like check and bill.')),

    METHOD_MONEY=ParameterDetails(
    _(u'Financial'),
    _(u'Money Payment Method'),
    _(u'Definition of the money payment method. This parameter is not '
      'editable')),

    DELIVERY_SERVICE=ParameterDetails(
    _(u'Sales'),
    _(u'Delivery Service'),
    _(u'The default delivery service in the system.')),

    DEFAULT_GIFT_CERTIFICATE_TYPE=ParameterDetails(
    _(u'Sales'),
    _(u'Default Gift Certificate Type'),
    _(u'The default gift certificate type used when canceling '
       'sales and during renegotiations.')),

    USE_LOGIC_QUANTITY=ParameterDetails(
    _(u'Stock'),
    _(u'Use Logic Quantity'),
    _(u'An integer that defines if the company can work or not with '
      'logic quantities during stock operations. See StockItem '
      'documentation.')),

    MAX_LATE_DAYS=ParameterDetails(
    _(u'Sales'),
    _(u'Client Maximum Late Days'),
    _(u'An integer that represents a maximum number of days which a certain '
      'client can have unpaid payments with normal status.')),

    # XXX This parameter is Stoq-specific. How to deal with that
    # in a better way?
    POS_FULL_SCREEN=ParameterDetails(
    _(u'Sales'),
    _(u'Show POS Application Full Screen'),
    _(u'Once this parameter is set the Point of Sale application '
      'will be showed as full screen')),

    POS_SEPARATE_CASHIER=ParameterDetails(
    _(u'Sales'),
    _(u'Exclude cashier operations in Point of Sale'),
    _(u'If you have a computer that will be a Point of Sales and have a '
      'fiscal printer connected, set this False, so the Till menu will '
      'appear on POS. If you prefer to separate the Till menu from POS '
      'set this True.')),

    ACCEPT_ORDER_PRODUCTS=ParameterDetails(
    _(u'Sales'),
    _(u'Accept Order Products'),
    _(u'Can this company make sales for products that doesn\'t '
      'actually exist in the stock ? If this parameter is True we can order '
      'products.')),

    CITY_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'City Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this city.')),

    STATE_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'State Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this state.')),

    COUNTRY_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'Country Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this country.')),

    HAS_DELIVERY_MODE=ParameterDetails(
    _(u'Sales'),
    _(u'Has Delivery Mode'),
    _(u'Does this branch work with delivery service? If not, the '
      'delivery option will be disable on Point of Sales Application.')),

    HAS_STOCK_MODE=ParameterDetails(
    _(u'Stock'),
    _(u'Has Stock Mode'),
    _(u'Does this branch work with storable items? If the answer is negative, '
      'we will disable stock operations in the system.')),

    MAX_SEARCH_RESULTS=ParameterDetails(
    _(u'General'),
    _(u'Max Search Results'),
    _(u'The maximum number of results we must show after searching '
      'in any dialog.')),

    MANDATORY_INTEREST_CHARGE=ParameterDetails(
    _(u'Sales'),
    _(u'Mandatory Interest Charge'),
    _(u'Once this paramter is set, the charge of monthly '
      'interest will be mandatory for every payment')),

    CONFIRM_SALES_ON_TILL=ParameterDetails(
    _(u'Sales'),
    _(u'Confirm Sales on Till'),
    _(u'Once this parameter is set, the sales confirmation are only made '
      'on till application and the fiscal coupon will be printed on '
      'that application instead of Point of Sales')),

    ACCEPT_CHANGE_SALESPERSON=ParameterDetails(
    _(u'Sales'),
    _(u'Accept Change Salesperson'),
    _(u'Once this parameter is set to true, the user will be '
      'able to change the salesperson of an opened '
      'order on sale checkout dialog')),

    USE_PURCHASE_PREVIEW_PAYMENTS=ParameterDetails(
    _(u'Purchase'),
    _(u'Use Purchase Preview '
      'Payments'),
    _(u'Generate preview payments for new purchases which are not received '
      'yet. Once the order is received the preview payments will be '
      'also confirmed as valid payments with STATUS_PENDING')),

    RETURN_MONEY_ON_SALES=ParameterDetails(
    _(u'Sales'),
    _(u'Return Money On Sales'),
    _(u'Once this parameter is set the salesperson can return '
      'money to clients when there is overpaid values in sales '
      'with gift certificates as payment method.')),

    RECEIVE_PRODUCTS_WITHOUT_ORDER=ParameterDetails(
    _(u'Purchase'),
    _(u'Receive Products Without Order'),
    _(u'Can we receive products without having a purchase order created '
      'for them ? If yes, the first step of ReceivalWizard will accept going '
      'to the second step with no order selected.')),

    MAX_SALE_ORDER_VALIDITY=ParameterDetails(
    _(u'Sales'),
    _(u'Max sale order validity'),
    _(u'The max number of days that a sale order is valid')),

    # XXX: USE_SCALES_PRICE
    USE_SCALE_PRICE=ParameterDetails(
    _(u'Sales'),
    _(u'Use Scale Price'),
    _(u'Define if we are going to use the price supplied by the scales '
      'for items that require weighting')),

    # XXX: These parameters are Brazil-specific
    ASK_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Ask for Sale Order CFOP'),
    _(u'Once this parameter is set to True we will ask for the CFOP '
      'when creating new sale orders')),

    DEFAULT_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Default Sales CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when generating '
      'fiscal book entries.')),

    DEFAULT_RETURN_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Default Return Sales CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when returning '
      'sale orders ')),

    DEFAULT_RECEIVING_CFOP=ParameterDetails(
    _(u'Purchase'),
    _(u'Default Receiving CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when receiving '
      'products in the warehouse application.')),

    ICMS_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default ICMS tax'),
    _(u'Default ICMS to be applied on all the products of a sale. '
      'Note that this a percentage value and must be set as the '
      'format: 0 < value < 100. E.g: 18, which means 18% of tax.')),

    ISS_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default ISS tax'),
    _(u'Default ISS to be applied on all the services of a sale. '
      'Note that this a percentage value and must be set as the '
      'format: 0 < value < 100. E.g: 12, which means 12% of tax.')),

    SUBSTITUTION_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default Substitution tax'),
    _(u'The tax applied on all sale products with substitution tax type. '
      'Note that this a percentage value and must be set as the format: '
      '0 < value < 100. E.g: 16, which means 16% of tax.')),
    )

class ParameterAttr:
    def __init__(self, key, type, initial=None):
        self.key = key
        self.type = type
        self.initial = initial


class ParameterAccess(ClassInittableObject):
    """A mechanism to tie specific instances to constants that can be
    made available cross-application. This class has a special hook that
    allows the values to be looked up on-the-fly and cached.

    Usage:

        parameter = sysparam(conn).parameter_name
    """

    # New parameters must always be defined here
    constants = [
        # Adding constants
        ParameterAttr('USE_LOGIC_QUANTITY', bool, initial=True),
        ParameterAttr('POS_FULL_SCREEN', bool, initial=False),
        ParameterAttr('MAX_LATE_DAYS', int, initial=30),
        ParameterAttr('HAS_STOCK_MODE', bool, initial=True),
        ParameterAttr('HAS_DELIVERY_MODE', bool, initial=True),
        ParameterAttr('ACCEPT_ORDER_PRODUCTS', bool, initial=False),
        ParameterAttr('ACCEPT_CHANGE_SALESPERSON', bool, initial=False),
        ParameterAttr('MAX_SEARCH_RESULTS', int, initial=600),
        ParameterAttr('CITY_SUGGESTED', unicode, initial=u'Belo Horizonte'),
        ParameterAttr('STATE_SUGGESTED', unicode, initial=u'MG'),
        ParameterAttr('COUNTRY_SUGGESTED', unicode, initial=u'Brasil'),
        ParameterAttr('CONFIRM_SALES_ON_TILL', bool, initial=False),
        ParameterAttr('MANDATORY_INTEREST_CHARGE', bool, initial=False),
        ParameterAttr('USE_PURCHASE_PREVIEW_PAYMENTS', bool,
                      initial=True),
        ParameterAttr('RETURN_MONEY_ON_SALES', bool, initial=True),
        ParameterAttr('RECEIVE_PRODUCTS_WITHOUT_ORDER', bool,
                      initial=True),
        ParameterAttr('ASK_SALES_CFOP', bool, initial=False),
        ParameterAttr('MAX_SALE_ORDER_VALIDITY', int, initial=30),
        ParameterAttr('USE_SCALE_PRICE', bool, initial=False),
        ParameterAttr('ICMS_TAX', int, initial=18),
        ParameterAttr('ISS_TAX', int, initial=18),
        ParameterAttr('SUBSTITUTION_TAX', int, initial=18),
        ParameterAttr('POS_SEPARATE_CASHIER', bool, initial=False),
        # Adding objects -- Note that all the object referred here must
        # implements the IDescribable interface.
        ParameterAttr('DEFAULT_SALES_CFOP', u'fiscal.CfopData'),
        ParameterAttr('DEFAULT_RETURN_SALES_CFOP', u'fiscal.CfopData'),
        ParameterAttr('DEFAULT_RECEIVING_CFOP', u'fiscal.CfopData'),
        ParameterAttr('SUGGESTED_SUPPLIER',
                      u'person.PersonAdaptToSupplier'),
        ParameterAttr('MAIN_COMPANY',
                      u'person.PersonAdaptToBranch'),
        ParameterAttr('DEFAULT_BASE_CATEGORY',
                      u'sellable.BaseSellableCategory'),
        ParameterAttr('DEFAULT_SALESPERSON_ROLE',
                      u'person.EmployeeRole'),
        ParameterAttr('DEFAULT_PAYMENT_DESTINATION',
                      u'payment.destination.StoreDestination'),
        ParameterAttr('BASE_PAYMENT_METHOD',
                      u'payment.methods.PaymentMethod'),
        ParameterAttr('METHOD_MONEY',
                      u'payment.methods.PMAdaptToMoneyPM'),
        ParameterAttr('DELIVERY_SERVICE',
                      u'service.ServiceAdaptToSellable'),
        ParameterAttr('DEFAULT_GIFT_CERTIFICATE_TYPE',
                      u'giftcertificate.GiftCertificateType'),
        ]

    _cache = {}

    @classmethod
    def __class_init__(cls, namespace):
        for obj in cls.constants:
            prop = property(lambda self, n=obj.key, v=obj.type:
                            self.get_parameter_by_field(n, v))
            setattr(cls, obj.key, prop)

    def __init__(self, conn):
        ClassInittableObject.__init__(self)
        self.conn = conn

    def _remove_unused_parameters(self):
        """Remove any  parameter found in ParameterData table which is not
        used any longer.
        """
        global _parameter_info
        for param in ParameterData.select(connection=self.conn):
            if param.field_name not in _parameter_info.keys():
                ParameterData.delete(param.id, connection=self.conn)

    def _set_schema(self, field_name, field_value, is_editable=True):
        ParameterData(connection=self.conn, field_name=field_name,
                      field_value=unicode(field_value), is_editable=is_editable)

    def _get_parameter_by_name(self, param_name):
        res = ParameterData.select(ParameterData.q.field_name == param_name,
                                   connection=self.conn)
        if not res.count():
            raise DatabaseInconsistency("Can't find a ParameterData"
                                        "object for the key %s"
                                        % param_name)
        elif res.count() > 1:
            raise DatabaseInconsistency("It is not possible have more than "
                                        "one ParameterData for the same "
                                        "key (%s)" % param_name)
        return res[0]

    #
    # Public API
    #

    @argcheck(str, unicode)
    def update_parameter(self, parameter_name, value):
        param = self._get_parameter_by_name(parameter_name)
        param.field_value = unicode(value)
        self.rebuild_cache_for(parameter_name)

    def rebuild_cache_for(self, param_name):
        from stoqlib.domain.base import AbstractModel
        try:
            value = self._cache[param_name]
        except KeyError:
            return

        param = self._get_parameter_by_name(param_name)
        value_type = type(value)
        if not issubclass(value_type, AbstractModel):
            # XXX: workaround to works with boolean types:
            data = param.field_value
            if value_type is bool:
                data = int(data)
            self._cache[param_name] = value_type(data)
            return
        table = value_type
        obj_id = param.field_value
        self._cache[param_name] = table.get(obj_id, connection=self.conn)

    def rebuild_cache(self):
        map(self.rebuild_cache_for, self._cache.keys())

    def get_parameter_by_field(self, field_name, field_type):
        from stoqlib.domain.base import AbstractModel
        if isinstance(field_type, unicode):
            field_type = namedAny('stoqlib.domain.' + field_type)
        if self._cache.has_key(field_name):
            param = self._cache[field_name]
            if issubclass(field_type, AbstractModel):
                return field_type.get(param.id, connection=self.conn)
            return field_type(param)
        values = ParameterData.select(ParameterData.q.field_name == field_name,
                                      connection=self.conn)
        if values.count() > 1:
            msg = ('There is no unique correspondent parameter for this field '
                   'name. Found %s items.' % values.count())
            DatabaseInconsistency(msg)
        elif not values.count():
            return None
        value = values[0]
        if issubclass(field_type, AbstractModel):
            param = field_type.get(value.field_value, connection=self.conn)
        else:
            # XXX: workaround to works with boolean types:
            value = value.field_value
            if field_type is bool:
                value = int(value)
            param = field_type(value)
        self._cache[field_name] = param
        return param

    def set_defaults(self, update=False):
        self._remove_unused_parameters()
        constants = [c for c in self.constants if c.initial is not None]

        # Creating constants
        for obj in constants:
            if (update and self.get_parameter_by_field(obj.key, obj.type)
                is not None):
                continue

            if obj.type is bool:
                # Convert Bool to int here
                value = int(obj.initial)
            else:
                value = obj.initial
            self._set_schema(obj.key, value)

        # Creating system objects
        # When creating new methods for system objects creation add them
        # always here
        self.ensure_default_sales_cfop()
        self.ensure_default_return_sales_cfop()
        self.ensure_default_receiving_cfop()
        self.ensure_suggested_supplier()
        self.ensure_default_base_category()
        self.ensure_default_salesperson_role()
        self.ensure_main_company()
        self.ensure_payment_destination()
        self.ensure_payment_methods()
        self.ensure_delivery_service()
        self.ensure_default_gift_certificate_type()

    #
    # Methods for system objects creation
    #

    def ensure_suggested_supplier(self):
        from stoqlib.domain.person import Person
        key = "SUGGESTED_SUPPLIER"
        table = Person.getAdapterClass(ISupplier)
        if self.get_parameter_by_field(key, table):
            return
        person_obj = Person(name=key, connection=self.conn)
        person_obj.addFacet(ICompany, cnpj='supplier suggested',
                            connection=self.conn)
        supplier = person_obj.addFacet(ISupplier, connection=self.conn)
        self._set_schema(key, supplier.id)

    def ensure_default_base_category(self):
        from stoqlib.domain.sellable import BaseSellableCategory
        key = "DEFAULT_BASE_CATEGORY"
        if self.get_parameter_by_field(key, BaseSellableCategory):
            return
        base_category = BaseSellableCategory(description=key,
                                             connection=self.conn)
        self._set_schema(key, base_category.id)

    def ensure_default_salesperson_role(self):
        from stoqlib.domain.person import EmployeeRole
        key = "DEFAULT_SALESPERSON_ROLE"
        if self.get_parameter_by_field(key, EmployeeRole):
            return
        role = EmployeeRole(name=u'Salesperson',
                            connection=self.conn)
        self._set_schema(key, role.id, is_editable=False)

    def ensure_main_company(self):
        from stoqlib.domain.person import Person, Address, CityLocation
        key = "MAIN_COMPANY"
        table = Person.getAdapterClass(IBranch)
        if self.get_parameter_by_field(key, table):
            return

        person_obj = Person(name=None, connection=self.conn)
        city_location = CityLocation(country=u"Brasil", connection=self.conn)
        Address(is_main_address=True,
                person=person_obj, city_location=city_location,
                connection=self.conn)
        person_obj.addFacet(ICompany, cnpj=None, fancy_name=None,
                            connection=self.conn)
        branch = person_obj.addFacet(IBranch, connection=self.conn)
        branch.manager = Person(connection=self.conn, name=u"Manager")
        self._set_schema(key, branch.id)

    def ensure_payment_destination(self):
        # Note that this method must always be called after
        # ensure_main_company
        from stoqlib.domain.payment.destination import StoreDestination
        key = "DEFAULT_PAYMENT_DESTINATION"
        if self.get_parameter_by_field(key, StoreDestination):
            return
        branch = self.MAIN_COMPANY
        pm = StoreDestination(description=_(u'Default Store Destination'),
                              branch=branch,
                              connection=self.conn)
        self._set_schema(key, pm.id)

    def ensure_payment_methods(self):
        from stoqlib.domain.payment.methods import PaymentMethod
        key = "METHOD_MONEY"
        table = PaymentMethod.getAdapterClass(IMoneyPM)
        if self.get_parameter_by_field(key, table):
            return
        destination = self.DEFAULT_PAYMENT_DESTINATION
        pm = PaymentMethod(connection=self.conn)
        for interface in [IMoneyPM, ICheckPM, IBillPM]:
            pm.addFacet(interface, connection=self.conn,
                        destination=destination)
        for interface in [ICardPM, IGiftCertificatePM, IFinancePM]:
            pm.addFacet(interface, connection=self.conn)
        self._set_schema('BASE_PAYMENT_METHOD', pm.id, is_editable=False)
        self._set_schema(key, IMoneyPM(pm).id,
                        is_editable=False)

    def ensure_delivery_service(self):
        from stoqlib.domain.sellable import BaseSellableInfo
        from stoqlib.domain.service import Service
        key = "DELIVERY_SERVICE"
        table = Service.getAdapterClass(ISellable)
        if self.get_parameter_by_field(key, table):
            return

        service = Service(connection=self.conn)

        sellable_info = BaseSellableInfo(connection=self.conn,
                                         description=_(u'Delivery'))
        sellable = service.addFacet(ISellable,
                                    base_sellable_info=sellable_info,
                                    connection=self.conn)
        self._set_schema(key, sellable.id)

    def ensure_default_gift_certificate_type(self):
        """Creates a initial gift certificate that will be tied with return
        values of sale cancelations.
        """
        from stoqlib.domain.sellable import BaseSellableInfo
        from stoqlib.domain.giftcertificate import GiftCertificateType
        key = "DEFAULT_GIFT_CERTIFICATE_TYPE"
        if self.get_parameter_by_field(key, GiftCertificateType):
            return
        description = _(u'General Gift Certificate')
        sellable_info = BaseSellableInfo(connection=self.conn,
                                         description=description,
                                         price=currency(0))
        certificate = GiftCertificateType(connection=self.conn,
                                          base_sellable_info=sellable_info)
        self._set_schema(key, certificate.id)

    def _ensure_cfop(self, key, description, code):
        from stoqlib.domain.fiscal import CfopData
        if self.get_parameter_by_field(key, CfopData):
            return
        data = CfopData(code=code, description=description,
                        connection=self.conn)
        self._set_schema(key, data.id)

    def ensure_default_return_sales_cfop(self):
        self._ensure_cfop("DEFAULT_RETURN_SALES_CFOP",
                          u"Devolucao",
                          u"5.202")

    def ensure_default_sales_cfop(self):
        self._ensure_cfop("DEFAULT_SALES_CFOP",
                          u"Venda de Mercadoria Adquirida",
                          u"5.102")

    def ensure_default_receiving_cfop(self):
        self._ensure_cfop("DEFAULT_RECEIVING_CFOP",
                          u"Compra para Comercializacao",
                          u"1.102")


#
# General routines
#


def sysparam(conn):
    return ParameterAccess(conn)


def get_parameter_by_field(field_name, conn):
    values = ParameterData.select(ParameterData.q.field_name == field_name,
                                  connection=conn)
    if values.count() > 1:
        msg = ('There is no unique correspondent parameter for this field '
               'name. Found %s items.' % values.count())
        DatabaseInconsistency(msg)
    elif not values.count():
        return None
    return values[0]


def get_foreign_key_parameter(field_name, conn):
    parameter = get_parameter_by_field(field_name, conn)
    if not (parameter and parameter.foreign_key):
        msg = _('There is no defined %s parameter data'
                'in the database.' % field_name)
        raise DatabaseInconsistency(msg)
    return parameter


def get_parameter_details(field_name):
    """ Returns a ParameterDetails class for the given parameter name, or
    None if the name supplied isn't a valid parameter name.
    """
    global _parameter_info
    try:
        return _parameter_info[field_name]
    except KeyError:
        raise NameError("Does not exists no parameters "
                        "with name %s" % field_name)


#
# Ensuring everything
#

def check_parameter_presence(conn):
    """
    Check so the number of installed parameters are equal to
    the number of available ones
    @returns: True if they're up to date, False otherwise
    """

    global _parameter_info
    results = ParameterData.select(connection=conn)

    return results.count() == len(_parameter_info)

def ensure_system_parameters(update=False):
    log.info("Creating default system parameters")
    trans = new_transaction()
    param = sysparam(trans)
    param.set_defaults(update)
    finish_transaction(trans, 1)
