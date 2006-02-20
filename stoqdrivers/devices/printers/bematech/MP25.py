# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
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
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Cleber Rodrigues      <cleber@globalred.com.br>
##              Henrique Romano       <henrique@async.com.br>
##
"""
stoqdrivers/drivers/bematech/MP25.py:

    Drivers implementation for Bematech printers.
"""
import gettext
from decimal import Decimal

from zope.interface import implements

from stoqdrivers.devices.serialbase import SerialBase
from stoqdrivers.exceptions import (DriverError, OutofPaperError, PrinterError,
                                    CommandError, CouponOpenError,
                                    HardwareFailure, AlmostOutofPaper,
                                    PrinterOfflineError, PaymentAdditionError,
                                    ItemAdditionError, CancelItemError,
                                    CouponTotalizeError)
from stoqdrivers.constants import (TAX_IOF, TAX_ICMS, TAX_NONE, TAX_EXEMPTION,
                                   TAX_SUBSTITUTION, MONEY_PM, CHEQUE_PM,
                                   UNIT_WEIGHT, UNIT_METERS, UNIT_LITERS,
                                   UNIT_EMPTY, UNIT_CUSTOM)
from stoqdrivers.devices.printers.interface import ICouponPrinter
from stoqdrivers.devices.printers.capabilities import Capability

_ = lambda msg: gettext.dgettext("stoqdrivers", msg)

#
# This part will be improved when bug #2246 is fixed
# Right now, we just set CHEQUE_PM with the same value
# of MONEY_PM
#
payment_methods = {MONEY_PM: "01",
                   CHEQUE_PM: "01"}

# This is broken, have to educate myself about taxes
tax_translate_dict = {TAX_IOF: "II",
                      TAX_ICMS: "II",
                      TAX_SUBSTITUTION: "II",
                      TAX_EXEMPTION: "II",
                      TAX_NONE: "II"}

unit_translate_dict = {UNIT_WEIGHT: "Kg",
                       UNIT_METERS: "m ",
                       UNIT_LITERS: "Lt",
                       UNIT_EMPTY: "  "}

CASH_IN_TYPE = "SU"
CASH_OUT_TYPE = "SA"
CMD_READ_X = 6
CMD_COUPON_CANCEL = 14
CMD_CLOSE_TILL = 5
CMD_ADD_VOUCHER = 25
CMD_ADD_ITEM = 63
CMD_COUPON_GET_SUBTOTAL = 29
CMD_COUPON_OPEN = 0
CMD_CANCEL_ITEM = 31
CMD_COUPON_TOTALIZE = 32
CMD_COUPON_CLOSE = 34
CMD_ADD_PAYMENT = 72
CMD_REDUCE_Z = 5
CMD_GET_VARIABLES = 35
CMD_GET_COUPON_NUMBER = 30
VAR_LAST_ITEM_ID = 12
VAR_PAID_VALUE = 22
NAK = 21
ACK = 6
STX = 2

#
# Helper functions
#

def bcd2dec(data):
    return int(''.join(['%x' % ord(i) for i in data]))

#
# Driver implementation
#

