# coding: utf-8

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import Warning


class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _inherit = 'mrp.workorder'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    spm_ids = fields.One2many('schedule.planning.mo', 'wo_id',  string='Schedule plannif')
    
    
    @api.model
    def create(self, vals):
        """
            A la création l'OF on crée des copies dans les OTs
        """
        res = super(mrp_workorder, self).create(vals=vals)
        for spm in res.mo_id.spm_ids:
            spm.copy({
                        'mo_id': False,
                        'parent_id': spm.id,
                        'wo_id': res.id
                    })
        
        return res



class mrp_manufacturingorder(models.Model):
    """ 
        Manufacturing order 
    """
    _inherit = 'mrp.manufacturingorder'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    spm_ids = fields.One2many('schedule.planning.mo', 'mo_id',  string='Schedule planning')
    
    
    
    