# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005,2006 Async Open Source <http://www.async.com.br>
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
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
""" Constants related to flowable styles, like paragraphs, pages, tables and
    texts.
"""
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import TableStyle

# FIXME: Add support for TTF fonts
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
    'Raw',
    fontName='Courier'))

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

# XXX: Hack to have table without borders
TABLE_LINE_BLANK = (1, colors.white)
TABLE_STYLE = TableStyle(default_table_cmds)
TABLE_HEADER_FONT = 'Helvetica-Bold'
TABLE_HEADER_FONT_SIZE = 10
TABLE_HEADER_TEXT_COLOR = colors.black
TABLE_HEADER_BACKGROUND = colors.white

