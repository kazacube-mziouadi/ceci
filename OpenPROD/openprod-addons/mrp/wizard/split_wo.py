# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class mrp_wo_split_line(models.TransientModel):
    """ 
        WorkOrder Split Line
    """
    _name = 'mrp.wo.split.line'
    _description = 'WorkOrder Split Line'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_split_id = fields.Many2one('mrp.wo.split', string='WO Split', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    to_split = fields.Boolean(string='To split', default=False, help='Work orders will be splited to the last selected')
    

class mrp_wo_split_line_qty(models.TransientModel):
    """ 
        WorkOrder Split Line qty
    """
    _name = 'mrp.wo.split.line.qty'
    _description = 'WorkOrder Split Line qty'
    _rec_name = 'wo_split_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_split_id = fields.Many2one('mrp.wo.split', string='WO Split', required=False, ondelete='cascade')
    new_qty = fields.Float(string='Quantity', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    date = fields.Datetime(string='Date', required=True, default=lambda self: fields.Datetime.now())
    wo_remainder_id = fields.Many2one('mrp.workorder', string='Wo remainder', required=False, ondelete='cascade')
    
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



class mrp_wo_split(models.TransientModel):   
    """ 
        WorkOrder Split
    """
    _name = 'mrp.wo.split'
    _description = 'WorkOrder Split'
    _rec_name = 'wo_id'
    
    
    @api.one
    @api.depends('quantity', 'line_qty_ids', 'line_qty_ids.new_qty')
    def _calc_field_remainder(self):
        new_qty = 0
        for line_qty in self.line_qty_ids:
            new_qty += line_qty.new_qty
            
        self.remainder = self.quantity - new_qty

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', related='wo_id.quantity', readonly=1)
    remainder = fields.Float(string='Remainder Quantity', compute='_calc_field_remainder')
    line_ids = fields.One2many('mrp.wo.split.line', 'wo_split_id',  string='Next Work Orders')
    line_qty_ids = fields.One2many('mrp.wo.split.line.qty', 'wo_split_id',  string='Lines qty')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def split_wo_button(self):
        """ 
            Validation du split
        """
        wo_obj = self.env['mrp.workorder']
        mwslq_obj = self.env['mrp.wo.split.line.qty']
        for wiz in self:
            ids_to_split = []
            # Vérifie la cohérence des quantités
            if wiz.remainder > 0:
                mwslq_obj.create({'wo_remainder_id': wiz.wo_id.id,
                                  'wo_split_id': wiz.id,
                                  'new_qty': wiz.remainder,
                                  'date': '2010-01-01 01:00:00'})
                
            new_qty = 0
            for line_qty in wiz.line_qty_ids:
                new_qty += line_qty.new_qty
                
            if new_qty <= 0:
                raise except_orm('Error', _('Original WO Quantity must be greater than 0'))
            if new_qty > wiz.quantity:
                raise except_orm('Error', _('Original WO Quantity must be less than old quantity'))
                                
            last = False
            for line in wiz.line_ids:
                ids_to_split.append(line.wo_id.id)
                if line.to_split:
                    last = line.wo_id.id
                    
            # S'il y a une case cochée on ne split pas les suivants
            if last:
                ids_to_split = ids_to_split[:ids_to_split.index(last) + 1]
            else:
                ids_to_split = []
            
            qty_total_consommation = 0
            for consom in wiz.wo_id.workorder_consumption_ids:
                if consom.state == 'done':
                    qty_total_consommation += consom.quantity
                    
            qty_total_production = 0
            for produce in wiz.wo_id.workorder_produce_ids:
                if produce.state == 'done':
                    qty_total_production += produce.qty_ok
            
            if qty_total_production > qty_total_consommation:
                qty = qty_total_production
            else:
                qty = qty_total_consommation
            
            if qty > new_qty:
                raise except_orm('Error', _('Original WO Quantity must be greater than %f'%(qty)))
            
            ctx = self.env.context.copy()
            ctx['return_wo_splited'] = True
            # Ajout de l'opération depuis laquelle le split est fait
            ids_to_split.insert(0, wiz.wo_id.id)
            line_qty_rcs = mwslq_obj.search([('wo_split_id', '=', wiz.id)], order='date asc')
            quantity_qty = wiz.quantity
            first = True
            last = False
            i = 0
            for line_qty in line_qty_rcs:
                if not last:
                    i += 1
                    next_line_qty = line_qty_rcs[i]
                    if next_line_qty == line_qty_rcs[-1]:
                        last = True 
                else:
                    next_line_qty = False
                    
                if line_qty.new_qty == 0:
                    raise except_orm('Error', _('The line must not be zero.'))
                
                data_other = {} 
                if first and not line_qty.wo_remainder_id:
                    wiz.wo_id.write({'requested_date': line_qty.date,
                                     'planned_start_date': line_qty.date,
                                     'planned_end_date': line_qty.date,})
                if next_line_qty:
                    data_other = {'requested_date': next_line_qty.date,
                                  'planned_start_date': next_line_qty.date,
                                  'planned_end_date': next_line_qty.date,}
                if not first:
                    ctx['no_label_splited'] = True
                        
                first = False
                if quantity_qty/line_qty.new_qty != 1:
                    dic_wo_splited = wo_obj.with_context(ctx).split_wo(wo_obj.browse(ids_to_split), quantity_qty/line_qty.new_qty, data_other=data_other)
                    quantity_qty -= line_qty.new_qty
                    ids_to_split = dic_wo_splited
                elif ids_to_split and wiz.wo_id.state not in ('draft', 'cancel'):
                    wo_rcs = wo_obj.search([('id', 'in', ids_to_split)], order='sequence asc')
                    if wo_rcs:
                        wo_int_rcs = wo_obj.search([('mo_id', '=', wo_rcs[0].mo_id.id)], order='sequence asc')
                        if wo_rcs.ids != wo_int_rcs.ids:
                            date = line_qty.date
                            for wo in wo_rcs:
                                if wo.state == 'draft':
                                    wo.wkf_waiting(automatic_purchase=False, is_procur_level_manufact=True, is_procur_level_purchase=True, modif_state=True)
                                     
                                    wo.action_plannification_wo_at_earlier(date, automatic_purchase=False, is_procur_level_manufact=True, 
                                                                           is_procur_level_purchase=True, no_modif_prio_date=False)
                                    date = wo.planned_end_date
                       
            
        return True
    
    
    