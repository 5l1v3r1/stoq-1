# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2009 Async Open Source <http://www.async.com.br>
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
## GNU General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s):   George Y. Kussumoto     <george@async.com.br>
##
""" NF-e XML document generation """

import datetime
import math
import os.path
import random
from xml.etree.ElementTree import Element
from xml.sax.saxutils import escape

from stoqdrivers.enum import TaxType

import stoqlib
from stoqlib.domain.interfaces import ICompany, IIndividual
from stoqlib.lib.parameters import sysparam
from stoqlib.enums import NFeDanfeOrientation


from utils import (get_state_code, get_city_code, nfe_tostring,
                   remove_accentuation)

#
# the page numbers refers to the "Manual de integração do contribuinte v3.00"
# and could be found at http://www.nfe.fazenda.gov.br/portal/integracao.aspx
# (brazilian portuguese only).
#

class NFeGenerator(object):
    """NF-e Generator class.
    The NF-e generator is responsible to create a NF-e XML document for a
    given sale.
    """
    def __init__(self, sale, conn):
        self._sale = sale
        self.conn = conn
        self.root = Element('NFe', xmlns='http://www.portalfiscal.inf.br/nfe')

    #
    # Public API
    #

    def generate(self):
        """Generates the NF-e."""
        branch = self._sale.branch
        self._add_identification(branch)
        self._add_issuer(branch)
        self._add_recipient(self._sale.client)
        self._add_sale_items(self._sale.get_items())
        self._add_totals()
        self._add_transport_data(self._sale.transporter,
                                 self._sale.get_items())
        self._add_billing_data()
        self._add_additional_information()

    def save(self, location=''):
        """Saves the NF-e.
        @param location: the path to save the NF-e.
        """
        # a string like: NFe35090803852995000107550000000000018859747268
        data_id = self._nfe_data.get_id_value()
        # ignore the NFe prefix
        name = "%s-nfe.xml" % data_id[3:]
        filename = os.path.join(location, name)
        fp = open(filename, 'w')
        fp.write(nfe_tostring(self.root))
        fp.close()

    def export_txt(self, location=''):
        """Exports the NF-e in a text format that can used to import the NF-e
        by the current NF-e management software provided by the government.
        More information: http://www.emissornfehom.fazenda.sp.gov.br/.

        @param location: the patch to save the NF-e in text format.
        """
        # a string like: NFe35090803852995000107550000000000018859747268
        data_id = self._nfe_data.get_id_value()
        # ignore the NFe prefix
        name = "%s-nfe.txt" % data_id[3:]
        filename = os.path.join(location, name)
        fp = open(filename, 'w')
        # we need to remove the accentuation to avoid import errors from
        # external applications.
        fp.write(remove_accentuation(self._as_txt()))
        fp.close()

    #
    # Private API
    #

    def __str__(self):
        return nfe_tostring(self.root)

    def _as_txt(self):
        nfe =  [u'NOTA FISCAL|1|\n',
               self._nfe_data.as_txt(),]
        return u''.join(nfe)

    def _calculate_verifier_digit(self, key):
        # Calculates the verifier digit. The verifier digit is used to
        # validate the NF-e key, details in page 72 of the manual.
        assert len(key) == 43

        weights = [2, 3, 4, 5, 6, 7, 8, 9]
        weights_size = len(weights)
        key_numbers = [int(k) for k in key]
        key_numbers.reverse()

        key_sum = 0
        for i, key_number in enumerate(key_numbers):
            # cycle though weights
            i = i % weights_size
            key_sum += key_number * weights[i]

        remainder = key_sum % 11
        if remainder == 0 or remainder == 1:
            return '0'
        return str(11 - remainder)

    def _get_cnpj(self, person):
        company = ICompany(person, None)
        assert company is not None
        #FIXME: fix get_cnpj_number method (fails if start with zero).
        cnpj = ''.join([c for c in company.cnpj if c in '1234567890'])
        assert len(cnpj) == 14
        return cnpj

    def _get_address_data(self, person):
        """Returns a tuple in the following format:
        (street, streetnumber, complement, district, city, state, postal_code,
         phone_number)
        """
        address = person.get_main_address()
        postal_code = ''.join([i for i in address.postal_code if i in '1234567890'])
        location = address.city_location
        return (address.street, address.streetnumber, address.complement,
                address.district, location.city, location.state,
                postal_code, person.get_phone_number_number())

    def _add_identification(self, branch):
        # Pg. 71
        branch_location = branch.person.get_main_address().city_location
        cuf = str(get_state_code(branch_location.state) or '')

        today = datetime.date.today()
        aamm = today.strftime('%y%m')

        nnf = self._sale.invoice_number
        assert nnf

        payments = self._sale.group.get_items()
        series = sysparam(self.conn).NFE_SERIAL_NUMBER
        orientation = sysparam(self.conn).NFE_DANFE_ORIENTATION

        nfe_identification = NFeIdentification(cuf, branch_location.city,
                                               series, nnf, today,
                                               list(payments), orientation)
        # The nfe-key requires all the "zeros", so we should format the
        # values properly.
        mod = '%02d' % int(nfe_identification.get_attr('mod'))
        serie = '%03d' % int(nfe_identification.get_attr('serie'))
        cnf = '%09d' % nfe_identification.get_attr('cNF')
        nnf_str = '%09d' % nnf
        cnpj = self._get_cnpj(branch)
        # Key format (Pg. 71):
        # cUF + AAMM + CNPJ + mod + serie + nNF + cNF + (cDV)
        key = cuf + aamm + cnpj + mod + serie + nnf_str + cnf
        cdv = self._calculate_verifier_digit(key)
        key += cdv

        nfe_identification.set_attr('cDV', cdv)
        self._nfe_identification = nfe_identification

        self._nfe_data = NFeData(key)
        self._nfe_data.append(nfe_identification)
        self.root.append(self._nfe_data.element)

    def _add_issuer(self, issuer):
        cnpj = self._get_cnpj(issuer)
        person = issuer.person
        name = person.name
        company = ICompany(issuer, None)
        state_registry = company.state_registry
        self._nfe_issuer = NFeIssuer(name, cnpj=cnpj,
                                     state_registry=state_registry)
        self._nfe_issuer.set_address(*self._get_address_data(person))
        self._nfe_data.append(self._nfe_issuer)

    def _add_recipient(self, recipient):
        person = recipient.person
        name = person.name
        individual = IIndividual(person, None)
        if individual is not None:
            cpf = ''.join([c for c in individual.cpf if c in '1234567890'])
            self._nfe_recipient = NFeRecipient(name, cpf=cpf)
        else:
            cnpj = self._get_cnpj(recipient)
            company = ICompany(person, None)
            state_registry = company.state_registry
            self._nfe_recipient = NFeRecipient(name, cnpj=cnpj,
                                               state_registry=state_registry)

        self._nfe_recipient.set_address(*self._get_address_data(person))
        self._nfe_data.append(self._nfe_recipient)

    def _add_sale_items(self, sale_items):
        # cfop code without dot.
        cfop_code = self._sale.cfop.code.replace('.', '')

        for item_number, sale_item in enumerate(sale_items):
            # item_number should start from 1, not zero.
            item_number += 1
            nfe_item = NFeProduct(item_number)

            sellable = sale_item.sellable
            product = sellable.product
            if product:
                ncm = product.ncm
                ex_tipi = product.ex_tipi
                genero = product.genero
            else:
                ncm = ''
                ex_tipi = ''
                genero = ''

            nfe_item.add_product_details(sellable.code,
                                         sellable.get_description(),
                                         cfop_code,
                                         sale_item.quantity,
                                         sale_item.price,
                                         sellable.get_unit_description(),
                                         barcode=sellable.barcode,
                                         ncm=ncm,
                                         ex_tipi=ex_tipi,
                                         genero=genero)

            nfe_item.add_tax_details(sellable.get_tax_constant())
            self._nfe_data.append(nfe_item)

    def _add_totals(self):
        sale_total = self._sale.get_total_sale_amount()
        items_total = self._sale.get_sale_subtotal()
        nfe_total = NFeTotal()
        nfe_total.add_icms_total(sale_total, items_total)
        self._nfe_data.append(nfe_total)

    def _add_transport_data(self, transporter, sale_items):
        nfe_transport = NFeTransport()
        self._nfe_data.append(nfe_transport)
        if transporter:
            nfe_transporter = NFeTransporter(transporter)
            self._nfe_data.append(nfe_transporter)

        for item_number, sale_item in enumerate(sale_items):
            sellable = sale_item.sellable
            product = sellable.product
            if not product:
                continue

            unitary_weight = product.weight
            if not unitary_weight:
                continue

            unit = sellable.unit and sellable.unit.get_description() or ''
            weight = sale_item.quantity * unitary_weight
            vol = NFeVolume(quantity=sale_item.quantity, unit=unit,
                            net_weight=weight, gross_weight=weight)
            self._nfe_data.append(vol)

    def _add_billing_data(self):
        cob = NFeBilling()
        self._nfe_data.append(cob)

        sale_total = self._sale.get_total_sale_amount()
        items_total = self._sale.get_sale_subtotal()

        fat = NFeInvoice(self._sale.id, items_total,
                         self._sale.discount_value, sale_total)
        self._nfe_data.append(fat)

        payments = self._sale.group.get_items()
        for p in payments:
            dup = NFeDuplicata(p.id, p.due_date, p.value)
            self._nfe_data.append(dup)

    def _add_additional_information(self):
        nfe_info = NFeSimplesNacionalInfo(self._sale.notes)
        self._nfe_data.append(nfe_info)

