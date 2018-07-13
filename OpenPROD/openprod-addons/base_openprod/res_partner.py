# -*- coding: utf-8 -*-
from openerp import models, api, fields, _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    def _auto_init(self, cursor, context=None):
        """
            On rempli les champs de pays et de langue du partenaire
            dès le module openprod car ils deviennent requis dans le module 
            partner_openprod
        """
        res = super(res_partner, self)._auto_init(cursor, context=context)
        #Association du pays à ceux qui n'en ont pas
        cursor.execute('SELECT id FROM res_partner WHERE country_id IS NULL')
        for partner_id in cursor.fetchall():
            query = "UPDATE res_partner partner SET country_id=(SELECT id FROM res_country WHERE code='FR') WHERE id=%s"%(partner_id)
            cursor.execute(query)
        #Association de la langue à ceux qui n'en ont pas
        cursor.execute('SELECT id FROM res_partner WHERE lang IS NULL')
        for partner_id in cursor.fetchall():
            query = "UPDATE res_partner partner SET lang='fr_FR' WHERE id=%s"%(partner_id)
            cursor.execute(query)
        
        return res
    
    
