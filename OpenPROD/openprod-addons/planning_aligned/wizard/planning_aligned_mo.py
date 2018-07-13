# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp

class planning_aligned_mo(models.TransientModel):
    """ 
        Planning aligned mo
    """
    _name = 'planning.aligned.mo'
    _description = 'Planning aligned mo'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(planning_aligned_mo, self).default_get(fields_list=fields_list)
        mo = self.env['mrp.manufacturingorder'].browse(self.env.context.get('active_id'))
        
        res['mo_id'] = mo.id
        res['date'] = mo.min_start_date
        return res

    
    @api.model
    def _type_alignment_get(self):
        return [
                ('at_earlier', _('At earlier')),
                ('at_the_latest', _('At the latest')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date of alignment', required=True)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing Order', required=True, ondelete='cascade')
    is_sublevel = fields.Boolean(string='Alignment sublevel', default=False)
    type_alignment = fields.Selection('_type_alignment_get', string='Type of alignment', required=True, default='at_the_latest')
        
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_mo_aligned(self):
        """
            Bouton qui plannifie l'OF à l'alignement
        """
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            wo_obj.plannification_mo_aligned(wiz.date, wiz.mo_id, wiz.type_alignment, wiz.is_sublevel)
        return True
