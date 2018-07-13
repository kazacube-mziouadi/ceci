# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp
import pytz
from datetime import datetime, timedelta, date



def convert_tz(date, t_from, t_to):
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    tz = pytz.timezone(t_from)
    date_user = tz.localize(date)
    tz1 = pytz.timezone(t_to)
    date_final = date_user.astimezone(tz1)
    date_final = datetime.strftime(date_final, '%Y-%m-%d %H:%M:%S')
    return date_final


class production_operator_time(models.TransientModel):
    """ 
    Production Operator Time, wizard qui permet d'imprimer l'analyse des temps de production
    """
    _name = 'production.operator.time'
    _description = 'Production Operator Time'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(production_operator_time, self).default_get(fields_list=fields_list)
        date_now = datetime.now()
        isocal = date_now.isocalendar()
        week_num = isocal[1]-1
        if week_num == 0:
            res['year_num'] = date_now.year-1
            res['week_num'] = 52
        else:
            res['year_num'] = date_now.year
            res['week_num'] = week_num
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    week_num = fields.Integer(string='Week', default=0, required=False)
    year_num = fields.Integer(string='Year', default=0, required=False)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    area_id = fields.Many2one('mrp.area', string='Area', required=False, ondelete='cascade')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')

    
    def get_week_dates(self, week, year):
        # Renvoie la date de débue et la date de fin d'une semaine
        res = {'start_date': False, 'end_date': False}
        date_format = '%Y-%m-%d %H:%M:%S'
        week_date = datetime.strptime('%04d-%02d-1' % (year, week), '%Y-%W-%w')
        user = self.env.user
        if date(year, 1, 4).isoweekday() > 4:
            res['start_date'] = (week_date - timedelta(days=7)).strftime(date_format)
            res['end_date'] = convert_tz((week_date - timedelta(seconds=1)).strftime(date_format), user.tz, 'UTC')
        else:
            res['start_date'] = (week_date).strftime(date_format)
            res['end_date'] = convert_tz((week_date + timedelta(days=7) - timedelta(seconds=1)).strftime(date_format), user.tz, 'UTC')
            
        return res
    
    
    @api.onchange('week_num', 'year_num')
    def onchange_week_num(self):
        res = {}
        if self.week_num and self.week_num > 53:
            res['warning'] = {'title': _('Warning'), 'message': _('Week number must be between 1 and 52.')}
            self.from_date = ''
            self.to_date = ''
        elif not self.year_num:
            date_now = datetime.now()
            year = date_now.year
            if self.week_num:
                res_get_week = self.get_week_dates(self.week_num, year)
                self.from_date = res_get_week['start_date']
                self.to_date = res_get_week['end_date']
        elif self.week_num and self.year_num:
            res_get_week = self.get_week_dates(self.week_num, self.year_num)
            self.from_date = res_get_week['start_date']
            self.to_date = res_get_week['end_date']
    
        return res
    
        
    @api.multi
    def button_report_time_prod(self):
        for wiz in self:
            data = {}
            data['model'] = 'mrp.workorder'
            from_date_str = '%s/%s/%s' %(wiz.from_date[8:10],wiz.from_date[5:7],wiz.from_date[0:4])
            to_date_str = '%s/%s/%s' %(wiz.to_date[8:10],wiz.to_date[5:7],wiz.to_date[0:4])
            data['jasper'] = {
                'date_from': from_date_str,        
                'date_to': to_date_str,
                'section': wiz.area_id and wiz.area_id.name or '',
                'num_sem': wiz.week_num,
                'num_year': wiz.year_num,
                'product': wiz.product_id and wiz.product_id.name or '',
                'mo': wiz.mo_id and wiz.mo_id.name or '',
                'customer': wiz.customer_id and wiz.customer_id.name or '',
                'operator': wiz.user_id and wiz.user_id.login or '',
                'machine': wiz.resource_id and wiz.resource_id.name or '',
                'no_filter': False
            }
            from_date = '%s 00:00:00'%(wiz.from_date)
            to_date = '%s 23:59:59'%(wiz.to_date)
            args_list = [('real_end_date','>=',from_date),('real_end_date','<=',to_date),('state','=','done')]
            if wiz.area_id:
                resource_rcs = self.env['mrp.resource'].search([('area_id','=',wiz.area_id.id)])
                if resource_rcs:
                    args_list.append(('first_resource_id','in',resource_rcs.ids))
                else:
                    raise except_orm(_('Error'), _("There is no line for this area."))
            
            if wiz.mo_id:
                args_list.append(('mo_id','=',wiz.mo_id.id))
            
            if wiz.product_id or wiz.customer_id:
                search_mo = []
                if wiz.product_id:
                    search_mo.append(('product_id','=',wiz.product_id.id))
                
                if wiz.customer_id:
                    search_mo.append(('customer_id','=',wiz.customer_id.id))
                    
                production_rcs = self.env['mrp.manufacturingorder'].search(search_mo)
                if production_rcs:
                    args_list.append(('mo_id','in',production_rcs.ids))
                else:
                    raise except_orm(_('Error'), _("There is no line for this product or this customer."))
            
            if wiz.user_id:
                timesheet_rcs = self.env['resource.timetracking'].search([('user_id','=',wiz.user_id.id)])
                if timesheet_rcs:
                    wo_ids = [x.wo_id.id for x in timesheet_rcs if x.wo_id]
                    if wo_ids:
                        args_list.append(('id','in',wo_ids))
                    else:
                        raise except_orm(_('Error'), _("There is no line for this operator."))
                else:
                    raise except_orm(_('Error'), _("There is no line for this operator."))
                
            if wiz.resource_id:
                args_list.append(('first_resource_id','=',wiz.resource_id.id))
            
            data_rcs = self.env['mrp.workorder'].search(args_list)
            if not data_rcs:
                raise except_orm(_('Error'), _("There is no line."))
            else:
                data['ids'] = data_rcs.ids
            
            report_rcs = self.env['jasper.document'].search([('report_unit' ,'=', 'production_operator_time_analysis')])
            if report_rcs:
                report = report_rcs[0]
                if report and report.report_id:
                    return {
                            'type': 'ir.actions.report.xml',
                            'report_name': report.report_id and report.report_id.report_name or '',
                            'datas': data,
                    }
            else: 
                raise except_orm(_('Error'), _("no report declared (production_operator_time_analysis)."))
        return True