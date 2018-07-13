# -*- coding: utf-8 -*-
from openerp import models, fields, api



class stock_picking(models.Model):
    """ 
        stock_picking
    """
    _inherit = 'stock.picking'
    
    
    def arg_search_move_piece_maintenance(self):
        return [('state', 'in', ('draft', 'waiting')), ('type', '=', 'out'), 
                ('picking_id', '!=', False), ('purchase_line_id', '=', False), ('sale_line_id', '=', False)]
        
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_piking
        """
        arg0, arg1, arg_1 = super(stock_picking, self).additional_function_domain(arg)
        if arg and arg[0] == 'domain_piece_maintenance_intervention':
            arg0 = 'id'
            arg1 = 'in'
            picking_ids = []
            if arg[-1]:
                arg_search_move_piece_maintenance = self.arg_search_move_piece_maintenance()
                for x in self.env['stock.move'].search(arg_search_move_piece_maintenance):
                    if x.picking_id.id not in picking_ids and x.picking_id.partner_id and x.picking_id.partner_id.id == arg[-1]:
                        picking_ids.append(x.picking_id.id)
                        
            arg_1 = list(set(picking_ids))
            
        return arg0, arg1, arg_1
    
    
    
class stock_label(models.Model):
    """ 
         stock_label
    """
    _inherit = 'stock.label'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_label
        """
        arg0, arg1, arg_1 = super(stock_label, self).additional_function_domain(arg)
        if arg[0] == 'domain_label_create_park':
            arg0 = 'id'
            arg1 = 'not in'
            label_ids = False
            park_rcs = self.env['park'].search()
            label_ids = [parck_read['num_serie_id'] for parck_read in park_rcs.read(['num_serie_id'], load='_classic_write') if parck_read['num_serie_id']]
            arg_1 = label_ids
            
        return arg0, arg1, arg_1



class stock_warehouse(models.Model):
    """ 
         stock_warehouse
    """
    _inherit = 'stock.warehouse'
    
    
    location_sav_id = fields.Many2one('stock.location', string='SAV location', required=False, ondelete='restrict')
    


class stock_move(models.Model):
    """ 
         stock_move
    """
    _inherit = 'stock.move'
    
    
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
    
    
    
