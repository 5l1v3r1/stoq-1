# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2006 Async Open Source <http://www.async.com.br>
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
## Author(s): Rud� Porto Filgueir    <rudazz@gmail.com>
##            Evandro Vale Miquelito    <evandro@async.com.br>
##            Johan Dahlin              <jdahlin@async.com.br>
##

from stoqlib.domain.address import Address, CityLocation
from stoqlib.lib.parameters import sysparam

from tests.base import DomainTest

class TestCityLocation(DomainTest):
    def testIsValidModel(self):
        location = self.create_city_location()
        self.failUnless(location.is_valid_model())
        invalid_location = CityLocation(connection=self.trans)
        self.failIf(invalid_location.is_valid_model())

    def testGetSimilar(self):
        location = self.create_city_location()
        self.assertEquals(location.get_similar().count(), 0)

        clone = location.clone()
        self.assertEquals(location.get_similar().count(), 1)

        clone.city = "Chicago"
        self.assertEquals(location.get_similar().count(), 0)

    def testGetDefault(self):
        location = CityLocation.get_default(self.trans)
        self.failUnless(isinstance(location, CityLocation))
        self.assertEquals(location.city,
                          sysparam(self.trans).CITY_SUGGESTED)
        self.assertEquals(location.state,
                          sysparam(self.trans).STATE_SUGGESTED)
        self.assertEquals(location.country,
                          sysparam(self.trans).COUNTRY_SUGGESTED)

class TestAddress(DomainTest):
    def testIsValidModel(self):
        person = self.create_person()
        empty_location = CityLocation(connection=self.trans)
        empty_address = Address(connection=self.trans,
                                person=person,
                                city_location=empty_location)
        is_valid_model = empty_address.is_valid_model()
        assert bool(is_valid_model) is False

    def test_ensure_address(self):
        addresses = Address.select(connection=self.trans)
        self.failUnless(addresses)
        address = addresses[0]

        old_location = address.city_location
        address.city_location = old_location.clone()

        address.ensure_address()
        self.assertEqual(address.city_location, old_location)

    def test_get_city_location_attributes(self):
        person = self.create_person()
        city = 'Acapulco'
        country = 'Brazil'
        state = 'Cracovia'
        location = CityLocation(city=city, state=state, country=country,
                                connection=self.trans)
        address = Address(person=person, city_location=location,
                          connection=self.trans)
        self.assertEquals(address.get_city(), 'Acapulco')
        self.assertEquals(address.get_country(), 'Brazil')
        self.assertEquals(address.get_state(), 'Cracovia')

    def test_get_address_string(self):
        person = self.create_person()
        location = self.create_city_location()

        street = 'Rua das Couves'
        number = 283
        district = 'Federal'
        address = Address(person=person, city_location=location,
                          street=street, number=number, district=district,
                          connection=self.trans)
        string = address.get_address_string()
        self.assertEquals(string, u'%s %s, %s' % (street, number, district))

