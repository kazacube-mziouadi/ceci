# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class wizard_add_resource_valid(models.TransientModel):
    _name = 'wizard.add.resource.valid'
    _rec_name = 'routing_line_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    resource_ids = fields.One2many('wizard.add.operation.resource2', 'operation_id',  string='resources')
    existing_resource_ids = fields.One2many('wizard.add.operation.resource4', 'operation_id',  string='Existing resources', readonly=True)
    
    
    @api.multi
    def action_validate(self):
        mrlr_obj = self.env['mrp.rl.resource']
        for wiz in self:
            for ex_line in wiz.existing_resource_ids:
                if ex_line.is_active:
                    rlv_rcs = mrlr_obj.search([('rl_category_id', '=', ex_line.rl_resource_category_id.id), ('resource_id', '=', ex_line.resource_id.id)])
                    if rlv_rcs:
                        rlv_rcs.write({'sequence': ex_line.sequence})
                else:
                    rlv_rcs = mrlr_obj.search([('rl_category_id', '=', ex_line.rl_resource_category_id.id), ('resource_id', '=', ex_line.resource_id.id)])
                    if rlv_rcs:
                        rlv_rcs.unlink()
                    
            sequences = []
            for line in wiz.resource_ids:
                ress = line.rl_resource_category_id
                sequences.extend(l.sequence for l in ress.rl_resource_ids)
    
            sequence = sequences and max(sequences) or 0
            for line in wiz.resource_ids:
                if not mrlr_obj.search([('rl_category_id', '=', line.rl_resource_category_id.id), ('resource_id', '=', line.resource_id.id)], limit=1):
                    sequence += 10
                    mrlr_obj.create({
                                        'sequence': sequence,
                                        'resource_id': line.resource_id.id,
                                        'name': line.resource_id.name,
                                        'rl_category_id': line.rl_resource_category_id.id
                                    })
        
        return {'type': 'ir.actions.act_window_close'}



class wizard_add_operation_resource2(models.TransientModel):
    _name = 'wizard.add.operation.resource2'
    _rec_name = 'rl_resource_category_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    rl_resource_category_id = fields.Many2one('mrp.rl.resource.category', string='Resource categ', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    operation_id = fields.Many2one('wizard.add.resource.valid', string='Operation', required=False, ondelete='cascade')
    resource_categ_id = fields.Many2one('mrp.resource.category', string='Resource category', required=False, ondelete='cascade')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('rl_resource_category_id')
    def onchange_resource_categ_id(self):
        self.resource_categ_id = self.rl_resource_category_id and self.rl_resource_category_id.category_id and self.rl_resource_category_id.category_id.id or False



class wizard_add_operation_resource4(models.TransientModel):
    _name = 'wizard.add.operation.resource4'
    _rec_name = 'rl_resource_category_id'
    _order = 'sequence ASC'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(string='Sequence resource', default=0, required=False)
    rl_resource_category_id = fields.Many2one('mrp.rl.resource.category', string='Resource categ', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    operation_id = fields.Many2one('wizard.add.resource.valid', string='Operation', required=False, ondelete='cascade')
    is_active = fields.Boolean(string='Active', default=True)

    
    @api.multi
    def up(self):
        for wiz in self:
            if wiz.sequence:
                wiz.write({'sequence': wiz.sequence - 10})
            
        return {'type':'ir.actions.act_window_dialog_reload'}
    
    @api.multi
    def down(self):
        for wiz in self:
            wiz.write({'sequence': wiz.sequence and wiz.sequence + 10 or 10})
                
        return {'type':'ir.actions.act_window_dialog_reload'}

    @api.multi
    def delete(self):
        self.write({'is_active': False})
        return {'type':'ir.actions.act_window_dialog_reload'}


