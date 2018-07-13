# -*- coding: utf-8 -*-

{
    'name' : 'Online Billing',
    'version' : '1.1',
    'author' : 'Objectif-PI OpenERP SA',
    'license': 'LGPL',
    'summary': 'Send Invoices and Track Payments',
    'description': """
Invoicing & Payments by Accounting Voucher & Receipts
=====================================================
The specific and easy-to-use Invoicing system in OpenERP allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your suppliers and customers. 

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. 

The Invoicing system includes receipts and vouchers (an easy way to keep track of sales and purchases). It also offers you an easy method of registering payments, without having to encode complete abstracts of account.

This module manages:

* Voucher Entry
* Voucher Receipt [Sales & Purchase]
* Voucher Payment [Customer & Supplier]
    """,
    'category': 'Accounting & Finance',
    'sequence': 4,
    'website' : 'https://www.odoo.com/page/billing',
    'depends' : ['account'],
    'demo' : [],
    'data' : [
        'data/bank_statement_openprod_report_data_workflow.xml',
        'security/ir.model.access.csv',
        'account_voucher_sequence.xml',
        'account_voucher_workflow.xml',
        'account_voucher_view.xml',
        'voucher_payment_receipt_view.xml',
        'voucher_sales_purchase_view.xml',
        'account_voucher_wizard.xml',
        'account_voucher_pay_invoice.xml',
        'report/account_voucher_sales_receipt_view.xml',
        'security/account_voucher_security.xml',
        'account_bank_view.xml',
    ],
    'test' : [
        'test/account_voucher_users.yml',
        'test/case5_suppl_usd_usd.yml',
        'test/account_voucher.yml',
        'test/sales_receipt.yml',
        'test/sales_payment.yml',
        'test/case1_usd_usd.yml',
        'test/case1_usd_usd_payment_rate.yml',
        'test/case2_usd_eur_debtor_in_eur.yml',
        'test/case2_usd_eur_debtor_in_usd.yml',
        'test/case3_eur_eur.yml',
        'test/case4_cad_chf.yml',
        'test/case_eur_usd.yml',
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
