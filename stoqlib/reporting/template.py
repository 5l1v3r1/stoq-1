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
Este m�dulo implementa a classe BaseReportTemplate, onde todos os m�todos para
inser��o de elementos no relat�rio est�o definidos e, parcialmente,
implementados.
"""

from reportlab.lib import pagesizes
from reportlab import platypus

from stoqlib.reporting import tables, flowables
from stoqlib.reporting.default_style import (DOC_DEFAULTS, SPACING,
                                             STYLE_SHEET, TABLE_STYLE,
                                             DEFAULT_MARGIN, TABLE_LINE)

class BaseReportTemplate(platypus.BaseDocTemplate):
    """ 
    Classe respons�vel pela implementa��o dos m�todos para inser��o de
    elementos no relat�rio.
    """
    header_height = 0
    footer_height = 0
    def __init__(self, filename, report_name, pagesize=pagesizes.A4,
                 landscape=0, do_header=0, do_footer=0, **kwargs):
        """
        Classe respons�vel pela implementa��o dos m�todos para inser��o de
        elementos no relat�rio. Os par�metros para esta classe, que podem (e
        devem) ser passados � classe ReportTemplate (a qual sua classe deve
        herdar), s�o:

            - filename: o nome do arquivo onde o relat�rio deve ser
            constru�do; esse nome de arquivo � passado por build_report � 
            classe do usu�rio e � obrigat�rio.
            - report_name: o nome do relat�rio, par�metro obrigat�rio; o nome
            do relat�rio � utilizado, basicamente, para a constru��o do rodap�
            do relat�rio.
            - pagesize: o tamanho da p�gina; os tamanhos dispon�veis podem ser
            encontrados em reportlab.lib.pagesizes.
            - landscape: define se o relat�rio deve ser gerado no formato
            paisagem; o padr�o � o formato "retrato" (landscape=0).
            - do_footer: define se o rodap� deve ser desenhado.
        """
        self.do_header = do_header
        self.do_footer = do_footer
        self.report_name = report_name

        doc_kwargs = DOC_DEFAULTS.copy()
        doc_kwargs.update(kwargs)

        if landscape:
            pagesize = pagesizes.landscape(pagesize)

        platypus.BaseDocTemplate.__init__(self, filename, pagesize=pagesize,
                                          title=report_name, **doc_kwargs)
        self.flowables = []
        self.grouping = 0
        # Group of flowables wich shouldn't be separated on different pages
        self._together_flowables = []
        # Number of flowables to include in the current group.
        self._together_count = 0

    #
    # External API
    #
    
    def save(self):
        """ 
        Constru��o e salvamento do relat�rio. M�todo chamado internamente.
        """
        self.build()

    def build(self):
        """
        M�todo chamado internamente para constru��o do relat�rio. Inicializa
        as p�ginas do relat�rio e constr�i os elementos.
        """
        # Adds forgotten flowables
        self.end_group()
        
        # If page size has changed, we try to make ReportLab work
        self._calc()

        self.setup_page_templates()
        platypus.BaseDocTemplate.build(self, self.flowables)

    #
    # Doc structure
    #

    def setup_page_templates(self):
        """ 
        Inicializa��o das p�ginas do relat�rio. Temos, basicamente, neste
        m�todo a defini��o do espa�o vertical dispon�vel para desenho,
        baseado no tamanho do rodap� e cabe�alho do relat�rio.
        """
        frame_y = self.bottomMargin
        height = self.height

        if self.do_header:
            height -= self.header_height

        if self.do_footer:
            height -= self.footer_height
            frame_y += self.footer_height

        main_frame = platypus.Frame(self.leftMargin, frame_y,
                                    self.width, height,
                                    bottomPadding=SPACING,
                                    topPadding=SPACING)

        template = platypus.PageTemplate(id='Normal', frames=main_frame,
                                         pagesize=self.pagesize,
                                         onPage=self.paint_page_canvas)
        self.addPageTemplates([template])

    #
    # Internal API
    #
    
    def add(self, flowable):
        """ 
        M�todo chamado para inser��o de elementos no relat�rio. Cada elemento
        criado, tal como um par�grafo, uma tabela, um titulo ou uma assinatura
        deve ser inserido no "relat�rio" atr�ves deste m�todo para que ele
        possa ser desenhado quando uma chamada ao m�todo build for feita. Esse
        m�todo pertence � API interna e n�o deve ser chamado na maioria dos
        casos (a menos que voc� esteja criando um novo tipo de flowable :)
        """
        if self.grouping:
            self._together_flowables.append(flowable)
            self.end_group(self._together_count - 1)
        else:
            self.flowables.append(flowable)

    def start_group(self):
        """ 
        Utilizado para agrupar elementos, como por exemplo, � necess�rio no
        caso do m�todo para inser��o de t�tulos no relat�rio; se uma nota de
        t�tulo for provida, ela deve ser agrupada junto com o t�tulo, pois 
        tanto ela quanto o t�tulo s�o, basicamente, um �nico elemento: um
        t�tulo. 
        """
        self.grouping = 1

    def end_group(self, min_flowables=0):
        """
        Termina o agrupamento de elementos, isto �, todos os elementos que
        deviam ser agrupados j� o foram. 
        """
        # Updating _together_count
        if min_flowables >= 0:
            self._together_count = min_flowables
        # If there is not more flowables, close the group and add it.
        if not min_flowables:
            self.grouping = 0
            if self._together_flowables:
                self.add(platypus.KeepTogether(self._together_flowables))
            self._together_flowables = []

    def get_usable_width(self):
        """
        Retorna o espa�o horizontal ainda dispon�vel para inser��o/desenho de
        elementos 
        """
        return self._rightMargin - self.leftMargin 

    def get_usable_height(self):
        """
        Retorna o espa�o vertical ainda dispon�vel para inser��o/desenho de
        elementos 
        """
        return self._topMargin - self.bottomMargin

    def set_page_number(self, number):
        """ Define o n�mero da p�gina atual """
        self.add(flowables.PageNumberChanger(number))

    def get_page_number(self):
        """ 
        Retorna o n�mero da p�gina atual, isto �, a p�gina que est� sendo
        constru�da. 
        """
        return self.page
        
    #
    # Features
    #
        
    def add_page_break(self):
        """ Adiciona uma simples quebra de p�gina. """
        self.add(platypus.PageBreak())

    def add_document_break(self):
        """
        Basicamente insere uma quebra de p�gina e inicia um novo documento. � 
        como se tivessemos dois documentos no mesmo relat�rio.
        """
        self.set_page_number(0)
        self.add_page_break()
        
    def add_blank_space(self, height=10, width=-1):
        """ 
        Adiciona um espa�o branco na posi��o atual. Parametros:

           - height: o tamanho do espa�o a ser inserido
           - width: o comprimento do espa�o

        Atrav�s dos parametros height e width podemos definir o tipo de 
        espacamento que queremos, ou seja, se queremos um espa�amento vertical,
        neste caso definimos height=-1 e width=X (X=tamanho do espacamento) ou
        se queremos um espa�amento horizontal, neste caso, height=X e with=-1;
        espa�amento vertical � o padr�o. 
        """
        self.add(platypus.Spacer(width, height))

    def add_signatures(self, labels, *args, **kwargs):
        """
        Adiciona uma assinatura no relat�rio. Par�metros:

            - labels: Uma lista de strings de assinatura, cada item da lista
            ser� uma assinatura e ser� inserida no relat�rio lado a lado;
            dependendo do tamanho da p�gina e do parametro landscape, s�o
            permitidos de 2 a 4 assinaturas na mesma linha.
            - align: define o alinhamento do elemento, deve-se utilizar as
            constantes LEFT, CENTER ou RIGHT definidas neste m�dulo.
            - line_width: comprimento da linha de assinatura.
            - height: espa�o vertical disponibilizado acima da linha.
            - text_align: alinhamento do texto de assinatura.
            - style_data: permite utilizar estilos de par�grafos para o texto
            de assinatura, caso n�o seja especificado o padr�o (definido no
            m�dulo default_style) ser� utilizado.
        """
        self.add(flowables.Signature(labels, *args, **kwargs))

    def add_preformatted_text(self, text, style='Raw', *args, **kwargs):
        """
        Adiciona um texto pr�-formatado ao relat�rio. Par�metros:

            - text: o texto a ser inserido
            - style: define o estilo a ser utilizado. Como padr�o o estilo
            'Raw' (consulte o m�dulo default_style para mais detalhes) �
            utilizado.

        Voc� pode utilizar esse m�todo para inser��o de textos com
        espa�amento.

        Note que par�metros extras podem ser passados para essa
        fun��o, nesse caso eles ser�o repassados diretamente para a
        classe Preformatted do ReportLab. 
        """
        style = STYLE_SHEET[style]
        self.add(platypus.flowables.Preformatted(text, style, *args, **kwargs))

    def add_paragraph(self, text, style='Normal', **kwargs):
        """ 
        Adiciona um par�grafo. Parametros:

            - text: o texto a ser inserido no relat�rio.
            - style: define o estilo a ser utilizado; v�rios deles est�o
            definidos no m�dulo default_style.
        """
        style = STYLE_SHEET[style]
        self.add(platypus.Paragraph(text, style, **kwargs))

    def add_report_table(self, data, header=None, style=TABLE_STYLE,
                         margins=DEFAULT_MARGIN, align=flowables.CENTER,
                         extra_row=None, table_line=TABLE_LINE,
                         highlight=tables.HIGHLIGHT_ODD, *args, **kwargs):
        """
        Inserc�o de uma tabela relat�rio na lista de elementos. Os
        par�metros para este tipo de tabela, s�o:

            - data: uma lista de listas contendo as linhas da tabela, cada
            lista interna representa uma linha, enquanto seus elementos
            representam as colunas desta linha.
            - header: uma lista que, se especificada, ser� utilizada como
            cabe�alho da tabela; o tamanho desta lista deve ser o mesmo
            das listas internas especificadas no par�metro data.
            - style: permite a especifica��o de estilos (TableStyle)
            pr�prios para uso na tabela.
            - margins: margens verticais antes e ao�s tabela.
            - align: alinhamento da tabela; voc� pode encontrar as
            constantes para alinhamento no m�dulo flowables.
            - extra_row: uma lista com a linha extra � ser inserida. Assim 
            como o par�metro header, a lista especificada como argumento
            deve possuir o mesmo tamanho das listas internas especificadas
            ao par�metro data.
            - table_line: define o tipo de linha a ser utilizada na tabela.
            Stoqlib Reporting fornece os tipos TABLE_LINE (linhas simples) e
            TABLE_LINE_BLANK (sem linhas).
            - highlight: habilita (constante HIGHLIGHT_ODD) ou desabilita
            (HIGHLIGHT_NEVER) o uso do estilo zebrado nas linhas da tabela.
            O padr�o � habilitado (HIGHLIGHT_ODD).
        """
        self.add_blank_space(margins)
        table_builder = tables.ReportTableBuilder(data, style, header,
                                                  table_line,
                                                  extra_row=extra_row)
        kwargs["align"] = align
        table_builder.set_highlight(highlight)
        self.add(table_builder.create_table(*args, **kwargs))
        self.add_blank_space(margins)
    
    def add_column_table(self, data, columns, style=TABLE_STYLE,
                         margins=DEFAULT_MARGIN, align=flowables.CENTER,
                         extra_row=None, table_line=TABLE_LINE, do_header=1,
                         highlight=tables.HIGHLIGHT_ODD, *args, **kwargs):
        """
        Inser��o de uma tabela coluna na lista de elementos. Os par�metros
        para este tipo de tabela, s�o:

            - data: uma lista de listas, onde cada lista internO ideal seria ter a opcao de definir o comportamento: truncar os caracteres OU
