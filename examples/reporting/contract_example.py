#!/usr/bin/env python
from sys import path
path.insert(0, '..')

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from stoqlib.reporting import  build_report, print_preview
from stoqlib.reporting.printing import ReportTemplate
from stoqlib.reporting.default_style import STYLE_SHEET

class ContractExample(ReportTemplate):
    def __init__(self, filename):
        ReportTemplate.__init__(self, filename, "", do_footer=0, topMargin=0,
                                bottomMargin=0)
        self.add_title("Termo de Compromisso de Est�gio")
        self.add_info_table()
        self.add_blank_space(10)
        self.add_contract_body()

    def create_extra_styles(self):
        styles = [ParagraphStyle("JustifyParagraph",
                                 fontName="Helvetica",
                                 fontSize=10,
                                 leading=11,
                                 alignment=TA_JUSTIFY,
                                 spaceAfter=6)]
        for style in styles:
            STYLE_SHEET.add(style)
    
    def add_info_table(self):
        rows = [["Concedente:", ""],
                ["Endere�o:", ""],
                ["Estagi�rio:", ""],
                ["Institui��o de Ensino:", ""],
                ["Endere�o:", ""],
                ["N�vel:", ""],
                ["Curso:", ""]]
        self.add_data_table(rows)

    def add_contract_body(self):
        contract_body = [
            ("As Partes acima justificadas assinam o presente Termo de "
             "Compromisso regido pelas condi��es estabelecidas no "
             "Instrumento Jur�dico celebrado com a Institui��o de Ensino e "
             "mediante as seguintes condi��es:"),
            ("1- O prop�sito do presente est�gio � propiciar ao estagi�rio(a) "
             "treinamento pr�tico, aperfei�oamento t�cnico, cultural, "
             "cient�fico e de relacionamento humano, como complementa��o do "
             "ensino ou aprendizagem a serem planejadas de conformidade com "
             "os programas e calend�rios escolares."),
            ("2 - A jornada de atividade do(a) estagi�rio(a), compat�veis "
             "com o seu hor�rio escolar e com o hor�rio da CONCEDENTE, Ter� "
             "uma carga de _______ horas semanais. O termo de compromisso "
             "ter� in�cio em ____________________ e t�rmino em "
             "____________________, podendo ser interrompido a qualquer "
             "momento, unilateralmente, mediante comunica��o escrita. Nos "
             "per�odos de f�rias escolares, a jornada de est�gio ser� "
             "estabelecida de comum acordo entre o(a) estagi�rio(a) e a "
             "CONCEDENTE, com o conhecimento da Institui��o de Ensino "
             "envolvida."),
            ("3 - Fica estabelecida a Bolsa de Est�gio de R$ ________,00 por "
             "m�s."),
            ("4 - O presente est�gio n�o cria v�nculo empregat�cio de qualquer "
             "natureza nos termos de legisla��o aplic�vel em vigor. Na "
             "vig�ncia deste compromisso, o(a) estagi�rio(a) compromete-se a "
             "observar as normas de seguran�a bem como as instru��es "
             "aplic�veis a terceiros."),
            ("A CONCEDENTE incluir� o(a) estagi�rio(a), em uma ap�lice de "
             "seguros de acidentes pessoais. Se solicitado pela Institui��o de "
             "Ensino do(a) estagi�rio(a), a CONCEDENTE expedir� uma Declara��o"
             "de Est�gio."),
            ("5 - O(a) estagi�rio(a) dever� informar de imediato e por "
             "escrito � CONCEDENTE, qualquer fato que interrompa, suspenda ou "
             "cancele sua matr�cula na Institui��o de Ensino interveniente, "
             "ficando ele respons�vel de quaisquer despesas causadas pela "
             "aus�ncia dessa informa��o."),
            ("6 - E por estarem de comum acordo com as condi��es acima, "
             "firmam o presente compromisso em tr�s vias de igual teor.")]

        self.create_extra_styles()
        map(lambda t: self.add_paragraph(t, style="JustifyParagraph"),
            contract_body)
        self.add_blank_space(20)
        self.add_paragraph("Data:", style="JustifyParagraph")
        self.add_blank_space(10)
        self.add_paragraph("Testemunhas:", style="JustifyParagraph")

        self.add_signatures(["Assinatura do(a) Estagi�rio(a)",
                             "Respons�vel Legal"], height=20)
        self.add_signatures(["Respons�vel Legal", "Institui��o de Ensino"])

filename = build_report(ContractExample)
print_preview(filename)

