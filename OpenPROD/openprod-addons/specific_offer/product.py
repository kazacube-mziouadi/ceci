# coding: utf8
from openerp import models, fields
from openerp.tools.translate import _
    

class parameter_dimension(models.Model):
    """ 
    Parameter Dimension 
    """
    _inherit = 'parameter.dimension'
    _description = 'Parameter Dimension'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    specific_offer_id = fields.Many2one('specific.offer', string='Specific offer', required=False, ondelete='cascade')