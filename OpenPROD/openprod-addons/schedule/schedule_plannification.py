# coding: utf-8

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import Warning



class schedule_planning_mo(models.Model):
    """ 
        Schedule planning MO
 
    """
    _name = 'schedule.planning.mo'
    _description = 'Schedule planning MO'
    _order = 'date asc'
    
    
    @api.one
    def _compute_search_date(self):
        """
            Fonction qui calcule les champs utilisés dans la recherche
        """
        self.is_week = False
        self.is_month = False  
        self.is_tomorrow = False 
        self.is_today = False 
        
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
                to_char(min(date), 'WW') as week_date,
                to_char(min(date), 'YYYY') as year_date,
                to_char((current_date), 'WW') as week_now,
                to_char((current_date), 'YYYY') as year_now,
                id
             FROM 
                 schedule_planning_mo 
             WHERE           
                 date is not null
             group by id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        if res_ids:
            if self.env.context.get('view_mo'):
                res_ids = self.search([('id', 'in', res_ids), ('mo_id', '!=', False)]).ids
            else:
                res_ids = self.search([('id', 'in', res_ids), ('wo_id', '!=', False)]).ids

        res = [('id', 'in', res_ids)]
        return res
    
    
    def _search_is_tomorrow(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont d'hier
        """
        request = """
        select 
            id
        from
            schedule_planning_mo
        where
            date::date =(current_date + interval '1 days')::date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        if res_ids:
            if self.env.context.get('view_mo'):
                res_ids = self.search([('id', 'in', res_ids), ('mo_id', '!=', False)]).ids
            else:
                res_ids = self.search([('id', 'in', res_ids), ('wo_id', '!=', False)]).ids

        res = [('id', 'in', res_ids)]
        return res
    
    
    def _search_is_today(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont d'aujourdhui
        """
        request = """
        select 
            id
        from
            schedule_planning_mo
        where
            date::date =(current_date)::date"""
        
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        if res_ids:
            if self.env.context.get('view_mo'):
                res_ids = self.search([('id', 'in', res_ids), ('mo_id', '!=', False)]).ids
            else:
                res_ids = self.search([('id', 'in', res_ids), ('wo_id', '!=', False)]).ids

        res = [('id', 'in', res_ids)]
        return res
    
    
    def _search_is_month(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont dans le mois
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
                to_char(min(date), 'MM') as week_date,
                to_char(min(date), 'YYYY') as year_date,
                to_char((current_date), 'MM') as week_now,
                to_char((current_date), 'YYYY') as year_now,
                id
             FROM 
                 schedule_planning_mo 
             WHERE
                 date is not null
             group by id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        if res_ids:
            if self.env.context.get('view_mo'):
                res_ids = self.search([('id', 'in', res_ids), ('mo_id', '!=', False)]).ids
            else:
                res_ids = self.search([('id', 'in', res_ids), ('wo_id', '!=', False)]).ids

        res = [('id', 'in', res_ids)]
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product final', required=False, ondelete='restrict')
    date = fields.Datetime(string='Date', required=True)
    time = fields.Float(string='Time', digits=dp.get_precision('Time'), readonly=1)
    qty = fields.Float(string='Qty', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    parent_id = fields.Many2one('schedule.planning.mo', string='Parent', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    is_week = fields.Boolean(string='Is week', compute='_compute_search_date', search='_search_is_week')
    is_tomorrow = fields.Boolean(string='Is tomorrow', compute='_compute_search_date', search='_search_is_tomorrow')
    is_month = fields.Boolean(string='Is month', compute='_compute_search_date', search='_search_is_month')
    is_today = fields.Boolean(string='Is today', compute='_compute_search_date', search='_search_is_today')
        
        
    def _compute_time_mo(self, qty=0):
        qty_wo = qty or self.qty
        return self._compute_time_wo(self.mo_id.workorder_ids, qty=qty_wo)
    
    
    def _compute_time_wo(self, workorder_rcs, qty=0):
        time = 0
        qty_wo = qty or self.qty
        for wo in workorder_rcs:
            for wo_resource in wo.wo_resource_ids:
                res = wo_resource._get_compute_time(qty_wo=qty_wo)
                time += res['total_preparation_time']
                time += res['total_production_time']
        
        return time


    @api.model
    def create(self, vals):
        """
            A la création l'OF on crée des copies dans les OTs
        """
        res = super(schedule_planning_mo, self).create(vals=vals)
        if 'mo_id' in vals and vals['mo_id']:
            time = res._compute_time_mo()
            res.write({'time': time})
            res.product_id = res.mo_id.product_id.id
            for wo in res.mo_id.workorder_ids:
                time_wo = self._compute_time_wo(wo, qty=res.qty)
                res.copy({
                            'mo_id': False,
                            'parent_id': res.id,
                            'wo_id': wo.id,
                            'time': time_wo
                        })
        
        return res
    
    
    @api.one
    def write(self, vals, with_covers=True, update_transfer_move=False):
        """
            Au write dans l'OF on modifie tous les liens dans les OTs
        """
        if vals and 'qty' in vals and self.mo_id:
            vals['time'] = self._compute_time_mo(qty=vals['qty'])
            
        res = super(schedule_planning_mo, self).write(vals)
        vals_wo = vals
        spm_obj = self.env['schedule.planning.mo']
        mo_spm_rcs = self.env['schedule.planning.mo']
        for spm in self:
            if spm.mo_id:
                mo_spm_rcs |= spm
        
        if mo_spm_rcs and vals_wo:       
            if 'mo_id' in vals_wo:
                del vals['mo_id']
            if 'wo_id' in vals_wo:
                del vals['wo_id']
            
            if 'parent_id' in vals_wo:
                del vals['parent_id']
            
            spm_rcs = spm_obj.search([('parent_id', 'in', mo_spm_rcs.ids)])
            if spm_rcs:
                if 'time' in vals_wo:
                    for spm in spm_rcs:
                        vals_wo['time'] = self._compute_time_wo(spm.wo_id, qty=vals['qty'])
                        spm.write(vals_wo)
                        
                else:
                    spm_rcs.write(vals_wo)
                    
        
        return res



