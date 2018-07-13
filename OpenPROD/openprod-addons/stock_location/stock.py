# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError


class stock_location(models.Model):
    """
    Stock location
    """
    _name = 'stock.location'
    _description = 'Stock location'
    _parent_name = 'location_id'
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'
    _sql_constraints = [
        ('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !'),
        ('unique_name', 'unique(location_id,name)', 'Error: There is already an other location with this name.'),
    ]


#     @api.one
#     @api.depends('name', 'location_id', 'active', 'location_id.complete_name', 'location_id.name')
#     def _compute_complete_name(self):
#         """ 
#             Calcul le nom complet (Ex: "Stock / A3 / R2")
#             :type self: stock.location
#             :rtype: char
#         """
#         res = self.name
#         parent = self.location_id
#         while parent:
#             res = '%s / %s'%(parent.name, res)
#             parent = parent.location_id
#             
#         self.complete_name = res


    def compute_complete_name(self):
        name = self.name
        current = self
        while current.location_id:
            current = current.location_id
            name = '%s / %s' % (current.name, name)
        
        return name
    
            
    @api.one
    @api.depends('name', 'location_id.name', 'location_id')
    def _compute_complete_name(self):
        """ 
            Calcul le nom complet (Ex: "Stock / A3 / R2")
            :type self: stock.location
            :rtype: char
        """
        self.complete_name = self.compute_complete_name()
        
    
    @api.model
    def _usage_get(self):
        return [('internal', _('Internal Location')),
                ('view', _('View')),
                ('supplier', _('Supplier Location')),
                ('customer', _('Customer Location')),
                ('inventory', _('Inventory')),
                ('procurement', _('Procurement')),
                ('production', _('Production')),
                ('transit', _('Transit Location'))]


    @api.model
    def _get_default_warehouse(self):
        return self.env.user.company_id.warehouse_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    active = fields.Boolean(string='Active', default=True, help='By unchecking the active field, you may hide a location without deleting it.')
    usage = fields.Selection('_usage_get', string='Type', required=True, default='internal', help="""* Supplier Location: Virtual location representing the source location for products coming from your suppliers
                                                                                                   \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                                                                                                   \n* Internal Location: Physical locations inside your own warehouses,
                                                                                                   \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                                                                                                   \n* Inventory: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                                                                                                   \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (supplier or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                                                                                                   \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                                                                                                   \n* Transit Location: Counterpart location that should be used in inter-companies or inter-warehouses operations
                                                                                                  """, select=True)
    complete_name = fields.Char(string='Name', compute='_compute_complete_name', store=True)
    location_id = fields.Many2one('stock.location', string='Parent location', required=False, select=True, ondelete='cascade')
    child_ids_ids = fields.One2many('stock.location', 'location_id',  string='Child locations', copy=False)
    parent_left = fields.Integer(string='Left parent', select=True)
    parent_right = fields.Integer(string='Right parent', select=True)
    posx = fields.Integer(string='Corridor (X)', help='Optional localization details, for information purpose only')
    posy = fields.Integer(string='Shelves (Y)', help='Optional localization details, for information purpose only')
    posz = fields.Integer(string='Height (Z)', help='Optional localization details, for information purpose only')
    comment = fields.Text(string='Additional Information')
    partner_id = fields.Many2one('res.partner', string='Owner', required=False, ondelete='restrict', help='Owner of the location if not internal')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', select=True, default=lambda self: self.env.user.company_id)
    barcode = fields.Char(size=32, required=False)
    control = fields.Boolean(default=False, help='If this field is checked, labels present in this location will be in state control')
    quarantine = fields.Boolean(default=False, help='If this field is checked, labels present in this location will be in state quarantine')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict', default=_get_default_warehouse)
    
    
    def get_internal_usages(self):
        return ['internal']


    def get_external_usages(self):
        return ['supplier', 'customer', 'production', 'procurement', 'inventory', 'transit']
    
    
    def _get_sublocations(self, ids=False, active_test=False):
        """ 
            Renvoie les emplacements de stock sous celui qui est passé
            :type self: stock.location
            :param ids: Si renseigné, revoie les sous emplacements de ces ids. Sinon ceux de self.ids
            :type ids: list
            :param active_test: Si True: recherche parmis les inactifs 
            :type active_test: bool
        """
        
        if not ids:
            ids = self.ids
            
        args = [('id', 'child_of', ids)]
        if active_test:
            args.extend(['|', ('active', '=', True), ('active', '=', False)])
        
        res = self.search(args)
        return res
    
        
    @api.one
    def copy(self, default=None):
        raise UserError(_('Duplication prohibited.'))
        return super(stock_location, self).copy(default=default)
    
    
    @api.multi
    def write(self, vals=None):
        res = super(stock_location, self).write(vals=vals)
        if 'name' in vals or 'location_id' in vals:
            for sublocation in self._get_sublocations(active_test=True):
                sublocation.write({'complete_name': sublocation.compute_complete_name()})
                
        return res



class stock_warehouse(models.Model):
    """
    Stock warehouse
    """
    _name = 'stock.warehouse'
    _description = 'Stock warehouse'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=32, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)
    
    