#
# NF-e XML Groups
#

class BaseNFeXMLGroup(object):
    """Base XML group class.
    A XML group is a helper interface to xml.etree.Element hierarchy of
    several elements. Example:
    <root>
        <child1>default</child1>
    </root>

    @cvar tag: the root element of the hierarchy.
    @cvar txttag: the root element of the hierarchy used in the text format,
                  mainly used to export the NF-e.
    @cvar attributes: a list of tuples containing the child name and the
                      default value.
    """
    tag = u''
    txttag = u''
    attributes = []

    def __init__(self):
        self._element = None
        self._data = dict(self.attributes)
        self._children = []

    #
    # Properties
    #

    @property
    def element(self):
        if self._element is not None:
            return self._element

        self._element = Element(self.tag)
        for key, value in self.attributes:
            element_value = self._data[key] or value
            # ignore empty values
            if element_value is None:
                continue

            sub_element = Element(key)
            sub_element.text = self.escape(str(element_value))
            self._element.append(sub_element)

        return self._element

    #
    # Public API
    #

    def append(self, element):
        self._children.append(element)
        self.element.append(element.element)

    def get_children(self):
        return self._children

    def get_attr(self, attr):
        return self._data[attr]

    def set_attr(self, attr, value):
        self._data[attr] = value

    def format_date(self, date):
        # Pg. 93 (and others)
        return date.strftime('%Y-%m-%d')

    def format_value(self, value, precision=2):
        return '%.*f' % (precision, value)

    def escape(self, string):
        # Pg. 71
        return escape(string)

    def as_txt(self):
        """Returns the group as text, in the format expected to be accepted by
        the importer of the current NF-e management software provided by the
        government.
        If the element do not a txttag attribute value, it will be ignored.
        Subclasses should might override this method to handle more complex
        outputs.
        @returns: a string with the element in text format.
        """
        if not self.txttag:
            return ''

        txt = '%s|' % self.txttag
        for attr, default in self.attributes:
            # use the current value, not the default.
            value = self.get_attr(attr)
            txt += '%s|' % value
        return txt + '\n'

    def __str__(self):
        return nfe_tostring(self.element)


