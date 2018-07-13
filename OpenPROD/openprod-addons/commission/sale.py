# -*- coding: utf-8 -*-

from openerp import models, fields, api


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.one
    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.commission_ids = [(5, 0)]
        if not self.partner_id:
            return

        commission_ids = list()
        rate_obj = self.env['commission.rate']
        rate_rs = rate_obj.search([
            ('partner_id', '=', self.partner_id.id),
        ])
        for rate_id in rate_rs:
            commission_ids.append([
                0, False, {
                    'agent_id': rate_id.agent_id,
                    'partner_id': rate_id.partner_id,
                    'commission_rule_set_id': rate_id.commission_rule_set_id.id,
                    'rate_id': rate_id,
                }
            ])
        self.commission_ids = commission_ids
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    commission_ids = fields.One2many(
        comodel_name='commission.sale',
        inverse_name='sale_order_id',
        string='Commissions'
    )

    @api.multi
    def copy(self, default=None):
        copy_ = super(sale_order, self).copy(default)
        for commission_id in self.commission_ids:
            commission_id.copy(default={'sale_order_id': copy_.id})
        return copy_
