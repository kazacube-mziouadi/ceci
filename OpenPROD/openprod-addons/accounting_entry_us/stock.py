# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_compare
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, ValidationError, UserError
from openerp.addons.base_openprod import utils
from openerp.addons.base_openprod.common import get_form_view, hash_list
from operator import itemgetter

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY
from dateutil.parser import parse
from decimal import Decimal




class stock_valuation(models.Model):
    """ 
    Valuation 
    """
    _inherit = 'stock.valuation'


    def function_accounting_entry_us(self, svam_dico, price, uom_qty, move, qty, price_theo, account_move_rcs, account_move_obj, period_obj, lot_obj):
        line = []
        # Si le produit à pour Valorisation de l'inventaire LOT
        if 'lot_id' in svam_dico and svam_dico['lot_id']:
            name = _('Product: %s -- LOT: %s -- %s -- Qty: %f') %(svam_dico['product_code'], svam_dico['lot_name'], svam_dico['svam'].name, uom_qty)
        # Si non
        else:
            name = _('Product: %s -- %s -- Qty: %f') %(svam_dico['product_code'], svam_dico['svam'].name, uom_qty)
        
        mo_id = False
        if move.picking_id:
            name = _('%s -- Picking: %s') %(name, move.picking_id.name)
        elif move.wo_incoming_id:
            name = _('%s -- WO: %s[%s]') %(name, move.wo_incoming_id.mo_id.name, move.wo_incoming_id.sequence)
            mo_id = move.wo_incoming_id.mo_id.id
        elif move.wo_outgoing_id:
            name = _('%s -- WO: %s[%s]') %(name, move.wo_outgoing_id.mo_id.name, move.wo_outgoing_id.sequence)
            mo_id = move.wo_outgoing_id.mo_id.id
        elif move.wo_rm_subcontracting_id:
            name = _('%s -- WO: %s[%s]') %(name, move.wo_rm_subcontracting_id.mo_id.name, move.wo_rm_subcontracting_id.sequence)
            mo_id = move.wo_rm_subcontracting_id.mo_id.id
        elif move.wo_fp_subcontracting_id:
            name = _('%s -- WO: %s[%s]') %(name, move.wo_fp_subcontracting_id.mo_id.name, move.wo_fp_subcontracting_id.sequence)  
            mo_id = move.wo_fp_subcontracting_id.mo_id.id
        
        # Si le produit à comme Type valorisation réel
        if (svam_dico['supply_method'] == 'buy' and svam_dico['type_valuation_purchase'] == 'real') or (svam_dico['supply_method'] == 'produce' and svam_dico['type_valuation_production'] == 'real'):
            # On passe le montant négatif si le mouvement est sortant
            amount = price * uom_qty * (-1 if move.type == 'out' else 1) 
        # Si le produit à comme Type valorisation théo
        else:
            # On passe le montant négatif si le mouvement est sortant
            amount = price_theo * uom_qty * (-1 if move.type == 'out' else 1) 
        
        account_stock_in_id = svam_dico['account_stock_in_id']
        account_stock_out_id = svam_dico['account_stock_out_id']
        account_stock_value_in_id = svam_dico['account_stock_value_in_id']
        account_stock_value_out_id = svam_dico['account_stock_value_out_id']
        # Partie produit finit (produit fabriqué) 
        if svam_dico['supply_method'] == 'produce' and 'track_label' in svam_dico and svam_dico['track_label'] == True and 'start_date' in svam_dico and 'stop_date' in svam_dico and (( move.type == 'in' and move.wo_outgoing_id) or move.type == 'out'):
            if move.type == 'in' and move.wo_outgoing_id:
                # Mouvement entrant du produit finit du même OT avant la date du début
                self.env.cr.execute("""
                        select 
                            stock_label.lot_id,
                            max(stock_lot.total_mrp_rm_cost) as total_mrp_rm_cost,
                            max(stock_lot.total_mrp_produce_cost) as total_mrp_produce_cost
                        
                        from 
                            stock_move_label,
                            stock_label,
                            stock_lot
                        where 
                            stock_move_label.move_id in    (select
                                    id
                                from
                                    stock_move
                                where
                                    wo_outgoing_id = %s and
                                    date < %s and
                                    lot_id = %s) and
                            stock_label.id = stock_move_label.label_id
                            
                        group by 
                            stock_label.lot_id
                """, (move.wo_outgoing_id.id, svam_dico['start_date'], svam_dico['lot_id']))
                res_value_before_sql = self.env.cr.dictfetchall()
                before_total_mrp_rm_cost = 0
                before_total_mrp_produce_cost = 0
                for value_before_sql in res_value_before_sql:
                    before_total_mrp_rm_cost += value_before_sql['total_mrp_rm_cost']
                    before_total_mrp_produce_cost += value_before_sql['total_mrp_produce_cost']
                    
                # Mouvement entrant du produit finit du même OT dans la période
                self.env.cr.execute("""
                        select 
                            sum(stock_move_label.uom_qty) as uom_qty,
                            stock_label.lot_id
                        
                        from 
                            stock_move_label,
                            stock_label
                        where 
                            stock_move_label.move_id in (select
                                                            id
                                                         from
                                                            stock_move
                                                         where
                                                            wo_outgoing_id = %s and
                                                            date >= %s and
                                                            state='done') and
                            stock_label.id = stock_move_label.label_id
                            
                        group by 
                            stock_label.lot_id
                """, (move.wo_outgoing_id.id, svam_dico['start_date']))
                res_value_sql = self.env.cr.dictfetchall()
                move.wo_outgoing_id.mo_id.button_compute_theo_costs()
                move.wo_outgoing_id.mo_id.button_compute_real_costs()
                total_qty_lot_ids = 0
                total_qty_lot = 0
                for value_sql in res_value_sql:
                    total_qty_lot_ids += value_sql['uom_qty']
                    if svam_dico['lot_id'] == value_sql['lot_id']:
                        total_qty_lot += value_sql['uom_qty']
                
                if svam_dico['type_valuation_production'] == 'real':
                    mo_rm_cost = move.wo_outgoing_id.mo_id.real_rm_cost_aml
                    mo_produce_cost = move.wo_outgoing_id.mo_id.real_produce_cost
                else:
                    mo_rm_cost = move.wo_outgoing_id.mo_id.theo_rm_cost
                    mo_produce_cost = move.wo_outgoing_id.mo_id.theo_produce_cost
                
                lot_rm_cost = mo_rm_cost - before_total_mrp_rm_cost or mo_rm_cost
                lot_produce_cost = mo_produce_cost - before_total_mrp_produce_cost or mo_produce_cost
                lot_rm_cost = total_qty_lot_ids and lot_rm_cost / total_qty_lot_ids * total_qty_lot or lot_rm_cost
                lot_produce_cost = total_qty_lot_ids and lot_produce_cost / total_qty_lot_ids * total_qty_lot or lot_produce_cost
                lot = lot_obj.browse(svam_dico['lot_id'])
                if lot_rm_cost > 0:
                    total_mrp_rm_cost = lot.total_mrp_rm_cost + lot_rm_cost
                else:
                    total_mrp_rm_cost = lot.total_mrp_rm_cost
                
                if lot_produce_cost > 0:
                    total_mrp_produce_cost = lot.total_mrp_produce_cost + lot_produce_cost
                    name_produce = _('%s -- Produce')%(name)
                    lot_produce_cost_negative = -lot_produce_cost
                    account_move_rcs += svam_dico['svam'].scam_create_account_move(svam_dico['account_work_in_progress_id'], svam_dico['account_applied_overhead_id'], 
                                                                               svam_dico['account_applied_overhead_id'], svam_dico['account_work_in_progress_id'], 
                                                                               lot_produce_cost_negative, [], account_move_obj, name_produce, svam_dico['product_id'], 
                                                                               svam_dico['product_code'], move.date, uom_qty, svam_dico['uom_id'], period_obj, mo_id=mo_id, is_wo_rm=False)
                
                amount = lot_produce_cost + lot_rm_cost
                account_stock_in_id = svam_dico['account_finish_good_inv_id']
                account_stock_value_in_id = svam_dico['account_work_in_progress_id']
                name_total = _('%s -- Total')%(name)
                account_move_rcs += svam_dico['svam'].scam_create_account_move(account_stock_in_id, account_stock_out_id, 
                                                                               account_stock_value_in_id, account_stock_value_out_id, 
                                                                               amount, [], account_move_obj, name_total, svam_dico['product_id'], 
                                                                               svam_dico['product_code'], move.date, uom_qty, svam_dico['uom_id'], period_obj, mo_id=mo_id, is_wo_rm=True)
                
                lot.write({'qty_produce': move.wo_outgoing_id.mo_id.produce_total_qty,
                           'total_mrp_rm_cost': mo_rm_cost,
                           'total_mrp_produce_cost': mo_produce_cost})
            else:
                lot = lot_obj.browse(svam_dico['lot_id'])
                if lot.qty_produce:
                    total_mrp_rm_cost = lot.total_mrp_rm_cost / lot.qty_produce * uom_qty
                    total_mrp_produce_cost = lot.total_mrp_produce_cost / lot.qty_produce * uom_qty
                    account_stock_out_id = svam_dico['account_finish_good_inv_id']
                    account_stock_value_in_id = svam_dico['account_material_purchase_id']
                    account_stock_value_out_id = svam_dico['account_applied_overhead_id']
                    account_move_rcs += svam_dico['svam'].scam_create_account_move(account_stock_in_id, account_stock_out_id, 
                                                                               account_stock_value_in_id, account_stock_value_out_id, 
                                                                               total_mrp_produce_cost, line, account_move_obj, name, svam_dico['product_id'], 
                                                                               svam_dico['product_code'], move.date, uom_qty, svam_dico['uom_id'], period_obj, fp_delivery_mp=total_mrp_rm_cost, mo_id=mo_id, is_wo_rm=True)
        # Si le montant est différent de 0 on crée une pièce comptable et ses écritures
        elif amount != 0:
            account_move_rcs += svam_dico['svam'].scam_create_account_move(account_stock_in_id, account_stock_out_id, 
                                                                           account_stock_value_in_id, account_stock_value_out_id, 
                                                                           amount, line, account_move_obj, name, svam_dico['product_id'], 
                                                                           svam_dico['product_code'], move.date, uom_qty, svam_dico['uom_id'], period_obj, mo_id=mo_id, is_wo_rm=True)
        return account_move_rcs



