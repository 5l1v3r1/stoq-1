# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2007 Async Open Source
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
##                  Johan Dahlin                <jdahlin@async.com.br>
##

import commands
import os
import shutil
import tempfile

import gtk
from kiwi.python import Settable
from kiwi.ui.dialogs import ask_overwrite, error, save
from kiwi.ui.search import DateSearchFilter

from stoqlib.database.runtime import get_connection, get_current_user
from stoqlib.gui.base.dialogs import (BasicDialog, run_dialog,
                                      get_current_toplevel)
from stoqlib.gui.editors.baseeditor import BaseEditorSlave
from stoqlib.lib.translation import stoqlib_gettext
from stoqlib.reporting.base.utils import (print_file, print_preview,
                                          build_report)

try:
    import gtkunixprint
    gtkunixprint # pyflakes
except ImportError:
    gtkunixprint = None

_ = stoqlib_gettext

class PrintDialogSlave(BaseEditorSlave):
    gladefile = 'PrintDialogSlave'
    proxy_widgets = ('printer_combo',
                     'filename_entry')
    model_type = Settable

    def __init__(self, report_class, *args, **kwargs):
        self._available_printers = []
        BaseEditorSlave.__init__(self, None, None)
        preview_label = kwargs.pop("preview_label", None)
        if preview_label is not None:
            self.print_preview_button.set_label(preview_label)
        self._preview_callback = kwargs.pop("preview_callback", None)
        default_filename = kwargs.pop("default_filename", None)
        if default_filename:
            self.model.filename = default_filename
            self.proxy.update("filename")
        self._report_class = report_class
        self._report_kwargs = kwargs
        self._report_args = args
        self._update_view()

    def get_printer_name(self):
        if self.printer_radio.get_active():
            return self.model.printer_name
        return None

    def get_filename(self):
        if self.file_radio.get_active():
            return self.model.filename
        return None

    def get_report_file(self):
        return build_report(self._report_class, *self._report_args,
                            **self._report_kwargs)

    def _setup_printer_combo(self):
        self._available_printers = self._get_available_printers()
        if self._available_printers:
            self.printer_combo.prefill(self._available_printers)

    def _get_available_printers(self):
        #TODO check also if cups is running or not and give
        # proper messages to users
        func = commands.getoutput
        if not func("lpstat -v"):
            return []
        printers = []
        res = func("lpstat -d").split(":")
        if len(res) > 1:
            printers.append(res[1].strip())
        for p in func('lpstat -a').split('\n'):
            printer_name = p.split()[0].strip()
            if printer_name in printers:
                continue
            printers.append(printer_name)
        return printers

    def _setup_widgets(self):
        self._setup_printer_combo()

    def _update_view(self):
        if self._available_printers:
            is_active = self.printer_radio.get_active()
            self.filename_entry.set_sensitive(not is_active)
            self.file_selection_button.set_sensitive(not is_active)
            self.printer_combo.set_sensitive(is_active)
        else:
            self.printer_radio.set_sensitive(False)
            self.printer_combo.set_sensitive(False)

    #
    # BaseEditorSlave hooks
    #

    def create_model(self, dummy):
        return Settable(printer_name=None, filename=u'relat1.pdf')

    def get_title(self, dummy):
        return _("Print Dialog")

    def setup_proxies(self):
        self.proxy = self.add_proxy(self.model, PrintDialogSlave.proxy_widgets)
        self._setup_widgets()

    #
    # Kiwi callbacks
    #

    def on_printer_radio__toggled(self, widget):
        self._update_view()

    def on_file_selection_button__clicked(self, *args):
        filename = save(_("Select the file"))
        if not filename:
            return
        self.filename_entry.set_text(filename)

    def on_print_preview_button__clicked(self, *args):
        if self._preview_callback is not None:
            return self._preview_callback(
                self._report_class, *self._report_args, **self._report_kwargs)
        return print_preview(self.get_report_file())

