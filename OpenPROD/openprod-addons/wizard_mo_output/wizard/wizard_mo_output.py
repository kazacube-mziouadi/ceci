# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class wizard_mo_output(models.TransientModel):
    """ 
        Wizard sortie OF
    """
    _name = 'wizard.mo.output'
    _description = "Wizard sortie OF"
    _rec_name = 'mo_id'
    
    
    @api.one
    @api.depends('mo_id')
    def _compute_mo(self):
        self.uom_id = self.mo_id and self.mo_id.uom_id.id or False
        self.total_qty = self.mo_id and self.mo_id.quantity or 0.0
        produce_qty = 0
        if self.mo_id:
            wo = self.env['mrp.workorder'].search([('mo_id', '=', self.mo_id.id)], order='sequence desc', limit=1)
            for wo_produce in wo.workorder_produce_ids:
                produce_qty += wo_produce.qty_ok
                
        self.produce_qty = produce_qty
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=True, ondelete='cascade')
    qty = fields.Float(string='Qty remaining', default=0.0, required=True, help="Qty remaining to be produced")
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_mo')
    wo_ids = fields.Many2many('mrp.workorder', 'wizard_mo_output_mrp_wo_rel', 'wizard_id', 'wo_id', string='WO')
    line_ids = fields.One2many('wizard.mo.output.line', 'mo_output_id',  string='Lines')
    label_ids = fields.Many2many('stock.label', 'wizard_mo_output_stock_label_rel', 'wizard_id', 'label_id', string='Label')
    total_qty = fields.Float(string='Total quantity of OF', default=0.0, required=False, compute='_compute_mo')
    produce_qty = fields.Float(string='Produce quantity', default=0.0, required=False, compute='_compute_mo')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('mo_id')
    def _onchange_mo_id(self):
        """
            Compléter les OTs
        """
        if self.mo_id and self.mo_id.workorder_ids:
            self.wo_ids = [(6, 0, self.mo_id.workorder_ids.ids)]
        else:
            self.wo_ids = []
        
        qty = self.total_qty - self.produce_qty
        if qty > 0:
            self.qty = qty
        else:
            self.qty = 0 
            
    
    @api.onchange('line_ids', 'line_ids.label_ids')
    def _onchange_line_ids(self):
        """
            Compléter les OTs
        """
        label_ids = []
        for line in self.line_ids:
            if line.label_ids:
                label_ids.extend(line.label_ids.ids)
                
        self.label_ids = [(6, 0, label_ids)]
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_validation(self):
        """
            Bouton de validation
        """
        reserv_obj = self.env['mrp.reservation']
        move_obj = self.env['stock.move']
        mlc_obj = self.env['mrp.label.consumption']
        for wiz in self:
            for line in wiz.line_ids:
                move_id = False
                if line.qty:
                    if line.is_label:
                        label_rs = self.env['stock.label']
                        for label in line.label_ids:
                            if label.location_id != line.location_dest_id:
                                label_rs += label
                        
                        if label_rs:
                            label_rs.move(line.location_dest_id)
                        else:
                            raise except_orm(_('Error'), _('For line %s[%s] / [%s]%s, there is no selected label'%(line.wo_id.mo_id.name, line.wo_id.sequence, line.product_id.code, line.product_id.name)))
                        
                    else:
                        if not line.location_src_id:
                            raise except_orm(_('Error'), _('For line %s[%s] / [%s]%s, there is no selected location'%(line.wo_id.mo_id.name, line.wo_id.sequence, line.product_id.code, line.product_id.name)))
                                                
                        move_rcs = move_obj.create_move(line.product_id, src_location=line.location_src_id, dst_location=line.location_dest_id, qty=line.qty, uom=line.uom_id)
                        move_rcs.wkf_waiting()
                        move_rcs.wkf_done()
                        move_id = move_rcs.id
                
                total_qty = line.qty + line.qty_taken_stock
                if total_qty:
                    vals_reserv = {
                                    'wo_id': line.wo_id.id,
                                    'product_id': line.product_id.id,
                                    'move_id': move_id,
                                    'uom_id': line.uom_id.id,
                                    'qty': total_qty,
                                    'user_id': self.env.user.id,
                                    'qty_mo': wiz.qty,
                                    'date': fields.Date.today(),
                                    'qty_taken_stock': line.qty_taken_stock,
                                }
                    
                    if line.label_ids:
                        vals_reserv['label_ids'] = [(6, 0, line.label_ids.ids)]
                        for label in line.label_ids:
                            mlc_obj.create({'wo_id': line.wo_id.id,
                                            'label_id': label.id,
                                            'use_consumption': True,
                                            'quantity': label.uom_qty,
                                            })
                    
                    reserv_obj.create(vals_reserv)
                    
            wiz.mo_id.wkf_ready()
            
        return True
    
    
    @api.multi
    def button_delete_line(self):
        """
            Bouton de create line
        """
        for wiz in self:
            wiz.line_ids.unlink()
        
        return {'type': 'ir.actions.act_window_dialog_reload'}
    
        
    @api.multi
    def button_create_line(self):
        """
            Bouton de create line
        """
        line_obj = self.env['wizard.mo.output.line']
        uom_obj = self.env['product.uom']
        reserv_obj = self.env['mrp.reservation']
        move_obj = self.env['stock.move']
        wo_obj = self.env['mrp.workorder']
        lvlr_obj = self.env['location.stock.level.report']
        label_obj = self.env['stock.label']
        for wiz in self:
            wiz.line_ids.unlink()
            lvl_ids = []
            qty_product_stock = {}
            total_label_ids = []
            for wo in wiz.wo_ids:
                for rm in wo.rm_draft_ids:
                    #Calcule de la quantité du besoin - celle déjà réservé et non utilisé pour la consommation
                    #Qty besoin: (besoin OF – réservation OF)
                    #réservation OF = réservation – conso si OT couturé c'est 0
                    #Il faut tenir compte aussi de ce que l'on a pu prendre en stock dans les précédents OTs
                    rm_qty = rm.efficient_unit_qty * (wiz.qty * wo.quantity) / wiz.mo_id.quantity
                    need_qty_init = uom_obj._compute_qty_obj(rm.uom_id, rm_qty, rm.product_id.uom_id)
                    reserv_qty, already_consum, label_ids_temp = self.compute_reserv_qty_already_consum(wo, rm.product_id, rm.product_id.uom_id, reserv_obj, uom_obj, move_obj)
                    reserv_qty -= already_consum
                    total_label_ids.extend(label_ids_temp)
                    qty_already_taken = reserv_qty > 0 and reserv_qty or 0
                    need_qty = need_qty_init
                    if reserv_qty > 0:
                        need_qty -= reserv_qty
                        if need_qty < 0:
                            need_qty = 0
                    
                    if rm.product_id not in qty_product_stock:
                        #Qty sur stock= (stock emplacement - réservation TOUT OF)
                        wo_rcs = wo_obj.search([('id', '!=', wo.id), ('state', 'not in', ('done', 'cancel', 'draft'))])
                        if rm.track_label_product:
                            label_loc_rcs = label_obj.search([('product_id', '=', rm.product_id.id), ('location_id', '=', wo.first_resource_id.location_id.id), ('state', '=', 'available')])
                            total_qty_product = 0
                            for label_loc in label_loc_rcs:
                                total_qty_product += label_loc.uom_qty
                                
                        else: 
                            lvlr_rcs = lvlr_obj.search([('product_id', '=', rm.product_id.id), ('location_id', '=', wo.first_resource_id.location_id.id)])
                            total_qty_product = lvlr_rcs and lvlr_rcs.uom_qty or 0
                        
                        if reserv_qty >= 0:
                            total_qty_product = total_qty_product - reserv_qty
                        
                        
                        for wo_int in wo_rcs:
                            reserv_qty, already_consum, label_ids_temp = self.compute_reserv_qty_already_consum(wo_int, rm.product_id, rm.product_id.uom_id, reserv_obj, uom_obj, move_obj)
                            qty_temp = reserv_qty - already_consum
                            total_label_ids.extend(label_ids_temp)
                            if qty_temp:
                                total_qty_product -= qty_temp
                                if total_qty_product < 0:
                                    total_qty_product = 0
                                    break
                                    
                        if total_qty_product < 0:
                            total_qty_product = 0
                        
                        qty_product_stock[rm.product_id] = {'total_qty_product': total_qty_product,
                                                            'label_ids': []}
                        
                    else:
                        total_qty_product = qty_product_stock[rm.product_id]['total_qty_product']
                    
                    #Dico pour création de la ligne
                    vals = {'mo_output_id': self.id,
                            'wo_id': wo.id,
                            'move_id': rm.id,
                            'is_label': rm.track_label_product,
                            'location_dest_id': wo.first_resource_id.location_id.id,
                            'product_id': rm.product_id.id,
                            'uom_id': rm.product_id.uom_id.id,
                            'qty_need': need_qty_init,
                            'qty_already_taken': qty_already_taken,
                            'qty_stock': total_qty_product,
                            }
                    
                    #Si le produit n'est pas tracé
                    if not rm.track_label_product:
                        #Si deux produits sont les même on ne récupère pas la qty sur le même emplacement
                        res_sql = False
                        if lvl_ids:
                            self.env.cr.execute("""
                                select 
                                    lvl.uom_qty as "qty",
                                    loc.id as "location_src_id",
                                    SUM(lvl.uom_qty) OVER (ORDER BY lvl.id) as "sum",
                                    lvl.id
                                from 
                                    location_stock_level_report lvl
                                    inner join stock_location loc on loc.id=lvl.location_id
                                where 
                                    loc.usage='internal'
                                    and (loc.control is null or loc.control = false)
                                    and (loc.quarantine is null or loc.quarantine = false)  
                                    and lvl.product_id=%s
                                    and lvl.id not in %s
                                    and lvl.uom_qty > 0
                                    and loc.id != %s
                                """, (rm.product_id.id, tuple(lvl_ids), wo.first_resource_id.location_id.id))
                            res_sql = self.env.cr.dictfetchall()
                        
                        if not res_sql:
                            self.env.cr.execute("""
                                select 
                                    lvl.uom_qty as "qty",
                                    loc.id as "location_src_id",
                                    SUM(lvl.uom_qty) OVER (ORDER BY lvl.id) as "sum",
                                    lvl.id
                                from 
                                    location_stock_level_report lvl
                                    inner join stock_location loc on loc.id=lvl.location_id
                                where 
                                    loc.usage='internal'
                                    and (loc.control is null or loc.control = false)
                                    and (loc.quarantine is null or loc.quarantine = false)
                                    and lvl.product_id=%s
                                    and lvl.uom_qty > 0
                                    and loc.id != %s
                                """, (rm.product_id.id, wo.first_resource_id.location_id.id))
                            res_sql = self.env.cr.dictfetchall()
                            
                        if need_qty:
                            qty = 0
                            #S'il y a des valeurs dans la requête on crée autant de lignes que d'emplacement tant que la qté du besoin n'est pas atteinte
                            if res_sql:
                                is_no_stock = False
                                for vals_sql in res_sql:
                                    vals_int = vals.copy()
                                    if need_qty > qty:
                                        lvl_ids.append(vals_sql['id'])
                                        qty = vals_sql['sum']
                                        vals_int['location_src_id'] = vals_sql['location_src_id']
                                        vals_int['qty'] = min(vals_sql['qty'], need_qty)
                                        vals_int['is_no_stock'] = is_no_stock
                                        line_obj.create(vals_int)
                                        if not is_no_stock:
                                            is_no_stock = True
                                            
                            else:
                                vals_int = vals.copy()
                                vals_int['location_src_id'] = ''
                                vals_int['qty'] = need_qty
                                line_obj.create(vals_int)
                                
                        else:
                            vals_int = vals.copy()
                            vals['qty'] = 0
                            line_obj.create(vals)
                    
                    # Si le produit est tracé
                    else:
                        self.env.cr.execute("""
                        select 
                            label_id, 
                            label_qty, 
                            uom_name, 
                            location_id,
                            location_barcode, 
                            location_name, 
                            sum 
                        from(
                            select 
                                label.id as "label_id",
                                label.uom_qty as "label_qty",
                                (select name from product_uom where id=label.uom_id) as "uom_name",
                                label.location_id,
                                (select barcode from stock_location where id=label.location_id) as "location_barcode",
                                (select name from stock_location where id=label.location_id) as "location_name",
                                SUM(label.uom_qty) OVER (ORDER BY label.id) as "sum"
                            from 
                                stock_label label
                            where 
                                product_id = %s
                                and id in (select label_id from stock_move_label where move_id in (select id from stock_move where wo_incoming_id= %s))
                                and label.uom_qty > 0
                                and state in ('available')
                            order by 
                                id asc) as sub

                        UNION

                        select 
                            label_id, 
                            label_qty, 
                            uom_name, 
                            location_id,
                            location_barcode, 
                            location_name, 
                            sum 
                        from(
                            select 
                                label.id as "label_id",
                                label.uom_qty as "label_qty",
                                (select name from product_uom where id=label.uom_id) as "uom_name",
                                label.location_id,
                                (select barcode from stock_location where id=label.location_id) as "location_barcode",
                                (select name from stock_location where id=label.location_id) as "location_name",
                                SUM(label.uom_qty+(case 
                                                        when
                                                            (label.id=(select min(id) 
                                                                        from 
                                                                            stock_label
                                                                        where 
                                                                            product_id = %s
                                                                            and id not in (select label_id from stock_move_label where move_id in (select id from stock_move where wo_incoming_id= %s))
                                                                            and label.uom_qty > 0
                                                                            and state in ('available')) 
                                                                            and (select 
                                                                                    SUM(uom_qty) 
                                                                                from 
                                                                                    stock_label 
                                                                                where 
                                                                                    id in   (select 
                                                                                                label_id 
                                                                                            from 
                                                                                                stock_move_label 
                                                                                            where 
                                                                                                move_id in (select 
                                                                                                                id 
                                                                                                            from 
                                                                                                                stock_move 
                                                                                                            where 
                                                                                                                wo_incoming_id= %s))) 
                                                                            is not null) 
                                                                then (select 
                                                                        SUM(uom_qty) 
                                                                    from 
                                                                        stock_label 
                                                                    where 
                                                                        id in   (select 
                                                                                    label_id 
                                                                                from 
                                                                                    stock_move_label 
                                                                                where 
                                                                                    move_id in (select 
                                                                                                    id 
                                                                                                from 
                                                                                                    stock_move 
                                                                                                where 
                                                                                                    wo_incoming_id= %s)))
                                                        else 0 end)) OVER (ORDER BY label.id) as "sum"
                            
                            from 
                                stock_label label
                            where 
                                product_id = %s
                                and id not in (select label_id from stock_move_label where move_id in (select id from stock_move where wo_incoming_id= %s))
                                and label.uom_qty > 0
                                and state in ('available')
                            order by id asc) as sub
                        ORDER BY sum
                        """, (rm.product_id.id, wo.id, rm.product_id.id, wo.id, wo.id, wo.id, rm.product_id.id, wo.id))
                        res_sql = self.env.cr.dictfetchall()
                        if need_qty:
                            qty = 0
                            label_ids = []
                            #S'il y a des valeurs dans la requête on crée une ligne pour toutes les étiquettes tant que la qté du besoin n'est pas atteinte sans utiliser celles déjà utilisées
                            if res_sql:
                                for vals_sql in res_sql:
                                    if vals_sql['label_id'] not in qty_product_stock[rm.product_id]['label_ids'] and vals_sql['label_id'] not in total_label_ids and vals_sql['location_id'] != wo.first_resource_id.location_id.id:
                                        if need_qty > qty:
                                            qty += vals_sql['label_qty']
                                            label_ids.append(vals_sql['label_id'])
                                            total_label_ids.append(vals_sql['label_id'])
                                
                                vals['qty'] = qty
                                vals['location_src_id'] = res_sql[0]['location_id']
                                if label_ids:
                                    vals['label_ids'] = [(6, 0, label_ids)]
                                    qty_product_stock[rm.product_id]['label_ids'].extend(label_ids)
                                    
                                line_obj.create(vals)
                            else:
                                vals['location_src_id'] = ''
                                vals['label_ids'] = []
                                vals['qty'] = need_qty
                                line_obj.create(vals)
                        else:
                            vals['qty'] = 0
                            line_obj.create(vals)
            
            if total_label_ids:
                wiz.write({'label_ids': [(6, 0, total_label_ids)]})
                               
        return {'type': 'ir.actions.act_window_dialog_reload'}
    
    
    
    def compute_reserv_qty_already_consum(self, wo, product, uom_id, reserv_obj, uom_obj, move_obj):
        reserv_rcs = reserv_obj.search([('wo_id', '=', wo.id), ('product_id', '=', product.id)])
        reserv_qty = 0
        label_ids = []
        for reserv in reserv_rcs:
            if (reserv.move_id and reserv.move_id.state == 'done') or product.track_label:
                reserv_qty += uom_obj._compute_qty_obj(reserv.uom_id, reserv.qty, uom_id)
                if reserv.label_ids:
                    label_ids.extend(reserv.label_ids.ids)
            
            elif not reserv.move_id:
                reserv_qty += uom_obj._compute_qty_obj(reserv.uom_id, reserv.qty_taken_stock, uom_id)
            
        already_consum = 0
        rm_done_rcs = move_obj.search([('wo_incoming_id', '=', wo.id), ('product_id', '=', product.id), ('state', '=', 'done')])
        for rm_done in rm_done_rcs:
            already_consum += uom_obj._compute_qty_obj(rm_done.uom_id, rm_done.uom_qty, uom_id)
        
        return reserv_qty, already_consum, label_ids
        
        

