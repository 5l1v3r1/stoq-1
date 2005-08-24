# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Copyright (C) 2005 Async Open Source
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

""" 
Este m�dulo disponibiliza novos elementos (flowables) de forma � permitir
extender a funcionalidade do ReportLab. Os elementos referidos s�o
PageNumberChanger, ReportLine e Signature.

O m�dulo tamb�m importa todas as constantes de estilos do m�dulo
"default_style" e fornece as seguintes constantes para alinhamento: LEFT, 
CENTER e RIGHT, alinhamento � esquerda, ao centro e � direita,
respectivamente.
"""

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, ActionFlowable

from stoqlib.reporting.default_style import SIGNATURE_FONT, SPACING

# We use enums here only to help to find typos. Reportlab uses strings for
# alignment settings. Reportlab also defines other numeric enums for text
# alignment, called TA_*
LEFT = 'LEFT'
CENTER = 'CENTER'
RIGHT = 'RIGHT'

#
# Flowables
#

class PageNumberChanger(ActionFlowable):
    """ Classe para especifica��o do n�mero de p�gina atual. """
    def __init__(self, page_number):
        """
        Classe para especifica��o do n�mero de p�gina atual. Este elemento �
        utilzado basicamente em casos onde precisamos redefinir o n�mero da
        p�gina atual e, � utilizado no Stoqlib Reporting, quando uma chamada
        ao m�todo add_document_break() � feita, neste caso temos que
        considerar que as p�ginas subsequentes ao m�todo add_document_break()
        ser�o p�ginas novas, logo, faz sentido considerar a primeira p�gina
        como uma primeira p�gina. 
        """
        self.page_number = page_number

    def apply(self, doc):
        """ Chamado internamente pelo ReportLab. Recebe a inst�ncia da classe
        do relat�rio e define um novo n�mero de p�gina, sendo que este novo
        n�mero de p�gina ser� considerado para todas as p�ginas subsequentes
        ap�s a chamada � este m�todo. """
        doc.page = self.page_number

class ReportLine(Flowable):
    """ Classe para cria��o de um elemento linha. """
    def __init__(self, thickness=1, v_margins=5, h_margins=0,
                 dash_pattern=None):
        """
        Classe para cria��o de um elemento linha. A inst�ncia��o desta classe,
        assim como sua inser��o na lista de flowables � ser desenhados no
        relat�rio (controlada internamente pelo Stoqlib Reporting), � feita 
        pelo m�todo add_line() do m�dulo template. Os par�metros para a classe
        (que podem, e devem, ser passados ao m�todo add_line()) s�o:

            - thickness: espessura da linha;
            - v_margins: margens verticais;
            - h_margins: margens horizontais;
        """
        Flowable.__init__(self)
        self.thickness = thickness
        self.h_margins = h_margins
        self.v_margins = v_margins
        self.dash_pattern = dash_pattern

    def wrap(self, avail_width, avail_height):
        """ Retorna o espa�o horizontal e vertical utilizado pelo elemento. """
        self.avail_width = avail_width
        x = avail_width, 2 * self.v_margins + self.thickness
        return avail_width, 2 * self.v_margins + self.thickness
    
    def drawOn(self, canvas, x, y, *args, **kwargs):
        """
        M�todo respons�vel pelo desenho do elemento.  Aplica as configura��es
        passadas pelo usu�rio ao construtor da classe e desenha o elemento no
        relat�rio. 
        """
        canvas.saveState()
        canvas.setLineWidth(self.thickness)
        if self.dash_pattern:
            canvas.setDash(self.dash_pattern, 0)
        # We add a half of line thickness to the y coordinate because the
        # given y coordinate will be at the middle of the line. The 'error' is
        # only perceptible when the line is thick.
        y += self.v_margins + self.thickness / 2
        x1 = x + self.h_margins
        x2 = x + self.avail_width - self.h_margins
        canvas.line(x1, y, x2, y)
        canvas.restoreState()

