# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp

class importation_routing_line(models.TransientModel):
    """ 
    Wizard qui permet d'importer dans une gammes des lignes de gammes avec un model de gamme sélectionné
    """
    _name = 'importation.routing.line'
    _rec_name = 'routing_id'
    _description = 'Wizard that allows to import a routing of lines routing with a selected routing of model'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_id = fields.Many2one('mrp.routing', string='Routing model', required=False, ondelete='cascade')
    importation_routing_line_ids = fields.One2many('importation.routing.line.line', 'importation_routing_line_id',  string='Importation Routing line')
    
    @api.model
    def default_get(self, fields_list):
        res = super(importation_routing_line, self).default_get(fields_list=fields_list)
        routing_obj = self.env['mrp.routing']
        routing = routing_obj.browse(self._context.get('active_id'))
        importation_routing_line_ids = []
        if routing.template_id:
            for routing_line in routing.template_id.routing_line_ids:
                importation_routing_line_ids.append((0, 0, {'routing_line_id':routing_line.id,
                                                     'is_import':True,
                                                     'is_import_consumed_component':True,
                                                     'is_import_consumed_service':True,
                                                     'is_import_tools':True,
                                                     'is_import_complaints':True,
                                                     'is_import_documents':True,
                                                     'is_import_consigns':True,}))
        vals = {
            'routing_id': routing.id,
            'importation_routing_line_ids':importation_routing_line_ids,
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_importation(self):
        """ 
            Importer dans une gammes des lignes de gammes avec un model de gamme sélectionné
        """
        if self.routing_id:
            is_bom = False
            for line in self.importation_routing_line_ids:
                if line.is_import:
                    vals = {
                        'routing_id': self.routing_id.id,
                    }
                    if not line.is_import_consumed_component:
                        vals.update({'consumed_component_ids': False})
                    else:
                        is_bom = True
                        
                    if not line.is_import_consumed_service:
                        vals.update({'consumed_service_ids': False})
                        
                    if not line.is_import_tools:
                        vals.update({'tool_ids': False})
                        
                    if not line.is_import_complaints:
                        vals.update({'complaint_ids': False})
                        
                    if not line.is_import_documents:
                        vals.update({'document_ids': False})
                        
                    if not line.is_import_consigns:
                        vals.update({'consign_ids': False})
                        
                    line.routing_line_id.copy(default=vals)
            
            vals = {'note_mo': self.routing_id.template_id.note_mo}
            
            if is_bom:
                vals['bom_ids'] = [(4,x.id) for x in self.routing_id.template_id.bom_ids]
                
            self.routing_id.write(vals)
            
        return  {'type': 'ir.actions.act_window_close'}

    
    
class importation_routing_line_line(models.TransientModel):
    """ 
    Importation routing line line 
    """
    _name = 'importation.routing.line.line'
    _rec_name = 'routing_line_id'
    _description = 'Importation routing line line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_import = fields.Boolean(string='Import', default=True)
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line model', required=True, ondelete='cascade')
    importation_routing_line_id = fields.Many2one('importation.routing.line', string='Importation Routing line', required=False, ondelete='cascade')
    is_import_consumed_component = fields.Boolean(string='Import consumed component', default=False)
    is_import_consumed_service = fields.Boolean(string='Import consumed services', default=True)
    is_import_tools = fields.Boolean(string='Import tools', default=True)
    is_import_complaints = fields.Boolean(string='Import complaints', default=True)
    is_import_documents = fields.Boolean(string='Import documents', default=True)
    is_import_consigns = fields.Boolean(string='Import consigns', default=True)
    