class wizard_mo_output_line(models.TransientModel):
    """ 
        Wizard ligne sortie OF 
    """
    _name = 'wizard.mo.output.line'
    _description = "Wizard ligne sortie OF"
    _rec_name = 'wo_id'
    _order = 'wo_id asc, product_id asc'
    
    
    @api.one
    @api.depends('label_ids')
    def _compute_qty_label(self):
        qty_label = 0
        for label in self.label_ids:
            qty_label += label.uom_qty
        
        self.qty_label = qty_label
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_output_id = fields.Many2one('wizard.mo.output', 'Output MO')
    wo_id = fields.Many2one('mrp.workorder', string='MO', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    qty_need = fields.Float(string='Need qty', default=0.0, required=False)
    qty_stock = fields.Float(string='Qty on stock', default=0.0, required=False)
    qty_already_taken = fields.Float(string='Qty already taken', default=0.0, required=False, help="Quantity already taken but not used")
    qty = fields.Float(string='Qty', default=0.0, required=False)
    qty_taken_stock = fields.Float(string='Qty taken from stock', default=0.0)
    label_ids = fields.Many2many('stock.label', 'wizard_mo_output_line_stock_label_rel', 'wizard_id', 'label_id', string='Label')
    location_src_id = fields.Many2one('stock.location', string='Location src', required=False, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Location dest', required=False, ondelete='cascade')
    is_label = fields.Boolean(string='Is label', default=False)
    is_no_stock = fields.Boolean(string='No stock', default=False)
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('qty', 'qty_taken_stock', 'label_ids', 'location_dest_id')
    def _onchange_routing_id(self):
        if self.is_label:
            qty = 0
            qty_taken_stock = 0
            for label in self.label_ids:
                if label.location_id != self.location_dest_id:
                    qty += label.uom_qty
                else:
                    qty_taken_stock += label.uom_qty
                
                self.location_src_id = label.location_id.id
            
            self.qty = qty
            self.qty_taken_stock = qty_taken_stock
    


class wizard_mo_output_line_add(models.TransientModel):
    """ 
        Ajout Wizard ligne sortie OF
    """
    _name = 'wizard.mo.output.line.add'
    _description = "Ajout Wizard ligne sortie OF"
    _rec_name = 'mo_output_line_id'
    
    
    @api.one
    @api.depends('mo_output_line_id')
    def _compute_mo_output_line_id(self):
        self.wo_id = self.mo_output_line_id.wo_id.id
        self.product_id = self.mo_output_line_id.product_id.id
        self.uom_id = self.mo_output_line_id.uom_id.id
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_mo_output_line_add, self).default_get(fields_list=fields_list)
        mo_output_line_id = self.env.context.get('active_id')
        mo_output_line = self.env['wizard.mo.output.line'].browse(mo_output_line_id)
        res['mo_output_line_id'] = mo_output_line_id
        res['wo_id'] = mo_output_line.wo_id.id
        res['product_id'] = mo_output_line.product_id.id
        res['uom_id'] = mo_output_line.uom_id.id
        res['location_dest_id'] = mo_output_line.location_dest_id.id
        return res
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_output_line_id = fields.Many2one('wizard.mo.output.line', 'Output MO')
    wo_id = fields.Many2one('mrp.workorder', string='MO', compute='_compute_mo_output_line_id')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_mo_output_line_id')
    location_src_id = fields.Many2one('stock.location', string='Location src', required=False, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Location dest', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=False)
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_mo_output_line_id')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_validation(self):
        """
            Bouton de validation
        """
        for wiz in self:
            wiz.mo_output_line_id.copy({'qty': wiz.qty,
                                        'location_src_id': wiz.location_src_id.id,
                                        'qty_taken_stock': 0,
                                        'is_no_stock': True})
            
            return {'type': 'ir.actions.act_window_dialog_parent_reload'}   
            

    