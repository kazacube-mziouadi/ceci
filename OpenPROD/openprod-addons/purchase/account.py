# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class account_purchase_tax(models.Model):
    _name = "account.purchase.tax"
    _description = "Purchase Tax"
    _order = 'sequence'

    purchase_id = fields.Many2one('purchase.order', string='Purchase', ondelete='cascade', select=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('parent_id', '=', False)])
    account_id = fields.Many2one('account.account', string='Tax Account', required=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='purchase_id.currency_id', store=True, readonly=True)



class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='restrict', select=True,
                              help="The linked purchase in case of automatic payment")
    
    @api.model
    def proforma_voucher(self):
        """
            Surcharge pour prendre en compte la libération de l'achat et des pickings en cas de validation
            du paiement
        """
        res = super(account_voucher, self).proforma_voucher()
        purchase_rs = self.purchase_id
        if purchase_rs:
            purchase_rs.write({'check_paid': True})
            purchase_rs.picking_ids.write({'payment_lock': False})
                
        return res
    
    
    @api.multi
    def recompute_voucher_lines(self, partner_ids, journal_id, price, currency_id, ttype, date):
        """
            Surcharge pour prendre en compte les partenaires facturés du partenaire payeur
        """
        partner_type_obj = self.env['res.partner.purchase.type']
        search_partner_ids = []
        new_partner_ids = []
        if not isinstance(partner_ids, list):
            partner_ids = [partner_ids]
        
        for partner_id in partner_ids:
            new_partner_ids.append(partner_id)
            #On recherche les partenaires qui ont ce partenaire comme 'payé à"
            partners_types = partner_type_obj.search([('partner_type', '=', 'paid_to'), ('partner_type_id', '=', partner_id)])
            #On récupère automatiquement tous les partenaires qui sont factureur
            #Et on crée une liste pour récupérer les ids de tous les partenaires trouvés afin de rechercher leur factureurs 
            for part_type in partners_types:
                search_partner_ids.append(part_type.partner_id.id)
                if part_type.partner_id.invoiced_by:
                    new_partner_ids.append(part_type.partner_id.id)
            
            invoiced_partners_types = partner_type_obj.search([('partner_type', '=', 'invoiced_by'), ('partner_id', 'in', search_partner_ids)])
            invoiced_partners_ids = [invoiced_partner.partner_type_id.id for invoiced_partner in invoiced_partners_types if invoiced_partner.partner_type_id]
            if invoiced_partners_ids:
                new_partner_ids.extend(invoiced_partners_ids)
        
        if new_partner_ids:
            new_partner_ids = list(set(new_partner_ids))
            
        return super(account_voucher, self).recompute_voucher_lines(partner_ids=new_partner_ids, journal_id=journal_id, price=price,
                                                                     currency_id=currency_id, ttype=ttype, date=date)



class account_move_reconcile(models.Model):
    _inherit = "account.move.reconcile"
    
    
    def find_supp_partners(self, partner_id):
        """
            Fonction qui permet de gérer les payeurs et facturés des fournisseurs
            :type self: account.move.reconcile
            :param partner_id: id du partenaire facturé
            :type partner_id: integer
            :return: Liste d'ids de partenaires payeurs
            :rtype: list
        """
        supp_partner_link_obj = self.env['res.partner.purchase.type']
        super(account_move_reconcile, self).find_supp_partners(partner_id=partner_id)
        #On recherche tous les partenaires 'payé à' de ce partenaire
        supp_paid_by_rs = supp_partner_link_obj.search([('partner_type', '=', 'paid_to'), ('partner_id', '=', partner_id)], order='partner_type_id asc')
        #Et tous les partenaires 'payé à' du partenaire dont il est factureur
        link_line = supp_partner_link_obj.search([('partner_type', '=', 'invoiced_by'), ('partner_type_id', '=', partner_id)])
        if link_line:
            supp_paid_by_rs += supp_partner_link_obj.search([('partner_type', '=', 'paid_to'), ('partner_id', '=', link_line.partner_id.id)], 
                                                            order='partner_type_id asc')
        
        paid_by_ids = [paid_rs.partner_type_id.id for paid_rs in supp_paid_by_rs]
        paid_by_ids = list(set(paid_by_ids))
        return paid_by_ids