# Pg. 92
class NFeData(BaseNFeXMLGroup):
    """
    - Attributes:

        - versao: Versao do leiaute.
        - Id: Chave de acesso da NF-e precedida do literal 'NFe'.
    """
    tag = 'infNFe'
    txttag = 'A'

    def __init__(self, key):
        BaseNFeXMLGroup.__init__(self)
        self.element.set('xmlns', 'http://www.portalfiscal.inf.br/nfe')
        self.element.set('versao', u'1.10')

        # Pg. 92
        assert len(key) == 44

        value = u'NFe%s' % key
        self.element.set('Id', value)

    def get_id_value(self):
        return self.element.get('Id')

    def as_txt(self):
        txt = u'%s|%s|%s|\n' % (self.txttag, self.element.get('versao'),
                                self.get_id_value())
        children = self.get_children()
        for child in self.get_children():
            txt += child.as_txt()

        return txt


# Pg. 92
class NFeIdentification(BaseNFeXMLGroup):
    """
    - Attributes:

        - cUF: Código da UF do emitente do Documento Fiscal. Utilizar a Tabela
               do IBGE de código de unidades da federação.

        - cNF: Código numérico que compõe a Chave de Acesso. Número aleatório
               gerado pelo emitente para cada NF-e para evitar acessos
               indevidos da NF-e.

        - natOp: Natureza da operação

        - indPag: 0 - Pagamento a vista (default)
                  1 - Pagamento a prazo
                  2 - outros

        - mod: Utilizar código 55 para identificação de NF-e emitida em
               substituição ao modelo 1 ou 1A.

        - serie: Série do Documento Fiscal, informar 0 (zero) para série
                 única.

        - nNF: Número do documento fiscal.

        - dEmi: Data de emissão do documento fiscal.

        - tpNF: Tipo de documento fiscal.
                0 - entrada
                1 - saída (default)

        - cMunFG: Código do município de ocorrência do fato gerador.

        - tpImp: Formato de impressão do DANFE.
                 1 - Retrato
                 2 - Paisagem (default)

        - tpEmis: Forma de emissão da NF-e
                  1 - Normal (default)
                  2 - Contingência FS
                  3 - Contingência SCAN
                  4 - Contingência DPEC
                  5 - Contingência FS-DA

        - cDV: Dígito verificador da chave de acesso da NF-e.

        - tpAmb: Identificação do ambiente.
                 1 - Produção
                 2 - Homologação

        - finNFe: Finalidade de emissão da NF-e.
                  1 - NF-e normal (default)
                  2 - NF-e complementar
                  3 - NF-e de ajuste

        - procEmi: Identificador do processo de emissão da NF-e.
                   0 - emissãp da NF-e com aplicativo do contribuinte
                   1 - NF-e avulsa pelo fisco
                   2 - NF-e avulsa pelo contribuinte com certificado através
                       do fisco
                   3 - NF-e pelo contribuinte com aplicativo do fisco.
                       (default).

        - verProc: Identificador da versão do processo de emissão (versão do
                   aplicativo emissor de NF-e)
    """
    tag = u'ide'
    attributes = [(u'cUF', ''),
                  (u'cNF', ''),
                  (u'natOp', 'venda'),
                  (u'indPag', '0'),
                  (u'mod', '55'),
                  (u'serie', '0'),
                  (u'nNF', ''),
                  (u'dEmi', ''),
                  (u'dSaiEnt', ''),
                  (u'tpNF', '1'),
                  (u'cMunFG', ''),
                  (u'tpImp', '2'),
                  (u'tpEmis', '1'),
                  (u'cDV', ''),
                  #TODO: Change tpAmb=1 in the final version.
                  (u'tpAmb', '1'),
                  (u'finNFe', '1'),
                  (u'procEmi', '3'),
                  (u'verProc', '')]
    txttag = 'B'
    danfe_orientation = {
        NFeDanfeOrientation.PORTRAIT: '1',
        NFeDanfeOrientation.LANDSCAPE: '2',
    }

    def __init__(self, cUF, city, series, nnf, emission_date, payments,
                 orientation):
        BaseNFeXMLGroup.__init__(self)

        self.set_attr('cUF', cUF)
        # Pg. 92: Random number of 9-digits
        self.set_attr('cNF', random.randint(100000000, 999999999))

        payment_type = 1
        installments = len(payments)
        if installments == 1:
            payment = payments[0]
            if payment.paid_date == datetime.datetime.today():
                payment_type = 0
        self.set_attr('indPag', payment_type)

        self.set_attr('nNF', nnf)
        self.set_attr('serie', series)
        self.set_attr('dEmi', self.format_date(emission_date))
        self.set_attr('cMunFG', get_city_code(city, code=cUF) or '')
        self.set_attr('tpImp', self.danfe_orientation[orientation])


