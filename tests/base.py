# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005 Async Open Source <http://www.async.com.br>
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
## Author(s):   Rud� Porto Filgueiras   <rudazz@gmail.com>
##              Evandro Vale Miquelito  <evandro@async.com.br>
##
""" Base module to be used by all domain test modules"""

import datetime
import decimal
try:
    from twisted.trial import unittest
    unittest # pyflakes
except:
    import unittest

from kiwi.datatypes import currency
from sqlobject.col import (SOUnicodeCol, SOIntCol, SODecimalCol, SODateTimeCol,
                           SODateCol, SOBoolCol, SOForeignKey, SOBLOBCol)

from stoqlib.database.columns import SOPriceCol
from stoqlib.database.runtime import new_transaction
from stoqlib.exceptions import StoqlibError
from stoqlib.lib.component import Adapter
from stoqlib.lib.parameters import sysparam
from stoqlib.domain.interfaces import (IBranch, ICompany, IEmployee,
                                       IIndividual, ISupplier,
                                       ISellable, IStorable, ISalesPerson)

from bootstrap import bootstrap_testsuite

# Default values for automatic instance creation and set value tests.
STRING_TEST_VALUES = ('Instance Creation String','Set Test String')
DECIMAL_TEST_VALUES = (decimal.Decimal("24.38"),
                       decimal.Decimal("445.67"))
CURRENCY_TEST_VALUES = (currency(decimal.Decimal("98.42")),
                        currency(decimal.Decimal("876.98")))
INT_TEST_VALUES = (20, 55)
DATE_TEST_VALUES = (datetime.date.today(),
                    datetime.date.today() + datetime.timedelta(1))
DATETIME_TEST_VALUES = (datetime.datetime.now(),
                        datetime.datetime.now() + datetime.timedelta(1))
BOOL_TEST_VALUES = (True, False)

def column_type_data(column):
    """ This function returns tuples of values for each SQLObject
    column type:
    SOUnicodeCol, SODecimalCol, SOIntCOl, SODateCOl, SODateTimeCOl,
    SOBollCol. Any other column types receive None value.

    The first value of each pair is used to create an instance and are
    sent to the domain class constructor.

    The second value is used to update the attribute of created instance.
    """
    if isinstance(column, SOUnicodeCol):
        return STRING_TEST_VALUES
    elif isinstance(column, SOIntCol):
        return INT_TEST_VALUES
    elif isinstance(column, SOPriceCol):
        return CURRENCY_TEST_VALUES
    elif isinstance(column, SODecimalCol):
        return DECIMAL_TEST_VALUES
    elif isinstance(column, SODateCol):
        return DATE_TEST_VALUES
    elif isinstance(column, SODateTimeCol):
        return DATETIME_TEST_VALUES
    elif isinstance(column, SOBoolCol):
        return BOOL_TEST_VALUES
    elif isinstance(column, SOForeignKey):
        return None, None
    elif isinstance(column, SOBLOBCol):
        return "", ""
    else:
        raise ValueError('Invalid column type, got %s'
                         % type(column))


class DomainTest(unittest.TestCase):
    def setUp(self):
        self.trans = new_transaction()

    def tearDown(self):
        self.trans.rollback()

    def create_branch(self):
        from stoqlib.domain.person import Person
        person = Person(name='Dummy', connection=self.trans)
        person.addFacet(ICompany, fancy_name='Dummy shop', connection=self.trans)
        return person.addFacet(IBranch, connection=self.trans)

    def create_supplier(self):
        from stoqlib.domain.person import Person
        person = Person(name='Supplier', connection=self.trans)
        person.addFacet(ICompany, fancy_name='Company Name', connection=self.trans)
        return person.addFacet(ISupplier, connection=self.trans)

    def create_storable(self):
        from stoqlib.domain.product import Product
        product = Product(connection=self.trans)
        return product.addFacet(IStorable, connection=self.trans)

    def create_sellable(self):
        from stoqlib.domain.product import Product
        from stoqlib.domain.sellable import BaseSellableInfo
        product = Product(connection=self.trans)
        sellable_info = BaseSellableInfo(connection=self.trans,
                                         description="Description",
                                         price=10)
        return product.addFacet(ISellable,
                                base_sellable_info=sellable_info,
                                connection=self.trans)

    def create_salesperson(self):
        from stoqlib.domain.person import Person, EmployeeRole
        person = Person(name='SalesPerson', connection=self.trans)
        person.addFacet(IIndividual, connection=self.trans)
        role = EmployeeRole(name='Role', connection=self.trans)
        person.addFacet(IEmployee, role=role, connection=self.trans)
        return person.addFacet(ISalesPerson, connection=self.trans)

    def create_sale(self):
        from stoqlib.domain.sale import Sale
        from stoqlib.domain.till import Till
        till = Till.get_current(self.trans)
        salesperson = self.create_salesperson()
        return Sale(till=till,
                    coupon_id=0,
                    open_date=datetime.datetime.now(),
                    salesperson=salesperson,
                    cfop=sysparam(self.trans).DEFAULT_SALES_CFOP,
                    connection=self.trans)

    def create_person(self):
        from stoqlib.domain.person import Person
        return Person(name='John', connection=self.trans)

    def create_city_location(self):
        from stoqlib.domain.address import CityLocation
        return CityLocation(country='Groenlandia',
                            city='Acapulco',
                            state='Wisconsin',
                            connection=self.trans)


