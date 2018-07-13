# -*- coding: utf-8 -*-

from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import except_orm


class res_users(models.Model):
    _inherit = 'res.users'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    context_printer_medium_id = fields.Many2one('printers.list', string='Printer 2', required=False, ondelete='restrict', help='res.users.context_printer_medium_id')
    context_printer_small_id = fields.Many2one('printers.list', string='Printer 3', required=False, ondelete='restrict', help='res.users.context_printer_small_id')
    context_printer_4_id = fields.Many2one('printers.list', string='Printer 4', required=False, ondelete='restrict', help='res.users.context_printer_4_id')
    context_printer_5_id = fields.Many2one('printers.list', string='Printer 5', required=False, ondelete='restrict', help='res.users.context_printer_4_id')


class printers_report(models.Model):
    _inherit = 'printers.report'
    
    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    jasper_id = fields.Many2one('jasper.document', string='Jasper document', required=False, ondelete='cascade')
    report_id = fields.Many2one('ir.actions.report.xml', string='Report', related='jasper_id.report_id', readonly=True)
    
    
    
    def do_print(self, ids_to_print, report_xml_id_str):
        super(printers_report, self).do_print(ids_to_print, report_xml_id_str)
        report_active = True
        printer_id = False
        report_id = False

        print_report_rs = self.env.ref(report_xml_id_str)
        if print_report_rs:
            report_active = print_report_rs.active_report
            report_id = print_report_rs.report_id.id
            printer_type_id = print_report_rs.printer_type_id

        if not report_id and report_active:
            raise except_orm(_('Error'), _('Report not found.'))

        user = self.env.user
        if printer_type_id:
            if user.context_printer_id and user.context_printer_id.type_id and user.context_printer_id.type_id.id == printer_type_id.id:
                printer_id = user.context_printer_id
            elif user.context_printer_medium_id and user.context_printer_medium_id.type_id and user.context_printer_medium_id.type_id.id == printer_type_id.id:
                printer_id = user.context_printer_medium_id
            elif user.context_printer_small_id and user.context_printer_small_id.type_id and user.context_printer_small_id.type_id.id == printer_type_id.id:
                printer_id = user.context_printer_small_id
            elif user.context_printer_4_id and user.context_printer_4_id.type_id and user.context_printer_4_id.type_id.id == printer_type_id.id:
                printer_id = user.context_printer_4_id
            elif user.context_printer_5_id and user.context_printer_5_id.type_id and user.context_printer_5_id.type_id.id == printer_type_id.id:
                printer_id = user.context_printer_5_id
        else:
            if user.context_printer_id:
                printer_id = user.context_printer_id

        if not printer_id:
            if printer_type_id:
                raise except_orm(_('Error'), _('No printer %s type found for this user.') % (printer_type_id.name))
            else:
                raise except_orm(_('Error'), _('No default printer found for this user.'))

        if report_active:
            printer_id.send_printer(report_id, ids_to_print)

        return True

    @api.multi
    def unlink(self):
        raise except_orm(_('Error'), _('You can not delete any record.'))
        return True
