# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.modules.registry import Registry 
import threading
import subprocess
import logging
from openerp import http
_logger = logging.getLogger(__name__)

class BIServer(models.Model):
    _name = 'bi.server'

    name = fields.Char()
    db_name = fields.Char()
    base_location = fields.Char()
    pentaho_server_address = fields.Char()
    bi_instalation_dir = fields.Char()

    def lancerThread(self, dir , db_name, my_env) :
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            bi_server = self.env['bi.server']
            if not dir or not db_name:
                _logger.error("Error when updating DB for the BI module : Invalid path for Pentaho instalation directory, fix it in BI -> Configuration")
                bi_server.send_email('BI Error path')
                new_cr.close()
                return
            er = subprocess.call(dir + "updateBDD.sh " + db_name + " " + dir, shell=True)
            if er == 1 :
                _logger.error("Error when updating DB for the BI module :bash script error")
                bi_server.send_email('BI Error bash')
            elif er == 4 :
                _logger.error("Error when updating DB for the BI module : no configuration file")
                bi_server.send_email('BI Error config')
            elif er == 2 :
                _logger.error("Error when updating DB for the BI module : Java-8-oracle needs to be instaled")
                bi_server.send_email('BI Error java')
            elif er == 3 :
                _logger.error("Error when updating DB for the BI module : Error during the data transformation see 'etl.log' for more details")
                bi_server.send_email('BI Error etl')
            elif er == 0 :
                _logger.info("successfully updated the BI database")
            elif er == 127 :
                _logger.error("Error when updating DB for the BI module : Invalid path for Pentaho instalation directory, fix it in BI -> Configuration")
                bi_server.send_email('BI Error path')
            new_cr.close()
            return 


    def send_email(self, title):
        template_ids = self.env['mail.template'].sudo().search([('name','=',title)], limit = 1) 
        admin = self.env['res.users'].sudo().search([('login','=','admin')], limit = 1) 
        template_ids.write({'email_to':admin.email})
        template_ids.write({'email_from':admin.email})
        temp = self.env['mail.template'].sudo().browse([template_ids[0].id])
        temp.send_mail(template_ids[0].id, force_send=True)
        return True


    def update_bi(self):
        pentaho_server = self.env['bi.server'].sudo().search([('id','=',1)])
        dir = pentaho_server.bi_instalation_dir
        db_name = pentaho_server.db_name
        my_env = self.env
        thread_maj = threading.Thread(target=self.lancerThread, args=(dir,db_name , my_env))
        thread_maj.start()
        return

class BIRoles(models.Model):
    _name = 'bi.roles'

    name = fields.Char()