class BaseDomainTest(unittest.TestCase):
    """Base class to be used by all domain test classes.
    This class has some basic infrastructure:

    @param conn: an SQLObject Transaction instance
    @param _table: reference to a stoqlib domain class that will be
                   tested by the Test class.
    @param foreign_key_attrs: a dict with foreign keys used by the class
                              to be tested:
                             {'foreign_key_attrs_name': fk_class_reference}
                             where fk_class_reference is a stoqlib domain
                             class
    @param skip_attr: attributes that will not be automaticaly tested
    """
    foreign_key_attrs = None
    _table = None
    skip_attrs = ['model_modified','_is_valid_model','model_created',
                  'childName']

    def setUp(self):
        if not self._table:
            raise StoqlibError("You must provide a _table attribute")
        self.trans = new_transaction()
        self._table_count = self._table.select(connection=self.trans).count()
        self._check_foreign_key_data()
        self.insert_dict, self.edit_dict = self._generate_test_data()
        self._generate_foreign_key_attrs()

    def tearDown(self):
        self.trans.rollback()

    #
    # Class methods
    #

    def _check_foreign_key_data(self):
        self._foreign_key_data = self.get_foreign_key_data()
        for fkey_data in self._foreign_key_data:
            assert fkey_data.get_connection() is self.trans

    def _check_foreign_key(self, table, fkey_name):
        return fkey_name == table.sqlmeta.soClass.__name__

    def _get_fkey_data_by_fkey_name(self, fkey_name):
        for data in self._foreign_key_data:
            table = type(data)
            if self._check_foreign_key(table, fkey_name):
                return data
            table = table.sqlmeta.parentClass
            if table and self._check_foreign_key(table, fkey_name):
                return data

    def _generate_test_data(self):
        """This method uses column_type_data function and return two dicts:
        insert_args: 'column_name': value #used to instance creation.
        edit_args: 'column_name': value   #used to set_and_get test.
        """
        insert = dict()
        edit = dict()
        cols = column_type_data

        columns = self._table.sqlmeta.columns.values()
        table = self._table.sqlmeta.parentClass
        if table:
            columns += table.sqlmeta.columns.values()

        extra_values = self.get_extra_field_values()
        for column in columns:
            colname = column.origName
            if colname in self.skip_attrs:
                continue
            data = self._get_fkey_data_by_fkey_name(column.foreignKey)
            if data:
                insert[colname] = edit[colname] = data
            elif colname in extra_values.keys():
                insert[colname], edit[colname] = extra_values[colname]
            else:
                insert[colname], edit[colname] = cols(column)
        return insert, edit

    def _generate_foreign_key_attrs(self):
        """Create all foreign key objects using foreign_key_attrs dict and
        apeend to insert_dict attribute.
        """
        if self.foreign_key_attrs and isinstance(self.foreign_key_attrs, dict):
            for key, klass in self.foreign_key_attrs.items():
                fk_test_instance = klass(connection=self.trans)
                insert_dict, edit_dict = fk_test_instance._generate_test_data()
                fk_table = fk_test_instance._table
                fk_instance = fk_table(connection=self.trans,
                                       **insert_dict)
                self.insert_dict[key] = fk_instance

    #
    # General methods
    #

    def _check_set_and_get(self, test_value, db_value, key):
        if isinstance(test_value, datetime.datetime):
            # There is no microseconds stored in the database and that's
            # why we are ignoring them here
            assert abs(test_value - db_value) < datetime.timedelta(seconds=1)
            return
        assert test_value == db_value

    #
    # Hooks
    #

    def get_foreign_key_data(self):
        return []

    def get_extra_field_values(self):
        """This hook returns a dictionary of tuples. Each tuple has two values:
        an 'insert' and an 'edit' values. This list will be used when
        setting attributes in self._table. The dict keys are attribute names
        of self._table
        """
        return {}

    def get_adapter(self):
        """This method must be overwritten by child when testing adapters.
        It must always return an instance of _table type
        """
        raise NotImplementedError

    #
    # Tests
    #

    def create_instance(self):
        """ Create a domain class instance using insert_dict attribute and
        assert a new row in the database was inserted.
        """
        if issubclass(self._table, Adapter):
            self._instance = self.get_adapter()
        else:
            self._instance = self._table(connection=self.trans,
                                         **self.insert_dict)
        assert self._instance is not None
        self._table_count = long(self._table_count + 1)
        assert (self._table_count ==
                self._table.select(connection=self.trans).count())

    def set_and_get(self):
        """Update each common attribute of a domain class using edit_dict
        and verify if the value was updated.
        """
        for key, value in self.edit_dict.items():
            value = self.edit_dict[key]
            setattr(self._instance, key, value)
            db_value = getattr(self._instance, key)
            self._check_set_and_get(value, db_value, key)

bootstrap_testsuite()
