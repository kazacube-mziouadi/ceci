# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from lxml import etree
from openerp.osv.orm import setup_modifiers


class edi_choose_m2o(models.TransientModel):
    """ 
    """
    _name = 'edi.choose.m2o'
    _description = ''
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    record_id = fields.Integer(string='Record ID')
    record_name = fields.Char(string='Record name', size=256, required=False)
    model = fields.Char(string='Model', size=256, required=False)
    param_id = fields.Many2one('edi.transformation.procedure.method.param', string='Param', required=True, ondelete='cascade')

    
    #===========================================================================
    # FUNCTIONS & BUTTONS
    #===========================================================================
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(edi_choose_m2o, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            context = self.env.context
            group = doc.xpath("//group[@name='fields']")
            if group:
                f_display = {'string': _('Value'), 
                             'name': 'value', 
                             'required': '1', 
                             'type': 'many2one', 
                             'selectable': '1', 
                             'relation': context.get('edi_comodel_name'), 
                             'comodel_name': context.get('edi_comodel_name')}
                f = etree.Element('field', f_display)
                res['fields']['value'] = f_display
                group[0].append(f)
                setup_modifiers(f, f_display)
                res['arch'] = etree.tostring(doc)
                
        return res
    
    
    #===========================================================================
    # FUNCTIONS & BUTTONS
    #===========================================================================
    @api.multi
    def write(self, vals=None):
        """
            Redéfinition pour les opérations consommées
        """
        for wiz in self:
            if 'value' in vals and wiz.model:
                vals['record_id'] = vals['value']
                vals['record_name'] = self.env[wiz.model].browse(vals['value']).name_get()[0][-1]
                
        return super(edi_choose_m2o, self).write(vals=vals)
        
    
    @api.multi
    def validate_button(self):
        for this in self:
            this.param_id.write({'value': this.record_id, 'note': this.record_name})
            
        return {'type': 'ir.actions.act_window_close'}