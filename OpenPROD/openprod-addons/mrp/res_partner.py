# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    
    def compute_suppinfo_search_args(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les fournisseurs du service ou des services
            s'il n'est pas en achat libre
        """
        args2 = super(res_partner, self).compute_suppinfo_search_args(args)
        for arg in args:
            match = False
            if arg[0] == 'supplierinfo_service_search':
                list_service = False
                service_ids = False
                if not arg[-1]:
                    match = True
                    args2 = []
                    args2.append(('is_company', '=', True))
                    args2.append(('is_supplier', '=', True))
                    break
                elif isinstance(arg[-1], int):
                    service_ids = [arg[-1]]
                elif isinstance(arg[-1], list) and isinstance(arg[-1][0], int):
                    service_ids = arg[-1]
                elif isinstance(arg[-1], list) and isinstance(arg[-1][0], list):
                    service_ids = []
                    for list_arg in arg[-1]:
                        service_ids.append(list_arg[1])
                        
                if service_ids:
                    product_obj = self.env['product.product']
                    arg[-1] = []
                    # Flag qui indique que les services ne peuvent pas être achetés n'importe où
                    not_free_purchase = False
                    # On va rechercher les fournisseur pour les services, il doit y avoir au moins un fournisseur commun pour les services 
                    for service in product_obj.browse(service_ids):
                        if not service.free_purchase:
                            not_free_purchase = True
                            list_service = True
                            arg[0] = 'id'
                            arg[1] = 'in'
                            # Listes des fournisseurs pour ce service
                            arg_tmp = [supplierinfo.partner_id.id for supplierinfo in service.sinfo_ids if supplierinfo.partner_id and supplierinfo.state=='active']
                            if not arg[-1] and arg_tmp:
                                arg[-1].extend(arg_tmp)
                            elif arg_tmp:
                                # Recherche des fournisseurs commun
                                arg[-1] = list(set(arg[-1]) & set(arg_tmp))
                                if not arg[-1]:
                                    # Erreur il n'y pas de fournisseurs ou de fournisseurs commun
                                    break
                            else:
                                # Erreur il n'y pas de fournisseurs ou de fournisseurs commun
                                arg[-1] = []
                                break
                    
                    if not_free_purchase:  
                        # Erreur il n'y pas de fournisseurs ou de fournisseurs commun  
                        if not arg[-1]:
                            raise except_orm(_('Error'), _('We need a common supplier for each service.'))
                    
                    else:
                        # Les services peuvent être achetés n'importe où   
                        match = True
                        args2 = []
                        args2.append(('is_company', '=', True))
                        args2.append(('is_supplier', '=', True))
                        break
                else:
                    match = True
                    index = args2.index(arg)
                    args2= []
                    args2.append(('is_company', '=', True))
                    args2.append(('is_supplier', '=', True))
            
                if not match:
                    if list_service:
                        arg[-1] = list(set(arg[-1]))
                    args2.append(arg)
            
            if arg[0] == 'next_wo_supplierinfo_service_search':
                wo_id = False
                if not arg[-1]:
                    match = True
                    args2 = []
                    args2.append('|')
                    args2.append(('is_company', '=', False))
                    args2.append('&')
                    args2.append(('is_company', '=', True))
                    args2.append(('is_supplier', '=', True))
                    break
                elif isinstance(arg[-1], int):
                    wo_id = arg[-1]
                
                if wo_id:
                    wo_obj = self.env['mrp.workorder']
                    arg[-1] = []
                    list_service = False
                    service_ids = False
                    # Flag qui indique que les services ne peuvent pas être achetés n'importe où
                    not_free_purchase = False
                    # On va rechercher les fournisseur pour les services, il doit y avoir au moins un fournisseur commun pour les services 
                    wo = wo_obj.browse(wo_id)
                    next_wo = wo.next_wo_ids and wo.next_wo_ids[0] or False
                    if next_wo and next_wo.is_subcontracting and next_wo.consumed_service_ids:
                        for consumed_service in next_wo.consumed_service_ids:
                            service = consumed_service.product_id
                            if not service.free_purchase:
                                not_free_purchase = True
                                list_service = True
                                arg[0] = 'id'
                                arg[1] = 'in'
                                # Listes des fournisseurs pour ce service
                                arg_tmp = [supplierinfo.partner_id.id for supplierinfo in service.sinfo_ids if supplierinfo.partner_id]
                                if not arg[-1] and arg_tmp:
                                    arg[-1].extend(arg_tmp)
                                elif arg_tmp:
                                    # Recherche des fournisseurs commun
                                    arg[-1] = list(set(arg[-1]) & set(arg_tmp))
                                    if not arg[-1]:
                                        # Erreur il n'y pas de fournisseurs ou de fournisseurs commun
                                        break
                                else:
                                    # Erreur il n'y pas de fournisseurs ou de fournisseurs commun
                                    arg[-1] = []
                                    break
                        
                        if not_free_purchase:  
                            # Erreur il n'y pas de fournisseurs ou de fournisseurs commun  
                            if not arg[-1]:
                                raise except_orm(_('Error'), _('We need a common supplier for each service.'))
                
                        else:
                            # Les services peuvent être achetés n'importe où   
                            match = True
                            args2 = []
                            args2.append('|')
                            args2.append(('is_company', '=', False))
                            args2.append('&')
                            args2.append(('is_company', '=', True))
                            args2.append(('is_supplier', '=', True))
                            break
                    else:
                        match = True
                        args2 = []
                        args2.append('|')
                        args2.append(('is_company', '=', False))
                        args2.append('&')
                        args2.append(('is_company', '=', True))
                        args2.append(('is_supplier', '=', True))
                        break
                    
                    
                if not match:
                    if list_service:
                        arg[-1] = list(set(arg[-1]))
                    args2.append(arg)
            
        return args2
    
    @api.multi
    def show_partner_wo(self):
        """
            Fonction qui cherche et retourne les OT du partenaire
        """
        action_struc = {}
        action_dict = get_form_view(self, 'mrp.action_see_all_workorder')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'customer_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc


