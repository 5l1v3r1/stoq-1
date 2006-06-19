# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
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
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Henrique Romano        <henrique@async.com.br>
##

from decimal import Decimal

from stoqdrivers.devices.printers.fiscal import FiscalPrinter
from stoqdrivers.constants import (TAX_NONE, UNIT_LITERS, UNIT_CUSTOM,
                                   MONEY_PM, TAX_ICMS, CUSTOM_PM,)
from stoqdrivers.exceptions import (CouponOpenError, PendingReduceZ,
                                    PendingReadX, PaymentAdditionError,
                                    AlreadyTotalized, CancelItemError,
                                    InvalidValue, CloseCouponError,
                                    CouponNotOpenError)
from tests.base import BaseTest

class TestCoupon(BaseTest):
    """ Test a coupon creation """
    device_class = FiscalPrinter

    #
    # Helper methods
    #

    def _open_coupon(self):
        self._device.identify_customer("Henrique Romano", "Async", "1234567890")
        while True:
            try:
                self._device.open()
                break
            except CouponOpenError:
                self._device.cancel()
            except PendingReduceZ:
                self._device.close_till()
            except PendingReadX:
                self._device.summarize()

    #
    # Tests
    #

    def test_add_item(self):
        self._open_coupon()
        # 1. Specify discount and surcharge at the same time
        self.failUnlessRaises(TypeError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              TAX_NONE, discount=Decimal("1"),
                              surcharge=Decimal("1"))

        # 2. Specify unit_desc with unit different from UNIT_CUSTOM
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              TAX_NONE, unit=UNIT_LITERS, unit_desc="XX")

        # 3. Specify unit as UNIT_CUSTOM and not supply a unit_desc
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              TAX_NONE, unit=UNIT_CUSTOM)

        # 4. Specify unit as UNIT_CUSTOM and unit_desc greater than 2 chars
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              TAX_NONE, unit=UNIT_CUSTOM, unit_desc="XXXX")

        # 5. Add item without price
        self.failUnlessRaises(InvalidValue, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("0"),
                              TAX_NONE)

        #
        # 6. Dataregis specific: the first 6 chars of the product code must
        # be digits.
        self._device.add_item(u"ABCDEF", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE, items_quantity=Decimal("2"))

        # A "normal" item...
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE, items_quantity=Decimal("1"))

        # A item with customized unit
        self._device.add_item(u"123456", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE, items_quantity=Decimal("1"),
                              unit=UNIT_CUSTOM, unit_desc="Tx")

        # A item with surcharge
        self._device.add_item(u"123456", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE, items_quantity=Decimal("1"),
                              surcharge=Decimal("1"))

        # 7. Add item with coupon totalized
        self._device.totalize()
        self.failUnlessRaises(AlreadyTotalized,
            self._device.add_item, u"123456", u"Monitor LG Flatron T910B",
            Decimal("10"), TAX_NONE)

        self._device.add_payment(MONEY_PM, Decimal("100"))
        self._device.close()

        # 8. Add item without coupon
        self.failUnlessRaises(CouponNotOpenError, self._device.add_item,
                              u"123456", u"Monitor LG Flatron T910B",
                              Decimal("500"), TAX_NONE, discount=Decimal("1"))

    def test_cancel_item(self):
        self._open_coupon()
        item_id = self._device.add_item(u"987654", u"Monitor LG 775N",
                                        Decimal("10"), TAX_NONE,
                                        items_quantity=Decimal("1"))
        # 1. Cancel invalid item
        self.failUnlessRaises(CancelItemError,
                              self._device.cancel_item, item_id + 9)
        self._device.cancel_item(item_id)
        # 2. Cancel item twice
        self.failUnlessRaises(CancelItemError,
                              self._device.cancel_item, item_id)
        item_id = self._device.add_item(u"987654", u"Monitor LG 775N",
                                        Decimal("10"), TAX_NONE,
                                        items_quantity=Decimal("1"))
        self._device.totalize()
        self._device.add_payment(MONEY_PM, Decimal("100"))
        self._device.close()

    def test_totalize(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE, items_quantity=Decimal("1"))
        # 1. discount and surcharge together
        self.failUnlessRaises(TypeError, self._device.totalize,
                              Decimal("1"), Decimal("1"))

        # 2. specify surcharge with taxcode equals TAX_NONE
        self.failUnlessRaises(ValueError, self._device.totalize,
                              surcharge=Decimal("1"), taxcode=TAX_NONE)

        # 3. surcharge with taxcode equals to TAX_ICMS
        # (daruma FS345 specific)
        self._device.totalize(surcharge=Decimal("1"), taxcode=TAX_ICMS)
        self._device.add_payment(MONEY_PM, Decimal("12"))
        self._device.close()

        # 4. surcharge with taxcode different of TAX_ICMS
#         self._open_coupon()
#         self._device.add_item("987654", u"Monitor LG 775N", Decimal("10"),
#                                TAX_ICMS, items_quantity=Decimal("1"))
#         self._device.totalize(surcharge=Decimal("1"), taxcode=TAX_IOF)
#         self._device.add_payment(MONEY_PM, Decimal("10"))
#         self._device.close()

    def test_add_payment(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE)
        # 1. Add payment without totalize the coupon
        self.failUnlessRaises(PaymentAdditionError,
                              self._device.add_payment, MONEY_PM,
                              Decimal("100"))
        self._device.totalize()

        # 2. Add payment with customized type without describe it
        self.failUnlessRaises(ValueError,
                              self._device.add_payment, CUSTOM_PM,
                              Decimal("100"))

        # 3. Describe the payment type not using CUSTOM_PM
        self.failUnlessRaises(ValueError,
                              self._device.add_payment, MONEY_PM,
                              Decimal("100"), custom_pm="02")

        # 4. Add payment with customized type.
        # XXX: Not trivial to do, since customized types depends directly
        # of the device configuration; as this test must execute with all
        # the coupon printers, we can't just assume a "always existent"
        # payment type.

        self._device.add_payment(MONEY_PM, Decimal("100"))
        self._device.close()

    def test_close_coupon(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              TAX_NONE)
        # 1. Close without totalize
        self.failUnlessRaises(CloseCouponError, self._device.close)

        # 2. Close without payments
        self._device.totalize()
        self.failUnlessRaises(CloseCouponError, self._device.close)

        # 3. Close with the payments total value lesser than the totalized
        self._device.add_payment(MONEY_PM, Decimal("5"))
        self.failUnlessRaises(CloseCouponError, self._device.close)

        self._device.add_payment(MONEY_PM, Decimal("100"))
        # 4. Close the coupon with a BIG message
        self._device.close(u"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    def test_cancel_coupon(self):
        self._open_coupon()
        self._device.cancel()

    def test_till_add_cash(self):
        self._device.till_add_cash(Decimal("10"))

    def test_till_remove_cash(self):
        self._device.till_remove_cash(Decimal("10"))

    def test_coupon_open(self):
        self._open_coupon()
        self.failUnlessRaises(CouponOpenError, self._device.open)
        self._device.cancel()
