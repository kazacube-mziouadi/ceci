# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class report_wo_planning(models.TransientModel):
    """ 
        Wizard Report WO Planning
    """
    _name = 'report.wo.planning'
    _description = 'Wizard Report WO Planning'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    week = fields.Integer(string='Week', default=0, required=False)
    area_id = fields.Many2one('mrp.area', string='Area', required=False, ondelete='cascade')
    date_planned = fields.Date(string='Planned Date')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    is_print = fields.Boolean(string='Is Print', default=False)
    year = fields.Integer(string='Year', default=0, required=False)
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validate(self):
        """
            Action generation planning 
        """
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            if not wiz.week and not wiz.date_planned:
                raise except_orm(_('Error'), _('Select at least a date or week number.'))

            s_args = []
            if wiz.week and not wiz.date_planned:
                if wiz.week < 10:
                    week = '0%d'%(wiz.week)
                else:
                    week = str(wiz.week)
                s_args.append(('week_number', '=', week))
                
            if wiz.year and not wiz.date_planned:
                s_args.append(('year', '=', str(wiz.year)))
                
            if wiz.area_id:
                s_args.append(('area_first_resource_id', '=', wiz.area_id.id))
                
            if wiz.resource_id:
                s_args.append(('first_resource_id','=',wiz.resource_id.id))
                
            if wiz.date_planned:
                date_planned_start = '%s 00:00:00' %(wiz.date_planned)
                date_planned_stop = '%s 23:59:59' %(wiz.date_planned)
                s_args.append(('planned_start_date', '>=', date_planned_start))
                s_args.append(('planned_start_date', '<=', date_planned_stop))
            
            wo_rcs = wo_obj.search(s_args)
            if not wo_rcs:
                raise except_orm(_('Error'), _('No workorder to print'))
            
            data = {}
            data['ids'] = wo_rcs.ids
            data['model'] = 'mrp.workorder'
            data['jasper'] = {
                        'week': wiz.week or 'false',
                        'area': wiz.area_id and wiz.area_id.name or 'false',
                        'date_planned': wiz.date_planned or 'false',
                  }
            
            report_rcs = self.env['jasper.document'].search([('report_unit' ,'=', 'production_planning_section')])
            if report_rcs:
                report = report_rcs[0]
                if report and report.report_id:
                    return {
                            'type': 'ir.actions.report.xml',
                            'report_name': report.report_id and report.report_id.report_name or '',
                            'datas': data,
                    }
            else: 
                raise except_orm(_('Error'), _("no report declared (production_planning_section)."))
            
            return {'type': 'ir.actions.act_window_close'}
    
    
    