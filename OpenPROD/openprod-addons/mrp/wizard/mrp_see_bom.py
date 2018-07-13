# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class mrp_see_bom(models.Model):
    """ 
    The launched wizard when you click in a bom 
    """
    _name = 'mrp.see.bom'
    _description = 'The launched wizard when you click in a bom'
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_see_bom, self).default_get(fields_list=fields_list)
        bom_obj = self.env['mrp.bom']
        #Fonction permettant de passer par défaut l'id de la nomenclature ouverte
        bom = bom_obj.browse(self._context.get('active_id'))
        #Fonction permettant de cocher ou de décocher le boléen, ce qui permettra de faire apparaître le bon bouton (créer une nouvelle nomenclature ou voir la nomenclature)
        head_id = bom.product_id and bom_obj.search([('bom_id', '=', False), ('product_id', '=', bom.product_id.id), ('state','=','active')], limit=1) or False
        if bom.product_id and not bom.product_id.produce_ok:
            is_no_produce = True
            is_flag_bom = False
        else:
            is_no_produce = False
            if head_id:
                is_flag_bom = True
            else:
                is_flag_bom = False
        
        vals = {
            'is_flag_bom': is_flag_bom,
            'bom_id': self._context.get('active_id'),
            'is_no_produce': is_no_produce,
        }
 
        res.update(vals)
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    
    name = fields.Char(required=False, size=32)
    bom_id = fields.Many2one('mrp.bom', string='Bill of material', required=False, ondelete='set null')
    is_flag_bom = fields.Boolean(string='Flag')
    is_no_produce = fields.Boolean(string='No produce')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        """
        """
        self.name = self.bom_id and self.bom_id.product_id and self.bom_id.product_id.code or ''
    
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def create_head_bom(self):
        """ 
            Fonction associée au bouton permettant de créer une nouvelle nomenclature de tête à partir du composant sélectionné
        """
        bom_obj = self.env['mrp.bom']
        res = {}
        bom = False
        head_bom_id = False
        for wiz in self:
            #On vérifie si le champ de nomenclature du wizard est bien rempli
            if not wiz.bom_id:
                raise except_orm('Error', 'There is not BoM')
            else:
                bom = wiz.bom_id
                #Si la nomenclature n'a pas de parents, cela signifie que c'est une nomenclature de tête, donc on récupère son id
                if not bom.bom_id:
                    head_bom_id = bom
                #Sinon, on recherche la nomenclature de tête correspondant à la nomenclature sélectionnée
                #Si on ne trouve rien, on va créer la nomenclature de tête à partir de la nomenclature sélectionnée
                else:
                    head_id = bom.product_id and bom_obj.search([('bom_id', '=', False), ('product_id', '=', bom.product_id.id)], limit=1) or False
                    if head_id:
                        head_bom_id = head_id[0]
                    else:
                        head_bom_id = bom.copy(default={'bom_id': False})
              
            #On va ensuite lancer la vue correspondante avec comme parent par défaut la nomenclature de tête trouvées ou créées précédemment
            if head_bom_id:
                data_pool = self.env['ir.model.data']
                action_model = False
                action = {}
                action_model, action_id = data_pool.get_object_reference('mrp', 'act_bill_of_materials_form')
                #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
                if action_model:
                    action_pool = self.env[action_model]
                    action = action_pool.browse(action_id).read()[0]
                    action['res_id'] = head_bom_id.id
                    action['context'] = {'save_button_ok': True}
                    res = action
         
        return res
      
    @api.multi
    def see_form_bom(self):
        """ 
            Fonction associée au bouton de la vue qui permet de lancer la vue form de la nomenclature sélectionnée
        """
        bom_obj = self.env['mrp.bom']
        bom = False
        head_id = []
        res = {}
        for wiz in self:
            #Si le champ bom_id est vide, on essaye de récupérer l'active_id
            if not wiz.bom_id:
                raise except_orm('Error', 'There is not BoM')
            #Sinon on récupère l'id du bom sélectionné dans le champ
            else:
                bom = wiz.bom_id
                head_id = bom.product_id and bom_obj.search([('bom_id', '=', False), ('product_id', '=', bom.product_id.id)], limit=1) or False
                if head_id:
                    #Si on a bien un id, on va récupérer les informations de l'action qui lance la vue form
                    data_pool = self.env['ir.model.data']
                    action_model = False
                    action = {}
                    action_model, action_id = data_pool.get_object_reference('mrp', 'act_bill_of_materials_form')
                    #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
                    if action_model:
                        action_pool = self.env[action_model]
                        action = action_pool.browse(action_id).read()[0]
                        action['res_id'] = head_id[0].id
                        action['context'] = {'save_button_ok': True}
                        res = action
                    
        return res


