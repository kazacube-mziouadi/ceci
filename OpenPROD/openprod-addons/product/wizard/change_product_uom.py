# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class change_product_uom(models.TransientModel):
    """ 
        Wizard to change the product uom
    """
    _name = 'change.product.uom'
    _description = 'Modification of the product uom'
    _rec_name = 'uom_id'
    
    @api.model
    def _dual_type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    change_unit = fields.Boolean(string='Change unit of measure', default=False)
    dual_unit = fields.Boolean(string='Dual unit', default=False)
    uom_id = fields.Many2one('product.uom', string='Unit of measure', required=False)
    sec_uom_id = fields.Many2one('product.uom', string='Second unit of measure', required=False)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    dual_unit_type = fields.Selection('_dual_type_get', string='Dual unit type', default='fixed')
    copy_internal_plans = fields.Boolean(string='Copy internal documents', default=True)
    copy_parameters = fields.Boolean(string='Copy parameters', default=True)
    copy_quality_control = fields.Boolean(string='Copy plan of control', default=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_product_uom, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_model') == 'product.product' and context.get('active_id'):
            product = self.env['product.product'].browse(context['active_id'])
            if product.dual_unit:
                res['dual_unit'] = True
                
            res['product_id'] = context['active_id']
                
        return res
    
    
    def copy_from_product(self, product, new_product_id):
        """
            Fonction permettant de prendre en compte les modifications futures pour
            la copie du produit
        """
        return True
    
    
    @api.multi
    def copy_product(self):
        """
            Fonction permettant de dupliquer le produit en modifiant ou non l'unité
            de gestion
        """
        action_struc = {}
        product = self.product_id
        if product:
            default = {}
            if self.change_unit and self.uom_id:
                default ['uom_id'] = self.uom_id.id
                if not self.dual_unit:
                    default.update({'uos_id': self.uom_id.id,
                                    'uop_id': self.uom_id.id,
                                    'sale_uoi_id': self.uom_id.id,
                                    'purchase_uoi_id': self.uom_id.id,
                                    })
            
            if self.dual_unit and self.dual_unit_type:
                default.update({'dual_unit': True,
                                'dual_unit_type': self.dual_unit_type,
                                'purchase_factor': 1,
                                'purchase_divisor': 1,
                                })
                if self.dual_unit_type == 'variable':
                    default.update({'sec_uom_id': self.sec_uom_id.id,
                                'uos_id': self.sec_uom_id.id,
                                'uop_id': self.sec_uom_id.id,
                                'sale_uoi_id': self.sec_uom_id.id,
                                'purchase_uoi_id': self.sec_uom_id.id,
                                })
            
            if not self.dual_unit:
                default.update({'dual_unit': False})
                    
            #Gestion de la surcharge depuis mrp
            context2 = {'copy_by_button': True}
            context2.update(self.env.context)
            new_product = product.with_context(context2).copy(default)
        
            default = {'product_id': new_product.id}
            
            #Copie des plans internes
            if self.copy_internal_plans:
                new_product.write({'internal_plan_ids': [(6, 0, product.internal_plan_ids.ids)]})
            self.copy_from_product(product, new_product.id)
            
            #Copie des paramètres
            if self.copy_parameters:
                product.parameter_ids.copy(default)
        
            #Copie des plans de controle
            if self.copy_quality_control and not product.control_categ_syncro:
                product.quality_control_ids.copy(default)
                
                
            action_dict = get_form_view(self, 'product.product_product_see_form')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['res_id'] = new_product.id
                action_struc = action_struc[0]
                  
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}