# -*- coding: utf-8 -*-
from openerp import models, api, fields

class import_help_fields_wizard(models.TransientModel):
    """ 
    Import help fields 
    """
    _name = 'import.help.fields.wizard'
    _description = 'Import help fields'
    
    @api.model
    def _import_type_get(self):
        return [
                ('update', 'Create and update'),
                ('create', 'Create only'),
                       ]
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    update_import_help = fields.Boolean(default=False)
    import_type = fields.Selection('_import_type_get', default='update', help='''
    Create and update:\n
    \tUpdate existing records and add new records\n\n
    
    Create only:\n
    \tCreate new records without updating existing ones
    ''')
    
    @api.multi
    def import_model(self):
        return self.env['import.help.fields'].import_model(self[0].model_id, self[0].import_type, self[0].update_import_help)