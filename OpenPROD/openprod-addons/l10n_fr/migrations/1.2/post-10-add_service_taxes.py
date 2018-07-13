# -*- coding: utf-8 -*-
from openerp import pooler
__name__ = "Add service taxes and allow reconciliation on account"

def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    # Taxes
    tax_tmpl_obj = pooler.get_pool(cr.dbname)['account.tax.template']
    tax_tmpl_obj.update_taxes(cr, 1, tax_tmpl_obj.search(cr, 1, [('chart_template_id', '!=', 1)]))
    # Positions fiscales
    fp_obj = pooler.get_pool(cr.dbname)['account.fiscal.position.template']
    fp_obj.update_fp(cr, 1, fp_obj.search(cr, 1, []))
    # Comptes
    cr.execute('''
    UPDATE
      account_account_template
    SET 
      reconcile = true
    WHERE
      code like '445%'
    ''')
    cr.execute('''
    UPDATE
      account_account
    SET 
      reconcile = true
    WHERE
      code like '445%'
    ''')
    