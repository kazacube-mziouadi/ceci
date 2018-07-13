# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class create_quick_sale(models.TransientModel):
    """ 
        Wizard to create sale quickly
    """
    _name = 'create.quick.sale'
    _description = 'Wizard to create sales quickly'
    _rec_name = 'date'
    
    
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
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade',
                                 domain=[('purchase_ok', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    sec_uom_id = fields.Many2one('product.uom', string='Sale unity', ondelete='cascade', compute='_compute_sec_uom_id')
    

    @api.multi
    def create_quick_sale(self):
        """
            Fonction permettant de créer rapidement une vente
        """
        action_struc = {}
        if self.product_id and self.partner_id:
            other_data = {}
            so_line = {self.product_id: {'sec_uom_qty': self.quantity}}
            so_line[self.product_id].update(self.env.context.get('create_quick_sale_other_data', {}))
            other_data.update(self.env.context.get('quick_sale_other_data_order', {}))
            new_sale = self.env['sale.order'].create_sale(self.partner_id, so_line, self.date, other_data)
            #Lien avec les actions. Si on retrouve l'id d'une action dans le context et que l'action n'est pas
            #liée à un objet, on la lie avec la vente
            context = self.env.context
            if context.get('active_model') == 'calendar.event' and context.get('active_id'):
                action = self.env['calendar.event'].browse(context['active_id'])
                if action and not action.sale_id:
                    action.write({'sale_id': new_sale.id})
        
        action_dict = get_form_view(self, 'sale.sale_order_see_form')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['res_id'] = new_sale.id
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
            Si le produit n'est pas en vente libre, on calcule la date planifiée en fonction
            du délai de livraison du référencement fournisseur, sinon on calcule à partir
            du délai de livraison du produit
        """
        if self.product_id:
            today = fields.Date.today()
            if self.partner_id:
                calendar = self.partner_id.calendar_id
                if not self.product_id.free_sale:
                    cinfo = self.product_id.get_cinfo(partner_id=self.partner_id.id, property_ids=False)
                    self.date = calendar.get_date(today, cinfo and cinfo.delivery_delay or False)
                else:
                    self.date = calendar.get_date(today, self.product_id.free_delivery_delay)
                
            else:
                self.date = today
    
    
    @api.onchange('date', 'partner_id')
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
                
     
     
class res_partner(models.Model):
    _inherit = 'res.partner'
     
    def compute_custinfo_search_args(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les clients du produit
            s'il n'est pas en vente libre
        """
        args2 = []
        if not args:
            args = []
            
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'customerinfo_product_search':
                if arg[-1] and self.env['product.product'].browse(arg[-1]):
                    product = self.env['product.product'].browse(arg[-1])
                    if not product.free_sale:
                        arg[0] = 'id'
                        arg[1] = 'in'
                        arg[-1] = [custinfo.partner_id.id for custinfo in product.cinfo_ids]
                    else:
                        match = True
                        args2.append('|')
                        args2.append(('is_company', '=', False))
                        args2.append('&')
                        args2.append(('is_company', '=', True))
                        args2.append(('is_customer', '=', True))
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
        args_modified = self.compute_custinfo_search_args(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
     
     
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search des partenaires
        """
        args = self.compute_custinfo_search_args(args)
        if name:
            if operator in ('not like', 'not ilike'):
                args = [('name', operator, name), '|',('first_name', operator, name),
                     ('reference', operator, name)] + args
            else:
                args = ['|', ('reference', operator, name), '|',('first_name', operator, name),
                     ('name', operator, name)] + args
        
        recs = self.search(args, limit=limit)
        return recs.name_get()
     
     
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_custinfo_search_args(domain)
        return super(res_partner, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)