class Signature(Flowable):
    """ Classe para cria��o de um elemento assinatura. """
    def __init__(self, labels, align=RIGHT, line_width=75*mm, height=60,
                 text_align=CENTER, style_data=None):
        """
        Classe para cria��o de um elemento assinatura. Permite a cria��o de
        v�rias assinaturas, alinhamento do texto de assinatura, alinhamento
        do elemento assinatura e v�rias linhas para o texto. Sua 
        instancia��o e inser��o na lista de flowables � feita pelo seu
        m�todo add_signatures do m�dulo template. 
        Seus par�metros s�o:

            - labels: uma lista de strings, com cada string representando uma
            assinatura. Cada uma das strings representa o texto de assinatura
            e pode possuir v�rias linhas, que s�o divididas por um caractere
            'new line' ('\\n').
            - align: define o alinhamento do elemento, deve-se utilizar as
            constantes LEFT, CENTER ou RIGHT definidas neste m�dulo.
            - line_width: comprimento da linha de assinatura.
            - height: espa�o vertical disponibilizado acima da linha.
            - text_align: alinhamento do texto de assinatura.
            - style_data: permite utilizar estilos de par�grafos para o texto
            de assinatura, caso n�o seja especificado o padr�o (definido no
            m�dulo default_style) ser� utilizado.
        """
        self.labels = labels
        self.align = align
        self.text_align = text_align
        self.line_width = line_width
        self.space_height = height
        self.style_data = style_data
        Flowable.__init__(self)

    def wrap(self, avail_width, avail_height):
        """
        M�todo chamado internamente pelo ReportLab para tomar conhecimento do
        espa�o ocupado pelo elemento.
        """
        self.avail_width = avail_width
        height = self.space_height + SIGNATURE_FONT[1] + 1 * mm + SPACING
        return avail_width, height

    def get_draw_string_func(self, canvas, align):
        """
        Este m�todo retorna, baseado no alinhamento de texto definido no
        construtor da classe, o m�todo correto para impress�o do texto de
        assinatura. O m�todo � chamado internamente por build_signatures.
        """
        if align == LEFT:
            return canvas.drawString
        elif align == RIGHT:
            return canvas.drawRightString
        else:
            return canvas.drawCentredString

    def build_signatures(self, canvas, x,  x1, x2, y, default_x2):
        """
        Desenha os elementos no relat�rio. M�todo chamado internamente por
        drawOn(). Recebe as coordenadas onde deve ser inserido os elementos e
        os desenha.
        """
        
        line_height = y + SIGNATURE_FONT[1] + 1 * mm

        # XXX Still missing support for a real style object
        default_font_name, default_font_size  = SIGNATURE_FONT
        font_name = (self.style_data and self.style_data.fontName or
                     default_font_name)
        font_size = (self.style_data and self.style_data.fontSize or
                     default_font_size)

        canvas.setFont(font_name, font_size)

        for label in self.labels:
            drawStringFunc = self.get_draw_string_func(canvas, self.text_align)
            if self.text_align == LEFT:
                horiz_v = x1
            elif self.text_align == RIGHT:
                horiz_v = x2
            else:
                horiz_v = (x1 + x2) / 2
            current_line = y
            for fragment in label.split('\n'):
                drawStringFunc(horiz_v, current_line, fragment)
                current_line -= default_font_size
            
            canvas.line(x1, line_height, x2, line_height)

            x1 = x2 + x
            x2 += default_x2
            horiz_v = (x1 + x2) / 2

    def drawOn(self, canvas, x, y, *args, **kwargs):
        """
        Define as posi��es iniciais para o(s) elemento(s) assinatura e em
        seguinda faz uma chamada ao m�todo build_signatures() para a 
        inser��o da(s) mesma(s) no relat�rio.  Este m�todo � chamado 
        internamente pelo ReportLab.
        """
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFont(*SIGNATURE_FONT)

        y += SPACING / 2

        # "Avail_width" is the width of page footer. "Left" is the amount of
        # space we need to move the first signature from left to right. The
        # "x" variable defines the space before the start and after the
        # end of page footer. "x1" and "x2' is the first and last position of 
        # canvas line, respectively.
        between_lines = (len(self.labels) - 1) * x
        left = len(self.labels) * self.line_width + between_lines
        if self.align == RIGHT:
            x1 = x + self.avail_width - left
            x2 = x1 + self.line_width

            default_x2 = x + self.line_width
            self.build_signatures(canvas, x, x1, x2, y, default_x2)

        elif self.align == CENTER:
            x1 = x + (self.avail_width - left) / 2
            x2 = x1 + self.line_width

            default_x2 = x + self.line_width
            self.build_signatures(canvas, x, x1, x2, y, default_x2)

        elif self.align == LEFT:
            x1 = x
            x2 = x + self.line_width
            
            default_x2 = x2
            self.build_signatures(canvas, x, x1, x2, y, default_x2)

        else:
            msg = 'Invalid value for signature alignment: \'%s\'' 
            raise AssertionError, msg % self.align

        canvas.restoreState()

