# -*- coding: utf-8 -*-

from openerp import models
from openerp import fields
from openerp import api


class printers_report(models.Model):

    """
    Manages printing reports
    """
    _name = 'printers.report'
    _description = 'List of printing reports'

    _rec_name = 'report_id'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    report_id = fields.Many2one('ir.actions.report.xml', string='Report', required=False, ondelete='cascade', help="")
    model_id = fields.Many2one('ir.model', string='Model', required=False, ondelete='cascade', help="")
    printer_type_id = fields.Many2one('printers.type', string='Printer type', required=False, ondelete='restrict', help="")
    description = fields.Text(string='Description', help="")
    active_report = fields.Boolean(string='Active', default=False, help="")

    def do_print(self, ids_to_print, report_xml_id_str):
        return True

