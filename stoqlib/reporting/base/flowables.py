# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
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
## Author(s):       Evandro Vale Miquelito      <evandro@async.com.br>
##                  Henrique Romano             <henrique@async.com.br>
##
"""Extra flowable implementation.
   The flowable alignment constants are defined here too.
"""

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, ActionFlowable
from reportlab.platypus.paragraph import Paragraph as RParagraph
from reportlab.pdfbase.pdfmetrics import stringWidth

from stoqlib.reporting.base.default_style import (SIGNATURE_FONT, SPACING,
                                                  STYLE_SHEET)

# We use enums here only to help to find typos. Reportlab uses strings for
# alignment settings. Reportlab also defines other numeric enums for text
# alignment, called TA_*
LEFT = 'LEFT'
CENTER = 'CENTER'
RIGHT = 'RIGHT'

ELLIPSIS_STRING = "..."

#
# Flowables
#

class PageNumberChanger(ActionFlowable):
    """ A flowable for current page number specification """

    def __init__(self, page_number):
        """ This flowable is used in cases where we need reset the current
        page number (see add_document_break method on BaseReportTemplate).
        """
        self.page_number = page_number

    def apply(self, doc):
        """ Apply the new page number. Internal use by Reportlab. """
        doc.page = self.page_number

class ReportLine(Flowable):
    """ Just a simple line flowable """

    def __init__(self, thickness=1, v_margins=5, h_margins=0,
                 dash_pattern=None):
        """
        @param thickness: The line thickness
        @type:         int

        @param v_margins: How much vertical space between the line? Defaults
                       to 5
        @type:         int

        @param h_margins: How much horizontal space between the line?
                       Defaults to 0
        @type:         int

        @param dash_pattern: The line dash pattern.
        @type:         float
        """
        Flowable.__init__(self)
        self.thickness = thickness
        self.h_margins = h_margins
        self.v_margins = v_margins
        self.dash_pattern = dash_pattern

    #
    # Reportlab callbacks
    #

    def wrap(self, avail_width, avail_height):
        """ Calculate the space required by the flowable. Internal use by
        Reportlab.
        """
        self.avail_width = avail_width
        x = avail_width, 2 * self.v_margins + self.thickness
        return avail_width, 2 * self.v_margins + self.thickness

    def drawOn(self, canvas, x, y, *args, **kwargs):
        """ Start drawing the flowable. This method is called internally by
        Reportlab
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
    """ A signature flowable """

    def __init__(self, labels, align=RIGHT, line_width=75*mm, height=60,
                 text_align=CENTER, style_data=None):
        """
        @param labels: A list of string, with each string representing
                       a signature.
        @type:         list

        @param align:  The signature alignment
        @type:         One of LEFT, CENTER or RIGHT constants

        @param line_width: The line width
        @type:         int/float

        @param height: How much space before the signature line?
        @type:         int/float

        @param text_align: The signature text alignment.
        @type:         One of CENTER, LEFT or RIGHT constants

        @param style_data: A string with the paragraph style.
        @type:         One of the styles defined in the default_style
                       module.
        """
        self.labels = labels
        self.align = align
        self.text_align = text_align
        self.line_width = line_width
        self.space_height = height
        self.style_data = style_data
        Flowable.__init__(self)

    def get_draw_string_func(self, canvas, align):
        """ Based on the alignment type, returns a 'text writer' function.
        """
        if align == LEFT:
            return canvas.drawString
        elif align == RIGHT:
            return canvas.drawRightString
        else:
            return canvas.drawCentredString

    def build_signatures(self, canvas, x,  x1, x2, y, default_x2):
        """ This is the method that really draw the flowable on the report.
        This is called internally by drawOn.
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

    #
    # Reportlab callbacks
    #

    def wrap(self, avail_width, avail_height):
        """ Calculate the space required by the flowable. Internal use by
        Reportlab.
        """
        self.avail_width = avail_width
        height = self.space_height + SIGNATURE_FONT[1] + 1 * mm + SPACING
        return avail_width, height

    def drawOn(self, canvas, x, y, *args, **kwargs):
        """ Start drawing the flowable. This method is called internally by
        Reportlab
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
        elif self.align == CENTER:
            x1 = x + (self.avail_width - left) / 2
            x2 = x1 + self.line_width
            default_x2 = x + self.line_width
        elif self.align == LEFT:
            x1 = x
            x2 = x + self.line_width
            default_x2 = x2
        else:
            raise TypeError("Invalid alignment for signature flowable: "
                            % self.align)
        self.build_signatures(canvas, x, x1, x2, y, default_x2)
        canvas.restoreState()

class Paragraph(RParagraph):
    def __init__(self, text, style=None, ellipsize=True, bulletText=None,
                 frags=None, caseSensitive=1):
        """
        @param text:   The paragraph text. You can use the same features
                       available on reportlab's Paragraph.
        @type text:    basestring

        @param style:  a string or ParagraphStyle instance representing
                       the paragraph style. If you do use a string, it'll
                       be searched in the styles provided by
                       default_style module.
        @type style:   object

        @param ellipsis: Define if the paragraph must use ellipsis when
                       the text doesn't fits in the available width. If
                       not set, reportlab will try break the text into
                       multiple lines (which can be fail if the
                       text haven't the required amount of space chars)
        @type ellipsis: bool
        """
        if not style:
            style = STYLE_SHEET["Raw"]
        if isinstance(style, basestring):
            if not style in STYLE_SHEET:
                raise ValueError("The style requested does not exists.")
            style = STYLE_SHEET[style]
        self._ellipsize = ellipsize
        # [total_width, [frag0, frag1, ...fragN]]
        self._first_line_frags = []
        RParagraph.__init__(self, text, style, bulletText, frags,
                            caseSensitive)

    #
    # Reportlab's Paragraph overwrites
    #

    def breakLines(self, widths):
        if self._ellipsize and self._first_line_frags:
            avail_width = widths[0]
            total_width, frags = self._first_line_frags
            for frag in frags[::-1]:
                ellipsis_width = stringWidth(ELLIPSIS_STRING, frag.fontName,
                                             frag.fontSize)
                frag_width = stringWidth(frag.text, frag.fontName,
                                         frag.fontSize)
                if total_width + ellipsis_width >= avail_width:
                    if (frag_width - (total_width - avail_width)
                        > ellipsis_width):
                        for letter in frag.text[::-1]:
                            frag.text = frag.text[:-1]
                            total_width -= stringWidth(letter, frag.fontName,
                                                       frag.fontSize)
                            if total_width + ellipsis_width < avail_width:
                                break
                        else:
                            total_width -= frag_width
                            frags.pop()
                            continue
                    else:
                        total_width -= frag_width
                        frags.pop()
                        continue
                frag.text += ELLIPSIS_STRING
                self.frags = frags
                break
        return RParagraph.breakLines(self, widths)

    # XXX: We need to overwrite RParagraph's wrap since there the requested
    # width is the maximum possible (that is the "avail_width" parameter).
    # Here we need request just what we need, so it can be properly aligned
    # when needed (in a table, for instance).
    def wrap(self, width, height):
        if not self._ellipsize:
            return RParagraph.wrap(self, self.minWidth(), height)
        if self.frags:
            total_width = 0.0
            first_line_frags = []
            space_width = 0.0
            for frag in self.frags:
                total_width += stringWidth(frag.text, frag.fontName,
                                           frag.fontSize)
                first_line_frags.append(frag)
                if total_width > width:
                    self._first_line_frags = [total_width, first_line_frags]
                    width = min(total_width, width)
                    break
            else:
                # No need to ellipsize if the frags width is lesser than
                # the available width
                self._ellipsize = False
        return RParagraph.wrap(self, width, height)
