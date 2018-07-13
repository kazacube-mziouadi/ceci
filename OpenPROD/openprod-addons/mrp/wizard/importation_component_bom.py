# -*- coding: utf-8 -*-
from openerp import models, api, fields

class importation_component_bom(models.TransientModel):
    """ 
    Wizard qui permet d'importer dans une nomenclature des composants dans model de nomenclature sélectionné
    """
    _name = 'importation.component.bom'
    _rec_name = 'bom_id'
    _description = 'Wizard that allows to import BOM components in selected model nomenclature'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    bom_id = fields.Many2one('mrp.bom', string='BoM model', required=False, ondelete='cascade')
    importation_component_ids = fields.One2many('importation.component.bom.line', 'importation_bom_id',  string='Importation Component')
    
    @api.model
    def default_get(self, fields_list):
        res = super(importation_component_bom, self).default_get(fields_list=fields_list)
        bom_obj = self.env['mrp.bom']
        bom = bom_obj.browse(self._context.get('active_id'))
        importation_component_ids = []
        if bom.template_id:
            for component in bom.template_id.bom_ids:
                importation_component_ids.append((0, 0, {'component_id':component.id,'quantity':component.quantity,'is_import':True}))
        
        vals = {
            'bom_id': bom.id,
            'importation_component_ids':importation_component_ids,
        }
        res.update(vals)
        return res
    
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def action_importation(self):
        """
            Bouton d'importation des composants de nomenclature
        """
        if self.bom_id:
            for line in self.importation_component_ids:
                if line.is_import:
                    vals = {
                        'bom_id': self.bom_id.id,
                        'quantity': line.quantity
                    }
                    line.component_id.copy(default=vals)
        return  {'type': 'ir.actions.act_window_close'}

    
    
class importation_component_bom_line(models.TransientModel):
    """ 
    Importation component BOM line 
    """
    _name = 'importation.component.bom.line'
    _rec_name = 'component_id'
    _description = 'Importation component BOM line '
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_import = fields.Boolean(string='Import', default=True)
    component_id = fields.Many2one('mrp.bom', string='Bom model', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    importation_bom_id = fields.Many2one('importation.component.bom', string='Importation BoM', required=False, ondelete='cascade')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('component_id')
    def _onchange_product_id(self):
        """
            Au changement du composant, changement de la quantité
        """
        self.quantity = self.component_id and self.component_id.quantity or 0.0
