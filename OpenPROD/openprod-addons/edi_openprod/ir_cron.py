# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import time
import openerp



class ir_cron(models.Model):
    """ 
    Ir cron 
    """
    _inherit = 'ir.cron'
    _description = 'Ir cron'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    edi_get_file_ids = fields.Many2many('edi.transformation.get.file', 'cron_edi_get_file_rel', 'cron_id', 'get_file_id', string='EDI get file')
    edi_processing_ids = fields.Many2many('edi.transformation.processing', 'cron_edi_processing_rel', 'cron_id', 'processing_id', string='EDI processing')

    
    #===========================================================================
    # Functions
    #===========================================================================
    def do_sleep(self):
        print 'START DO_SLEEP'
        self.env.cr.commit()
        time.sleep(60)
        print 'END DO_SLEEP'
        return True

    
    @api.model
    def _callback(self, model_name, method_name, args, job_id):
        res = super(ir_cron, self)._callback(model_name, method_name, args, job_id)
        if isinstance(res, tuple):
            history = res[-1]
            res = res[0]
        else:
            history = False
            
        if job_id:
            if history:
                history.log = '%s\n START Processing: %s'%(history.log or '', fields.Datetime.now())
                history.write({'log': history.log})
            
            with openerp.api.Environment.manage():
                with openerp.registry(self.env.cr.dbname).cursor() as cr_edi:
                    new_env = api.Environment(cr_edi, self.env.uid, self.env.context)
                    job = self.with_env(new_env).browse(job_id)
                    for edi_processing in job.edi_processing_ids:
                        if not edi_processing.in_progress:
                            edi_processing.run_all()
                            
                    if history:
                        history.log = '%s\n END Processing: %s'%(history.log or '', fields.Datetime.now())
                        history.log = '%s\n START Get file: %s'%(history.log or '', fields.Datetime.now())
                        history.write({'log': history.log, 'end_date': fields.Datetime.now()})
                    for edi_get_file in job.edi_get_file_ids:
                        if edi_get_file.is_active and not edi_get_file.in_progress:
                            edi_get_file.execute()
                            
                    if history:
                        history.log = '%s\n END Get file: %s'%(history.log or '', fields.Datetime.now())
                        history.write({'log': history.log, 'end_date': fields.Datetime.now()})
                    
                    cr_edi.commit()
            
        return res, history