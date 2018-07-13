# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _



class wizard_priority_wo(models.TransientModel):
    """ 
        Wizard priority wo
    """
    _name = 'wizard.priority.wo'
    _description = 'Wizard priority wo'
    _rec_name = 'planning_priority'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_priority_wo, self).default_get(fields_list=fields_list)
        res['wo_ids'] = self.env.context.get('active_ids')
        return res

    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    planning_priority = fields.Integer(string='Planning priority', default=0, required=True)
    wo_ids = fields.Many2many('mrp.workorder', 'wizard_priority_wo_wo_rel', 'wiz_id', 'wo_id',  string='WOs')


    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_validate(self):
        """
            Bouton qui modifie le planning_priority
        """
        for wiz in self:
            wiz.wo_ids.write({'planning_priority': wiz.planning_priority})
            
        return True



class planning_priority_wo(models.TransientModel):
    """ 
        Planning priority wo
    """
    _name = 'planning.priority.wo'
    _description = 'Planning priority wo'
    _rec_name = 'type_priority'
    
    
    @api.model
    def _type_priority_get(self):
        return [
                ('series', _('Series')),
                ('parallel', _('Parallel')),
                       ]
    
    @api.model
    def default_get(self, fields_list):
        res = super(planning_priority_wo, self).default_get(fields_list=fields_list)
        res['wo_ids'] = self.env.context.get('active_ids')
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', required=True, default=lambda self: fields.Datetime.now())
    wo_ids = fields.Many2many('mrp.workorder', 'planning_priority_wo_rel', 'wiz_id', 'wo_id',  string='WOs', copy=True)
    type_priority = fields.Selection('_type_priority_get', string='Type of priority', required=True, default='series')
        
        
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_priority_wo(self):
        """
            Bouton qui plannifie les OFs par priorité
        """
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            if wiz.type_priority == 'parallel':
                first_resource_id = False
                for wo in wo_obj.search([('id', 'in', wiz.wo_ids.ids), ('first_resource_id', '!=', False)], order='first_resource_id asc, planning_priority asc'):
#                     if first_resource_id != wo.first_resource_id.id:
#                         date_temp = wiz.date
#                         num_temp = wo.planning_priority
#                         first_resource_id = wo.first_resource_id.id
                    
#                     if num_temp == wo.planning_priority:
#                         date_temp = wo.first_resource_id.calendar_id.get_date(date_temp, 0, hours=True)
#                     else:
#                         date_temp = wo.first_resource_id.calendar_id.get_date(date_temp, 1, hours=True)
#                         num_temp = wo.planning_priority
                    
                    date_temp = wo.first_resource_id.calendar_id.get_date(wiz.date, wo.planning_priority, hours=True)
                    dico_date_temp = wo.first_resource_id.calendar_id.get_dates(date_temp, wo.total_time_theo)
                    wo.write({'is_at_earlier': True, 'sandbox_planned_start_date': dico_date_temp['start_date'], 
                              'sandbox_planned_end_date': dico_date_temp['end_date'], 'asynchronous': True})
            
            
            else:
                first_resource_id = False
                for wo in wo_obj.search([('id', 'in', wiz.wo_ids.ids), ('first_resource_id', '!=', False)], order='first_resource_id asc, planning_priority asc'):
                    if first_resource_id != wo.first_resource_id.id:
                        date_temp = wiz.date
                        first_resource_id = wo.first_resource_id.id
            
                    dico_date_temp = wo.first_resource_id.calendar_id.get_dates(date_temp, wo.total_time_theo)
                    wo.write({'is_at_earlier': True, 'sandbox_planned_start_date': dico_date_temp['start_date'], 
                              'sandbox_planned_end_date': dico_date_temp['end_date'], 'asynchronous': True})
                    date_temp = dico_date_temp['end_date']
            
        return True