class NFeAddress(BaseNFeXMLGroup):
    """
    - Attributes:
        - xLgr: logradouro.
        - nro: número.
        - XCpl: complemento
        - xBairro: bairro.
        - cMun: código do município.
        - xMun: nome do município.
        - UF: sigla da UF. Informar EX para operações com o exterior.
        - CEP: código postal.
        - CPais: código do país.
        - XPais: nome do país.
        - Fone: número do telefone.
    """
    attributes = [(u'xLgr', ''),
                  (u'nro', ''),
                  (u'XCpl', ''),
                  (u'xBairro', ''),
                  (u'cMun', ''),
                  (u'xMun', ''),
                  (u'UF', ''),
                  (u'CEP',''),
                  (u'CPais', '1058'),
                  (u'XPais', 'BRASIL'),
                  (u'Fone', ''),]

    def __init__(self, tag, street, number, complement, district, city, state,
                 postal_code='', phone_number=''):
        self.tag = tag
        BaseNFeXMLGroup.__init__(self)
        self.set_attr('xLgr', street)
        self.set_attr('nro', number or '')
        self.set_attr('xCpl', complement)
        self.set_attr('xBairro', district)
        self.set_attr('xMun', city)
        self.set_attr('cMun', str(get_city_code(city, state) or ''))
        self.set_attr('UF', state)
        self.set_attr('CEP', postal_code)
        self.set_attr('Fone', phone_number)


# Pg. 96
class NFeIssuer(BaseNFeXMLGroup):
    """
    - Attributes:
        - CNPJ: CNPJ do emitente.
        - xNome: Razão social ou nome do emitente
        - IE: inscrição estadual
    """
    tag = u'emit'
    address_tag = u'enderEmit'
    attributes = [(u'CNPJ', None),
                  (u'CPF', None),
                  (u'xNome', ''),]
    txttag = 'C'
    address_txt_tag = 'C05'
    doc_cnpj_tag = 'C02'
    doc_cpf_tag = 'C02a'

    def __init__(self, name, cpf=None, cnpj=None, state_registry=None):
        BaseNFeXMLGroup.__init__(self)
        if cnpj is not None:
            self.set_attr('CNPJ', cnpj)
        else:
            self.set_attr('CPF', cpf)

        self.set_attr('xNome', name)
        self._ie = state_registry

    def set_address(self, street, number, complement, district, city, state,
                    postal_code='', phone_number=''):
        self._address = NFeAddress(
            self.address_tag, street, number, complement, district, city,
            state, postal_code, phone_number)
        self._address.txttag = self.address_txt_tag
        self.append(self._address)
        # If we set IE in the __init__, the order will not be correct. :(
        ie_element = Element(u'IE')
        ie_element.text = self._ie
        self.element.append(ie_element)

    def get_doc_txt(self):
        doc_value = self.get_attr('CNPJ')
        if doc_value:
            doc_tag = self.doc_cnpj_tag
        else:
            doc_tag = self.doc_cpf_tag
            doc_value = self.get_attr('CPF')
        return '%s|%s|\n' % (doc_tag, doc_value,)

    def as_txt(self):
        if self.get_attr('CNPJ'):
            ie = self._ie or 'ISENTO'
        else:
            ie = ''
        base = '%s|%s||%s|||\n' % (self.txttag, self.get_attr('xNome'), ie,)
        return base + self.get_doc_txt() + self._address.as_txt()


# Pg. 99
class NFeRecipient(NFeIssuer):
    tag = 'dest'
    address_tag = u'enderDest'
    txttag = 'E'
    address_txt_tag = 'E05'
    doc_cnpj_tag = 'E02'
    doc_cpf_tag = 'E03'

    def as_txt(self):
        if self.get_attr('CNPJ'):
            ie = self._ie or 'ISENTO'
        else:
            ie = ''
        base = '%s|%s|%s|\n' % (self.txttag, self.get_attr('xNome'), ie)
        return base + self.get_doc_txt() + self._address.as_txt()

