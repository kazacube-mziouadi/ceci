# -*- coding: utf-8 -*-
__name__ = "Update accounts for reports"

def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""UPDATE account_account account set debit_account_type_id=(
                  SELECT debit_account_type_id 
                  FROM account_account_template tpl 
                  WHERE (tpl.code=account.code or account.code like tpl.code || '00' or account.code like tpl.code || '000' or account.code like tpl.code || '0') 
                  AND tpl.name=account.name)
                """)
    cr.execute("""UPDATE account_account account set credit_account_type_id=(
                  SELECT credit_account_type_id 
                  FROM account_account_template tpl 
                  WHERE (tpl.code=account.code or account.code like tpl.code || '00' or account.code like tpl.code || '000' or account.code like tpl.code || '0') 
                  AND tpl.name=account.name)
                """)
    cr.execute("""UPDATE account_account account set close_method=(CASE WHEN(
                  SELECT close_method 
                  FROM account_account_template tpl 
                  WHERE (tpl.code=account.code or account.code like tpl.code || '00' or account.code like tpl.code || '000' or account.code like tpl.code || '0') 
                  AND tpl.name=account.name) is null THEN 'none' ELSE (SELECT close_method 
                  FROM account_account_template tpl 
                  WHERE (tpl.code=account.code or account.code like tpl.code || '00' or account.code like tpl.code || '000' or account.code like tpl.code || '0') 
                  AND tpl.name=account.name) END)
                """)
    