class MP25(SerialBase):
    implements(ICouponPrinter)
    CMD_PROTO = 0x1C

    model_name = "Bematech MP25 FI"
    coupon_printer_charset = "cp850"

    st1_codes = {
        128: (OutofPaperError, _("Printer is out of paper")),
        64: (AlmostOutofPaper, _("Printer almost out of paper")),
        32: (PrinterError, _("Printer clock error")),
        16: (PrinterError, _("Printer in error state")),
        8: (CommandError, _("First data value in CMD is not ESC (1BH)")),
        4: (CommandError, _("Nonexistent command")),
        2: (CouponOpenError, _("Printer has a coupon currently open")),
        1: (CommandError, _("Invalid number of parameters"))}

    st2_codes = {
        128: (CommandError, _("Invalid CMD parameter")),
        64: (HardwareFailure, _("Fiscal memory is full")),
        32: (HardwareFailure, _("Error in CMOS memory")),
        16: (PrinterError, _("Given tax is not programmed on the printer")),
        8: (DriverError, _("No available tax slot")),
        4: (DriverError, _("Cancel operation is not allowed")),
        2: (PrinterError, _("Owner data (CGC/IE) not programmed on the printer")),
        1: (CommandError, _("Command not executed"))}

    st3_codes = {
        7: (CouponOpenError, _("Coupon already Open")),
        8: (DriverError, _("Coupon is closed")),
        13: (PrinterOfflineError, _("Printer is offline")),
        16: (DriverError, _("Surcharge or discount greater than coupon total "
                            "value")),
        17: (DriverError, _("Coupon with no items")),
        20: (PaymentAdditionError, _("Payment method not recognized")),
        22: (PaymentAdditionError, _("Isn't possible add more payments since "
                                     "the coupon total value already was "
                                     "reached")),
        23: (DriverError, _("Coupon isn't totalized yet")),
        43: (PrinterError, _("Printer not initialized")),
        45: (PrinterError, _("Printer without serial number")),
        52: (DriverError, _("Invalid start date")),
        53: (DriverError, _("Invalid final date")),
        85: (DriverError, _("Sale with null value")),
        91: (ItemAdditionError, _("Surcharge or discount greater than item "
                                  "value")),
        100: (DriverError, _("Invalid date")),
        115: (CancelItemError, _("Item doesn't exists or already was cancelled")),
        118: (DriverError, _("Surcharge greater than item value")),
        119: (DriverError, _("Discount greater than item value")),
        129: (DriverError, _("Invalid month")),
        169: (CouponTotalizeError, _("Coupon already totalized")),
        170: (PaymentAdditionError, _("Coupon not totalized yet")),
        171: (DriverError, _("Surcharge on subtotal already effected")),
        172: (DriverError, _("Discount on subtotal already effected")),
        176: (DriverError, _("Invalid date"))}

    def __init__(self, *args, **kwargs):
        SerialBase.__init__(self, *args, **kwargs)
        # XXX: Seems that Bematech doesn't contains any variable with the
        # coupon remainder value, so I need to manage it by myself.
        self.remainder_value = Decimal("0.00")
        self.setTimeout(5)
        self.setWriteTimeout(5)
        self._customer_name = None
        self._customer_document = None
        self._customer_address = None

    def _handle_error(self, reply):
        """ Here are some notes about the return codes:

        When using the first/simple protocol, the return code is composed of:

        ACK/NAK + ST1 + ST2

        If set, ST1 contains errors description related to the printer status
        and some basic command errors, like 'package doesn't starts with 0x1B'.
        ST2 contains more descriptive errors, but not enough for us
        (eg: 'cancellation not allowed'). Also ST2 can contains a value that
        represents 'command not executed' and is in this part that ST3 comes.

        With the second protocol, we have:

        ACK/NAK + ST1 + ST2 + STL + STH

        Where STL and STH are used to compose ST3. ST3 has more detailed
        errors and is used when ST2 is set to 1, representing 'command not
        executed'.  In this case we get the value stored on ST3 and search
        for a more descriptive error that will say why the command wasn't
        executed.
        """
        if not reply:
            raise DriverError
        # NAK mens that the request was packaged erroneously or there was
        # a timeout error while sending the data.
        elif reply[0] == NAK:
            raise DriverError
        st1 = ord(reply[1])
        st2 = ord(reply[2])
        nbytes = MP25.CMD_PROTO == 0x1C and 5 or 3

        def check_dict(d, value):
            for key in d.keys():
                if key & value:
                    exc, arg = d[key]
                    raise exc(arg)
        # If st1 is just a warning "printer ALMOST out of paper", we don't
        # can consider raising a exception here.
        if st1 and not (st1 & 64):
            check_dict(MP25.st1_codes, st1)
        elif not st2:
            return reply[nbytes:]
        # If st2 == 1, it means "Command not executed" -- if so, then I
        # will try get a more descriptive error from st3, if the extended
        # protocol is being used.
        if st2 == 1 and MP25.CMD_PROTO == 0x1C:
            st3 = ord(reply[4]) | ord(reply[3])
            try:
                exc, arg = MP25.st3_codes[st3]
                raise exc(arg)
            except KeyError:
                pass
        check_dict(MP25.st2_codes, st2)

    def _make_package(self, raw_data):
        """ Receive a 'pre-package' (command + params, basically) and involves
        it around STX, NBL, NBH, CSL and CSH:

        +-----+-----+-----+-----------------+-----+-----+
        | STX | NBL | NBH | 0x1C + raw_data | CSL | CSH |
        +-----+-----+-----+-----------------+-----+-----+

        Where:

        STX: 'Transmission Start' indicator byte
        NBL: LSB of checksum for raw_data+CSL+CSH
        NBH: MSB of checksum for raw_data+CSL+CSH
        CSL: LSB of checksum for raw_data
        CSH: MSB of checksum for raw_data
        """
        raw_data = chr(MP25.CMD_PROTO) + raw_data
        cs = sum([ord(i) for i in raw_data])
        csl = chr(cs & 0xFF)
        csh = chr(cs >> 8 & 0xFF)
        nb = len(raw_data+csl+csh)
        nbl = chr(nb & 0xFF)
        nbh = chr(nb >> 8 & 0xFF)
        return (chr(STX) + nbl + nbh + raw_data +
                csl + csh)

    def _send_packed(self, command):
        """ Receive a command (and its parameter), pack it and send to the
        printer.
        """
        self.write(self._make_package(command))

    def _get_reply(self, extrabytes_num=0):
        if MP25.CMD_PROTO == 0x1B:
            data = self.read_insist(3 + extrabytes_num)
        elif MP25.CMD_PROTO == 0x1C:
            data = self.read_insist(5 + extrabytes_num)
        else:
            raise TypeError("Invalid protocol used, got %r" % MP25.CMD_PROTO)
        self.debug("<<< %r (%dbytes)" % (data, len(data or '')))
        return data

    def _send_command(self, command):
        self._send_packed(command)
        return self._handle_error(self._get_reply())

    #
    # Helper methods
    #

    def get_coupon_subtotal(self):
        # Return value:
        # ACK/NAK + 7 Bytes (Subtotal in BCD format) + 3/2 Bytes (Status)
        # Where status is composed of ST1 + ST2 + ST3 if the second protocol
        # is used, or ST1 + ST2 if the first one is used instead.
        # See man page #49
        self._send_packed(chr(CMD_COUPON_GET_SUBTOTAL))
        reply = self._get_reply(extrabytes_num=7)
        self._handle_error(reply[0] + reply[8:])
        subtotal = reply[1:8]
        if subtotal:
            return Decimal(str(float(bcd2dec(subtotal)) / 1e2))
        return Decimal("0.0") # XXX: "**** BUSTED SUBTOTAL ****"

    def get_last_item_id(self):
        self._send_packed("%c%c" % (CMD_GET_VARIABLES, VAR_LAST_ITEM_ID))
        reply = self._get_reply(extrabytes_num=2)
        self._handle_error(reply[0] + reply[3:])
        return bcd2dec(reply[1:3])

    def _get_coupon_number(self):
        self._send_packed(chr(CMD_GET_COUPON_NUMBER))
        reply = self._get_reply(extrabytes_num=3)
        self._handle_error(reply[0] + reply[4:])
        coupon_number = reply[1:4]
        if coupon_number:
            return bcd2dec(coupon_number)
        raise ValueError("Inconsistent package received from the printer")


    def _add_voucher(self, type, value):
        value = "%014d" % int(float(value) * 1e2)
        self._send_command(chr(CMD_ADD_VOUCHER) + type + value)

    #
    # This implements the ICouponPrinter Interface
    #

    def summarize(self):
        """ Prints a summary of all sales of the day """
        self._send_command(chr(CMD_READ_X))

    def close_till(self):
        """ Close the till for the day, no other actions can be done after this
        is called.
        """
        self._send_command(chr(CMD_REDUCE_Z))

    def till_add_cash(self, value):
        self._add_voucher(CASH_IN_TYPE, value)

    def till_remove_cash(self, value):
        self._add_voucher(CASH_OUT_TYPE,value)

    def coupon_identify_customer(self, customer, address, document):
        self._customer_name = customer
        self._customer_document = document
        self._customer_address = address

    def coupon_open(self):
        """ This needs to be called before anything else """
        data = chr(CMD_COUPON_OPEN)
        if (self._customer_name or self._customer_address
            or self._customer_document):
            data += ("%-29s%-30s%-80s" % (self._customer_document,
                                          self._customer_name,
                                          self._customer_address))
        self._send_command(data)

    def coupon_cancel(self):
        """ Can only be called when a coupon is opened. It needs to be possible
        to open new coupons after this is called.
        """
        self._send_command(chr(CMD_COUPON_CANCEL))

    def coupon_close(self, message=""):
        """  This can only be called when the coupon is open, has items added,
        payments added and totalized is called. It needs to be possible to open
        new coupons after this is called.
        """
        self._send_command(chr(CMD_COUPON_CLOSE))
        return self._get_coupon_number()

    def coupon_add_item(self, code, quantity, price, unit, description, taxcode,
                        discount, markup, unit_desc=''):
        if unit == UNIT_CUSTOM:
            unit = unit_desc
        else:
            unit = unit_translate_dict[unit]
        data = ("%c"       # command
                "%02s"     # taxcode
                "%09d"     # value
                "%07d"     # quantity
                "%010d"    # discount
                "%010d"    # markup
                "%022d"    # padding
                "%2s"      # unit
                "%-48s\0"  # code
                "%-200s\0" # description
                % (CMD_ADD_ITEM, tax_translate_dict[taxcode],
                   int(float(price) * 1e3), int(float(quantity) * 1e3),
                   (discount and int(float(discount) * 1e2) or 0),
                   (markup and int(float(markup) * 1e2) or 0), 0, unit,
                   code, description))
        self._send_command(data)
        return self.get_last_item_id()

    def coupon_cancel_item(self, item_id=None):
        """ Cancel an item added to coupon; if no item id is specified,
        cancel the last item added. """
        # We would can use an apropriate command to cancel the last
        # item added (command #13, man page 34),  but as we already
        # have an internal counter, I don't think that this is
        # necessary.
        if not item_id:
            item_id = self.get_last_item_id()
        self._send_command("%c%04d" % (CMD_CANCEL_ITEM, item_id))

    def coupon_add_payment(self, payment_method, value, description=''):
        pm = payment_methods[payment_method]
        description = description and description[:80] or ""
        val = "%014d" % int(float(value) * 1e2)
        data = "%c%s%s%s" % (CMD_ADD_PAYMENT, pm, val, description)
        self._send_command(data)
        self.remainder_value -= value
        if self.remainder_value < 0.0:
            self.remainder_value = Decimal("0.0")
        return self.remainder_value

    def coupon_totalize(self, discount, markup, taxcode):
        if discount:
            type = 'D'
            val = '%04d' % int(float(discount) * 1e2)
        elif markup:
            type = 'A'
            val = '%04d' % int(float(markup) * 1e2)
        else:
            # Just to use the StartClosingCoupon in case of no discount/markup
            # be specified.
            type = 'A'
            val = '%04d' % 0
        self._send_command(chr(CMD_COUPON_TOTALIZE) + type + val)
        totalized_value = self.get_coupon_subtotal()
        self.remainder_value = totalized_value
        return totalized_value

    def get_capabilities(self):
        return {
            'item_code': Capability(max_len=13),
            'item_id': Capability(digits=4),
            'items_quantity': Capability(min_size=1, digits=4, decimals=3),
            'item_price': Capability(digits=6, decimals=2),
            'item_description': Capability(max_len=29),
            'payment_value': Capability(digits=12, decimals=2),
            'promotional_message': Capability(max_len=320),
            'payment_description': Capability(max_len=48),
            'customer_name': Capability(max_len=30),
            'customer_id': Capability(max_len=28),
            'customer_address': Capability(max_len=80),
            'add_cash_value': Capability(min_size=0.1, digits=12, decimals=2),
            'remove_cash_value': Capability(min_size=0.1, digits=12, decimals=2),
            }

    #
    # Here ends the implementation of the ICouponPrinter Driver Interface
    #

