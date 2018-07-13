# -*- coding: utf-8 -*-
from openerp import models, api, fields


class stock_move(models.Model):
    _inherit = 'stock.move'

    
    def update_procurement_vals(self):
        res = super(stock_move, self).update_procurement_vals()
        if self.wo_incoming_id.simulation_id:
            res['simulation_id'] = self.wo_incoming_id.simulation_id.id
        elif self.sale_line_id.simulation_id:
            res['simulation_id'] = self.sale_line_id.simulation_id.id
            
        return res



class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    simulation_id = fields.Many2one('mrp.simulation', string='Simulation', required=False, ondelete='restrict')
        
        
    def check_auto_validate(self):
        if self.supply_method == 'produce':
            res = False
        else:
            res = True
        
        return res
    
    
    def test_create_wo(self):
        return bool(self.move_id.wo_incoming_id)
    
    
    def test_create_without_qty(self):
        if self.waiting_delay:
            res = True
            # S'il existe déja une simulation, pas de recréation même si le champ est coché
            all_proc_rs = self.get_proc_to_compute()
            for proc_rs in all_proc_rs:
                if proc_rs.mo_id and proc_rs.mo_id.state != 'cancel':
                    res = False
                    break
                
        else:
            res = False
            
        return res
    
    
    def test_override_stock(self):
        return True
    
    
    def create_mo_update_other_wo_data(self):
        res = super(procurement_order, self).create_mo_update_other_wo_data()
        if self.simulation_id:
            res['simulation_id'] = self.simulation_id.id
            
        return res

    
    def create_wo_update_other_wo_data(self):
        res = super(procurement_order, self).create_wo_update_other_wo_data()
        if self.simulation_id:
            res['simulation_id'] = self.simulation_id.id
            
        return res
    
    
    def do_action_on_mo_create(self, mo):
        if not self.move_id.wo_incoming_id:
            simulation_rc = self.env['mrp.simulation'].create({'mo_id': mo.id})
            if simulation_rc:
                # Si la quantité de la simulation est supperieur à 0: validation (simulation)
                if simulation_rc.quantity > 0:
                    simulation_rc.simulate_button()
                    
                # Si la quantité de la simulation est inférieur à 0
                #  Si le produit doit attendre la validation: simulation en confirmation délai
                #  Si le produit ne doit pas attendre la validation: terminée et mise à jour de la vente avec la date demandée
                else:
                    if simulation_rc.product_id.get_delay_confirmation_with_stock():
                        simulation_rc.wkf_delay_confirmation()
                    else:
                        simulation_rc.wkf_delay_confirmation()
                        self.update_delay(with_raise=False)
                        simulation_rc.mo_id.write({'need_delay_validation': False})
                        simulation_rc.wkf_done()
            
        return True