# Pg. 102
class NFeProduct(BaseNFeXMLGroup):
    """
    - Attributes:
        - nItem: número do item
    """
    tag = u'det'
    txttag = 'H'

    def __init__(self, number):
        BaseNFeXMLGroup.__init__(self)
        # "nItem" is part of "det", not a regular attribute. So we need to
        # ensure it is a string.
        self.element.set('nItem', str(number))

    def add_product_details(self, code, description, cfop, quantity, price,
                            unit, barcode, ncm, ex_tipi, genero):
        details = NFeProductDetails(code, description, cfop, quantity, price,
                                    unit, barcode, ncm, ex_tipi, genero)
        self.append(details)

    def add_tax_details(self, sellable_tax):
        nfe_tax = NFeTax()
        nfe_icms = NFeICMS()
        nfe_pis = NFePIS()
        nfe_cofins = NFeCOFINS()

        # Vamos ignorar o TaxType enquanto não temos um bom suporte para todos
        # eles (em especial, Substituição Tributária). Nesse meio tempo, é
        # possível que o usuário faça o acerto dos impostos através do
        # aplicativo emissor da receita como um workaround para essa
        # limitação.

        tax_type = sellable_tax.tax_type
        #if tax_type in [TaxType.EXEMPTION, TaxType.NONE]:

        # Não tributado ou Isento/ICMS. Atualmente, apenas consideramos
        # que a empresa esteja enquadrada no simples nacional.
        icms = NFeICMS40(tax_type)
        nfe_icms.append(icms)
        pis = NFePISOutr()
        nfe_pis.append(pis)
        cofins = NFeCOFINSOutr()
        nfe_cofins.append(cofins)

        # TODO: handle service tax (ISS) and ICMS.

        nfe_tax.append(nfe_icms)
        nfe_tax.append(nfe_pis)
        nfe_tax.append(nfe_cofins)
        self.append(nfe_tax)

    def as_txt(self):
        base = '%s|%s||\n' % (self.txttag, self.element.get('nItem'),)
        details, tax = self.get_children()
        tax_txt = 'M|\nN|\n%s' % tax.as_txt()
        return base + details.as_txt() + tax_txt


# Pg. 102
class NFeProductDetails(BaseNFeXMLGroup):
    """
    - Attributes:
        - cProd: Código do produto ou serviço. Preencher com CFOP caso se
                 trate de itens não relacionados com mercadorias/produtos e
                 que o contribuinte não possua codificação própria.

        - cEAN: GTIN (Global Trade Item Number) do produto, antigo código EAN
                ou código de barras.

        - xProd: Descrição do produto ou serviço.

        - NCM: Código NCM. Preencher de acordo com a tabela de capítulos da
                NCM. EM caso de serviço, não incluir a tag.

        - CFOP: Código fiscal de operações e prestações. Serviço, não incluir
                a tag.

        - uCom: Unidade comercial. Informar a unidade de comercialização do
                produto.

        - qCom: Quantidade comercial. Informar a quantidade de comercialização
                do produto.

        - vUnCom: Valor unitário de comercialização. Informar o valor unitário
                  de comercialização do produto.

        - vProd: Valor total bruto dos produtos ou serviços.

        - cEANTrib: GTIN da unidade tributável, antigo código EAN ou código de
                    barras.

        - uTrib: Unidade tributável.

        - qTrib: Quantidade tributável.

        - vUnTrib: Valor unitário de tributação.
    """
    tag = u'prod'
    attributes = [(u'cProd', ''),
                  (u'cEAN', ''),
                  (u'xProd', ''),
                  (u'NCM', ''),
                  (u'EXTIPI', ''),
                  (u'genero', ''),
                  (u'CFOP', ''),
                  (u'uCom', u'un'),
                  (u'qCom', ''),
                  (u'vUnCom', ''),
                  (u'vProd', ''),
                  (u'cEANTrib', ''),
                  (u'uTrib', u'un'),
                  (u'qTrib', ''),
                  (u'vUnTrib', '')]
    txttag = 'I'

    def __init__(self, code, description, cfop, quantity, price, unit,
                 barcode, ncm, ex_tipi, genero):
        BaseNFeXMLGroup.__init__(self)
        self.set_attr('cProd', code)

        if barcode and len(barcode) in (8, 12, 13, 14):
            self.set_attr('cEAN', barcode)

        self.set_attr('xProd', description)
        self.set_attr('NCM', ncm or '')
        self.set_attr('EXTIPI', ex_tipi or '')
        self.set_attr('genero', genero or '')

        self.set_attr('CFOP', cfop)
        self.set_attr('vUnCom', self.format_value(price, precision=4))
        self.set_attr('vUnTrib', self.format_value(price, precision=4))
        self.set_attr('vProd', self.format_value(quantity * price))
        self.set_attr('qCom', self.format_value(quantity, precision=4))
        self.set_attr('qTrib', self.format_value(quantity, precision=4))
        self.set_attr('uTrib', unit)
        self.set_attr('uCom', unit)

    def as_txt(self):
        vs = [self.txttag]
        for attr, value in self.attributes:
            vs.append(self.get_attr(attr))

        return '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s||||\n' % tuple(vs)


