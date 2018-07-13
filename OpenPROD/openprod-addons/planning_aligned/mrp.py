# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import string
import datetime
from datetime import timedelta
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod.common import roundingUp, rounding
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import re
from decimal import Decimal
from operator import itemgetter



class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _inherit = 'mrp.workorder'


    def plannification_mo_aligned(self, date, mo, type_alignment, is_sublevel, ):
        """
            Si premier OF (OF principal): lancement de sa plannification au plus tôt
            Sinon (OF de sous niveau): lancement de sa plannification au plus tard par rapport a la date de début de l'OF suivant
            Si sous niveau: planification des sous niveaux
        """
        procurement_obj = self.env['procurement.order']
        workorder_rcs = self.search([('mo_id', '=', mo.id), ('state', 'not in', ('cancel', 'done'))])
        if is_sublevel:
            automatic_purchase = True
            is_procur_level_manufact = True
            is_procur_level_purchase = True
        else:
            automatic_purchase = False
            is_procur_level_manufact = False
            is_procur_level_purchase = False
        
        if workorder_rcs:
            for workorder in workorder_rcs:
                if workorder.state == 'draft':
                    workorder.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=True)
                elif workorder.state in ('waiting', 'plan'):
                    workorder.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=False)
            
            if is_sublevel:
                # Si pas de demande de génération d'achat: automatic_purchase=False
                for wo in mo.workorder_ids:
                    for procurement in procurement_obj.search([('origin_wo_id', '=', wo.id), 
                                                               ('supply_method', '=', 'produce'), 
                                                               ('mo_id', '!=', False)]):
                        self.plannification_mo_aligned(date, procurement.mo_id, type_alignment, is_sublevel)
            
            last_workorder_rcs = self.search([('mo_id', '=', mo.id), ('state', 'not in', ('cancel', 'done'))], order='sequence desc', limit=1)
            last_workorder_rcs.recursion_plannification_mo_aligned(date, type_alignment, is_sublevel, res=None)
            
        return date
    
    
    
    def recursion_plannification_mo_aligned(self, start_date, type_alignment, is_sublevel, res=None):
        """ 
            Fonction récursive qui permet de calculer les dates au plus tôt des OTs
            :param self: Le Recordset du dernier OT
            :type self: Un Recordset
            :param start_date: La date de départ du première OT
            :type start_date: Date
            :param res: Dico qui permet d'optimiser la recursion
            :type res: Dict
            :return: Date de fin.
        """
        if not res:
            res={}
        
        if type_alignment == 'at_earlier':
            # Si l'ot n'est pas dans ces états on ne plannifie pas l'ot et l'on récupère la date de fin plannifiée
            self.write({'is_at_earlier': True})
            if self.state in ('cancel'):
                res[self] = self.planned_end_date
            else:
                # Test Si l'oT à des précédents
                is_prev_wo = False
                if self.prev_wo_ids:
                    prev_wo_ids = self.env['mrp.workorder']
                    for prev_wo in self.prev_wo_ids:
                        if prev_wo.state not in ('cancel', 'done'):
                            prev_wo_ids += prev_wo
                            
                    if prev_wo_ids:
                        is_prev_wo = True
                
                # Si l'oT à des précédents
                if is_prev_wo:
                    # Pour chaque précédent on relance la fonction récursive de plannification si res ne contient pas l'ot et la date
                    for prev in prev_wo_ids:
                        if prev not in res and prev.state not in ('cancel', 'done'):
                            res.update(prev.recursion_plannification_mo_aligned(start_date, type_alignment, is_sublevel, res=res))
                        
                # On ajoute à res l'ot et la date_start
                self.action_plannification_wo_at_earlier(start_date)
                res[self] = start_date
            
            
            
        else:   
            self.write({'is_at_earlier': False})
            if self.state in ('cancel'):
                res[self] = self.planned_start_date
            # Si non
            else:
                if is_sublevel:
                        automatic_purchase=True
                        is_procur_level_manufact=True
                        is_procur_level_purchase=True
                else:
                    automatic_purchase=False
                    is_procur_level_manufact=False
                    is_procur_level_purchase=False
                        
                # On calcule la date et on ajoute à res l'ot et la date_end
                self.action_plannification_wo_at_the_latest(start_date, automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, 
                                                                        is_procur_level_purchase=is_procur_level_purchase)
                res[self] = start_date
                # Si l'OT a des OTs précédents on relance la fonction récursive de plannification
                if self.prev_wo_ids:
                    for prev in self.prev_wo_ids:
                        if prev not in res and prev.state not in ('cancel', 'done'):
                            res.update(prev.recursion_plannification_mo_aligned(start_date, type_alignment, is_sublevel, res=res))
            
        return res
    
    