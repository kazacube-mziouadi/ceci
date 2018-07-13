# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class mrp_resource_category(models.Model):
    """ 
    Resource category 
    """
    _name = 'mrp.resource.category'
    _description = 'Resource category '
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    hourly_rate = fields.Float(string='Hourly rate', default=0.0, digits=dp.get_precision('Hourly rate'), required=False)
    resource_ids = fields.Many2many('mrp.resource', 'mrp_resource_category_mrp_resource_rel', 'category_id', 'resource_id', string='Resources')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self:self.env.user.company_id)



class mrp_resource(models.Model):
    """ 
    Resource 
    """
    _name = 'mrp.resource'
    _description = 'Resource'
    
    @api.model
    def _type_get(self):
        return [
                ('human', _('Human')),
                ('machin', _('Machine')),
                ('subcontracting', _('Subcontracting')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    type = fields.Selection('_type_get', string='Type', required=True, default='human')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    hourly_rate = fields.Float(string='Hourly_rate', default=0.0, digits=dp.get_precision('Hourly rate'), required=False)
    category_resource_ids = fields.Many2many('mrp.resource.category', 'mrp_resource_category_mrp_resource_rel', 'resource_id', 'category_id', string='Resources category')
    start_date = fields.Date(string='Date Start')
    stop_date = fields.Date(string='Date Stop')
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = False, False, False
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_resource(self, args):
        #Pour ne pas pouvoir sélectionner dans les catégories des lignes de gammes deux fois la même ressource
        #Et permet également dans le wizard de déclaration des temps d'avoir les ressources associées au wo entré
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            arg0, arg1, arg_1 = self.additional_function_domain(arg)
            if arg0 and arg1:
                arg[0] = arg0
                arg[1] = arg1
                arg[-1] = arg_1
                
            args2.append(arg)

        return args2


    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_resource(args)
        return super(mrp_resource,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
