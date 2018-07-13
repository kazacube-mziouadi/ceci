# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp import pooler
import time

class ir_cron(osv.osv):
    _inherit = 'ir.cron'
    _columns = {
        'base_synchro_ids': fields.many2many('db.synchro.synchro', 'synchro_cron_rel', 'cron_id', 'synchro_id', 'DB Synchro'),
                }
    
    def _callback(self, cr, uid, model_name, method_name, args, job_id):
        res = super(ir_cron, self)._callback(cr, uid, model_name, method_name, args, job_id)
        if isinstance(res, tuple):
            history = res[-1]
            res = res[0]
        else:
            history = False
        
        if history:
            history.log = '%s\n START Synchronizations: %s'%(history.log or '', time.strftime('%Y-%m-%d %H:%M:%S'))
            history.write({'log': history.log})
        
        if job_id:
            cr_synchro = pooler.get_db(cr.dbname).cursor()
            job = self.browse(cr_synchro, uid, job_id)
            for base_synchro in job.base_synchro_ids:
                base_synchro.start_synchro_button()
            
            cr_synchro.commit()
            cr_synchro.close()
            
        if history:
            history.log = '%s\n END Synchronizations: %s'%(history.log or '', time.strftime('%Y-%m-%d %H:%M:%S'))
            history.write({'log': history.log, 'end_date': time.strftime('%Y-%m-%d %H:%M:%S')})

        return res, history