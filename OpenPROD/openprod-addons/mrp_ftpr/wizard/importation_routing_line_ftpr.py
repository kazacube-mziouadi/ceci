# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class importation_routing_line_ftpr(models.TransientModel):
    """ 
    Wizard qui permet d'importer dans une gammes des lignes de gammes avec un model de gamme sélectionné
    """
    _name = 'importation.routing.line.ftpr'
    _rec_name = 'routing_id'
    _description = 'Wizard that allows to import a routing of lines routing with a selected routing of model'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(importation_routing_line_ftpr, self).default_get(fields_list=fields_list)
        vals = {
            'ftpr_id': self._context.get('active_id')
        }
        res.update(vals)
        return res

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_id = fields.Many2one('mrp.ftpr', string='Ftpr', required=False, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing model', required=False, ondelete='cascade', domain=[('is_model', '=', True)])
    importation_routing_line_ids = fields.One2many('importation.routing.line.line.ftpr', 'importation_routing_line_id',  string='Importation Routing line')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('routing_id')
    def _onchange_product_id(self):
        importation_routing_line_ids = []
        for routing_line in self.routing_id.routing_line_ids:
            importation_routing_line_ids.append((0, 0, {
                                                         'routing_line_id':routing_line.id,
                                                         'is_import':True,
                                                         'is_import_consumed_component':True,
                                                         'is_import_consumed_service':True,
                                                         'is_import_tools':True,
                                                         'is_import_complaints':True,
                                                         'is_import_documents':True,
                                                         'is_import_consigns':True,}))
            
        self.importation_routing_line_ids = importation_routing_line_ids

    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_importation(self):
        """ 
            Importer dans une gammes des lignes de gammes avec un model de gamme sélectionné
        """
        if self.ftpr_id:
            for line in self.importation_routing_line_ids:
                if line.is_import:
                    vals = {
                        'routing_id': self.ftpr_id.routing_id.id,
                        'ftpr_id': self.ftpr_id.id,
                    }
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
            
            self.ftpr_id.action_compute_price()
            
        return  {'type': 'ir.actions.act_window_close'}

    
    
class importation_routing_line_line_ftpr(models.TransientModel):
    """ 
    Importation routing line line 
    """
    _name = 'importation.routing.line.line.ftpr'
    _rec_name = 'routing_line_id'
    _description = 'Importation routing line line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_import = fields.Boolean(string='Import', default=True)
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line model', required=True, ondelete='cascade')
    importation_routing_line_id = fields.Many2one('importation.routing.line.ftpr', string='Importation Routing line', required=False, ondelete='cascade')
    is_import_consumed_service = fields.Boolean(string='Import consumed services', default=True)
    is_import_tools = fields.Boolean(string='Import tools', default=True)
    is_import_complaints = fields.Boolean(string='Import complaints', default=True)
    is_import_documents = fields.Boolean(string='Import documents', default=True)
    is_import_consigns = fields.Boolean(string='Import consigns', default=True)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    