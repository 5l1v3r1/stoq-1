# -*- coding: iso-8859-1 -*-
""" Este m�dulo disponibiliza estilos de par�grafos e define estilos padr�es
� serem utilizados em p�ginas, tabelas e textos. Os estilos de par�grafos 
definidos aqui tem como objetivo b�sico extender os estilos fornecidos pelo
ReportLab. � poss�vel tamb�m criar seus pr�prios estilos seguindo o padr�o 
utilizado neste m�dulo, ou seja, simplesmente crie uma inst�ncia de
ParagraphStyle e adicione-a � STYLE_SHEET, um exemplo de como � poss�vel 
fazer isso � disponibilizado junto � distribui��o e � inclu�do no diret�rio
"examples/", com o nome "contract_example.py".

Os estilos de par�grafo disponibilizados s�o:

    - Normal: Fonte Helvetica, tamanho 10, alinhamento � esquerda
    - Normal-Bold: Fonte Helvetia-Bold, tamanho 10, alinhamento � esquerda
    - Normal-AlignRight: Fonte Helvetica, tamanho 10, alinhamento � esquerda
    - Title: Fonte Helvetica-Bold, tamanho 12, alinhamento � esquerda
    - Title-Note: Fonte Helvetica-Bold, tamanho 8, alinhamento � esquerda
    - Title-AlignCenter: Fonte Helvetica-Bold; tamanho 14, 
      alinhamento ao centro
    - Title-AlignRight: Fonte Helvetica-Bold, tamamho 12, 
      alinhamento � direita
"""
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import TableStyle

STYLE_SHEET = StyleSheet1()
STYLE_SHEET.add(ParagraphStyle(
    'Normal',
    fontName='Helvetica',
    fontSize=10,
    leftIndent=8,
    rightIndent=8,
    spaceAfter=3,
    spaceBefore=3,
    leading=12))

STYLE_SHEET.add(ParagraphStyle(
    'Normal-Bold',
    parent=STYLE_SHEET['Normal'],
    fontName='Helvetica-Bold'))

STYLE_SHEET.add(ParagraphStyle(
    'Normal-AlignRight',
    parent=STYLE_SHEET['Normal'],
    alignment=TA_RIGHT))

STYLE_SHEET.add(ParagraphStyle(
    'Title',
    parent=STYLE_SHEET['Normal'],
    fontName='Helvetica-Bold',
    leading=12,
    fontSize=12))

STYLE_SHEET.add(ParagraphStyle(
    'Title-Note',
    parent=STYLE_SHEET['Normal'],
    leading=10,
    fontSize=8))

STYLE_SHEET.add(ParagraphStyle(
    'Title-AlignCenter',
    parent=STYLE_SHEET['Title'],
    fontSize=14,
    alignment=TA_CENTER))

STYLE_SHEET.add(ParagraphStyle(
    'Title-AlignRight',
    parent=STYLE_SHEET['Title'],
    alignment=TA_RIGHT))

# This is a total padding preview used to calculate the expanded width for the
# columns:
COL_PADDING = 4

DOC_DEFAULTS = {'topMargin': 10 * mm,
                'leftMargin': 10 * mm,
                'rightMarging': 10 * mm,
                'bottomMargin': 20 * mm}

HIGHLIGHT_COLOR = colors.Color(0.9, 0.9, 0.9)
SOFT_LINE_COLOR = colors.gray
TEXT_COLOR = colors.black

SPACING = 4 * mm
DEFAULT_MARGIN = 5

SIGNATURE_FONT = ('Helvetica', 8)

DEFAULT_FONTNAME = 'Times-Roman'
DEFAULT_FONTSIZE = 10

default_table_cmds = (
    ('FONTNAME', (0,0), (-1,-1), DEFAULT_FONTNAME),
    ('FONTSIZE', (0,0), (-1,-1), DEFAULT_FONTSIZE),
    ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
    ('LEADING', (0,0), (-1,-1), 10),
    ('LEFTPADDING', (0,0), (-1,-1), 6),
    ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ('TOPPADDING', (0,0), (-1,-1), 3),
    ('BOTTOMPADDING', (0,0), (-1,-1), 3))

TABLE_LINE = (1, colors.black)
# Define bordas limpas(brancas) para as tabelas.
# XXX: Hack para que possamos definir uma tabela sem bordas.
TABLE_LINE_BLANK = (1, colors.white)
TABLE_STYLE = TableStyle(default_table_cmds)
TABLE_HEADER_FONT = 'Helvetica-Bold'
TABLE_HEADER_FONT_SIZE = 10
TABLE_HEADER_TEXT_COLOR = colors.black
TABLE_HEADER_BACKGROUND = colors.white