# Pg. 107
class NFeTax(BaseNFeXMLGroup):
    tag = 'imposto'
    taxtag = 'M|\nN|\n'

    def as_txt(self):
        base = '%s' % self.txttag
        for i in self.get_children():
            base += i.as_txt()
        return base


# Pg. 107
class NFeICMS(BaseNFeXMLGroup):
    tag = 'ICMS'

    def as_txt(self):
        icms = self.get_children()[0]
        return icms.as_txt()


# Pg. 108
class NFeICMS00(BaseNFeXMLGroup):
    """Tributada integralmente (CST=00).

    - Attributes:

        - orig: Origem da mercadoria.
                0 – Nacional
                1 – Estrangeira – Importação direta
                2 – Estrangeira – Adquirida no mercado interno

        - CST: Tributação do ICMS - 00 Tributada integralmente.

        - modBC: Modalidade de determinação da BC do ICMS.
                 0 - Margem Valor Agregado (%) (default)
                 1 - Pauta (Valor)
                 2 - Preço Tabelado Máx. (valor)
                 3 - Valor da operação

        - vBC: Valor da BC do ICMS.

        - pICMS: Alíquota do imposto.

        - vICMS: Valor do ICMS
    """
    tag = 'ICMS00'
    attributes = [(u'orig', '0'),
                  (u'CST', '00'),
                  (u'modBC', None),
                  (u'vBC', None),
                  (u'pICMS', None),
                  (u'vICMS', None),]


# Pg. 108
class NFeICMS10(NFeICMS00):
    """Tributada com cobrança do ICMS por substituição tributária (CST=10).
    - Attributes:

        - modBCST: Modalidade de determinação da BC do ICMS ST.
                   0 - Preço tabelado ou máximo sugerido
                   1 - Lista negativa (valor)
                   2 - Lista positiva (valor)
                   3 - Lista neutra (valor)
                   4 - Margem valor agregado (%)
                   5 - Pauta (valor)

        - pMVAST: Percentual da margem de valor adicionado do ICMS ST.

        - pRedBCST: Percentual da redução de BC do ICMS ST.

        - vBCST: Valor da BC do ICMS ST.

        - pICMSST: Alíquota do imposto do ICMS ST.

        - vICMSST: Valor do ICMS ST.
    """
    tag = 'ICMS10'
    attributes = NFeICMS00.attributes
    attributes.extend([(u'modBCST', ''),
                       (u'pMVAST', ''),
                       (u'pRedBCST', ''),
                       (u'vBCST', ''),
                       (u'pICMSST', ''),
                       (u'vICMSST', '',)])


# Pg. 108
class NFeICMS20(NFeICMS00):
    """Tributada com redução de base de cálculo (CST=20).

    - Attributes:
        - pRedBC: Percentual de Redução de BC.
    """
    tag = 'ICMS20'
    attributes = NFeICMS00.attributes
    attributes.append(('pRedBC', ''))


# Pg. 109
class NFeICMS30(NFeICMS10):
    """Isenta ou não tributada e com cobrança do ICMS por substituição
    tributária (CST=30).
    """
    tag = 'ICMS30'
    attributes = NFeICMS00.attributes


# Pg. 111
class NFeICMS40(BaseNFeXMLGroup):
    """Isenta (CST=40), Não tributada (CST=41), Suspensão (CST=50).
    """
    tag = 'ICMS40'
    attributes = [('orig', ''), (u'CST', 40)]
    txttag = 'N06'

    def __init__(self, tax_type):
        BaseNFeXMLGroup.__init__(self)

        if tax_type == TaxType.EXEMPTION:
            cst = 40
        else:
            cst = 41

        self.set_attr('CST', cst)
        self.set_attr('orig', '0')


# Pg. 117
class NFePIS(BaseNFeXMLGroup):
    tag = u'PIS'
    txttag = 'Q'

    def as_txt(self):
        base = '%s|\n' % (self.txttag)
        pis = self.get_children()[0]
        return base + pis.as_txt()


# Pg. 117, 118
class NFePISAliq(BaseNFeXMLGroup):
    """
    - Attributes:
        - CST: Código de Situação tributária do PIS.
               01 - operação tributável (base de cáculo - valor da operação
               normal (cumulativo/não cumulativo))
               02 - operação tributável (base de cálculo = valor da operação
               (alíquota diferenciada))

        - vBC: Valor da base de cálculo do PIS.

        - pPIS: Alíquota do PIS (em percentual).

        - vPIS: Valor do PIS.
    """
    tag = u'PISAliq'
    attributes = [(u'CST', ''),
                  (u'vBC', '0'),
                  (u'pPIS', '0'),
                  (u'vPIS', '0')]


