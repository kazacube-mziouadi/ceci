# -*- coding: utf-8 -*-
from openerp import models, api, fields
class import_help_fields(models.Model):
    """ 
    Import help fields 
    """
    _name = 'import.help.fields'
    _inherit = 'ir.model.fields'
    _description = 'Import help fields'
    
    
    def _check_related(self):
        return True
    
    
    def _check_relation_table(self):
        return True
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    import_help = fields.Text()
    is_stored = fields.Boolean(default=False)
    default = fields.Char(string='Default value', size=128)
    selection_txt = fields.Text('Possible values')
    
    
    @api.multi
    def import_model(self, model, import_type, update_import_help):
        fields_obj = self.env['ir.model.fields']
        model_obj = self.env[model.model]
        function_type = lambda x:x
        for f_rs in fields_obj.search([('model_id', '=', model.id)]):
            if f_rs.name in model_obj._fields:
                help_f = self.search([('model_id', '=', model.id), ('name', '=', f_rs.name)], limit=1)
                vals = f_rs.read([], load='_classic_write')[0]
                del vals['id']
                del vals['create_date']
                del vals['write_date']
                del vals['create_uid']
                del vals['write_uid']
                del vals['groups']
                del vals['__last_update']
                vals['is_stored'] = model_obj._fields[f_rs.name].store or False
                vals['import_help'] = model_obj._fields[f_rs.name].import_help or False
                if model_obj._fields[f_rs.name].default and type(model_obj._fields[f_rs.name].default) == type(function_type):
                    vals['default'] = model_obj._fields[f_rs.name].default(model_obj) or ''
                    
                if f_rs.ttype == 'many2one':
                    vals['on_delete'] = model_obj._fields[f_rs.name].ondelete or False
                    
                if f_rs.ttype == 'selection':
                    selection = model_obj._fields[f_rs.name].selection
                    if selection:
                        if isinstance(selection, list):
                            vals['selection_txt'] = '\n'.join(['"%s": %s'%(k, v) for k, v in selection])
                            vals['selection'] = str(selection)
                        else:
                            try:
                                selection_list = eval(selection)
                                if isinstance(selection_list, list):
                                    vals['selection'] = selection
                            except:
                                try:
                                    vals['selection'] = str(eval('model_obj.%s()'%(selection)))
                                except:
                                    pass
                            
                if help_f:
                    if import_type == 'update':
                        if update_import_help and help_f.import_help:
                            del vals['import_help']
                        
                        help_f.write(vals)
                else:
                    self.create(vals)
                
        return True
    
    
    @api.multi
    def write(self, vals=None):
        return super(models.Model, self).write(vals) 