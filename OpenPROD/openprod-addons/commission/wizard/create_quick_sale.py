# -*- coding: utf-8 -*-
from openerp import models, api


class create_quick_sale(models.TransientModel):
    """
        Wizard to create sale quickly
    """
    _inherit = 'create.quick.sale'

    @api.multi
    def create_quick_sale(self):
        """
            Fonction permettant de créer rapidement une vente
        """
        action_struc = super(create_quick_sale, self).create_quick_sale()
        res_id = action_struc.get('res_id', None)
        if not res_id:
            return action_struc

        sale_order_id = self.env['sale.order'].browse([res_id, ])
        rate_obj = self.env['commission.rate']
        commission_ids = list()

        rate_rs = rate_obj.search([
            ('partner_id', '=', sale_order_id.partner_id.id),
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
        sale_order_id.commission_ids = commission_ids
        return action_struc
