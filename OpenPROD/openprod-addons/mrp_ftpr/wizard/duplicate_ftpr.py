# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class duplicate_ftpr(models.TransientModel):
    """ 
    Wizard qui permet de dupliquer une FTPR
    """
    _name = 'duplicate.ftpr'
    _rec_name = 'ftpr_id'
    _description = 'Wizard qui permet de dupliquer une FTPR'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(duplicate_ftpr, self).default_get(fields_list=fields_list)
        vals = {
            'ftpr_id': self._context.get('active_id')
        }
        res.update(vals)
        return res

    
    @api.model
    def _type_get(self):
        return [
                ('simple', _('Simple - Same product')),
                ('product', _('Product - other product')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_id = fields.Many2one('mrp.ftpr', string='Ftpr', required=False, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
    copy_complaints = fields.Boolean(string='Copy link to complaints', default=True)
    copy_instruc_controls = fields.Boolean(string='Copy instructions and controls', default=True)
    copy_ope_attach = fields.Boolean(string='Copy operations attachments', default=True)
    type = fields.Selection('_type_get', string='Type', default='simple', required=True)
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_ducplicate(self):
        """ 
            Duplication FTPR
        """
        for wiz in self:
            default = {'state': 'draft'}
            context = self.env.context.copy()
            context['duplication'] = True
            if wiz.type == 'product':
                ftpr_bom_rcs = wiz.bom_id.copy()
                default['ftpr_bom_id'] = ftpr_bom_rcs.id
                
            new_ftpr_rcs = wiz.ftpr_id.with_context(context).copy(default)
            new_ftpr_rcs.routing_line_ids.write({'routing_id': new_ftpr_rcs.routing_id.id})
            new_ftpr_rcs.write({'routing_ids': [(6, 0, [new_ftpr_rcs.routing_id.id])]})
            if not wiz.copy_complaints or not wiz.copy_instruc_controls or not wiz.copy_ope_attach:
                for routing_line in new_ftpr_rcs.routing_line_ids:  
                    if not wiz.copy_complaints:
                        routing_line.complaint_ids.unlink()
                        
                    if not wiz.copy_instruc_controls:
                        routing_line.consign_ids.unlink()
                        routing_line.quality_control_ids.unlink()
                    
                    if not wiz.copy_ope_attach:
                        routing_line.document_ids.unlink()
                
            return {
                    'name': 'FTPR',
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'mrp.ftpr',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': new_ftpr_rcs.id,
                }

    
    