class PrintDialog(BasicDialog):
    """ A simple report print dialog, with options to preview or print the
    report on a file.
    """

    title = _("Print Dialog")

    def __init__(self, report_class, *args, **kwargs):
        # We don't have to check the relation of report_class with
        # BaseDocTemplate,  since we can just use the PrintDialog
        # to print a text file, for instance.
        BasicDialog.__init__(self)
        self._report_class = report_class
        preview_label = kwargs.pop("preview_label", None)
        default_filename = kwargs.pop("default_filename", None)
        title = kwargs.pop("title", PrintDialog.title)
        self._kwargs = kwargs
        self._args = args
        self._initialize(preview_label=preview_label, title=title,
                         default_filename=default_filename)
        self.register_validate_function(self.refresh_ok)
        self.force_validation()

    def _initialize(self, preview_label=None, default_filename=None, *args,
                    **kwargs):
        BasicDialog._initialize(self, *args, **kwargs)
        self.ok_button.set_label(gtk.STOCK_PRINT)
        self._setup_slaves(preview_label=preview_label,
                           default_filename=default_filename)

    def refresh_ok(self, validation_value):
        if validation_value:
            self.enable_ok()
        else:
            self.disable_ok()

    def _setup_slaves(self, preview_label=None, default_filename=None):
        self.print_slave = PrintDialogSlave(self._report_class,
                                            default_filename=default_filename,
                                            preview_label=preview_label,
                                            *self._args, **self._kwargs)
        self.attach_slave('main', self.print_slave)

    def confirm(self):
        printer = self.print_slave.get_printer_name()
        reportfile = self.print_slave.get_report_file()
        if not printer:
            filename = self.print_slave.get_filename()
            assert filename
            if os.path.exists(filename):
                if not ask_overwrite(filename):
                    return
            try:
                shutil.copy(reportfile, filename)
            except IOError, e:
                error("The file can't be saved", e.strerror)
            os.unlink(reportfile)
        else:
            print_file(reportfile, printer)
        BasicDialog.confirm(self)


class GtkPrintDialog(object):
    """A dialog to print PDFs using the printer dialog in Gtk+ 2.10+
    """
    def __init__(self, report):
        self._report = report
        self._dialog = self._create_dialog()

    def _create_dialog(self):
        dialog = gtkunixprint.PrintUnixDialog(parent=get_current_toplevel())
        dialog.set_manual_capabilities(gtkunixprint.PRINT_CAPABILITY_COPIES |
                                       gtkunixprint.PRINT_CAPABILITY_PAGE_SET)
        button = self._add_preview_button(dialog)
        button.connect('clicked', self._on_preview_button__clicked)
        button = self._add_mailto_button(dialog)
        button.connect('clicked', self._on_mailto_button__clicked)
        return dialog

    def _add_preview_button(self, dialog):
        # Add a preview button
        button = gtk.Button(stock=gtk.STOCK_PRINT_PREVIEW)
        dialog.action_area.pack_start(button)
        dialog.action_area.reorder_child(button, 0)
        button.show()
        return button

    def _add_mailto_button(self, dialog):
        # Add a mailto button
        button = gtk.Button(label=_('Send PDF by e-mail'))
        dialog.action_area.pack_start(button)
        dialog.action_area.reorder_child(button, 0)
        button.show()
        return button

    def _send_to_printer(self, printer, settings, page_setup):
        job = gtkunixprint.PrintJob(self._report.title, printer,
                                    settings, page_setup)
        job.set_source_file(self._report.filename)
        job.send(self._on_print_job_complete)

    def _print_preview(self):
        print_preview(self._report.filename, keep_file=True)

    def _pdfmailto(self):
        if not os.path.exists(self._report.filename):
            raise OSError, "the file does not exist"
        user = get_current_user(get_connection())
        os.system("/usr/local/bin/pdfmailto %s '%s'" % (
                                self._report.filename, user.person.name))

    #
    # Public API
    #

    def run(self):
        response = self._dialog.run()
        if response in [gtk.RESPONSE_CANCEL,
                        gtk.RESPONSE_DELETE_EVENT]:
            self._dialog.destroy()
            self._dialog = None
        elif response == gtk.RESPONSE_OK:
            self._send_to_printer(self._dialog.get_selected_printer(),
                                  self._dialog.get_settings(),
                                  self._dialog.get_page_setup())
            self._dialog.destroy()
            self._dialog = None
        else:
            raise AssertionError("unhandled response: %d" % (response,))

    #
    # Callbacks
    #

    def _on_preview_button__clicked(self, button):
        self._print_preview()

    def _on_mailto_button__clicked(self, button):
        self._pdfmailto()

    def _on_print_job_complete(self, job, data, error):
        if error:
            print 'FIXME, handle error:', error


def describe_search_filters_for_reports(**kwargs):
    filters = kwargs.pop('filters')
    filter_strings = []
    for filter in filters:
        description = filter.get_description()
        if description:
            filter_strings.append(description)

    kwargs['filter_strings'] = filter_strings
    return kwargs


def print_report(report_class, *args, **kwargs):
    if kwargs.has_key('filters') and kwargs['filters']:
        kwargs = describe_search_filters_for_reports(**kwargs)

    if gtkunixprint:
        tmp = tempfile.mktemp(prefix='stoqlib-reporting')
        report = report_class(tmp, *args, **kwargs)
        report.filename = tmp
        report.save()
        dialog = GtkPrintDialog(report)
        dialog.run()
        os.unlink(report.filename)
    else:
        run_dialog(PrintDialog, None, report_class, *args, **kwargs)
