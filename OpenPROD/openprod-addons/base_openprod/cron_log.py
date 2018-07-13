# -*- coding: utf-8 -*-
from openerp import models, fields, api, SUPERUSER_ID, exceptions
from psycopg2 import OperationalError
import logging, openerp, traceback, sys
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import pytz
import time


_logger = logging.getLogger(__name__)

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


def convert_tz(date, t_from, t_to):
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    tz = pytz.timezone(t_from)
    date_user = tz.localize(date)
    tz1 = pytz.timezone(t_to)
    date_final = date_user.astimezone(tz1)
    date_final = datetime.strftime(date_final, '%Y-%m-%d %H:%M:%S')
    return date_final


class ir_cron(models.Model):
    _inherit = 'ir.cron'
   
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_more_details = fields.Boolean(string='More details', default=False)
    is_last_month = fields.Boolean(string='Last day month', default=False)
    last_month = fields.Integer(string='Nb before/after last day month', default=0, required=False, 
                                help="Business Day Month End is selected, you can enter a number of shift days:  0: Last business day of the month, -1: Before last business day of the month, 1: First business day after the end of the month")
    monday = fields.Boolean(string='All monday', default=False)
    tuesday = fields.Boolean(string='All tuesday', default=False)
    wednesday = fields.Boolean(string='All wednesday', default=False)
    thursday = fields.Boolean(string='All thursday', default=False)
    friday = fields.Boolean(string='All friday', default=False)
    saturday = fields.Boolean(string='All saturday', default=False)
    sunday = fields.Boolean(string='All sunday', default=False)
    
    
    #===========================================================================
    # FUNCTIONS
    #===========================================================================
    def last_day(self, job_cr, year_month, last_month, nextcall, today_bis, calendar=None):
        """
            Ajouter un mode de calcul "Fin de mois jour ouvré"
            Si "Fin de mois jour ouvré est coché, avoir la possibilité de saisir un nombre de jour de décalage :
                 0 : Dernier jour ouvré du mois
                -1 : Avant dernier jour ouvré du mois
                 1 : Premier jour ouvré après la fin du mois
        """
        next_year_month = '%s-01 00:00:00'%(today_bis.strftime("%Y-%m"))
        next_year_month_01 = '%s-01 00:00:00'%(year_month)
        nextcall = '%s-01 %s'%(year_month, nextcall.strftime('%H:%M:%S'))
        if calendar:
            calendar_id = calendar[0] 
            calendar_line_obj = calendar[1]  
            calendar_obj = calendar[2] 
        else:
            calendar_id = False
            calendar_line_obj = False
            calendar_obj = False
        
        if calendar_id:
            last_line_ids = calendar_line_obj.search(job_cr, 1, [('start_date_related', '>=', next_year_month), 
                                                     ('start_date_related', '<', next_year_month_01), 
                                                     ('calendar_id', '=', calendar_id)
                                                    ], order="start_date_related desc", limit=1)

            calendar = calendar_obj.browse(job_cr, 1, calendar_id)
            if last_line_ids:
                last_line = calendar_line_obj.browse(job_cr, 1, last_line_ids[0])
                if last_month > 1:
                    nextcall = calendar.get_date(last_line.start_date_related, last_month, hours=True)
                elif last_month < 0:
                    last_month_pos = last_month*-1
                    nextcall = calendar.get_date_inverse(last_line.end_date_related, last_month_pos, hours=True)
    
        else:
            if last_month > 1:
                nextcall = (datetime.strptime(nextcall, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=last_month)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            elif last_month < 0:
                last_month_pos = last_month*-1
                nextcall = (datetime.strptime(nextcall, DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(days=last_month_pos)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        return nextcall
    
    
    def get_nextcall_calendar(self, job_cr, job):
        return None
    
    
    def compute_nextcall_more_details(self, job_cr, job, nextcall):
        nextcall += relativedelta(days=1)
        tz = pytz.timezone(nextcall.tzinfo.zone)
        day = time.strftime('%d')
        month = time.strftime('%m')
        year = time.strftime('%Y')
        today_bis = datetime.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d')
        list_day = []
        if job['monday']:
            list_day.append(1)
            
        if job['tuesday']:
            list_day.append(2)
            
        if job['wednesday']:
            list_day.append(3)
            
        if job['thursday']:
            list_day.append(4)
            
        if job['friday']:
            list_day.append(5)
            
        if job['saturday']:
            list_day.append(6)
            
        if job['sunday']:
            list_day.append(7)
        
        #Si case fin du mois coché  
        next_last_date = False
        next_time_day = False
        if job['is_last_month'] and job['last_month']:    
            next_year = year
            if month == '12':
                next_month = '01'
                next_year = str(int(year) +1)
            else:
                next_month = str(int(month) +1)
                if len(next_month) != 2: 
                    next_month = '0%s'%(next_month)
                
            year_month_next = '%s-%s'%(next_year,next_month)
            calendar = self.get_nextcall_calendar(job_cr, job)
            next_last_date = self.last_day(job_cr, year_month_next, job['last_month'], nextcall, today_bis, calendar=calendar) 
        elif list_day:
            next_day = False
            for list in list_day:
                if list > day:
                    next_day = list
                    break
            if not next_day: 
                next_day = list_day[0]   
                
            j_more_1 = 0
            for i in range(10):
                j_more_1 += 1
                next_date_strp = (today_bis + relativedelta(days = j_more_1))
                next_date_iso_day = next_date_strp.isocalendar()[2]
                if next_date_iso_day == next_day:
                    next_time_day = next_date_strp.strftime('%Y-%m-%d')
                    next_time_day = '%s %s'%(next_time_day, nextcall.strftime('%H:%M:%S'))
                    break
        
        #Calcule de la date suivante
        if next_time_day or next_last_date:
            if next_time_day and not next_last_date:
                nextcall = tz.localize(datetime.strptime(next_time_day, DEFAULT_SERVER_DATETIME_FORMAT))
            elif next_last_date and not next_time_day:
                nextcall = tz.localize(datetime.strptime(next_last_date, DEFAULT_SERVER_DATETIME_FORMAT))
            elif next_last_date and next_time_day:   
                if next_last_date > next_time_day:
                    nextcall = tz.localize(datetime.strptime(next_time_day, DEFAULT_SERVER_DATETIME_FORMAT))
                else:
                    nextcall = tz.localize(datetime.strptime(next_last_date, DEFAULT_SERVER_DATETIME_FORMAT))
        
        return nextcall
    
    
    def compute_nextcall(self, job_cr, job, nextcall):
        if not job['is_more_details']:
            nextcall += _intervalTypes[job['interval_type']](job['interval_number'])
        else:
            nextcall = self.compute_nextcall_more_details(job_cr, job, nextcall)
    
        return nextcall
    
    
    @api.one
    def run_manually(self):
        """Run a job from the cron form view."""

        if self.env.uid != SUPERUSER_ID and (not self.active or not self.numbercall):
            raise exceptions.AccessError(_('Only the admin user is allowed to execute inactive cron jobs manually'))

        try:
            # Try to grab an exclusive lock on the job row
            # until the end of the transaction
            self.env.cr.execute(
                """SELECT *
                   FROM ir_cron
                   WHERE id=%s
                   FOR UPDATE NOWAIT""",
                (self.id,), log_exceptions=False)

        except OperationalError as e:
            # User friendly error if the lock could not be claimed
            if getattr(e, "pgcode", None) == '55P03':
                raise exceptions.Warning(
                    _('Another process/thread is already busy executing this job'))

            raise

        _logger.info('Job `%s` triggered from form', self.name)

        # Do not propagate active_test to the method to execute
        ctx = dict(self.env.context)
        ctx.pop('active_test', None)

        # Execute the cron job
        method = getattr(
            self.with_context(ctx).sudo(self.user_id).env[self.model],
            self.function)
        args = safe_eval('tuple(%s)' % (self.args or ''))
        log = self.env['ir.cron.log'].start(self.name)
        try:
            ret = method(*args)
            openerp.modules.registry.RegistryManager.signal_caches_change(self.env.cr.dbname)
        except Exception as e:
            log.stop(error=traceback.format_exc())
            self.env.cr.commit()
            raise e
        log.stop()
        return ret

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_exception):
        raise
    
    @api.model
    def _callback(self, model_name, method_name, args, job_id):
        name = self.browse(job_id).name
        error = []
        log = self.env['ir.cron.log'].start(name)
        try:
            super(ir_cron, self)._callback(model_name, method_name, args, job_id)
        except Exception:
            error = traceback.format_exc()
        log.stop(error=error)
        
    @api.model
    def truc(self):
        a = 1 / 0
    
class ir_cron_log(models.Model):
    """ 
    Cron history 
    """
    _name = 'ir.cron.log'
    _description = 'Cron log'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    start_date = fields.Datetime()
    end_date = fields.Datetime()
    error = fields.Char()
    
    
    def start(self, cron_name):
        with openerp.api.Environment.manage():
            with openerp.registry(self.env.cr.dbname).cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                return self.with_env(new_env).create({
                     'name': cron_name,
                     'start_date': fields.Datetime.now()
                         })
        

    def stop(self, error=None):
        
        vals = {
                     'end_date': fields.Datetime.now()
                         }
        if error:
            error = "".join(error)
            vals['error'] = error
        with openerp.api.Environment.manage():
            with openerp.registry(self.env.cr.dbname).cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                return self.with_env(new_env).write(vals)
    
    