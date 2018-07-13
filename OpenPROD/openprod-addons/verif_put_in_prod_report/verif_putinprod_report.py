# -*- coding: utf-8 -*-
from openerp import models, api, _, fields
from openerp import netsvc
from openerp.exceptions import ValidationError


class verif_putinprod_report(models.Model):
    _name = 'verif.putinprod.report'


    @api.model
    def _get_state(self):
        return [
            ('declared', _('Declared')), 
            ('progress', _('In progress')),
            ('verification', _('Verification')),
            ('done', _('Done'))
        ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256)
    date = fields.Date(string='Date', default=lambda *a: fields.Date.today())
    code_rev = fields.Char(string='Revison code', size=256)
    jasper_rev = fields.Char(string='Revison jasper', size=256)
    printer = fields.Boolean(string='Print', default=True)
    printer_id = fields.Many2one('printers.list', string='Printer')
    line_ids = fields.One2many('verif.putinprod.report.line', 'verif_id', string='Lines')
    state = fields.Selection(selection='_get_state', string='State', default='declared')
    
    
    @api.multi
    def action_reset(self):
        self.write({'code_rev': '', 'jasper_rev': '', 'state': 'declared'})
        line_ids = self.env['verif.putinprod.report.line'].search([('verif_id', 'in', self.ids)])
        if line_ids:
            line_ids.write({
                'state': 'declared',
                'report_init': False,
                'report_final': False,
                'report_init_name': '',
                'report_final_name': ''
            })
            
        return True
    
    
    @api.multi
    def action_impression(self):
        for report in self:
            report.line_ids.action_impression_line()
            if report.state == 'declared' and report.line_ids:
                report.write({'state':'progress'})
                return True
                
            if report.state == 'progress' and report.line_ids:
                report.write({'state':'verification'})
                
        return True
    
    
        
class verif_putinprod_report_line(models.Model):
    _name = 'verif.putinprod.report.line'


    @api.model
    def _get_state(self):
        return [
            ('declared', _('Declared')), 
            ('printed_before', _('Printed before put in prod')),
            ('printed_after', _('Printed after put in prod')),
            ('validation', _('Validation test')),
            ('error', _('Error'))
        ]


    @api.model
    def _get_recording_type(self):
        return [
           ('id', _('ID')), 
           ('domain', _('Domain'))
        ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256)
    verif_id = fields.Many2one('verif.putinprod.report', string='Put in prod report', ondelete='cascade')
    jasper_id = fields.Many2one('jasper.document', string='Jasper document', required=True, ondelete='cascade')
    recording_type = fields.Selection(selection='_get_recording_type', string='Type', required=True, default='id')
    recording_id = fields.Integer('ID')
    recording_domain = fields.Text('Domain')
    limit = fields.Integer(string='Limit', help='Set 0 to disable limit')
    report_init = fields.Binary(string='Report initial')
    report_init_name = fields.Char(string='Report init name', size=128)
    report_final = fields.Binary(string='Report final')
    report_final_name = fields.Char(string='Report final name', size=128)
    state = fields.Selection(selection='_get_state', string='State', default='declared')
    
    
    def get_ids(self, line):
        if line.recording_type == 'id':
            res = [line.recording_id]
            error = False
        else:
            try:
                res = [rc.id for rc in self.env[line.jasper_id.model_id.model].search(eval(line.recording_domain), limit=line.limit > 0 and line.limit or None)]
                error = False
            except:
                res = []
                error = True
                
        return res, error
    
    
    @api.multi
    def action_test_get_ids(self):
        for line in self:
            res, error = self.get_ids(line)
            if error:
                raise ValidationError(_('Domain error.'))
            else:
                raise ValidationError(_('Domain validate.'))
            
        return True
    
    
    @api.multi
    def only_print_line(self):
        for line in self:
            recording_ids, error = line.get_ids(line)
            if error:
                raise ValidationError(_('Domain error.'))
            else:
                try:
                    if not line.verif_id.printer_id:
                        raise ValidationError(_('Select printer.'))
                    
                    if not line.jasper_id.report_id:
                        raise ValidationError(_('Select report.'))
                    
                    line.verif_id.printer_id.send_printer(line.jasper_id.report_id.id, recording_ids)
                except:
                    raise ValidationError(_('Error Print.'))
                
        return True
    
    
    @api.multi
    def action_impression_line(self):
        for line in self:
            recording_ids, error = line.get_ids(line)
            impression = False
            if line.jasper_id and not error:
                try:
                    (print_commands, format), model_report, report_binary, name_report = self.create_pdf(line.jasper_id, recording_ids, line.state)
                    if line.state == 'declared' or line.state == 'error':
                        impression = True
                        line.write({'report_init':report_binary, 'report_init_name':name_report,'state':'printed_before'})
                    elif line.state == 'printed_before':
                        impression = True
                        line.write({'report_final':report_binary, 'report_final_name':name_report, 'state':'printed_after'})
                    elif line.state == 'printed_after':
                        impression = True
                        
                    if line.verif_id.printer and impression:
                        if not line.verif_id.printer_id:
                            raise ValidationError(_('Select printer.'))
                        
                        if not line.jasper_id.report_id:
                            raise ValidationError(_('Select report.'))
                        
                        line.verif_id.printer_id.send_printer(line.jasper_id.report_id.id, recording_ids)
                        
                except:
                    line.write({'state': 'error'})
                    
            elif error:
                line.write({'state': 'error'})
                
        return True
    
    
    @api.multi
    def action_validation(self):
        for line in self:
            line.write({'state':'validation'})
            
        return True
    
    
    def create_pdf(self, doc_jasper_rc, res_ids, state):
        today = fields.Date.today()
        if doc_jasper_rc:
            xml_report_to_print_rc = doc_jasper_rc.report_id
            if xml_report_to_print_rc:
                report_service = netsvc.LocalService('report.' + xml_report_to_print_rc.report_name)
                datas = {'ids': res_ids, 'model': xml_report_to_print_rc.model}
                if 'jasper' in self.env.context:
                    datas['jasper'] = self.env.context['jasper']
                
                (print_commands, format) = report_service.create(self.env.cr, self.env.uid, res_ids, datas)
                attachments = {}
                if state == 'declared':
                    name_report = '%s_%s_init.%s'%(doc_jasper_rc.name,today, format)
                else:
                    name_report = '%s_%s_final.%s'%(doc_jasper_rc.name,today, format)
                    
                attachments[name_report] = print_commands
                report_binary = False
                for fname, fcontent in attachments.iteritems():
                    report_binary = fcontent and fcontent.encode('base64')
                    
                return (print_commands, format), xml_report_to_print_rc.report_name, report_binary, name_report
            
        return False
    
    
    @api.multi
    def write(self, values):
        res = super(verif_putinprod_report_line, self).write(values)
        report_dic = {}
        for line in self:
            if line.verif_id not in report_dic:
                report_dic[line.verif_id.id] = True
                
            if line.state != 'validation':
                report_dic[line.verif_id.id] = False
                
        if report_dic:
            report_ids = [x for x in report_dic if report_dic[x] == True]
            if report_ids:
                self.env['verif.putinprod.report'].browse(report_ids).write({'state':'done'})
                
        return res