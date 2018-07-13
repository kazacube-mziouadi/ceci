# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm

class assign_label_wizard(models.TransientModel):
    """ 
    Assign label
    """
    _name = 'assign.label.wizard'
    _description = 'Assign label'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'rel_assign_label_wizard_label', 'wizard_id', 'label_id', string='Labels')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(assign_label_wizard, self).default_get(fields_list=fields_list)
        move = self.env['stock.move'].browse(self.env.context.get('active_id'))
        if move:
            res['move_id'] = move.id
            res['warehouse_id'] = move.warehouse_id.id
            res['product_id'] = move.product_id.id
            
        return res
    
    
    @api.multi
    def assign_label(self):
        # TODO: tester les perfs si lent SQL
        # Lors de l'affectation interdiction de prendre une etiquette deja liée à un move ni done ni cancel appartenant à un picking
        # Remplacé par l'état "Réservé" sur les étiquettes mais laissé par sécurité
        move_same_label_ids = self.env['stock.move.label'].search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                                   ('move_id.picking_id', '!=', False), 
                                                                   ('label_id', 'in', self.label_ids.ids)], limit=1)
        if move_same_label_ids:
            raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
        
        ctx = self.env.context.copy()
        if self.move_id.type == 'in':
            ctx['authorize_return'] = True
            
        self.move_id.with_context(ctx).assign_label(self.label_ids, with_scrap=False)
        return False
    
    
    @api.multi
    def assign_inactive_label(self):
        # TODO: tester les perfs si lent SQL
        # Lors de l'affectation interdiction de prendre une etiquette deja liée à un move ni done ni cancel appartenant à un picking
        # Remplacé par l'état "Réservé" sur les étiquettes mais laissé par sécurité
        move_same_label_ids = self.env['stock.move.label'].search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                                   ('move_id.picking_id', '!=', False), 
                                                                   ('label_id', 'in', self.label_ids.ids)], limit=1)
        if move_same_label_ids:
            raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                
        self.move_id.assign_label(self.label_ids, with_scrap=False, inactive=True)
        return False
    


class add_move_label_wizard(models.TransientModel):
    """ 
    Assign label
    """
    _name = 'add.move.label.wizard'
    _description = 'Add move label'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'rel_add_move_label_wizard_label', 'wizard_id', 'label_id', string='Labels')
    is_declared_pf = fields.Boolean(string='Declared PF', default=False)
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_move_label_wizard, self).default_get(fields_list=fields_list)
        move = self.env['stock.move'].browse(self.env.context.get('active_id'))
        if move:
            res['move_id'] = move.id
            res['warehouse_id'] = move.warehouse_id and move.warehouse_id.id or (move.type == 'in' and move.location_id.warehouse_id.id) or (move.type == 'out' and move.location_dest_id.warehouse_id.id) or False 
            res['product_id'] = move.product_id.id
            
        return res
    
    
    @api.multi
    def add_move_label(self):
        # TODO: tester les perfs si lent SQL
        # Lors de l'affectation interdiction de prendre une etiquette deja liée à un move ni done ni cancel appartenant à un picking
        # Remplacé par l'état "Réservé" sur les étiquettes mais laissé par sécurité
        for wiz in self:
            move_label_obj = self.env['stock.move.label']
            move_same_label_ids = move_label_obj.search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                         ('move_id.picking_id', '!=', False), 
                                                         ('label_id', 'in', wiz.label_ids.ids)], limit=1)
            if move_same_label_ids:
                raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                    
            move_label_obj.create_move_label(wiz.label_ids, move_rs=wiz.move_id)
            wiz.move_id.prioritizing()
        return False
    

    
class assing_um_label_wizard(models.TransientModel):
    """ 
    Assign um label
    """
    _name = 'assing.um.label.wizard'
    _description = 'Assign um label'
    _rec_name = 'um_label_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(assing_um_label_wizard, self).default_get(fields_list=fields_list)
        res['label_ids'] = self.env.context.get('active_ids')
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    label_ids = fields.Many2many('stock.label', 'rel_assing_um_label_wizard_label', 'wizard_id', 'label_id', string='Labels')
    um_label_id = fields.Many2one('stock.label', string='Um label', required=True, ondelete='cascade')
    

    @api.multi
    def assing_um_label(self):
        for wiz in self:
            wiz.label_ids.assign_um_label(wiz.um_label_id)
                
        return False



class assing_uc_label_wizard(models.TransientModel):
    """ 
    Assign uc label
    """
    _name = 'assing.uc.label.wizard'
    _description = 'Assign uc label'
    _rec_name = 'um_label_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    um_label_id = fields.Many2one('stock.label', string='Um label', required=True, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'rel_assing_uc_label_wizard_label', 'wizard_id', 'label_id', string='Labels')
    

    @api.multi
    def assing_uc_label(self):
        for wiz in self:
            if wiz.label_ids:
                wiz.label_ids.assign_um_label(wiz.um_label_id)
                
        return False







