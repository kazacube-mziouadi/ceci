# -*- coding: utf-8 -*-
from openerp import models, fields, api


class add_agent_in_partner(models.TransientModel):
    """Add agent in partner"""
    
    _name = 'add.agent.in.partner'
    _rec_name = 'agent_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_agent_in_partner, self).default_get(fields_list=fields_list)
        if self._context.get('active_ids') and self._context.get('active_model') == 'res.partner':
            res['partner_ids'] = self._context.get('active_ids')
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    agent_id = fields.Many2one('commission.agent', string='Agent', required=True, ondelete='restrict')
    commission_id = fields.Many2one('commission.rule.set', string='Commission', required=True, ondelete='restrict')
    partner_ids = fields.Many2many('res.partner', 'add_agent_in_partner_partner_rel', 'wiz_id', 'partner_id',   string='Partners')
    is_propagate = fields.Boolean(string='Propagate order not invoiced or invoices not validated and invoice(not validate)', default=False)
    is_propagate_draft = fields.Boolean(string='Propagate only order draft', default=False)
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def validate(self):
        comm_rate_obj = self.env['commission.rate']
        sale_obj = self.env['sale.order']
        comm_sale_obj = self.env['commission.sale']
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        comm_invoice_line_obj = self.env['commission.invoice.line']
        for wiz in self:
            partner_ids = wiz.partner_ids.ids
            if partner_ids:
                #Remplacement dans la partie partenaire
                for partner_id in partner_ids:
                    part_agent_rcs = comm_rate_obj.search([('agent_id', '=', wiz.agent_id.id), ('partner_id', '=', partner_id)])
                    if not part_agent_rcs:
                        vals_agent = {  'agent_id': wiz.agent_id.id,
                                        'commission_rule_set_id': wiz.commission_id.id,
                                        'partner_id': partner_id}
                        
                        comm_rate_obj.create(vals_agent)
                
                if wiz.is_propagate:
                    #Remplacement dans la partie Vente si propagation si les ventes ne sont pas terminées et qu'il n'a pas un facture différente de brouillon
                    #Remplacement dans la partie Facturation si propagation si la facture est draf
                    sale_search = [('state', 'not in', ('cancel', 'done')), ('partner_id', 'in', partner_ids)]
                    invoice_search = [('state', '=', 'draft'), ('type', '=', 'out_invoice'), ('partner_id', 'in', partner_ids)]
                elif wiz.is_propagate_draft:
                    #Remplacement que dans la partie Vente si les ventes sont brouillons
                    sale_search = [('state', '=', 'draft'), ('partner_id', 'in', partner_ids)]
                    invoice_search = [('id', '=', False)]
               
                if wiz.is_propagate or wiz.is_propagate_draft:     
                    #Remplacement dans la partie Vente
                    sale_rcs = sale_obj.search(sale_search)
                    del_sale_ids = []
                    if sale_rcs:
                        for sale in sale_rcs:
                            for invoice_line in sale.invoice_line_ids:
                                if invoice_line.state not in ('draft', 'cancel'):
                                    del_sale_ids.append(sale.id)
                                    break
                        
                        sale_ids = sale_rcs.ids
                        if del_sale_ids:
                            sale_ids = list(set(sale_rcs.ids)-set(del_sale_ids))
                        
                        if sale_ids:
                            for sale_id in sale_ids:
                                sale_agent_rcs = comm_sale_obj.search([('agent_id', '=', wiz.agent_id.id), ('sale_order_id', '=', sale_id)])
                                if not sale_agent_rcs:
                                    vals_sale = {'agent_id': wiz.agent_id.id,
                                                 'commission_rule_set_id': wiz.commission_id.id,
                                                 'sale_order_id': sale_id}
                                    
                                    comm_sale_obj.create(vals_sale)
                    
                    #Remplacement dans la partie Facturation
                    invoice_rcs = invoice_obj.search(invoice_search)
                    if invoice_rcs:
                        invoice_line_rcs = invoice_line_obj.search([('account_invoice_line_id', 'in', invoice_rcs.ids)])
                        if invoice_line_rcs:
                            for invoice_line in invoice_line_rcs:
                                invoice_line_agent_rcs = comm_invoice_line_obj.search([('agent_id', '=', wiz.agent_id.id), ('account_invoice_line_id', '=', invoice_line.id)])
                                if not invoice_line_agent_rcs:
                                    vals_invoice = {'agent_id': wiz.agent_id.id,
                                                'commission_rule_set_id': wiz.commission_id.id,
                                                'account_invoice_line_id': invoice_line.id}
                                    comm_invoice_line_obj.create(vals_invoice)
        
        
        return {'type': 'ir.actions.act_window_close'}



