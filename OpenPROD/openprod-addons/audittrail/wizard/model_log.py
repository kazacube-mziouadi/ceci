# coding: utf-8
from openerp import models, fields, api

class model_log(models.TransientModel):
    """ 
    See all audit trail log for a model 
    """
    _name = 'audittrail.model_log'
    _description = 'See all audit trail log for a model'
    
    @api.model
    def default_get(self, fields_list):
        res = super(model_log, self).default_get(fields_list=fields_list)
        model_id = self.env.context.get('default_model_id')
        resource_id = self.env.context.get('resource_id')
        domain = [('rule_id.model_id', '=', model_id)]
        if resource_id:
            domain.append(('resource_id', '=', resource_id))
        res['audittrail_line_ids'] = self.env['audittrail.line'].search(domain).ids
        return res
    
    @api.one
    def _compute_lines(self):
        return False
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_id = fields.Many2one('ir.model', ondelete='cascade')
    audittrail_line_ids = fields.One2many('audittrail.line', compute='_compute_lines',  string='Lines')