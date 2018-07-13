# coding: utf-8

from openerp import fields, models, api, _
from openerp.exceptions import except_orm


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.one
    @api.depends('customs_unit_id', 'uom_id', 'uom_qty')
    def _compute_customs_qty(self):
        """
            Calcul de la quantité pour la douane
        """
        customs_qty = 0
        customs_unit_rs = self.customs_unit_id
        if not customs_unit_rs:
            customs_unit_rs = self.product_id and self.product_id.customs_unit_id or False
        
        if customs_unit_rs:
            customs_qty = self.env['product.uom']._compute_qty_obj(customs_unit_rs, self.uom_qty, self.uom_id, with_raise=False, with_round=False)
        
        self.customs_qty = customs_qty
    
    
    def _get_states(self):
        return {
            'waiting': [('readonly', True)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Douane
    customs_price = fields.Float(string='Customs price', default=0.0, required=False, states=_get_states)
    customs_unit_id = fields.Many2one('product.uom', string='Customs unit', required=False, ondelete='restrict', states=_get_states)
    customs_currency_id = fields.Many2one('res.currency', string='Customs currency', required=False, ondelete='restrict', states=_get_states)
    customs_qty = fields.Float(string='Custom qty', default=0.0, compute='_compute_customs_qty', store=True, states=_get_states)
    is_customs_price = fields.Boolean(string='Custome price', default=False, hemlp='Manage a specific price for customs', states=_get_states)
    
    
    def onchange_product_id(self, product_id, move_type=False):
        """
            On récupère les valeurs douanières
        """
        res = super(stock_move, self).onchange_product_id(product_id=product_id, move_type=move_type)
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        
        res['is_customs_price'] = product_id.is_customs_price
        res['customs_price'] = product_id.customs_price
        res['customs_currency_id'] = product_id.customs_currency_id and product_id.customs_currency_id.id or False
        res['customs_unit_id'] = product_id.customs_unit_id and product_id.customs_unit_id.id or False
        return res
    
    
    @api.one
    def update_customs_price(self, customs_price=0, customs_currency_id=False, customs_unit_id=False, is_customs_price=False):
        """
            Fonction qui permet de mettre à jour les prix et la devise douane des moves
            :param: customs_price: Nouveau prix de douane
            :type: customs_price: float
            :param: customs_currency_id: Id de la devise du nouveau prix 
            :type: with_round: integer
        """
        if self.state == 'done':
            raise except_orm(_('Error'), _("You can't update a customs price of a done move"))
        
        self.write({
            'is_customs_price': is_customs_price, 
            'customs_price': customs_price, 
            'customs_currency_id': customs_currency_id, 
            'customs_unit_id': customs_unit_id
        })    
            
        return True