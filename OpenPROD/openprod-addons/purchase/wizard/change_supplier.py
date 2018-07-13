# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod import utils

class change_purchase_supplier(models.TransientModel):
    """ 
        Wizard which allow to change supplier in a purchase
    """
    _name = 'change.purchase.supplier'
    _description = 'Wizard which allow to change supplier in a purchase'
    _rec_name = 'purchase_line_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null', readonly=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', required=False, ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='set null', readonly=True)
    supplier_id = fields.Many2one('res.partner', string='Actual supplier', required=False, ondelete='set null', readonly=True)
    need_date = fields.Date(string='Need date', readonly=True)
    need_qty = fields.Float(string='Need quantity', default=0.0, required=False, readonly=True)
    actual_qty = fields.Float(string='Actual quantity (in purchase unity)', default=0.0, required=False, readonly=True)
    origin = fields.Char(string='Origin', size=32, required=False, readonly=True)
    uom_id = fields.Many2one('product.uom', string='Purchase unity', required=False, ondelete='set null', readonly=True)
    supplierinfo_ids = fields.Many2many('product.supplierinfo', 'change_supplierinfo_rel', 'change_supplier_id', 
                                        'supplierinfo_id', string='Supplier information', readonly=True)
    new_supplierinfo_id = fields.Many2one('product.supplierinfo', string='New supplier', required=False, ondelete='set null')
    new_supplier_id = fields.Many2one('res.partner', string='New supplier', required=False, ondelete='set null', 
                                      domain=[('is_supplier', '=', True)])
    free_purchase = fields.Boolean(string='Free purchase', default=False)
    property_ids = fields.Many2many('purchase.property', string='Properties')
    
    
    @api.onchange('property_ids')
    def _onchange_property_ids(self):
        self.new_supplierinfo_id = False
        
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_purchase_supplier, self).default_get(fields_list=fields_list)
        po_line_id = self.env.context.get('active_id')
        if po_line_id:
            po_line = self.env['purchase.order.line'].browse(po_line_id)
            res['purchase_line_id'] = po_line_id
            res['purchase_id'] = po_line.purchase_order_id.id
            res['product_id'] = po_line.product_id.id
            res['supplier_id'] = po_line.purchase_partner_id and po_line.purchase_partner_id.id
            res['need_date'] = po_line.need_date
            res['need_qty'] = po_line.quantity
            res['actual_qty'] = po_line.sec_uom_qty
            res['origin'] = po_line.source
            res['uom_id'] = po_line.sec_uom_id.id
            if not po_line.product_id.free_purchase:
                res['free_purchase'] = False
                supplier_info_ids = [x.id for x in po_line.product_id.sinfo_ids if x.state != 'obsolete']
                res['supplierinfo_ids'] = supplier_info_ids
                property_ids = [x.id for x in po_line.property_ids]
                res['property_ids'] = property_ids
            else:
                res['free_purchase'] = True
            
        return res
    
    
    @api.multi
    def action_change_purchase_supplier(self):
        """
            Fonction permettant de modifier le fournisseur d'un achat
        """
        for wizard in self:
            new_vals = {}
            property_ids = False
            purchase_line_rs = wizard.purchase_line_id
            #On passe l'origine du wizard dans la nouvelle commande d'achat
            other_data = {'source_document': wizard.origin}
            #Si le produit est en achat libre on récupère le fournisseur sélectionné
            if wizard.free_purchase:
                partner = wizard.new_supplier_id
            #Si le produit n'est pas en achat libre, on récupère le fournisseur du référencement
            #fournisseur sélectionné
            else:
                partner = wizard.new_supplierinfo_id.partner_id
                if wizard.new_supplierinfo_id.property_ids:
                    property_ids = wizard.new_supplierinfo_id.property_ids.ids
            
            #Création de l'achat
            new_purchase = self.env['purchase.order'].create_purchase(partner.id, False, wizard.need_date, other_data)
            #Modification de la ligne d'achat et appel des onchanges
            new_vals['property_ids'] = property_ids
            new_vals['purchase_order_id'] = new_purchase.id
            res = purchase_line_rs.onchange_product_id(product_id=purchase_line_rs.product_id, purchase_order=new_purchase,
                                                 send_quantity=wizard.actual_qty, force_qty=True)
            new_vals.update(utils.transform_to_ids(purchase_line_rs, res))
            purchase_line_rs.write(new_vals)
            purchase_line_rs._onchange_sec_uom_qty(with_warning=False)
            #Suppression de l'achat s'il n'y a plus de ligne
            if not wizard.purchase_id.purchase_order_line_ids:
                wizard.purchase_id.unlink()
            
            #On retourne le nouvel achat créé
            if new_purchase:
                action_dict = get_form_view(self, 'purchase.purchase_order_see_form')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['res_id'] = new_purchase.id
                    action_struc = action_struc[0]
                      
                return action_struc
            else:
                return {'type': 'ir.actions.act_window_close'}



class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
     
     
    def compute_domain_args_supplierinfo(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les référencements fournisseurs du O2M
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
             
            if arg[0] == 'supplierinfo_in_supplierinfo_ids':
                arg[0] = 'id'
                supplier_info_list = arg[-1]
                arg[-1] = []
                for list_supplier in supplier_info_list:
                    if len(list_supplier) >= 3:
                        arg[-1] += list_supplier[2]
                 
            elif arg[0] == 'supplierinfo_in_property_ids':
                arg[0] = 'id'
                properties = arg[2][1]
                sinfo_ids = arg[2][0][0]
                if sinfo_ids and len(sinfo_ids) == 3:
                    sinfo_ids = sinfo_ids[-1]
                    
                property_ids = []
                for prop in properties:
                    if len(prop) >= 3:
                        property_ids += prop[2]
                
                if property_ids:
                    arg[2] = []
                    categ_properties = {}
                    for property_rs in self.env['purchase.property'].browse(property_ids):
                        if property_rs.category_id.id in categ_properties:
                            categ_properties[property_rs.category_id.id].append(property_rs.id)
                        else:
                            categ_properties[property_rs.category_id.id] = [property_rs.id]

                    for sinfo in self.env['product.supplierinfo'].browse(sinfo_ids):
                        match = True
                        sinfo_property_ids = [x.id for x in sinfo.property_ids]
                        for prop_ids in categ_properties.values():
                            if not set(prop_ids) & set(sinfo_property_ids):
                                match=False
                                break
                        
                        if match:
                            arg[2].append(sinfo.id)
                else:
                    arg[1] = '!='
                    arg[2] = 0
                
            args2.append(arg)
             
        return args2
 
 
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        """
            Fonction appelée par le search afin de n'afficher que les référencements fournisseurs du O2M
        """
        args = args or []
        args_modified = self.compute_domain_args_supplierinfo(args)
        return super(product_supplierinfo,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
      
      
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction appelée par le search afin de n'afficher que les référencements fournisseurs du O2M
        """
        recs = self.search(['|', ('partner_id.name', operator, name), ('partner_id.reference', operator, name)] + args, limit=limit)
        return recs.name_get()
      
      
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_supplierinfo(domain)
        return super(product_supplierinfo, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)