rolar para linha abaixo.a representa
            uma lista e cada elemento representa o valor � ser inserido em
            uma coluna.
            - columns: uma lista de inst�ncias TableColumn representando as
            colunas da tabela.
            - style: estilo de tabela a ser utilizado, permite a
            especifica��o de estilos (TableStyle) pr�prios para uso na
            tabela.
            - margins: margens verticais antes e ap�s a tabela.
            - align: alinhamento da tabela; voc� pode encontrar as
            constantes para alinhamento no m�dulo flowables.
            - extra_row: uma lista com a linha extra � ser inserida. A lista
            especificada como argumento deve possuir o mesmo tamanho das
            listas internas especificadas ao par�metro data.
            - table_line: define o tipo de linha a ser utilizado na tabela.
            Stoqlib Reporting fornece os tipos TABLE_LINE (linhas simples)
            e TABLE_LINE_BLANK (sem linhas). O tipo TABLE_LINE � o padr�o.
            - do_header: se definido como True, o cabe�alho da tabela ser�
            desenhado. O nome de cada coluna � obtida atrav�s do atributo
            'name' de cada inst�ncia especificada lista do argumento
            columns.
            - highlight: habilita (constante HIGHLIGHT_ODD) ou desabilita
            (HIGHLIGHT_NEVER) o uso do estilo zebrado nas linhas da
            tabela. O padr�o � habilitado (HIGHLIGHT_ODD).
        """
        self.add_blank_space(margins)
        table_builder = tables.ColumnTableBuilder(data, columns, style=style, 
                                                  table_line=table_line,
                                                  do_header=do_header,
                                                  extra_row=extra_row)
        kwargs["align"] = align
        table_builder.set_highlight(highlight)
        self.add(table_builder.create_table(*args, **kwargs))
        self.add_blank_space(margins)

    def add_object_table(self, objs, cols, expand=0, width=0, 
                         style=TABLE_STYLE, margins=DEFAULT_MARGIN,
                         extra_row=None, align=flowables.CENTER, 
                         table_line=TABLE_LINE, highlight=tables.HIGHLIGHT_ODD,
                         *args, **kwargs):
        """
        Inser��o de uma tabela objeto na lista de elementos. Os par�metros
        para este tipo de tabela, s�o:

            - objs: uma lista de objetos na qual a lista de linhas ser�
            constru�da.
            - cols: uma lista de colunas ObjectTableColumn.
            - expand:
            - width: utilizado para permitir ao usu�rio especificar o
              tamanho da tabela.
            - style: par�metro opcional, permite ao usu�rio definir um
              estilo de tabela (TableStyle) pr�prio.
            - margins: margens verticais antes e ap�s a tabela.
            - extra_row: uma lista de valores representado uma linha extra.
              Nem todos os elementos precisam estar preenchidos, mas �
              necess�rio que eles existam, isto �, � necess�rio que o
              tamanho desta lista seja o mesmo das listas internas do
              par�metro data.
            - align: alinhamento da tabela; voc� pode encontrar as
              constantes para alinhamento no m�dulo flowables.
            - table_line: define o tipo de linha a ser utilizado na tabela.
              Stoqlib Reporting fornece os tipos TABLE_LINE (linhas simples)
              e TABLE_LINE_BLANK (sem linhas).
            - highlight: habilita (constante HIGHLIGHT_ODD) ou desabilita
              (HIGHLIGHT_NEVER) o uso do estilo zebrado nas linhas da
              tabela. O padr�o � habilitado (HIGHLIGHT_ODD).
            
        """
        assert not (expand and width), \
            'Use only expand _OR_ only width at once'
        if expand:
            width = self.get_usable_width()

        self.add_blank_space(margins)
        table_builder = tables.ObjectTableBuilder(objs, cols, style,
                                                  width=width,
                                                  extra_row=extra_row,
                                                  table_line=table_line)
        kwargs["align"] = align
        table_builder.set_highlight(highlight)
        self.add(table_builder.create_table(*args, **kwargs))
        self.add_blank_space(margins)

    def add_grouping_table(self, objs, column_groups, column_widths,
                           header=None, style=TABLE_STYLE,
                           margins=DEFAULT_MARGIN, align=flowables.CENTER,
                           extra_row=None, *args, **kwargs):
        # """We need to set the table header directly for GroupingTableBuilder
        # because the Columns used with it does not have a name. Note that we
        # have one header for each column width defined and you can use a false
        # value (None, '', 0) to make the previous header span over it."""
        self.add_blank_space(margins)
        table_builder = tables.GroupingTableBuilder(objs, column_groups,
                                                    column_widths,
                                                    style=style,
                                                    header=header, 
                                                    extra_row=extra_row)
        kwargs["align"] = align
        self.add(table_builder.create_table(*args, **kwargs))
        self.add_blank_space(margins)
    
    def add_data_table(self, data, style=TABLE_STYLE, margins=DEFAULT_MARGIN, 
                       align=flowables.LEFT, *args, **kwargs):
        """ 
        Inser��o de uma tabela simples. Os parametros s�o:

            - data: uma lista de listas, onde cada lista interna representa uma
            linha da tabela, e cada item desta lista as colunas.
            - style: define o estilo que a tabela deve seguir, mais estilos 
            voc� pode encontrar em stoqlib.reporting.default_style
            - margins: margens verticais antes e depois da tabela.
            - align: alinhamento da tabela
        """
            
        self.add_blank_space(margins)
        table_builder = tables.DataTableBuilder(data, style)
        kwargs["align"] = align
        self.add(table_builder.create_table(*args, **kwargs))
        self.add_blank_space(margins)
    
    def add_line(self, *args, **kwargs):
        """ Adiciona uma simples linha na posi��o atual """
        line = flowables.ReportLine(*args, **kwargs)
        self.add(line)

    def add_title(self, title, note=None, space_before=SPACING,
                  style='Title', note_style='Title-Note'):
        """
        Adiciona um t�tulo na posi��o atual. Par�metros:

            - title: o texto que ser� o t�tulo
            - note: se especificado, ser� inserido como uma nota ao t�tulo
            - space_before: define o tamanho do espa�amento a ser inserido
            ap�s o t�tulo
            - style: define o estilo a ser utilizado para o par�grafo 'title';
            n�o � recomendado sua altera��o, uma vez que isto quebra o padr�o
            utilizado em todo o documento (a n�o ser que um novo padr�o seja
            especificado em um atributo da classe)
            - note_style: define o estilo a ser utilizado para o par�grafo
            'note'
        """
        self.add_blank_space(space_before)
        self.start_group()
        self.add_line(v_margins=1)
        self.add_paragraph(title, style=style)
        if note:
            self.add_paragraph(note, style=note_style)
        self.add_line(v_margins=1)
        self.end_group(1)

    #
    # Handlers
    #

    def paint_page_canvas(self, canvas, doc):
        """
        M�todo chamado quando uma nova p�gina � criada; basicamente o
        processamento feito aqui � a inser��o do rodap� e cabe�alho. 
        """
        if self.do_header:
            self.draw_header(canvas)
        if self.do_footer:
            self.draw_footer(canvas)
            
    def draw_header(self, canvas):
        raise NotImplementedError

    def draw_footer(self, canvas):
        raise NotImplementedError

