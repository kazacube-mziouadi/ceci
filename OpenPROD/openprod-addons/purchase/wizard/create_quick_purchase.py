# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class create_quick_purchase(models.TransientModel):
    """ 
        Wizard to create purchase quickly
    """
    _name = 'create.quick.purchase'
    _description = 'Wizard to create purchases quickly'
    _rec_name = 'date'
    
#    Demande de raphael mettre ce wizard en UoG et laisser le wizard de vente en UoV
#     @api.one
#     @api.depends('product_id', 'partner_id')
#     def _compute_sec_uom_id(self):
#         sec_uom_id = False
#         product = self.product_id
#         if product:
#             if self.partner_id:
#                 sinfo = product.get_sinfo(partner_id=self.partner_id.id, property_ids=False, state_dev=False)
#                 uoms = product.get_uoms(pinfo=sinfo or False, partner=self.partner_id, type='in', property_ids=False,
#                                     with_factor=True)
#                 if isinstance(uoms, dict) and uoms.get('sec_uom_id'):
#                     sec_uom_id = uoms['sec_uom_id'] 
#                 
#         self.sec_uom_id = sec_uom_id
    
    @api.one
    @api.depends('product_id')
    def _compute_uom_id(self):
        self.uom_id = self.uom_forced_id and self.uom_forced_id.id or self.product_id and self.product_id.uom_id and self.product_id.uom_id.id or False
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Date', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null',
                                 domain=[('purchase_ok', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='set null')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
#     sec_uom_id = fields.Many2one('product.uom', string='Purchases unity', ondelete='set null', compute='_compute_sec_uom_id')
    uom_id = fields.Many2one('product.uom', string='UoM', ondelete='set null', compute='_compute_uom_id')
    uom_forced_id = fields.Many2one('product.uom', string='UoM forced', required=False, ondelete='restrict')
    
    
    def write_intervention(self, new_purchase):
        return True


    @api.multi
    def create_quick_purchase(self):
        """
            Fonction permettant de créer rapidement un achat
        """
        action_struc = {}
        if self.product_id and self.partner_id:
            other_data = {}
            po_line = {self.product_id: {'uom_qty': self.quantity, 'uom_id': self.uom_id.id}}
            if self.env.context.get('affair_id'):
                po_line[self.product_id]['affair_id'] = self.env.context.get('affair_id')
            other_data.update(self.env.context.get('quick_purchase_other_data_order', {}))
            new_purchase = self.env['purchase.order'].create_purchase(self.partner_id, po_line, self.date, other_data, 'uom_qty')
            #Lien avec les actions. Si on retrouve l'id d'une action dans le context et que l'action n'est pas
            #liée à un objet, on la lie avec l'achat
            context = self.env.context
            if context.get('active_id'):
                if context.get('active_model') == 'calendar.event':
                    action = self.env['calendar.event'].browse(context['active_id'])
                    if action and not action.purchase_id:
                        action.write({'purchase_id': new_purchase.id})
                elif context.get('active_model') == 'stock.transfer.request':
                    action = self.env['stock.transfer.request'].browse(context['active_id']).wkf_cancel()
                    
            #Point d'entree pour la GMAO/SAV
            self.write_intervention(new_purchase)
            
        action_dict = get_form_view(self, 'purchase.purchase_order_see_form')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['res_id'] = new_purchase.id
            action_struc = action_struc[0]
              
        return action_struc
                    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Si on change le produit, on vide le partenaire
        """
        if self.product_id:
            self.partner_id = False
    
    
    @api.onchange('product_id', 'partner_id')
    def _onchange_calc_date(self):
        """
            Si le produit n'est pas en achat libre, on calcule la date planifiée en fonction
            du délai de livraison. Sinon, on affiche la date du jour
        """
        if self.product_id:
            today = fields.Date.today()
            if not self.product_id.free_purchase and self.partner_id:
                calendar = self.partner_id.calendar_id
                sinfo = self.product_id.get_sinfo(partner_id=self.partner_id.id, property_ids=False, state_dev=False)
                self.date = calendar.get_date(today, sinfo.delivery_delay)
            else:
                self.date = today
            
    
    @api.onchange('date', 'partner_id')
    def _onchange_check_date(self):
        """
            Au changement de la date, on vérifie que celle-ci fait bien partie du calendrier fournisseur
        """
        if self.date and self.partner_id:
            res = {'warning': {}}
            if self.partner_id.calendar_id:
                check_date = self.env['calendar.line'].search([('calendar_id', '=', self.partner_id.calendar_id.id),
                                                               ('start_date', '<=', self.date),
                                                               ('end_date', '>=', self.date)])
                if not check_date:
                    res['warning'] = {'title': _('Warning'), 'message': _('The selected date is not a business '
                                                                          'day for this supplier')}
                    return res
                
    
    
class res_partner(models.Model):
    _inherit = 'res.partner'
    
    def compute_suppinfo_search_args(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les fournisseurs du produit
            s'il n'est pas en achat libre
        """
        args2 = []
        for arg in args:
            match = False
            if arg[0] == 'supplierinfo_product_search':
                if arg[-1] and self.env['product.product'].browse(arg[-1]):
                    product = self.env['product.product'].browse(arg[-1])
                    if not product.free_purchase:
                        arg[0] = 'id'
                        arg[1] = 'in'
                        arg[-1] = [supplierinfo.partner_id.id for supplierinfo in product.sinfo_ids if supplierinfo.state == 'active']
                    else:
                        match = True
                        args2.append(('is_supplier', '=', True))
                else:
                    arg = []
             
            if not match:
                args2.append(arg)
 
        return args2
     
     
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        """
            Modification du search afin de n'afficher que les produits ayant le partenaire en référencement
        """
        args = args or []
        args_modified = self.compute_suppinfo_search_args(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
     
     
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search des partenaires
        """
        args = self.compute_suppinfo_search_args(args)
        if name:
            args = ['|', ('reference', operator, name), '|',('first_name', operator, name),
                     ('name', operator, name)] + args
        
        recs = self.search(args, limit=limit)
        return recs.name_get()
     
     
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_suppinfo_search_args(domain)
        return super(res_partner, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)