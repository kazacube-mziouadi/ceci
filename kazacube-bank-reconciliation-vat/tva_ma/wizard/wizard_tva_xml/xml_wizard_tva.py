# -*- encoding: UTF-8 -*-

from openerp import models, fields, api, _, exceptions
from dateutil.relativedelta import relativedelta
from dateutil import parser
from pyPdf import PdfFileWriter, PdfFileReader
import base64


class xml_tva_wizard(models.TransientModel):

    _name = "report.tva.xml.wizard"

    TVA_file = fields.Binary(string="TVA")
    tva_filename = fields.Char(string="Nom du fichier tva")

xml_tva_wizard()
