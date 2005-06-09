# -*- encoding: iso-8859-1 -*-
""" Stoqlib Reporting � um pacote criado para facilitar a constru��o de 
relat�rios com o ReportLab. O maior destaque do pacote est� em suas rotinas 
para gera��o de tabelas, que fornecem suporte para cria��o do mais simples 
tipo de tabela, onde dispomos informa��es alinhadas, at� tabelas objeto, que 
permitem a cria��o de relat�rios tendo somente uma lista de inst�ncias (que 
pode ser obtida atrav�s de, por exemplo, uma pesquisa em uma base de dados). 

"""

from printing import ReportTemplate

import os
import tempfile
import sys
from types import TupleType, StringType

__name__ = "Stoqlib Reporting"
__version__ = "0.1"
__author__ = "Async Open Source"
__email__ = "async@async.com.br"
__license__ = "GNU LGPL 2.1"

# Editores padr�es � serem utilizados para visualiza��o de documentos
PROGRAMS = [('xpdf', ()),
            ('gv', ()),
            ('ggv', ())]

def build_report(report_class, *args):
    """ Fun��o respons�vel pela constru��o do relat�rio.
    Par�metros:

        - report_class: a classe utilizada para a constru��o do relat�rio,
          isto �, a classe criada pelo usu�rio (uma subclasse de
          ReportTemplate) que define os elementos � serem inseridos no 
          relat�rio e como eles podem ser constru�dos.
        - args: argumentos extras que podem ser passados � classe 
          especificada no par�metro report_class.
    """
    filename = '%s.pdf' % tempfile.mktemp() 
    report = report_class(filename, *args)
    report.save()
    return filename

def print_file(filename, printer=None, extra_opts=[]):
    """ Fun��o utilizada para impress�o de arquivos. Geralmente utilizada para
    impress�o do arquivo criado por uma chamada pr�via � fun��o build_report.
    Par�metros:

        - filename: o nome do arquivo a ser impresso.
        - printer: nome da impressora � ser utilizada; se n�o especificado, a
          impressora padr�o ser� utilizada.
        - extra_opts: par�metros *opcionais* que precisam ser passados ao 
          comando de impress�o do documento.
    """
    if not os.path.exists(filename):
        raise ValueError, "File %s not found" % filename

    if sys.platform == "win32":
        return print_preview(filename)
	
    options = " ".join(extra_opts)
    if printer:
        options += " -P%s" % printer
    ret = os.system("lpr %s %s" % (options, filename))
    os.remove(filename)
    return ret

def print_preview(filename, keep_file=0):
    """ Fun��o utilizada para visualiza��o de arquivos pdf e ps, geralmente
    criados por build_report. Alguns editores (e suas devidas op��es) est�o
    definidos na vari�vel PROGRAMS; o primeiro editor encontrado no sistema
    ser� utilizado. Parametros:

        - filename: o nome do arquivo � visualizar.
        - keep_file: TRUE, caso o arquivo deva ser salvo no disco ap�s sua
          visualiza��o.
    """
    if not os.path.exists(filename):
        raise OSError, "the file does not exist"

    path = os.environ['PATH'].split(':')

    # Open the file with the program registered for the PDF extension.
    if sys.platform == "win32": 
        os.system('start %s' % filename) 
        return

    for program, args in PROGRAMS:
        assert (type(program) is StringType) and (type(args) is TupleType)
        for part in path:
            full = os.path.join(part, program)
            if not os.access(full, os.R_OK|os.X_OK):
                continue
            if not os.fork():
                args = " ".join(args)
                os.system("%s %s %s" % (full, args, filename))
                if not keep_file:
                    os.remove(filename)
                # See http://www.gtk.org/faq/#AEN505 -- _exit()
                # keeps file descriptors open, which avoids X async
                # errors after we close the child window.
                os._exit(-1)
            return

    print "Could not find a pdf viewer, aborting"

