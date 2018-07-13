# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class ir_config_parameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    #==========================================================================
    # COLUMNS
    #==========================================================================
    note = fields.Char(size=128, required=False)
    
    @api.multi
    def unlink(self):
        """
            Interdiction de supprimer un paramètre
        """
        raise except_orm(_('Error'), _('You cannot delete any record'))
        return super(ir_config_parameter, self).unlink()