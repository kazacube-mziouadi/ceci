# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class mrp_mo_split_line(models.TransientModel):
    """ 
        ManufacturingOrder Split Line
    """
    _name = 'mrp.mo.split.line'
    _description = 'ManufacturingOrder Split Line'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_split_id = fields.Many2one('mrp.mo.split', string='MO Split', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')



class mrp_mo_split_line_qty(models.TransientModel):
    """ 
        Manufacturingorder Split Line qty
    """
    _name = 'mrp.mo.split.line.qty'
    _description = 'Manufacturingorder Split Line qty'
    _rec_name = 'mo_split_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_split_id = fields.Many2one('mrp.mo.split', string='MO Split', required=False, ondelete='cascade')
    new_qty = fields.Float(string='Quantity', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    date = fields.Datetime(string='Date', required=True, default=lambda self: fields.Datetime.now())
    mo_remainder_id = fields.Many2one('mrp.manufacturingorder', string='MO remainder', required=False, ondelete='cascade')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('new_qty')
    def _onchange_quantity(self):
        """
            Au changement de la nouvelle quantité
        """
        if self.new_qty < 0:
            self.new_qty = 0.0
            
            

class mrp_mo_split(models.TransientModel):   
    """ 
        ManufacturingOrder Split
    """
    _name = 'mrp.mo.split'
    _description = 'ManufacturingOrder Split'
    _rec_name = 'mo_id'
    
    
    @api.one
    @api.depends('quantity', 'line_qty_ids', 'line_qty_ids.new_qty')
    def _calc_field_remainder(self):
        new_qty = 0
        for line_qty in self.line_qty_ids:
            new_qty += line_qty.new_qty
            
        self.remainder = self.quantity - new_qty
    
    
    @api.one
    @api.depends('mo_id')
    def _quantity_compute(self):
        self.quantity = self.mo_id.quantity

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing Order', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', readonly=1, compute='_quantity_compute')
    remainder = fields.Float(string='Remainder', compute='_calc_field_remainder')
    line_ids = fields.One2many('mrp.mo.split.line', 'mo_split_id',  string='Work Orders')
    line_qty_ids = fields.One2many('mrp.mo.split.line.qty', 'mo_split_id',  string='Lines qty')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def split_mo_button(self):
        """ 
            Validation du split
        """
        mo_obj = self.env['mrp.manufacturingorder']
        wo_obj = self.env['mrp.workorder']
        mmslq_obj = self.env['mrp.mo.split.line.qty']
        for wiz in self:
            # Vérifie la cohérence des quantités
            if wiz.remainder > 0:
                mmslq_obj.create({'mo_remainder_id': wiz.mo_id.id,
                                  'mo_split_id': wiz.id,
                                  'new_qty': wiz.remainder,
                                  'date': '2010-01-01 01:00:00'})
            
            new_qty = 0
            for line_qty in wiz.line_qty_ids:
                new_qty += line_qty.new_qty
                
            if new_qty <= 0:
                raise except_orm('Error', 'New quantity must be greater than 0')
            if new_qty > wiz.quantity:
                raise except_orm('Error', 'New quantity must be less than old quantity')
            
            line_qty_rcs = mmslq_obj.search([('mo_split_id', '=', wiz.id)], order='date asc')
            mo_ids = [wiz.mo_id.id]
            mo_rcs = wiz.mo_id
            ctx = self.env.context.copy()
            ctx['return_mo_wo_splited'] = True
            ctx['no_label'] = True
            first = True
            last = False
            i = 0
            for line_qty in line_qty_rcs: 
                if line_qty.new_qty == 0:
                    raise except_orm('Error', _('The line must not be zero.'))
                
                if not last:
                    i += 1
                    next_line_qty = line_qty_rcs[i]
                    if next_line_qty == line_qty_rcs[-1]:
                        last = True 
                else:
                    next_line_qty = False
                    
                plannif_mo = False
                data_other = {} 
                if first and not line_qty.mo_remainder_id:
                    plannif_mo = True
                
                if next_line_qty:
                    data_other = {
                                  'requested_date': next_line_qty.date,
                                  'planned_start_date': next_line_qty.date,
                                  'planned_end_date': next_line_qty.date,} 
                
                first = False
                if mo_rcs.quantity/line_qty.new_qty != 1:
                    mo_wo_splited = mo_obj.with_context(ctx).split(mo_ids, mo_rcs.quantity / line_qty.new_qty, data_other=data_other)
                    mo_ids = [mo_wo_splited.keys()[0].id]
                    mo_rcs = mo_wo_splited.keys()[0]
                    if plannif_mo:
                        wo_obj.plannification_mo_at_earlier(line_qty.date, 
                                              wiz.mo_id, 
                                              is_sublevel=True, 
                                              is_procur_level_manufact=True,
                                              is_product_sublevel_manufact=True,
                                              is_procur_level_purchase=True,
                                              automatic_purchase=True,
                                              is_procur_sublevel_purchase=True,
                                              first_mo_id=False,
                                              is_delay_rm=False,
                                              change_resources=False, 
                                              no_modif_prio_date=False)
                    
                elif mo_rcs and wiz.mo_id.state not in ('draft', 'cancel'):
                    wo_obj.plannification_mo_at_earlier(line_qty.date, 
                                              mo_rcs, 
                                              is_sublevel=True, 
                                              is_procur_level_manufact=True,
                                              is_product_sublevel_manufact=True,
                                              is_procur_level_purchase=True,
                                              automatic_purchase=True,
                                              is_procur_sublevel_purchase=True,
                                              first_mo_id=False,
                                              is_delay_rm=False,
                                              change_resources=False, 
                                              no_modif_prio_date=False)
        return True
    
    
    