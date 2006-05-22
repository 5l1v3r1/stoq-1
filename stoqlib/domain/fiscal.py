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
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
##      Author(s):  Evandro Vale Miquelito
##
##
""" Domain classes to manage fiscal informations.

Note that this whole module is Brazil-specific.
"""

from datetime import datetime

from sqlobject import UnicodeCol, DateTimeCol, ForeignKey, IntCol, SQLObject
from zope.interface import implements

from stoqlib.lib.parameters import sysparam
from stoqlib.domain.base import Domain, BaseSQLView, InheritableModel
from stoqlib.domain.interfaces import IDescribable, IReversal
from stoqlib.domain.columns import PriceCol, AutoIncCol


class CfopData(Domain):
    """A Brazil-specific class wich defines a fiscal code of operations.
    In Brazil it means 'Codigo fiscal de operacoes e prestacoes'
    """
    implements(IDescribable)

    code = UnicodeCol()
    description = UnicodeCol()

    def get_description(self):
        return u"%s %s" % (self.code, self.description)


class AbstractFiscalBookEntry(InheritableModel):
    implements(IReversal)

    identifier = AutoIncCol("stoqlib_abstract_bookentry_seq")
    date = DateTimeCol(default=datetime.now)
    invoice_number = IntCol()
    cfop = ForeignKey("CfopData")
    branch = ForeignKey("PersonAdaptToBranch")
    drawee = ForeignKey("Person")
    payment_group = ForeignKey("AbstractPaymentGroup")

    def reverse_entry(self):
        raise NotImplementedError("This method must be overwrited on child")

    def get_reversal_clone(self, invoice_number, **kwargs):
        conn = self.get_connection()
        cfop = sysparam(conn).DEFAULT_RETURN_SALES_CFOP
        cls = self.__class__
        return cls(connection=conn, cfop=cfop, branch=self.branch,
                   invoice_number=invoice_number, drawee=self.drawee,
                   payment_group=self.payment_group, **kwargs)


class IcmsIpiBookEntry(AbstractFiscalBookEntry):

    icms_value = PriceCol()
    ipi_value = PriceCol()

    def reverse_entry(self, invoice_number):
        icms = -self.icms_value
        ipi = -self.ipi_value
        return self.get_reversal_clone(invoice_number, icms_value=icms,
                                       ipi_value=ipi)

class IssBookEntry(AbstractFiscalBookEntry):

    iss_value = PriceCol()

    def reverse_entry(self, invoice_number):
        iss = -self.iss_value
        return self.get_reversal_clone(invoice_number, iss_value=iss)

#
# Views
#

class AbstractFiscalView(SQLObject, BaseSQLView):
    """Stores general informations about fiscal entries"""

    identifier = IntCol()
    date = DateTimeCol()
    invoice_number = IntCol()
    cfop_code = UnicodeCol()
    cfop_data_id = IntCol()
    drawee_name = UnicodeCol()
    drawee_id = IntCol()
    branch_id = IntCol()
    payment_group_id = IntCol()


class IcmsIpiView(AbstractFiscalView):
    """Stores general informations about ICMS/IPI book entries"""

    icms_value = PriceCol()
    ipi_value = PriceCol()


class IssView(AbstractFiscalView):
    """Stores general informations about ISS book entries"""

    iss_value = PriceCol()
