from openerp import models, fields, api, _


class product_product(models.Model):
    _inherit = "product.product"

    # Compte comptable
    property_account_income_id = fields.Many2one('account.account', domain=[('type', '!=', 'view')],
                                                 string='Income Account', ondelete='restrict',
                                                 help="This account will be used for invoices instead "
                                                      "of the default one to value sales for the current product.")
    property_account_expense_id = fields.Many2one('account.account', domain=[('type', '!=', 'view')],
                                                  string='Expense Account', ondelete='restrict',
                                                  help="This account will be used for invoices instead "
                                                       "of the default one to value expenses for the current product.")
