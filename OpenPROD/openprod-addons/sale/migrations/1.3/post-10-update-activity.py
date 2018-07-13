# -*- coding: utf-8 -*-
from openerp import pooler

__name__ = "Migration pour les modifications sur les methodes de facturations et paiements"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""ALTER TABLE res_partner DROP CONSTRAINT IF EXISTS res_partner_check_sale_qualified_partner""")
    # Suppression des transitions de la génération manuelle de facture
    cr.execute("""DELETE FROM 
                    wkf_transition 
                  WHERE 
                    sequence in (700, 620, 600, 710, 580, 570, 560, 550, 540, 530, 520, 510, 500, 490, 480, 470, 460, 450, 340) AND
                    (act_from IN (SELECT id from wkf_activity WHERE wkf_id IN (SELECT id FROM wkf WHERE osv='sale.order')) OR 
                     act_to IN (SELECT id from wkf_activity WHERE wkf_id IN (SELECT id FROM wkf WHERE osv='sale.order')))""") 
    
    
    
    cr.execute("""
        SELECT 
          count(s.id) AS c, 
          s.sale_invoicing_trigger, 
          s.sale_invoiced_on,
          p.payment_type
        FROM 
          res_partner s
          JOIN account_payment_term p ON p.id = s.property_payment_term_id
        WHERE 
          is_company 
        GROUP BY 
          s.sale_invoicing_trigger, 
          s.sale_invoiced_on,
          p.payment_type
        ORDER BY 
          c DESC;""")
    
    res = cr.dictfetchall()
    possibilities = []
    for res_item in res:
        if res_item['sale_invoicing_trigger'] and res_item['sale_invoiced_on'] and res_item['payment_type']:
            sale_fields = (res_item['sale_invoicing_trigger'], res_item['sale_invoiced_on'], res_item['payment_type'])
            if sale_fields not in possibilities:
                possibilities.append(sale_fields)
    
    db_pooler = pooler.get_pool(cr.dbname)
    invoicing_method_obj = db_pooler['account.invoicing.method']
    for possibility in possibilities:
        name = '%s invoicing on %s quantities'%(possibility[0].capitalize(), possibility[1] == 'order' and 'ordered' or 'delivered')
        if possibility[2] != 'after_invoicing':
            name = '%s (%s)'%(name, possibility[2].replace('_', ' '))
            payment_line_ids = [(0, 0, {'payment_type': possibility[2],
                                        'value': 'procent',
                                        'value_amount': 1,
                                        'is_blocking': True})]
        else:
            payment_line_ids = []
            
        invoicing_method_ids = invoicing_method_obj.search(cr, 1, [('name', '=', name)])
        if invoicing_method_ids:
            invoicing_method_id = invoicing_method_ids[0]
        else:
            invoicing_method_id = invoicing_method_obj.create(cr, 1, {
                                                                  'name': name,
                                                                  'payment_line_ids': payment_line_ids,
                                                                  'line_ids': [(0, 0, {'invoice_trigger': possibility[0],
                                                                                       'account_invoiced_on': possibility[1] or 'delivery'})]
                                                                  })
            
        cr.execute("""
            UPDATE
              res_partner c
            SET
              sale_invoicing_method_id = %s
            FROM
              account_payment_term p
            WHERE
              p.id = c.property_payment_term_id AND
              c.sale_invoicing_trigger = '%s' AND
              c.sale_invoiced_on = '%s' AND
              p.payment_type = '%s'
        """%(invoicing_method_id, possibility[0], possibility[1], possibility[2]))
        
        cr.execute("""
            UPDATE
              sale_order
            SET
              invoicing_method_id = %s
            WHERE
              invoiced_customer_id IN (
                SELECT
                  c.id
                FROM
                  res_partner c,
                  account_payment_term p
                WHERE
                  p.id = c.property_payment_term_id AND
                  c.sale_invoicing_trigger = '%s' AND
                  c.sale_invoiced_on = '%s' AND
                  p.payment_type = '%s')
        """%(invoicing_method_id, possibility[0], possibility[1], possibility[2]))