class stock_valuation_account_move(models.Model):
    """ 
        Accounting for inventory valuation
    """
    _name = 'stock.valuation.account.move'
    _description = 'Accounting for inventory valuation'

    
    @api.model
    def _type_get(self):
        return [
                ('every_move', _('Every moves')),
                ('every_month', _('Every months')),
                       ]

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('cancel', _('Cancel')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    start_date = fields.Date(string='Start date', required=True)
    stop_date = fields.Date(string='Stop date', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict', help='If the field is empty it is launched for all warehouses')
    type = fields.Selection('_type_get', string='Type', default='every_month', required=True)
    state = fields.Selection('_state_get', string='State', default='draft', required=True)
    account_move_ids = fields.One2many('account.move', 'stock_val_id',  string='Account move')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, ondelete='restrict')
    comment = fields.Text(string='Comment')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('start_date', 'stop_date', 'type')
    def _onchange_date(self):
        res = {'warning' : {}}
        if self.type == 'every_month':
            if self.start_date:
                start_date = '%s01' %(self.start_date[0:8])
                if start_date != self.start_date:
                    self.start_date = start_date
                    res['warning'] = {'title': _('Warning'), 'message':_('If you choose every months, the start date must be the first of the month and the end date must be the last of the month')}
                
            if self.stop_date:
                stop_date = '%s01' %(self.stop_date[0:8])
                stop_date = fields.Date.to_string(datetime.strptime(stop_date, "%Y-%m-%d") + relativedelta(months=1) - timedelta(days=1))
                if stop_date != self.stop_date:
                    self.stop_date = stop_date
                    res['warning'] = {'title': _('Warning'), 'message':_('If you choose every months, the start date must be the first of the month and the end date must be the last of the month')}
        return res
    
    
    @api.onchange('type')
    def _onchange_type(self):
        if self.start_date:
            start_date = '%s01' %(self.start_date[0:8])
        else:
            start_date = '%s01' %(fields.Date.today()[0:8])
        self.start_date = start_date
        
        
    #===========================================================================
    # Buttons
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    @api.multi
    def wkf_cancel(self):
        for svam in self:
            if svam.account_move_ids:
                svam.account_move_ids.button_cancel() 
                svam.account_move_ids.unlink()
            
        self.write({'state': 'cancel'})
    
    
    @api.multi
    def wkf_validate(self):
        """
            Fonction de validation qui permet de créer les pièces comptables et les écritures selon une période donnée et un entrepot s'il est indiqué
        """
        period_obj = self.env['account.period']
        account_move_obj = self.env['account.move']
        lot_obj = self.env['stock.lot']
        move_obj = self.env['stock.move']
        warehouse_obj = self.env['stock.warehouse']
        valu_obj = self.env['stock.valuation']
        valu_lot_obj = self.env['stock.valuation.lot']
        uom_obj = self.env['product.uom']
        product_obj = self.env['product.product']
        for svam in self:
            date = fields.Date.context_today(svam)
            if svam.warehouse_id:
                warehouse_id = svam.warehouse_id.id
            else:
                warehouse_id = False
            
            # On recherche s'il y a un enregistrement sur la période donnée
            svam_exist_rcs = self.search([('id', '!=', svam.id), ('state', '=', 'validated'),
                                          '|', ('warehouse_id', '=', warehouse_id), ('warehouse_id', '=', False),
                                          '|', 
                                          '&', ('start_date', '<=', svam.start_date), ('stop_date', '>=', svam.start_date),
                                          '&', ('start_date', '<=', svam.stop_date), ('stop_date', '>=', svam.stop_date)], limit=1)
            if svam_exist_rcs:
                raise except_orm(_('Error'), _('There is already a record for this period. (%s)'%(svam_exist_rcs.name)))
            
            # Si on choisit par mois on se base sur la valorisation
            if svam.type == 'every_month':
                start_date = datetime.strptime(svam.start_date, "%Y-%m-%d")
                list_month = [start_date]
                i = 1
                # On calcule le nombre de mois entre les deux dates
                while svam.stop_date > fields.Date.to_string(start_date + relativedelta(months=i)):
                    list_month.append(start_date + relativedelta(months=i))
                    i += 1
                
                # On boucle sur les mois
                for date_month in list_month:
                    list_product_warehouse = []
                    month = str(date_month.month).zfill(2)
                    year = str(date_month.year)
                    # La date de la pièce comptable est le dernier jour du mois
                    date_temp = date_month + relativedelta(months=1) - timedelta(days=1)
                    date_temp = fields.Date.to_string(date_temp)
                    # Requête qui retourne tous les produits et infos présents dans les valos et valos par lots pour générer les écritures
                    self.env.cr.execute("""
                            (SELECT
                                product.id as product_id,
                                product.code as product_code,
                                product.inventory_valuation,
                                product.type_valuation_purchase,
                                product.type_valuation_production,
                                product.supply_method,
                                product.account_stock_out_id,
                                product.account_stock_in_id,
                                product.account_stock_value_in_id,
                                product.account_stock_value_out_id,
                                product.uom_id,
                                product_categ.account_stock_out_id as categ_account_stock_out_id,
                                product_categ.account_stock_in_id as categ_account_stock_in_id,
                                product_categ.account_stock_value_in_id as categ_account_stock_value_in_id,
                                product_categ.account_stock_value_out_id as categ_account_stock_value_out_id,
                                valuation.id as valuation_id,
                                0 as lot_id,
                                valuation.last_valuation as last_valuation,
                                valuation.valuation as valuation,
                                valuation.qty_in_stock as qty,
                                valuation.last_valuation_theo as last_valuation_theo,
                                valuation.warehouse_id as warehouse_id,
                                valuation.valuation_theo as valuation_theo
                            
                            FROM
                                product_product product,
                                product_category product_categ,
                                stock_valuation valuation
                            
                            WHERE
                                product.id = valuation.product_id and
                                product.categ_id = product_categ.id and
                                (product.account_stock_in_id is not null or product_categ.account_stock_in_id is not null) and
                                valuation.month = %s and
                                valuation.year = %s and
                                product.inventory_valuation = 'average'
                            
                            order by product.id)
                            
                            union all
                            
                            (SELECT
                                product.id as product_id,
                                product.code as product_code,
                                product.inventory_valuation,
                                product.type_valuation_purchase,
                                product.type_valuation_production,
                                product.supply_method,
                                product.account_stock_out_id,
                                product.account_stock_in_id,
                                product.account_stock_value_in_id,
                                product.account_stock_value_out_id,
                                product.uom_id,
                                product_categ.account_stock_out_id as categ_account_stock_out_id,
                                product_categ.account_stock_in_id as categ_account_stock_in_id,
                                product_categ.account_stock_value_in_id as categ_account_stock_value_in_id,
                                product_categ.account_stock_value_out_id as categ_account_stock_value_out_id,
                                valuation_lot.id as valuation_id,
                                valuation_lot.lot_id,
                                valuation_lot.last_valuation as last_valuation,
                                valuation_lot.valuation as valuation,
                                valuation_lot.qty_in_stock as qty,
                                valuation_lot.last_valuation_theo as last_valuation_theo,
                                valuation_lot.warehouse_id as warehouse_id,
                                valuation_lot.valuation_theo as valuation_theo
                            FROM
                                product_product product,
                                product_category product_categ,
                                stock_valuation_lot valuation_lot
                            WHERE
                                product.id = valuation_lot.product_id and
                                product.categ_id = product_categ.id and
                                (product.account_stock_in_id is not null or product_categ.account_stock_in_id is not null) and
                                valuation_lot.month = %s and
                                valuation_lot.year = %s and
                                product.inventory_valuation = 'lot'
                            order by 
                                product.id)
                      """, (month, year, month, year))
                    res_sql = self.env.cr.dictfetchall()
                    # Bouclé par produit ou lot
                    for x in res_sql:
                        if not svam.warehouse_id or svam.warehouse_id.id == x['warehouse_id']:
                            line = []
                            # Si plusieur ligne pour un produit non géré par lot on crée qu'une seule fois la piéce comptable
                            if (x['product_id'], x['warehouse_id']) not in list_product_warehouse:
                                if (x['inventory_valuation'] == 'lot' and x['valuation_id'] and x['lot_id'] > 0) or (x['inventory_valuation'] == 'average' and x['valuation_id'] and x['lot_id'] == 0):
                                    name = _('Product: %s -- %s') %(x['product_code'], svam.name)
                                    # Si pas géré par lot
                                    if x['inventory_valuation'] == 'average' and x['valuation_id'] and x['lot_id'] == 0:
                                        list_product_warehouse.append((x['product_id'], x['warehouse_id']))
                                    # Si géré par lot
                                    elif x['inventory_valuation'] == 'lot' and x['valuation_id'] and x['lot_id'] > 0:
                                        lot_name = lot_obj.browse(x['lot_id']).read(['name'])[0]['name']
                                        name = _('Product: %s -- LOT: %s -- %s') %(x['product_code'], lot_name, svam.name)
                                
                                    # Si géré prix réel
                                    if (x['supply_method'] == 'buy' and x['type_valuation_purchase'] == 'real') or (x['supply_method'] == 'produce' and x['type_valuation_production'] == 'real'):
                                        last_valuation = x['last_valuation'] or 0
                                        valuation = x['valuation'] or 0
                                    # Si géré prix théo
                                    else:
                                        last_valuation = x['last_valuation_theo'] or 0
                                        valuation = x['valuation_theo'] or 0
                                
                                else:
                                    last_valuation = 0
                                    valuation = 0
                                
                                # Si la valo est différente du mois précédent on génére la pièce comptable
                                if (valuation or last_valuation) and valuation - last_valuation != 0:
                                    account_stock_in_id = x['account_stock_in_id'] or x['categ_account_stock_in_id']
                                    account_stock_out_id = x['account_stock_out_id'] or x['categ_account_stock_out_id']
                                    account_stock_value_in_id = x['account_stock_value_in_id'] or x['categ_account_stock_value_in_id']
                                    account_stock_value_out_id = x['account_stock_value_out_id'] or x['categ_account_stock_value_out_id']
                                    amount = valuation - last_valuation
                                    move = svam.scam_create_account_move(account_stock_in_id, account_stock_out_id, account_stock_value_in_id, 
                                                                         account_stock_value_out_id, amount, line, account_move_obj, name, 
                                                                         x['product_id'], x['product_code'], date_temp, x['qty'], x['uom_id'], period_obj, is_wo_rm=True)
                                    # Pass invoice in context in method post: used if you want to get the same
                                    # account move reference when creating the same invoice after a cancelled one:
                                    move.post()
            # On boucle sur les mouvements
            else:
                start_date = '%s 00:00:00'%(svam.start_date)
                stop_date = '%s 23:59:59'%(svam.stop_date)
                # Requête qui sort les produits non gérés par lot dont il y a eu au moins un mouvement dans la période 
                self.env.cr.execute("""
                        SELECT
                            product.id as product_id,
                            product.code as product_code,
                            product.inventory_valuation,
                            product.type_valuation_purchase,
                            product.type_valuation_production,
                            product.supply_method,
                            product.track_label,
                            product.account_stock_out_id,
                            product.account_stock_in_id,
                            product.account_stock_value_in_id,
                            product.account_stock_value_out_id,
                            product.account_finish_good_inv_id,
                            product.account_work_in_progress_id,
                            product.account_applied_overhead_id,
                            product.account_material_purchase_id,
                            product.uom_id,
                            product_categ.account_stock_out_id as categ_account_stock_out_id,
                            product_categ.account_stock_in_id as categ_account_stock_in_id,
                            product_categ.account_stock_value_in_id as categ_account_stock_value_in_id,
                            product_categ.account_stock_value_out_id as categ_account_stock_value_out_id,
                            product_categ.account_finish_good_inv_id as categ_account_finish_good_inv_id,
                            product_categ.account_work_in_progress_id as categ_account_work_in_progress_id,
                            product_categ.account_applied_overhead_id as categ_account_applied_overhead_id,
                            product_categ.account_material_purchase_id as categ_account_material_purchase_id
                        FROM
                            product_product product,
                            product_category product_categ
                        WHERE
                            product.categ_id = product_categ.id and
                            product.inventory_valuation = 'average' and
                            (select id from stock_move where product_id = product.id and date >= %s and date <= %s and type in ('in', 'out') and state = 'done' limit 1) is not null
                """, (start_date, stop_date))
                res_product_sql = self.env.cr.dictfetchall()
                if svam.warehouse_id:
                    warehouse_rcs = svam.warehouse_id
                else:
                    warehouse_rcs = warehouse_obj.search([('company_id', '=', svam.company_id.id)])
                
                first_date = '%s01' %(svam.start_date[0:8])
                last_month = datetime.strptime(first_date, "%Y-%m-%d") - relativedelta(months=1)
                moves_for_period_out = {}
                # On boucle sur chaques produits
                for res_product in res_product_sql:
                    res_product['svam'] = svam
                    res_product['account_stock_in_id'] = res_product['account_stock_in_id'] or res_product['categ_account_stock_in_id']
                    res_product['account_stock_out_id'] = res_product['account_stock_out_id'] or res_product['categ_account_stock_out_id']
                    res_product['account_stock_value_in_id'] = res_product['account_stock_value_in_id'] or res_product['categ_account_stock_value_in_id']
                    res_product['account_stock_value_out_id'] = res_product['account_stock_value_out_id'] or res_product['categ_account_stock_value_out_id']
                    res_product['account_finish_good_inv_id'] = res_product['account_finish_good_inv_id'] or res_product['categ_account_finish_good_inv_id']
                    res_product['account_work_in_progress_id'] = res_product['account_work_in_progress_id'] or res_product['categ_account_work_in_progress_id']
                    res_product['account_applied_overhead_id'] = res_product['account_applied_overhead_id'] or res_product['categ_account_applied_overhead_id']
                    res_product['account_material_purchase_id'] = res_product['account_material_purchase_id'] or res_product['categ_account_material_purchase_id']
                    del res_product['categ_account_stock_in_id']
                    del res_product['categ_account_stock_out_id']
                    del res_product['categ_account_stock_value_in_id']
                    del res_product['categ_account_stock_value_out_id']
                    del res_product['categ_account_finish_good_inv_id']
                    del res_product['categ_account_work_in_progress_id']
                    del res_product['categ_account_applied_overhead_id']
                    del res_product['categ_account_material_purchase_id']
                    # On boucle sur les entrepots
                    for warehouse in warehouse_rcs:
                        # On recherche tous les mouvements sortant ou entrant si pas d'une production
                        moves_for_period = move_obj.search([
                                          ('date', '>=', start_date),
                                          ('date', '<=', stop_date),
                                          ('product_id', '=', res_product['product_id']),
                                          ('state', '=', 'done'),
                                          ('warehouse_id', '=', warehouse.id),
                                          '|', ('type', '=', 'out'), '&', '&', ('type', '=', 'in'), ('wo_outgoing_id', '=', False), ('wo_fp_subcontracting_id', '=', False)
                                          ], order="date ASC")
                        
                        
                        moves_for_period_temp = move_obj.search([
                                          ('date', '>=', start_date),
                                          ('date', '<=', stop_date),
                                          ('product_id', '=', res_product['product_id']),
                                          ('state', '=', 'done'),
                                          ('warehouse_id', '=', warehouse.id),
                                          ('type', '=', 'in'),
                                          '|', ('wo_outgoing_id', '!=', False), ('wo_fp_subcontracting_id', '!=', False)
                                          ], order="date ASC")
                        
                        if moves_for_period or moves_for_period_temp:
                            # On recherche la valo du mois précédent la première date du mouvement
                            last_valuation_id = valu_obj.search([('product_id', '=', res_product['product_id']), ('month', '=', str(last_month.month).zfill(2)), 
                                                                 ('year', '=', last_month.year), ('warehouse_id', '=', warehouse_id)])
                            if not len(last_valuation_id):
                                last_valuation_id = valu_obj.default_get(('qty_in_stock','valuation','price','valuation_theo','price_theo'))
                            
                            res_product['start_date'] = start_date
                            res_product['stop_date'] = stop_date
                            product = product_obj.browse(res_product['product_id'])
                            if moves_for_period_temp:
                                moves_for_period_out[product] = [moves_for_period_temp, last_valuation_id, res_product]
                            
                            # On va générer les écritures via la fonction du pmp
                            if moves_for_period:
                                account_move_rcs = valu_obj._get_price_pmp(moves_for_period, last_valuation_id, uom_obj, product=product, svam_dico=res_product)
                                if account_move_rcs:
                                    # Pass invoice in context in method post: used if you want to get the same
                                    # account move reference when creating the same invoice after a cancelled one:
                                    account_move_rcs.post()
                
                # Requête qui sort les produits gérés par lot dont il y a eu au moins un mouvement du lot dans la période 
                self.env.cr.execute("""
                        SELECT
                            product.id as product_id,
                            product.code as product_code,
                            product.inventory_valuation,
                            product.type_valuation_purchase,
                            product.type_valuation_production,
                            product.supply_method,
                            product.track_label,
                            product.account_stock_out_id,
                            product.account_stock_in_id,
                            product.account_stock_value_in_id,
                            product.account_stock_value_out_id,
                            product.account_finish_good_inv_id,
                            product.account_work_in_progress_id,
                            product.account_applied_overhead_id,
                            product.account_material_purchase_id,
                            product.uom_id,
                            product_categ.account_stock_out_id as categ_account_stock_out_id,
                            product_categ.account_stock_in_id as categ_account_stock_in_id,
                            product_categ.account_stock_value_in_id as categ_account_stock_value_in_id,
                            product_categ.account_stock_value_out_id as categ_account_stock_value_out_id,
                            product_categ.account_finish_good_inv_id as categ_account_finish_good_inv_id,
                            product_categ.account_work_in_progress_id as categ_account_work_in_progress_id,
                            product_categ.account_applied_overhead_id as categ_account_applied_overhead_id,
                            product_categ.account_material_purchase_id as categ_account_material_purchase_id,
                            lot.id as lot_id,
                            lot.name as lot_name
                        FROM
                            product_product product,
                            product_category product_categ,
                            stock_lot lot
                        WHERE
                            product.categ_id = product_categ.id and
                            product.inventory_valuation = 'lot' and
                            lot.product_id = product.id and
                            lot.id in (select lot_id from stock_label where id in 
                                        (select label_id from stock_move_label where move_id in 
                                            (select id from stock_move where product_id = product.id and date >= %s and date <= %s and type in ('in', 'out') and state = 'done' )) group by lot_id)
                """, (start_date, stop_date))
                res_product_lot_sql = self.env.cr.dictfetchall()
                moves_for_period_out_lot = {}
                # On boucle sur chaques lots
                for res_product_lot in res_product_lot_sql:
                    res_product_lot['is_lot'] = True
                    res_product_lot['svam'] = svam
                    res_product_lot['account_stock_in_id'] = res_product_lot['account_stock_in_id'] or res_product_lot['categ_account_stock_in_id']
                    res_product_lot['account_stock_out_id'] = res_product_lot['account_stock_out_id'] or res_product_lot['categ_account_stock_out_id']
                    res_product_lot['account_stock_value_in_id'] = res_product_lot['account_stock_value_in_id'] or res_product_lot['categ_account_stock_value_in_id']
                    res_product_lot['account_stock_value_out_id'] = res_product_lot['account_stock_value_out_id'] or res_product_lot['categ_account_stock_value_out_id']
                    res_product_lot['account_finish_good_inv_id'] = res_product_lot['account_finish_good_inv_id'] or res_product_lot['categ_account_finish_good_inv_id']
                    res_product_lot['account_work_in_progress_id'] = res_product_lot['account_work_in_progress_id'] or res_product_lot['categ_account_work_in_progress_id']
                    res_product_lot['account_applied_overhead_id'] = res_product_lot['account_applied_overhead_id'] or res_product_lot['categ_account_applied_overhead_id']
                    res_product_lot['account_material_purchase_id'] = res_product_lot['account_material_purchase_id'] or res_product_lot['categ_account_material_purchase_id']
                    del res_product_lot['categ_account_stock_in_id']
                    del res_product_lot['categ_account_stock_out_id']
                    del res_product_lot['categ_account_stock_value_in_id']
                    del res_product_lot['categ_account_stock_value_out_id']
                    del res_product_lot['categ_account_finish_good_inv_id']
                    del res_product_lot['categ_account_work_in_progress_id']
                    del res_product_lot['categ_account_applied_overhead_id']
                    del res_product_lot['categ_account_material_purchase_id']
                    # On boucle sur les entrepots
                    for warehouse in warehouse_rcs:
                        # On recherche tous les mouvements sortant ou entrant sans production
                        self.env.cr.execute(""" SELECT
                                                    stock_move_label.move_id
                                                FROM
                                                    stock_move_label
                                                WHERE
                                                    stock_move_label.move_id in 
                                                        (select id from stock_move where 
                                                                                        product_id = %s and date >= %s and date <= %s and state = 'done' and warehouse_id = %s and 
                                                                                        ((type = 'in' and wo_outgoing_id is null and wo_fp_subcontracting_id is null)
                                                                                        or (type = 'out' and (wo_incoming_id is not null or wo_rm_subcontracting_id is not null)))) and
                                                    stock_move_label.label_id in 
                                                        (select id from stock_label where lot_id = %s)
                                            """, (res_product_lot['product_id'], start_date, stop_date, warehouse.id, res_product_lot['lot_id']))
                        res_move_ids = self.env.cr.fetchall()
                        moves_for_period = [x[0] for x in res_move_ids]
                        
                        # On recherche tous les mouvements entrant avec production
                        self.env.cr.execute(""" SELECT
                                                    stock_move_label.move_id
                                                FROM
                                                    stock_move_label
                                                WHERE
                                                    stock_move_label.move_id in 
                                                        (select id from stock_move where product_id = %s and date >= %s and date <= %s and state = 'done' and warehouse_id = %s and
                                                                                        ((type = 'out' and wo_incoming_id is null and wo_rm_subcontracting_id is null) or 
                                                                                        (type = 'in' and (wo_outgoing_id is not null or wo_fp_subcontracting_id is not null)))) and
                                                    stock_move_label.label_id in 
                                                        (select id from stock_label where lot_id = %s)
                                            """, (res_product_lot['product_id'], start_date, stop_date, warehouse.id, res_product_lot['lot_id']))
                        res_move_temp_ids = self.env.cr.fetchall()
                        moves_for_period_temp = [x[0] for x in res_move_temp_ids]
                        if moves_for_period or moves_for_period_temp:
                            # On range tous les mouvements
                            moves_for_period = move_obj.search([('id', 'in', moves_for_period )], order="date ASC")
                            
                            # On recherche la valo du mois précédent la première date du mouvement
                            last_valuation_lot_id = valu_lot_obj.search([('product_id', '=', res_product_lot['product_id']), 
                                                                         ('month', '=', str(last_month.month).zfill(2)), 
                                                                         ('year', '=', last_month.year), 
                                                                         ('warehouse_id', '=', warehouse_id), 
                                                                         ('lot_id', '=', res_product_lot['lot_id'])])

                            if not len(last_valuation_lot_id):
                                last_valuation_lot_id = valu_obj.default_get(('qty_in_stock','valuation','price','valuation_theo','price_theo'))
                            
                            res_product_lot['start_date'] = start_date
                            res_product_lot['stop_date'] = stop_date
                            product = product_obj.browse(res_product_lot['product_id'])
                            if moves_for_period_temp:
                                moves_for_period_temp = move_obj.search([('id', 'in', moves_for_period_temp )], order="date ASC")
                                moves_for_period_out_lot[res_product_lot['lot_id']] = [moves_for_period_temp, last_valuation_lot_id, res_product_lot, product]
                            
                            # On va générer les écritures via la fonction du pmp
                            if moves_for_period:
                                account_move_rcs = valu_obj._get_price_pmp(moves_for_period, last_valuation_lot_id, uom_obj, product=product, svam_dico=res_product_lot)
                                if account_move_rcs:
                                    # Pass invoice in context in method post: used if you want to get the same
                                    # account move reference when creating the same invoice after a cancelled one:
                                    account_move_rcs.post()
                
                self.env.cr.commit()
                # Ecriture des mouvements entrant de produit finit, fait à la fin pour avec le prix des matières consommées soient correcte
                for moves_out in moves_for_period_out:
                    # On va générer les écritures via la fonction du pmp
                    account_move_rcs = valu_obj._get_price_pmp(moves_for_period_out[moves_out][0], moves_for_period_out[moves_out][1], uom_obj, 
                                                                                    product=moves_out, svam_dico=moves_for_period_out[moves_out][2])
                    if account_move_rcs:
                        # Pass invoice in context in method post: used if you want to get the same
                        # account move reference when creating the same invoice after a cancelled one:
                        account_move_rcs.post()
                
                # Ecriture des mouvements entrant de produit finit, fait à la fin pour avec le prix des matières consommées soient correcte 
                # ainsi que les mouvements sortant du produit finit pour que les prix des 3 écritures soient correct
                for moves_out_lot in moves_for_period_out_lot:
                    # On va générer les écritures via la fonction du pmp
                    account_move_rcs = valu_obj._get_price_pmp(moves_for_period_out_lot[moves_out_lot][0], moves_for_period_out_lot[moves_out_lot][1], uom_obj, 
                                                               product=moves_for_period_out_lot[moves_out_lot][3], svam_dico=moves_for_period_out_lot[moves_out_lot][2])
                    if account_move_rcs:
                        # Pass invoice in context in method post: used if you want to get the same
                        # account move reference when creating the same invoice after a cancelled one:
                        account_move_rcs.post()
                
                
                # Ecritures de compensations
                self.env.cr.commit()
                self.env.cr.execute("""
                         select 
                            val.sum_debit,
                            val.sum_credit,
                            val.mo_id,
                            val.product_id,
                            val.product_code,
                            val.uom_id,
                            val.account_stock_1_id,
                            val.account_stock_2_id
                        from
                        
                            (select 
                                sum(debit) sum_debit,
                                sum(credit) sum_credit,
                                mo_id,
                                (select product_id from mrp_manufacturingorder where id = mo_id) product_id,
                                (select code from product_product where id =(select product_id from mrp_manufacturingorder where id = mo_id)) product_code,
                                (select uom_id from product_product where id =(select product_id from mrp_manufacturingorder where id = mo_id)) uom_id,
                                (select account_id from account_move_line where mo_id = account_move_line.mo_id and credit != 0 limit 1) account_stock_1_id,
                                (select account_id from account_move_line where move_id = (select move_id from account_move_line where mo_id = account_move_line.mo_id and credit != 0 limit 1) and debit != 0) account_stock_2_id
                                                            
                            from
                                account_move_line
                            where
                            
                                mo_id in (select
                                    max(wo_done.mo_id)
                            
                                from
                                    (select 
                                    id,
                                    mo_id,
                                    sequence
                                    from 
                                    mrp_workorder
                            
                                    where
                                    real_end_date <= %s and 
                                    state = 'done') wo_done,
                                    mrp_workorder
                            
                                where
                                    wo_done.sequence = (select sequence from mrp_workorder where mo_id = wo_done.mo_id order by sequence desc limit 1)
                                    
                                group by
                            
                                    wo_done.id)
                            
                            group by
                                mo_id) val
                        where 
                        val.sum_debit != val.sum_credit""", (stop_date,))          
                
                res_mo_ids = self.env.cr.dictfetchall()   
                for res_mo in res_mo_ids:
                    if res_mo['sum_debit'] != res_mo['sum_credit'] and res_mo['account_stock_1_id'] and res_mo['account_stock_2_id']:
                        amount = res_mo['sum_debit'] - res_mo['sum_credit']
                        if amount != 0:
                            name = _('Product: %s -- %s') %(res_mo['product_code'], svam.name)
                            svam.scam_create_account_move_compensation(amount, account_move_obj, name, res_mo['product_id'], res_mo['product_code'],
                                                                       res_mo['uom_id'], period_obj, res_mo['account_stock_1_id'], res_mo['account_stock_2_id'], mo_id=res_mo['mo_id'])  
                
                    
            self.write({'state': 'validated'})
            return True
            
            
            
    def svam_prepa_account_move_line(self, date, name, product_id, product_code, account_id, debit, credit, stock_val_id, qty, uom_id, mo_id=False, is_wo_rm=False):
        """
            Fonction qui retourne le dico de creation d'écriture comptable
        """
        return {
            'date_maturity': False,
            'partner_id': False,
            'name': name[:64],
            'date': date,
            'debit': debit,
            'credit': credit,
            'account_id': account_id,
            'analytic_lines': [],
            'amount_currency': 0.0,
            'currency_id': False,
            'tax_code_id': False,
            'tax_amount': False,
            'ref': product_code,
            'quantity': qty,
            'product_id': product_id,
            'product_uom_id': uom_id,
            'analytic_account_id': False,
            'stock_val_id': stock_val_id,
            'mo_id': mo_id,
            'is_wo_rm': is_wo_rm,
        }
                 
    
    def scam_create_account_move(self, account_stock_in_id, account_stock_out_id, account_stock_value_in_id, account_stock_value_out_id, 
                                 amount, line, account_move_obj, name, product_id, product_code, date_temp, qty, uom_id, period_obj, fp_delivery_mp=False, mo_id=False, is_wo_rm=False):
        """
            Fonction qui permet de créer la pièce comptable et ses écritures
        """
        if not fp_delivery_mp:
            if amount > 0:
                name = _('IN -- %s')%(name)
                line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_value_in_id, 0, amount, self.id, qty, uom_id, mo_id=mo_id)))
                line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_in_id, amount, 0, self.id, qty, uom_id)))
            else:
                amount *= -1
                name = _('OUT -- %s')%(name)
                line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_out_id, 0, amount, self.id, qty, uom_id)))
                line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_value_out_id, amount, 0, self.id, qty, uom_id, mo_id=mo_id, is_wo_rm=is_wo_rm)))
        else:
            name = _('OUT -- %s')%(name)
            total = round((amount+fp_delivery_mp), 2)
            amount = round((amount), 2)
            fp_delivery_mp = round((fp_delivery_mp), 2)
            if total != (amount + fp_delivery_mp):
                ecart = float(Decimal(str(total)) - Decimal(str(amount)) - Decimal(str(fp_delivery_mp)))
                if ecart < 0.05:
                    fp_delivery_mp += ecart
            
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_out_id, 0, total, self.id, qty, uom_id)))
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_value_out_id, amount, 0, self.id, qty, uom_id, mo_id=mo_id, is_wo_rm=is_wo_rm)))
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_value_in_id, fp_delivery_mp, 0, self.id, qty, uom_id, mo_id=mo_id, is_wo_rm=is_wo_rm)))
                
        move_vals = {
            'ref': name,
            'line_id': line,
            'journal_id': self.journal_id.id,
            'date': date_temp,
            'narration': self.comment,
            'company_id': self.company_id.id,
            'stock_val_id': self.id
        }
        ctx = dict(self._context, lang=self.env.user.lang)
        ctx['company_id'] = self.company_id.id
        period = period_obj.with_context(ctx).find(date_temp)[:1]
        if period:
            move_vals['period_id'] = period.id
            for i in line:
                i[2]['period_id'] = period.id
        
        ctx_nolang = ctx.copy()
        ctx_nolang.pop('lang', None)
        return account_move_obj.with_context(ctx_nolang).create(move_vals)
    
    
    
    def scam_create_account_move_compensation(self, amount, account_move_obj, name, product_id, product_code, uom_id, period_obj, account_stock_1_id, account_stock_2_id, mo_id):
        """
            Fonction qui permet de créer la pièce comptable et ses écritures de compensation
        """
        name = _('Compensation -- %s')%(name)
        line = []
        date_temp = self.stop_date
        qty = 1
        if amount > 0:
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_1_id, 0, amount, self.id, qty, uom_id, mo_id=mo_id)))
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_2_id, amount, 0, self.id, qty, uom_id)))
        else:
            amount *= -1
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_1_id, amount, 0, self.id, qty, uom_id, mo_id=mo_id)))
            line.append((0, 0, self.svam_prepa_account_move_line(date_temp, name, product_id, product_code, account_stock_2_id, 0, amount, self.id, qty, uom_id)))
        move_vals = {
            'ref': name,
            'line_id': line,
            'journal_id': self.journal_id.id,
            'date': date_temp,
            'narration': self.comment,
            'company_id': self.company_id.id,
            'stock_val_id': self.id
        }
        ctx = dict(self._context, lang=self.env.user.lang)
        ctx['company_id'] = self.company_id.id
        period = period_obj.with_context(ctx).find(date_temp)[:1]
        if period:
            move_vals['period_id'] = period.id
            for i in line:
                i[2]['period_id'] = period.id
        
        ctx_nolang = ctx.copy()
        ctx_nolang.pop('lang', None)
        return account_move_obj.with_context(ctx_nolang).create(move_vals)
    
    @api.model
    def function_for_cron_create_accounting_inventory_valuation(self, type):
        """
            Fonction qui permet de créer le cron qui lance la création des pièces comptables de stock du mois précédent
        """
        last_month = datetime.strptime(fields.Date.today(), "%Y-%m-%d") - relativedelta(months=1)
        jounal = self.env['account.journal'].search([('type', '=', 'stock')], limit=1)
        name = _("Period %s/%s")%(str(last_month.month).zfill(2), str(last_month.year))
        date = datetime.strftime(last_month, "%Y-%m-%d")
        start_date = '%s01' %(date[0:8])
        stop_date = '%s01' %(date[0:8])
        stop_date = fields.Date.to_string(datetime.strptime(stop_date, "%Y-%m-%d") + relativedelta(months=1) - timedelta(days=1))
        vals = {'name': name,
                'start_date': start_date,
                'stop_date': stop_date,
                'type': type,
                'journal_id': jounal.id}
        
        svam_rcs = self.create(vals)
        svam_rcs.wkf_validate()
        return svam_rcs
        
        
    @api.model
    def cron_create_accounting_inventory_valuation_move(self):  
        """
            Cron qui lance la création des pièces comptables de stock sur les movements du mois précédent
        """ 
        self.function_for_cron_create_accounting_inventory_valuation(type='every_move')
    
    
    @api.model
    def cron_create_accounting_inventory_valuation_month(self):  
        """
            Cron qui lance la création des pièces comptables de stock sur le mois précédent
        """ 
        self.function_for_cron_create_accounting_inventory_valuation(type='every_month')
        
        
