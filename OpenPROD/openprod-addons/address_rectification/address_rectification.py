# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

#===============================================================================
# Champ fonction multiple
#===============================================================================

# Modèle à mettre à jour
model = ['address', 'res.partner']
# Fonction appelé par le(s) champs fonction
function = ['_compute_partner_address_id', '_compute_address_id']

class address_rectification(models.TransientModel):
    _name = 'address.rectification'
    
    @api.multi
    def go(self):
        # Recuperation de tous les ids du model
        multi_address = self.env['ir.module.module'].search([('name', '=', 'multi_address')], limit=1)
        if multi_address and multi_address.state == 'installed':
            all_ids = self.env[model[1]].search([])
            getattr(all_ids, function[1])()
        else:
            # Recuperation des résultats de la fonction
            all_ids = self.env[model[0]].search([])
            getattr(all_ids, function[0])()
        
        #On lance le onchange pour calculer toutes les adresses des contacts liés à des partenaires
        contact_ids = self.env['res.partner'].search([('is_company', '=', False), ('company_address', '=', True)])
        for contact in contact_ids:
            contact._onchange_address_id()
        
        return {'type': 'ir.actions.act_window_close'}
    