class stock_label_traceability(models.Model):
    """
    Label traceability
    """
    _inherit = 'stock.label.traceability'
    
    
    def get_additional_clause(self):
        return 'wo.intervention_id IS NULL AND '
    
    
    def get_sav_label_in(self, label_rc):
        """
        Récupération de tous les mouvements entrants liés à une intervention (directement ou via un OT) 
        elle même liée à un park lui même lié à une des étiquettes composant l'étiquette
        """
        self.env.cr.execute('''
          SELECT DISTINCT label_id FROM stock_move_label WHERE move_id IN (
            SELECT
              sm.id
            FROM
              stock_move sm
              LEFT OUTER JOIN intervention smi on sm.intervention_id = smi.id 
              LEFT OUTER JOIN park smp ON smi.park_id = smp.id
              LEFT OUTER JOIN stock_label sml ON sml.id = smp.num_serie_id

              LEFT OUTER JOIN mrp_workorder wo on sm.wo_outgoing_id = wo.id 
              LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id 
              LEFT OUTER JOIN intervention woi on mo.intervention_id = woi.id 
              LEFT OUTER JOIN park wop ON woi.park_id = wop.id 
              LEFT OUTER JOIN stock_label wol ON wol.id = wop.num_serie_id
            WHERE
              sm.type = 'in' AND
              sm.state = 'done' AND
              (
                sml.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s) OR
                wol.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s)
              )
          )  
        '''%(label_rc.id, label_rc.id))
        return self.env.cr.dictfetchall()
    
    
    def get_sav_label_out(self, label_rc):
        """
        Récupération de tous les mouvements sortants liés à une intervention (directement ou via un OT) 
        elle même liée à un park lui même lié à une des étiquettes composant l'étiquette
        """
        self.env.cr.execute('''
          SELECT x.move_id, x.intervention_name, x.wo_intervention_name, ml.done_date, ml.uom_qty, ml.label_id, x.product_id FROM 
            (SELECT
               sm.id as move_id,
               sm.product_id as product_id,
               smi.name as intervention_name,
               woi.name as wo_intervention_name
             FROM
               stock_move sm
               LEFT OUTER JOIN intervention smi on sm.intervention_id = smi.id 
               LEFT OUTER JOIN park smp ON smi.park_id = smp.id
               LEFT OUTER JOIN stock_label sml ON sml.id = smp.num_serie_id
 
               LEFT OUTER JOIN mrp_workorder wo on sm.wo_incoming_id = wo.id 
               LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id 
               LEFT OUTER JOIN intervention woi on mo.intervention_id = woi.id 
               LEFT OUTER JOIN park wop ON woi.park_id = wop.id 
               LEFT OUTER JOIN stock_label wol ON wol.id = wop.num_serie_id
             WHERE
               sm.type = 'out' AND
               sm.state = 'done' AND
               (
                 sml.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s) OR
                 wol.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s)
               )
            ) x
            JOIN stock_move_label ml ON ml.move_id = x.move_id
              
        '''%(label_rc.id, label_rc.id))
        return self.env.cr.dictfetchall()
    
    
    def get_sav_lot_in(self, label_rc):
        """
        Récupération de tous les mouvements entrants liés à une intervention (directement ou via un OT) 
        elle même liée à un park lui même lié à une des étiquettes composant l'étiquette
        """
        self.env.cr.execute('''
          SELECT DISTINCT lot_id FROM stock_move_lot WHERE move_id IN (
            SELECT
              sm.id
            FROM
              stock_move sm
              LEFT OUTER JOIN intervention smi on sm.intervention_id = smi.id 
              LEFT OUTER JOIN park smp ON smi.park_id = smp.id
              LEFT OUTER JOIN stock_label sml ON sml.id = smp.num_serie_id

              LEFT OUTER JOIN mrp_workorder wo on sm.wo_outgoing_id = wo.id 
              LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id 
              LEFT OUTER JOIN intervention woi on mo.intervention_id = woi.id 
              LEFT OUTER JOIN park wop ON woi.park_id = wop.id 
              LEFT OUTER JOIN stock_label wol ON wol.id = wop.num_serie_id
            WHERE
              sm.type = 'in' AND
              sm.state = 'done' AND
              (
                sml.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s) OR
                wol.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s)
              )
          )  
        '''%(label_rc.id, label_rc.id))
        return self.env.cr.dictfetchall()
    
    
    def get_sav_lot_out(self, label_rc):
        """
        Récupération de tous les mouvements sortant liés à une intervention (directement ou via un OT) 
        elle même liée à un park lui même lié à une des étiquettes composant l'étiquette
        """
        self.env.cr.execute('''
          SELECT x.move_id, x.intervention_name, x.wo_intervention_name, x.done_date, x.uom_qty, ml.lot_id, x.product_id FROM 
            (SELECT
               sm.id as move_id,
               sm.date as done_date,
               sm.uom_qty as uom_qty,
               sm.product_id as product_id,
               smi.name as intervention_name,
               woi.name as wo_intervention_name
             FROM
               stock_move sm
               LEFT OUTER JOIN intervention smi on sm.intervention_id = smi.id 
               LEFT OUTER JOIN park smp ON smi.park_id = smp.id
               LEFT OUTER JOIN stock_label sml ON sml.id = smp.num_serie_id
 
               LEFT OUTER JOIN mrp_workorder wo on sm.wo_incoming_id = wo.id 
               LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id 
               LEFT OUTER JOIN intervention woi on mo.intervention_id = woi.id 
               LEFT OUTER JOIN park wop ON woi.park_id = wop.id 
               LEFT OUTER JOIN stock_label wol ON wol.id = wop.num_serie_id
             WHERE
               sm.type = 'out' AND
               sm.state = 'done' AND
               (
                 sml.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s) OR
                 wol.id in (SELECT label_id FROM stock_label_traceability WHERE from_label_id = %s)
               )
            ) x
            JOIN stock_move_lot ml ON ml.move_id = x.move_id
              
        '''%(label_rc.id, label_rc.id))
        return self.env.cr.dictfetchall()
    
    
    def after_build_traceability(self, label_rc=False, lot_rc=False):
        """
            Construit les lignes de traçabilité de l'étiquette passée en paramètre
        """
        res = super(stock_label_traceability, self).after_build_traceability(label_rc=label_rc, lot_rc=lot_rc)
        if label_rc:
            # GESTION PAR ETIQUETTES
            # Suppression des informations "actuelles" et des enfants des étiquettes trouvés dans les mouvements sortants du SAV
            for label_datas in self.get_sav_label_in(label_rc):
                line_rcs = self.search([
                    ('from_label_id', '=', label_rc.id), 
                    '|', 
                        ('label_id', '=', label_datas['label_id']), 
                        '&', 
                            ('label_id', '=', False), 
                            ('initial_label_id', '=', label_datas['label_id'])
                ])
                if line_rcs:
                    line_rcs.write({
                        'label_id': False,
                        'lot_id': False,
                        'date': False,
                        'quantity': False,
                        'origin': False,
                    })
                    line_rcs.unlink_childs()
      
            # Ajout les informations "actuelles" et les enfants des étiquettes trouvés dans les mouvements entrants du SAV
            sav_label_out = {}
            # Conservation de la dernière ligne pour chaque étiquette en fonction de la date
            for label_out in self.get_sav_label_out(label_rc):
                if label_out['label_id'] in sav_label_out:
                    if label_out['done_date'] > sav_label_out[label_out['label_id']]['done_date']:
                        sav_label_out[label_out['label_id']] = label_out
                         
                else:
                    sav_label_out[label_out['label_id']] = label_out 
     
            for label_datas in sav_label_out.values():
                line_rcs = self.search([('from_label_id', '=', label_rc.id), ('product_id', '=', label_datas['product_id'])])
                origin = label_datas['intervention_name'] or label_datas['wo_intervention_name']
                if line_rcs:
                    line_rcs.write({
                        'label_id': label_datas.get('label_id', False), 
                        'lot_id': label_datas.get('lot_id', False), 
                        'date': label_datas['done_date'],
                        'quantity': label_datas['uom_qty'],
                        'origin': origin,
                    })
                else:
                    create_datas = {
                        'product_id': label_datas['product_id'], 
                        'move_date': label_datas['done_date'], 
                        'qty': label_datas['uom_qty'], 
                        'label_id': label_datas.get('label_id', False), 
                        'lot_id': label_datas.get('lot_id', False), 
                    }
                    line_rcs = self.create(self.prepare_line(create_datas, origin, label_rc.id, level=1, parent_rc=False))
                  
                line_rcs.compute_traceability()
    
    
            # GESTION PAR LOTS
            # Suppression des informations "actuelles" et des enfants des lots trouvés dans les mouvements sortants du SAV
            for lot_datas in self.get_sav_lot_in(label_rc):
                line_rcs = self.search([
                    ('from_label_id', '=', label_rc.id), 
                    '|', 
                        ('lot_id', '=', lot_datas['lot_id']), 
                        '&', 
                            ('lot_id', '=', False), 
                            ('initial_lot_id', '=', lot_datas['lot_id'])
                ])
                if line_rcs:
                    line_rcs.write({
                        'lot_id': False,
                        'label_id': False,
                        'date': False,
                        'quantity': False,
                        'origin': False,
                    })
                    line_rcs.unlink_childs()
      
            # Ajout les informations "actuelles" et les enfants des lots trouvés dans les mouvements entrants du SAV
            sav_lot_out = {}
            # Conservation de la dernière ligne pour chaque lot en fonction de la date
            for lot_out in self.get_sav_lot_out(label_rc):
                if lot_out['lot_id'] in sav_lot_out:
                    if lot_out['done_date'] > sav_lot_out[lot_out['lot_id']]['done_date']:
                        sav_lot_out[lot_out['lot_id']] = lot_out
                         
                else:
                    sav_lot_out[lot_out['lot_id']] = lot_out 
     
            for lot_datas in sav_lot_out.values():
                line_rcs = self.search([('from_label_id', '=', label_rc.id), ('product_id', '=', lot_datas['product_id'])])
                origin = lot_datas['intervention_name'] or lot_datas['wo_intervention_name']
                if line_rcs:
                    line_rcs.write({
                        'label_id': lot_datas.get('label_id', False), 
                        'lot_id': lot_datas.get('lot_id', False), 
                        'date': lot_datas['done_date'],
                        'quantity': lot_datas['uom_qty'],
                        'origin': origin,
                    })
                else:
                    create_datas = {
                        'product_id': lot_datas['product_id'], 
                        'move_date': lot_datas['done_date'], 
                        'qty': lot_datas['uom_qty'], 
                        'label_id': lot_datas.get('label_id', False), 
                        'lot_id': lot_datas.get('lot_id', False), 
                    }
                    line_rcs = self.create(self.prepare_line(create_datas, origin, label_rc.id, level=1, parent_rc=False))
                  
                line_rcs.compute_traceability()
                  
        return res