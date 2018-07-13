# -*- coding: utf-8 -*-
from openerp import models, api, fields, osv
import sys
import traceback


class compute_stored_fields(models.Model):
    """ 
    Compute stored fields 
    """
    _name = 'compute.stored.fields'
    _description = 'Compute stored fields'
    _rec_name = 'model_name'
    _sql_constraints = [('unique_model', 'unique(model_id)', 'Impossible to have two records with same model')]
    _order = 'model_name asc'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade', select=True)
    model_name = fields.Char(string='Technical name', related='model_id.model', store=True)
    last_date = fields.Datetime(select=True)
    is_ignored = fields.Boolean(string='Ignore', default=False, help="This field allow to ignore the record during a mass recompute")
    log = fields.Text()
    
    
    def import_models(self):
        self.env.cr.execute('''
            SELECT
              id
            FROM
              ir_model
            WHERE
              id NOT IN (SELECT model_id FROM compute_stored_fields)
        ''')
        for model_id in [x[0] for x in self.env.cr.fetchall()]:
            self.create({'model_id': model_id})
    
    
    def compute(self, override_errors=False):
        for line_rc in self:
            if override_errors:
                try:
                    obj = self.env[line_rc.model_id.model]
                    field_to_compute_list = []
                    rcs = obj.search([])
                    computed_col_field_name = {}
                    # Gestion des champs déclarés en anciennes APIs
                    for col_field_name, col_field in obj._columns.iteritems():
                        if type(col_field) == osv.fields.function and col_field.store:
                            computed_col_field_name[col_field_name] = col_field
                        
                    for field in obj._field_computed.keys():
                        if field.store and field.name != 'display_name':
                            self.env.add_todo(field, rcs)
                            field_to_compute_list.append(field.name)
                    
                    field_list = field_to_compute_list + computed_col_field_name.keys()
                    line_rc.write({'log': 'Nb IDS: %d\nFIELDS: %s\nSTART: %s'%(len(rcs.ids), field_list and ', '.join(field_list) or '/', fields.Datetime.now())})
                    self.env.cr.commit()
                    if field_to_compute_list:
                        obj.recompute()
                    
                    for k, f in computed_col_field_name.iteritems():
                        obj._update_store(f, k)
                    
                    self.env.cr.commit()
                    line_rc.write({'log': '%s\nEND: %s'%(line_rc.log, fields.Datetime.now()), 'last_date': fields.Datetime.now()})
                except Exception as e:
                    self.env.cr.commit()
                    line_rc.write({'log': 'ERROR: %s'%(str(e)), 'last_date': fields.Datetime.now()})
                finally:
                    self.env.cr.commit()
                    
            else:
                obj = self.env[line_rc.model_id.model]
                field_to_compute_list = []
                rcs = obj.search([])
                computed_col_field_name = {}
                # Gestion des champs déclarés en anciennes APIs
                for col_field_name, col_field in obj._columns.iteritems():
                    if type(col_field) == osv.fields.function and col_field.store:
                        computed_col_field_name[col_field_name] = col_field
                        
                for field in obj._field_computed.keys():
                    if field.store and field.name != 'display_name':
                        self.env.add_todo(field, rcs)
                        field_to_compute_list.append(field.name)
                
                field_list = field_to_compute_list + computed_col_field_name.keys()
                line_rc.write({'log': 'Nb IDS: %d\nFIELDS: %s\nSTART: %s'%(len(rcs.ids), field_list and ', '.join(field_list) or '/', fields.Datetime.now())})
                self.env.cr.commit()
                if field_to_compute_list:
                    obj.recompute()
                
                for k, f in computed_col_field_name.iteritems():
                    obj._update_store(f, k)
                
                self.env.cr.commit()
                line_rc.write({'log': '%s\nEND: %s'%(line_rc.log, fields.Datetime.now()), 'last_date': fields.Datetime.now()})
                self.env.cr.commit()
            

    def compute_selection(self, date=False, override_errors=False):
        if date:
            args = ['|', ('last_date', '<=', date), ('last_date', '=', False), ('is_ignored', '=', False)]
        else:    
            args = []
        
        return self.search(args).compute(override_errors=override_errors)
        
            
    @api.multi    
    def compute_button(self):
        self.compute(self.is_ignored)