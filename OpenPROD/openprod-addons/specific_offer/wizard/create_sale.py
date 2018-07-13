# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class create_sale_from_offer(models.TransientModel):
    """ 
        Wizard to create sale from the specific offer
    """
    _name = 'create.sale.from.offer'
    _description = 'Wizard to create from the specific offer'
    _rec_name = 'date'
    
    @api.model
    def default_get(self, fields_list):
        res = super(create_sale_from_offer, self).default_get(fields_list=fields_list)
        offer_id = self.env.context.get('active_id')
        if offer_id:
            offer = self.env['specific.offer'].browse(offer_id)
            res['product_id'] = offer.product_id.id
            res['partner_id'] = offer.partner_id.id
            res['offer_id'] = offer_id
            
        return res
    
    
    @api.one
    @api.depends('product_id', 'partner_id')
    def _compute_sec_uom_id(self):
        sec_uom_id = False
        product = self.product_id
        if product:
            if self.partner_id:
                cinfo = product.get_cinfo(partner_id=self.partner_id.id, property_ids=False)
                uoms = product.get_uoms(pinfo=cinfo or False, partner=self.partner_id, type='out', property_ids=False,
                                    with_factor=True)
                if isinstance(uoms, dict) and uoms.get('sec_uom_id'):
                    sec_uom_id = uoms['sec_uom_id'] 
                
        self.sec_uom_id = sec_uom_id
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Date', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null',
                                 domain=[('purchase_ok', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='set null')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    sec_uom_id = fields.Many2one('product.uom', string='Sale unity', compute='_compute_sec_uom_id')
    offer_id = fields.Many2one('specific.offer', string='Offer', required=False, ondelete='set null')
    
    
    @api.multi
    def create_sale_offer(self):
        """
            Fonction qui permet de créer la vente liée au partenaire et au produit
        """
        sale_obj = self.env['sale.order']
        data_obj = self.env['ir.model.data']
        offer_obj = self.env['specific.offer']
        for wizard in self:
            offer = wizard.offer_id
            if offer.partner_id and offer.product_id:
                #Création de la vente avec le produit et le partenaire
                so_line = {offer.product_id: {'option_lines_ids': [(0,0, {'option_id': x.option_id.id, 'price_unit': x.price_unit}) for x in offer.option_ids], 
                                              'variant_category_value_ids': [(6, 0, [y.id for y in offer.variant_value_ids])],
                                              'sec_uom_qty': wizard.quantity}}
                so_line[offer.product_id].update(offer_obj.add_product_line_values(offer))
                new_sale = sale_obj.create_sale(offer.partner_id, so_line, wizard.date, {})
                #On passe l'offre au statut validé et la CRM liée à "Gagnée"
                offer.state = 'validated'
                if offer.crm_id:
                    object_model, object_id = data_obj.get_object_reference('crm_openprod', 'crm_state_won')
                    if object_model and object_model == 'crm.state':
                        offer.crm_id.write({'state_id': object_id})
                
                #On renvoie la vue de la vente créée
                if new_sale:
                    action_dict = get_form_view(self, 'sale.sale_order_see_form')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()
                        action_struc[0]['res_id'] = new_sale.id
                        action_struc = action_struc[0]
                        return action_struc
                    
            return True

    
    @api.onchange('date')
    def _onchange_check_date(self):
        """
            Au changement de la date, on vérifie que celle-ci fait bien partie du calendrier de la société
        """
        if self.date:
            res = {'warning': {}}
            calendar = self.env.user.company_id.partner_id.calendar_id
            if calendar:
                check_date = self.env['calendar.line'].search([('calendar_id', '=', calendar.id),
                                                               ('start_date', '<=', self.date),
                                                               ('end_date', '>=', self.date)])
                if not check_date:
                    res['warning'] = {'title': _('Warning'), 'message': _('The selected date is not a business '
                                                                          'day')}
                    return res
                
     
