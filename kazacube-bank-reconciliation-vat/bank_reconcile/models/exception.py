# -*- encoding: utf-8 -*-
from openerp import models, fields,  api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime
import time
class report_exception(models.Model):
    _name = 'report.exception'

    _order ="date desc"

    date=fields.Datetime(string="Date")
    title=fields.Char(string="Titre", required=False)
    code=fields.Char(string="Code", required=False)
    message=fields.Char(string="Message", required=False)
    type=fields.Selection([('load','Extraction'),('cron','Cron Facture'),('exchange_jp2','Echange JP2'),('etebac','ETEBAC3')],required=False,string="Type")

    @api.multi
    def set_exception(self,code=False,output=False,type='cron',title='Erreur de configuration'):
        now=datetime.now()
        today=time.strftime("%d-%m-%Y")
        code=code+"_"+str(today)
        if not self.search([('code','=',code)]) :
            vals={
                                'date':now,
                                'code':code,
                                'title':title,
                                'type':type,
                                'message':output
                            }
            self.create(vals)
        return True


report_exception()