class modif_agent_in_partner(models.TransientModel):
    """modificate_agent_in_partner"""
    
    _name = 'modif.agent.in.partner'
    _rec_name = 'agent_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(modif_agent_in_partner, self).default_get(fields_list=fields_list)
        if self._context.get('active_id') and self._context.get('active_model') == 'commission.agent':
            res['agent_id'] = self._context.get('active_id')
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    agent_id = fields.Many2one('commission.agent', string='Agent', required=True, ondelete='restrict')
    new_agent_id = fields.Many2one('commission.agent', string='New agent', required=True, ondelete='restrict')
    commission_id = fields.Many2one('commission.rule.set', string='Commission', required=True, ondelete='restrict')
    is_propagate = fields.Boolean(string='Propagate order not invoiced or invoices not validated and invoice(not validate)', default=False)
    is_propagate_draft = fields.Boolean(string='Propagate only order draft', default=False)
    
    
    @api.multi
    def validate(self):
        comm_rate_obj = self.env['commission.rate']
        sale_obj = self.env['sale.order']
        comm_sale_obj = self.env['commission.sale']
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        comm_invoice_line_obj = self.env['commission.invoice.line']
        for wiz in self:
            vals = {'agent_id': wiz.new_agent_id.id, 'commission_rule_set_id': wiz.commission_id.id}
            #Remplacement dans la partie partenaire
            part_agent_rcs = comm_rate_obj.search([('agent_id', '=', wiz.agent_id.id)])
            if part_agent_rcs:
                part_agent_rcs.write(vals)
            
            if wiz.is_propagate:
                #Remplacement dans la partie Vente si propagation si les ventes ne sont pas terminées et qu'il n'a pas un facture différente de brouillon
                #Remplacement dans la partie Facturation si propagation si la facture est draf
                sale_search = [('state', 'not in', ('cancel', 'done'))]
                invoice_search = [('state', '=', 'draft'), ('type', '=', 'out_invoice')]
            elif wiz.is_propagate_draft:
                #Remplacement que dans la partie Vente si les ventes sont brouillons
                sale_search = [('state', '=', 'draft')]
                invoice_search = [('id', '=', False)]
            
            if wiz.is_propagate or wiz.is_propagate_draft:
                #Remplacement dans la partie Vente
                sale_rcs = sale_obj.search(sale_search)
                del_sale_ids = []
                if sale_rcs:
                    for sale in sale_rcs:
                        for invoice_line in sale.invoice_line_ids:
                            if invoice_line.state not in ('draft', 'cancel'):
                                del_sale_ids.append(sale.id)
                                break
                    
                    if del_sale_ids:
                        sale_ids = list(set(sale_rcs.ids)-set(del_sale_ids))
                    else:
                        sale_ids = sale_rcs.ids
                    
                    if sale_ids:
                        sale_agent_rcs = comm_sale_obj.search([('agent_id', '=', wiz.agent_id.id), ('sale_order_id', 'in', sale_ids)])
                        if sale_agent_rcs:
                            sale_agent_rcs.write(vals)
                
                #Remplacement dans la partie Facturation    
                invoice_rcs = invoice_obj.search(invoice_search)
                if invoice_rcs:
                    invoice_line_rcs = invoice_line_obj.search([('account_invoice_line_id', 'in', invoice_rcs.ids)])
                    if invoice_line_rcs:
                        invoice_line_agent_rcs = comm_invoice_line_obj.search([('agent_id', '=', wiz.agent_id.id), ('account_invoice_line_id', 'in', invoice_line_rcs)])
                        if invoice_line_agent_rcs:
                            invoice_line_agent_rcs.write(vals)
                                    
        return {'type': 'ir.actions.act_window_close'}
    