# Pg. 118
class NFePISOutr(NFePISAliq):
    """
    - Attributes:
        - CST: Código da situação tributária do PIS.
            99 - Operação tributável (tributação monofásica (alíquota zero))
    """
    tag = u'PISOutr'
    attributes = NFePISAliq.attributes
    txttag = 'Q05'

    def __init__(self):
        NFePISAliq.__init__(self)
        self.set_attr('CST', '99')

    def as_txt(self):
        base = '%s|%s|%s|\n' % (self.txttag, self.get_attr('CST'),
                                self.get_attr('vPIS'))
        q = '%s|%s|%s|\n' % ('Q07', self.get_attr('vBC'), self.get_attr('pPIS'))
        return base + q

# Pg. 120, 121
class NFeCOFINS(BaseNFeXMLGroup):
    tag = u'COFINS'
    txttag = 'S'

    def as_txt(self):
        base = '%s|\n' % self.txttag
        cofins = self.get_children()[0]
        return base + cofins.as_txt()


# Pg. 121
class NFeCOFINSAliq(BaseNFeXMLGroup):
    """
    - Attributes:
        - CST: Código de situação tributária do COFINS.
               01 - Operação tributável (base de cálculo = valor da operação
               alíquota normal (cumulativo/não cumulativo).

               02 - Operação tributável (base de cálculo = valor da operação
               (alíquota diferenciada)).

        - vBC: Valor da base do cálculo da COFINS.
        - pCOFINS: Alíquota do COFINS (em percentual).
        - vCOFINS: Valor do COFINS.
    """
    tag = u'COFINSAliq'
    attributes = [(u'CST', ''),
                  (u'vBC', '0'),
                  (u'pCOFINS', '0'),
                  (u'vCOFINS', '0')]


# Pg. 121
class NFeCOFINSOutr(NFeCOFINSAliq):
    """
    - Attributes:
        - CST: Código da situação tributária do COFINS.
            99 - Outras operações
    """
    tag = u'COFINSOutr'
    attributes = NFeCOFINSAliq.attributes
    txttag = 'S05'

    def __init__(self):
        NFeCOFINSAliq.__init__(self)
        self.set_attr('CST', '99')

    def as_txt(self):
        base = '%s|%s|%s|\n' % (self.txttag, self.get_attr('CST'),
                                self.get_attr('vCOFINS'))
        s = '%s|%s|%s|\n' % ('S07', self.get_attr('vBC'),
                             self.get_attr('pCOFINS'))
        return base + s


# Pg. 123
class NFeTotal(BaseNFeXMLGroup):
    tag = u'total'
    txttag = 'W'

    def add_icms_total(self, sale_total, items_total):
        icms_total = NFeICMSTotal(sale_total, items_total)
        self.append(icms_total)

    def as_txt(self):
        base = '%s|\n' % self.txttag
        total = self.get_children()[0]
        return base + total.as_txt()


# Pg. 123
class NFeICMSTotal(BaseNFeXMLGroup):
    """
    - Attributes:
        - vBC: Base de Cálculo do ICMS.
        - vICMS: Valor Total do ICMS.
        - vBCST: Base de Cálculo do ICMS ST.
        - vST: Valor Total do ICMS ST.
        - vProd    Valor Total dos produtos e serviços.
        - vFrete: Valor Total do Frete.
        - vSeg: Valor Total do Seguro.
        - vDesc: Valor Total do Desconto.
        - vII Valor Total do II.
        - vIPI: Valor Total do IPI.
        - vPIS: Valor do PIS.
        - vCOFINS Valor do COFINS.
        - vOutro: Outras Despesas acessórias.
        - vNF: Valor Total da NF-e.
    """
    tag = u'ICMSTot'
    attributes = [(u'vBC', ''),
                  (u'vICMS', '0.00'),
                  (u'vBCST', '0'),
                  (u'vST', '0'),
                  (u'vProd', ''),
                  (u'vFrete', '0'),
                  (u'vSeg', '0'),
                  (u'vDesc', '0'),
                  (u'vII', '0'),
                  (u'vIPI', '0'),
                  (u'vPIS', '0'),
                  (u'vCOFINS', '0'),
                  (u'vOutro', '0'),
                  (u'vNF', ''),]
    txttag = 'W02'

    def __init__(self, sale_total, items_total):
        BaseNFeXMLGroup.__init__(self)
        self.set_attr('vBC', self.format_value(sale_total))
        self.set_attr('vNF', self.format_value(sale_total))
        self.set_attr('vProd', self.format_value(items_total))
        discount = items_total - sale_total
        if discount > 0:
            self.set_attr('vDesc', self.format_value(discount))


# Pg. 124
class NFeTransport(BaseNFeXMLGroup):
    """
    - Attributes:
        - modFrete: Modalidade do frete.
                    0 - por conta do emitente
                    1 - por conta do destinatário (default)
    """
    tag = u'transp'
    attributes = [('modFrete', '1'),]
    txttag = 'X'


