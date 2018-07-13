# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    
    @api.one
    def _get_supplier_account_position_id(self):
        """
            Fonction qui retourne la position fiscale selon la société
        """
        mcpfpp_rcs = self.env['multi.company.partner.fiscal.position.purchase'].search([('partner_id', '=', self.id), 
                                                                                        ('company_id', '=', self.env.user.company_id.id)], limit=1)
        if mcpfpp_rcs:
            self.supplier_account_position_id = mcpfpp_rcs.account_position_id.id
        else:
            self.supplier_account_position_id = False
                
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mcpap_ids = fields.One2many('multi.company.partner.acc.payable', 'partner_id',  string='Account payable')
    mcpar_ids = fields.One2many('multi.company.partner.acc.receivable', 'partner_id',  string='Account receivable')
    mcpfps_ids = fields.One2many('multi.company.partner.fiscal.position.sale', 'partner_id',  string='Fiscal position')
    mcpfpp_ids = fields.One2many('multi.company.partner.fiscal.position.purchase', 'partner_id',  string='Fiscal position')
    supplier_account_position_id = fields.Many2one('account.fiscal.position', string='Fiscal position', compute='_get_supplier_account_position_id', 
                                                   help="The fiscal position will determine taxes"
                                                   " and accounts used for the partner.")
    
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
                
        res = super(res_partner, self).write(vals=vals)
        mcpap_obj = self.env['multi.company.partner.acc.payable']
        mcpar_obj = self.env['multi.company.partner.acc.receivable']
        mcpfps_obj = self.env['multi.company.partner.fiscal.position.sale']
        mcpfpp_obj = self.env['multi.company.partner.fiscal.position.purchase']
        company = self.env.user.company_id
        for partner in self:
            if partner.state == 'qualified':
                if partner.is_supplier:
                    mcpap_rcs = mcpap_obj.search([('partner_id', '=', partner.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpap_rcs:
                        raise except_orm(_('Error'), _("You need an supplier account for this company '%s' in this partner '%s'."%(company.name, partner.reference)))
                    
                    mcpfpp_rcs = mcpfpp_obj.search([('partner_id', '=', partner.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpfpp_rcs:
                        raise except_orm(_('Error'), _("You need an supplier fiscal position for this company '%s' in this partner '%s'."%(company.name, partner.reference)))
                
                if partner.is_customer:
                    mcpar_rcs = mcpar_obj.search([('partner_id', '=', partner.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpar_rcs:
                        raise except_orm(_('Error'), _("You need an customer account for this company '%s' in this partner '%s'."%(company.name, partner.reference)))
                    
                    mcpfps_rcs = mcpfps_obj.search([('partner_id', '=', partner.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpfps_rcs:
                        raise except_orm(_('Error'), _("You need an customer fiscal position for this company '%s' in this partner '%s'."%(company.name, partner.reference)))
        
        return res


    
class multi_company_partner_acc_payable(models.Model):
    """ 
    Multi company partner account payable 
    """
    _name = 'multi.company.partner.acc.payable'
    _description = 'Multi company partner account payable'
    _rec_name = 'account_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_id = fields.Many2one('account.account', string='Account payable', required=True, ondelete='restrict',
                                 help="This account will be used instead of the default one as the payable account for the current partner")
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')



class multi_company_partner_acc_receivable(models.Model):
    """ 
    Multi company partner account receivable 
    """
    _name = 'multi.company.partner.acc.receivable'
    _description = 'Multi company partner account receivable'
    _rec_name = 'account_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_id = fields.Many2one('account.account', string='Account receivable', required=True, ondelete='restrict', 
                                 help="This account will be used instead of the default one as the receivable account for the current partner")
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')



class multi_company_partner_fiscal_position_sale(models.Model):
    """ 
    Multi company partner fiscal position sale
    """
    _name = 'multi.company.partner.fiscal.position.sale'
    _description = 'Multi company partner fiscal position sale'
    _rec_name = 'account_position_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_position_id = fields.Many2one('account.fiscal.position', string='Fiscal position', required=False, 
                                                   ondelete='restrict', help="The fiscal position will determine taxes"
                                                   " and accounts used for the partner.")
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')       
        


class multi_company_partner_fiscal_position_purchase(models.Model):
    """ 
    Multi company partner fiscal position purchase
    """
    _name = 'multi.company.partner.fiscal.position.purchase'
    _description = 'Multi company partner fiscal position purchase'
    _rec_name = 'account_position_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_position_id = fields.Many2one('account.fiscal.position', string='Fiscal position', required=False, 
                                                   ondelete='restrict', help="The fiscal position will determine taxes"
                                                   " and accounts used for the partner.")
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')  
