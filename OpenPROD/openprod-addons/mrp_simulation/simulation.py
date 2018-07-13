# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from openerp.exceptions import ValidationError
import openerp.addons.decimal_precision as dp

class mrp_simulation(models.Model):
    """ 
    Simulation 
    """
    _name = 'mrp.simulation'
    _description = 'Simulation'
    _rec_name = 'simulation_name'
    _inherits = {'mrp.manufacturingorder': 'mo_id'}
    

    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('progress', _('Progress')),
            ('delay_confirmation', _('Delay confirmation')),
            ('done', _('Done')),
            ('cancel', _('Cancel')),
        ]
    
    
    @api.one
    @api.depends('wo_ids')
    def _compute_pol_ids(self):
        self.rm_pol_ids = False
        self.fp_pol_ids = False
        for wo in self.wo_ids:
            if wo.is_subcontracting:
                self.rm_pol_ids |= wo.wo_subc_pol_rm_ids
                self.fp_pol_ids |= wo.wo_subc_pol_fp_ids
                 
        
        
    #===========================================================================
    # COLUMNS mrp_simulation
    #===========================================================================
    simulation_name = fields.Char(string='Name', size=64, required=True, default='/', readonly=True)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing order', required=True, ondelete='cascade')
    simulation_line_ids = fields.One2many('mrp.simulation.line', 'simulation_id',  string='Lines')
    wo_ids = fields.One2many('mrp.workorder', 'simulation_id',  string='Work orders')
    sale_uom_qty = fields.Float(string='Sale quantity', related='sale_line_id.uom_qty', readonly=True, digits=dp.get_precision('Product quantity'))
    sale_uom_id = fields.Many2one('product.uom', string='Sale UoM', related='sale_line_id.uom_id', readonly=True)
    need_delay_validation = fields.Boolean(related='mo_id.need_delay_validation', readonly=True)
    date_ok = fields.Date(string='Date of availability')
    warning = fields.Char(size=64, required=False)
    unit_price = fields.Float(string='Unit price', default=0.0, required=False, digits=dp.get_precision('Product price'))
    multi_level = fields.Boolean(default=False)
    rm_pol_ids = fields.One2many('purchase.order.line', string='RM PoL', compute='_compute_pol_ids')
    fp_pol_ids = fields.One2many('purchase.order.line', string='RM PoL', compute='_compute_pol_ids')
    state = fields.Selection('_state_get', default='draft', copy=False)
    
    
    #===========================================================================
    # ONCHANGE mrp_simulation
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement l'uom
        """
        res_onchange = self.env['mrp.manufacturingorder'].onchange_product_id(self.product_id, self.option_ids)
        self.uom_id = res_onchange['uom'] and res_onchange['uom'].id or False
        self.bom_id = res_onchange['bom'] and res_onchange['bom'].id or False
        self.routing_id = res_onchange['routing'] and res_onchange['routing'].id or False
    
        
    @api.onchange('needed_quantity', 'bom_id')
    def _onchange_quantity(self):
        """
            Vérification des minimum et multiples
        """
        res_onchange = self.env['mrp.manufacturingorder'].onchange_quantity(self.product_id, self.needed_quantity, self.bom_id)
        self.quantity = res_onchange['quantity']
            
    
    @api.onchange('routing_id', 'bom_id')
    def _onchange_bom_routing_id(self):
        """
            Au changement de la nomenclature ou de la gamme, changement de la note pour production
        """
        res_onchange = self.env['mrp.manufacturingorder'].onchange_bom_routing_id(self.bom_id, self.routing_id)
        self.note_manufacturing = res_onchange['note']
        
        
    #===========================================================================
    # BOUTONS & METHODES mrp_simulation
    #===========================================================================
    def get_bom_qty(self, bom, qty):
        if bom.type_component == 'formula':
            return roundingUp(bom.compute_qty_formula(bom.formula_component, bom.quantity, bom.efficiency, qty*bom.quantity, qty, [('specific_offer_id', '=', self.id)]), bom.round)
        elif bom.type_component == 'variable':
            return roundingUp(bom.quantity * qty / (bom.efficiency if bom.efficiency else 1), bom.round)
        else:
            return roundingUp(bom.quantity / (bom.efficiency if bom.efficiency else 1), bom.round)
    
            
    @api.one
    def compute_critical_path(self):
        self.simulation_line_ids.write({'critical_path':False})
        crit = self.simulation_line_ids[0]
        pos = 1
        cont = True
        while cont and len(self.simulation_line_ids) > pos + 1:
            crit.critical_path = True
            new_crit = self.simulation_line_ids[pos+1]
            next_pos = -1
            # Trouve la bonne ligne
            for i, line in enumerate(self.simulation_line_ids[pos+1:]):
                if line.level == crit.level:
                    break
                elif line.level == crit.level + 1 and line.availability_date > new_crit.availability_date:
                    new_crit = line
                    next_pos = i
                else:
                    continue
                
            # Marque la ligne trouvée précédemment comme critique
            for i, line in enumerate(self.simulation_line_ids[pos+1:]):
                if line.level == crit.level:
                    break
                elif line.level == crit.level + 1 and line.availability_date == new_crit.availability_date:
                    line.critical_path = True
                else:
                    continue
                
            if next_pos == -1:
                cont = False
            crit = new_crit
            pos = pos + next_pos + 1
            
        return True
            
            
    def get_lines(self, product_rs, value_ids, option_ids, level, qty, uom_id, start_date, multi_level=True, first=True):
        bom_obj = self.env['mrp.bom']
        wo_obj = self.env['mrp.workorder']
        if product_rs:
            bom_rs = bom_obj._bom_find(product_rs.id, product_rs.uom_id, option_ids)
            if bom_rs:
                routing = bom_rs.routing_ids[0]
                option_id = bom_rs.option_id.id
                product_rs = wo_obj._get_product(bom_rs, value_ids, product_rs)
            else:
                routing = None
                option_id = None
                product_rs = wo_obj._get_product(None, value_ids, product_rs)
            
            if product_rs.supply_method == 'produce' and routing:
                pricetime = routing.function_compute_price(serie_eco=qty, option_ids=option_ids.ids)
                unit_price = pricetime[0]
                delay = pricetime[2] / self.env['calendar'].get_avg_hours()
            elif product_rs.supply_method == 'buy':
                delay = product_rs.get_default_supply_delay_purchase()
                unit_price = bom_obj.compute_price_component_buy(product_rs, qty, product_rs.uom_id, self.env.user.company_id.currency_id)
            else:
                unit_price = 0
                delay = 0
            
            res = [{
                'name': product_rs.name,
                'bom_id': bom_rs.id if bom_rs else None,
                'product_id': product_rs.id,
                'level': level,
                'supply_method': product_rs.supply_method,
                'quantity': qty,
                'available_stock': product_rs.available_stock,
                'virtual_stock': product_rs.virtual_stock,
                'option_id': option_id,
                'routing_id': routing and routing.id or False,
                'unit_price': unit_price,
                'total_price': unit_price * qty,
                'uom_id': uom_id.id,
                'delay': delay,
                'supplier_id': product_rs.sinfo_ids and product_rs.sinfo_ids[0].partner_id.id,
            }]
            max_delay = 0
            new_start_date = start_date
            if bom_rs and (multi_level or first):
                for bom in wo_obj._get_list_bom_consommed(bom_rs, option_ids):
                    bom_qty = self.get_bom_qty(bom, qty)
                    child_vals = self.get_lines(bom.product_id, value_ids, option_ids, level + 1, bom_qty, bom.uom_id, start_date, multi_level=multi_level, first=False)
                    new_start_date = max(new_start_date, child_vals[0]['availability_date'])
                    res += child_vals
                    max_delay = max(max_delay, child_vals[0]['cumulative_delay'])
                    
            availability_date = product_rs.simulate_availability(qty, None, self.option_ids, new_start_date)
            res[0]['availability_date'] = availability_date
            res[0]['cumulative_delay'] = delay + max_delay
        else:
            res = []
        
        return res
        
    
    @api.multi
    def simulate_button(self):
        for simulation in self:
            simulation.simulate()
            simulation.action_generating_wo()
            simulation.wkf_progress()
        
    def simulate(self):
        """
            Création des lignes de simulation en fonction de la nomenclature
        """
        bom_obj = self.env['mrp.bom']
        option_ids = self.env['mrp.option'].browse([x.option_id.id for x in self.option_ids])
        bom_id = bom_obj._bom_find(self.product_id.id, self.product_id.uom_id, option_ids)
        if not (bom_id and bom_id.routing_ids[0]):
            raise ValidationError(_('BoM not found'))
        
        self.simulation_line_ids.unlink()
        line_vals = self.get_lines(self.product_id, [], option_ids, 1, self.quantity, self.uom_id, self.requested_date, self.multi_level)
        vals = {
            'simulation_line_ids': [(0, 0, x) for x in line_vals],
        }
        self.write(vals)
        self.compute_critical_path()
        return True
    

    @api.multi
    def button_del_mo_and_son_mo(self):
        """
            Suppression des ordres de travail
        """
        for simulation in self:
            simulation.mo_id.del_mo_and_son_mo(without_head=True)
    
        return True
    

    @api.multi
    def conf_delay_button(self):
        """
            Confirmation délai
        """
        return self[0].mo_id.conf_delay_button()

        
    @api.multi
    def action_generating_wo(self):
        """
            Génération des ordres de travail
        """
        wo_obj = self.env['mrp.workorder']
        for simulation in self:
            simulation.mo_id.action_generating_wo()
            wo_obj.plannification_mo_at_earlier(
                simulation.requested_date, 
                simulation.mo_id,
                is_sublevel=True, 
                is_procur_level_manufact=self.multi_level,
                is_product_sublevel_manufact=self.multi_level,
                is_procur_level_purchase=True,
                automatic_purchase=True,
                is_procur_sublevel_purchase=self.multi_level,
                first_mo_id=True,
                is_delay_rm=False,
                change_resources=True,
                no_modif_prio_date=False,
            )
        
        return True
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_progress(self):
        self.write({'state': 'progress'})
        
        
    @api.multi
    def wkf_delay_confirmation(self):
        self.write({'state': 'delay_confirmation'})
        for simulation_rc in self:
            simulation_rc.mo_id.write({'state': 'done'})
    
    
    @api.multi
    def wkf_done(self):
        for simulation_rc in self:
            if simulation_rc.need_delay_validation:
                raise ValidationError(_('Impossible to make done a simulation that requires a date confirmation.'))                
            
        self.write({'state': 'done'})
    
    
    @api.multi
    def wkf_cancel(self):
        self.button_del_mo_and_son_mo()
        self.write({'state': 'cancel'})
    
    
    @api.multi
    def wkf_reset(self):
        self.wkf_cancel()
        self.wkf_draft()
    
    
    @api.model
    def create(self, vals):
        """
            Nom à partir de sa séquence en base
            Liaison de l'OF avec la simulation pour permettre la propagation de la simulation dans les OT
        """
        if vals.get('simulation_name', '/') == '/':
            vals['simulation_name'] = self.env['ir.sequence'].get('mrp.simulation') or '/'
        
        if 'mo_id' not in vals:
            mo_rs = self.env['mrp.manufacturingorder'].create_mo(
                        self.env['product.product'].browse(vals['product_id']), 
                        quantity=1.0, 
                        bom=vals.get('bom_id', False) and self.env['mrp.bom'].browse(vals['bom_id']), 
                        routing=vals.get('routing_id', False) and self.env['mrp.routing'].browse(vals['routing_id']), 
                    )
            if mo_rs:
                vals['mo_id'] = mo_rs.id
            
        res = super(mrp_simulation, self).create(vals)
        if res:
            res.mo_id.write({'simulation_id': res.id})
        
        return res
    
    
    @api.multi
    def copy(self, default=None):
        """
            Interdiction de copie
        """
        if not self._context.get('ok_copy', False):
            raise ValidationError(_('Impossible to copy a simulation.'))
        
        return super(mrp_simulation, self).copy(default=default)


    
class mrp_simulation_line(models.Model):
    """ 
    Simulation line 
    """
    _name = 'mrp.simulation.line'
    _description = 'Simulation line'
    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
            ('produce', _('Produce')),
        ]
        
    
    @api.depends('level')
    def _compute_name(self):
        for rec in self:
            rec.name = '----' * (rec.level - 1) + rec.product_id.name
    
    
    @api.one
    @api.depends()
    def _compute_availability(self):
        for line in self:
#             reservation_move_rs = self.env['stock.move'].search([
#                                       ('state', '=', 'waiting'),
#                                       ('simulation_reservation_id', '=', line.simulation_id.id),
#                                       ('product_id', '=', line.product_id.id),
#                                   ], limit=1)
#             if reservation_move_rs:
#                 self.availability = reservation_move_rs.read(['covered_by_stock_percent'])[0]['covered_by_stock_percent']
#             else:  
                self.availability = 0.0
        
    #===========================================================================
    # COLUMNS mrp_simulation_line
    #===========================================================================
    name = fields.Char(compute='_compute_name', string='Name')
    simulation_id = fields.Many2one('mrp.simulation', string='Simulation', required=True, ondelete='cascade', select=True)
    product_id = fields.Many2one('product.product', ondelete='restrict')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, domain="[('is_supplier', '=', True)]", ondelete='restrict')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='restrict')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='restrict')
    option_id = fields.Many2one('mrp.option', string='Options', delete='cascade')
    level = fields.Integer(string='Level', default=1, required=True)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    delay = fields.Integer(string='Delay')
    cumulative_delay = fields.Integer('Cumulative delay')
    unit_price = fields.Float(string='Unit price', default=0.0, digits=dp.get_precision('Account'), required=False)
    total_price = fields.Float(string='Total price', default=0.0, digits=dp.get_precision('Account'), required=False)
    available_stock = fields.Float(string='Available stock qty', default=0.0, required=False)
    virtual_stock = fields.Float(string='Virtual stock qty', default=0.0, required=False)
    availability_date = fields.Date(string='Availability date')
    critical_path = fields.Boolean(string='Critical Path', default=False)
    availability = fields.Float(compute='_compute_availability')