# Pg. 124 (optional)
class NFeTransporter(BaseNFeXMLGroup):
    """
    - Attributes:
        - CNPJ: Informar o CNPJ ou o CPF do transportador.
        - CPF: Informar o CNPJ ou o CPF do transportador.
        - xNome: Razão social ou nome.
        - IE: Inscrição estadual.
        - xEnder: Endereço completo.
        - xMun: Nome do município.
        - UF: Sigla da UF.
    """
    tag = u'transporta'
    txttag = 'X03'
    doc_cnpj_tag = 'X04'
    doc_cpf_tag = 'X05'

    attributes = [(u'CNPJ', None),
                  (u'CPF', None),
                  (u'xNome', ''),
                  (u'IE', ''),
                  (u'xEnder', ''),
                  (u'xMun', ''),
                  (u'UF', ''),]

    def __init__(self, transporter):
        BaseNFeXMLGroup.__init__(self)
        person = transporter.person
        name = person.name
        self.set_attr('xNome', name)

        individual = IIndividual(person, None)
        if individual is not None:
            cpf = ''.join([c for c in individual.cpf if c in '1234567890'])
            self.set_attr('CPF', cpf)
        else:
            company = ICompany(person)
            cnpj = ''.join([c for c in company.cnpj if c in '1234567890'])
            self.set_attr('CNPJ', cnpj)
            self.set_attr('IE', company.state_registry)

        address = person.get_main_address()
        if address:
            postal_code = ''.join([i for i in address.postal_code if i in '1234567890'])
            self.set_attr('xEnder', address.get_address_string()[:60])
            self.set_attr('xMun', address.city_location.city[:60])
            self.set_attr('UF', address.city_location.state)

    def get_doc_txt(self):
        doc_value = self.get_attr('CNPJ')
        if doc_value:
            doc_tag = self.doc_cnpj_tag
        else:
            doc_tag = self.doc_cpf_tag
            doc_value = self.get_attr('CPF')
        return '%s|%s|\n' % (doc_tag, doc_value or '',)

    def as_txt(self):
        base_txt = "%s|%s|%s|%s|%s|%s\n" % (self.txttag,
                                            self.get_attr('xNome') or '',
                                            self.get_attr('IE') or '',
                                            self.get_attr('xEnder') or '',
                                            self.get_attr('UF') or '',
                                            self.get_attr('xMun') or '',)
        doc_txt = self.get_doc_txt()

        return base_txt + doc_txt


class NFeVolume(BaseNFeXMLGroup):
    """
    - Attributes:
        - nItem: número do item
    """
    tag = u'vol'
    txttag = 'X26'

    attributes = [(u'qVol', ''),
                  (u'esp', ''),
                  (u'marca', ''),
                  (u'nVol', ''),
                  (u'pesoL', ''),
                  (u'pesoB', ''),]

    def __init__(self, quantity=0, unit='', brand='', number='',
                 net_weight=0.0, gross_weight=0.0):
        BaseNFeXMLGroup.__init__(self)
        # XXX: the documentation doesn't really say what quantity is all
        # about...
        if quantity:
            self.set_attr('qVol', int(math.ceil(quantity)))
        self.set_attr('esp', unit)
        self.set_attr('marca', brand)
        self.set_attr('nVol', number)
        if net_weight:
            self.set_attr('pesoL', "%.3f" % net_weight)
        if gross_weight:
            self.set_attr('pesoB', "%.3f" % gross_weight)


# Pg. 126 - Cobranca
class NFeBilling(BaseNFeXMLGroup):
    """
    """
    tag = u'cobr'
    txttag = 'Y'


# Fatura
class NFeInvoice(BaseNFeXMLGroup):
    """
    """
    tag = u'fat'
    txttag = 'Y02'

    attributes = [(u'nFat', ''),
                  (u'vOrig', ''),
                  (u'vDesc', ''),
                  (u'vLiq', ''),]

    def __init__(self, number, original_value, discount, liquid_value):
        BaseNFeXMLGroup.__init__(self)

        if discount:
            discount = self.format_value(discount)
        else:
            discount = ''

        self.set_attr('nFat', number)
        self.set_attr('vOrig', self.format_value(original_value))
        self.set_attr('vDesc', discount)
        self.set_attr('vLiq', self.format_value(liquid_value))


class NFeDuplicata(BaseNFeXMLGroup):
    """
    """
    tag = u'dup'
    txttag = 'Y07'

    attributes = [(u'nDup', ''),
                  (u'dVenc', ''),
                  (u'vDup', ''),]

    def __init__(self, number, due_date, value):
        BaseNFeXMLGroup.__init__(self)

        self.set_attr('nDup', number)
        self.set_attr('dVenc', self.format_date(due_date))
        self.set_attr('vDup', self.format_value(value))



class NFeAdditionalInformation(BaseNFeXMLGroup):
    tag = u'infAdic'
    attributes = [(u'infAdFisco', None),
                  (u'infCpl', None)]
    txttag = 'Z'


class NFeSimplesNacionalInfo(NFeAdditionalInformation):
    def __init__(self, sale_notes):
        NFeAdditionalInformation.__init__(self)
        msg = u'Documento emitido por ME ou EPP optante pelo SIMPLES' \
              u' NACIONAL. Não gera Direito a Crédito Fiscal de ICMS e de'\
              u' ISS. Conforme Lei Complementar 123 de 14/12/2006.'

        self.set_attr('infAdFisco', msg)
        self.set_attr('infCpl', sale_notes)
