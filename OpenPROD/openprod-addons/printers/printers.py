# -*- coding: utf-8 -*-


from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp import report
from openerp.exceptions import except_orm


from common import JOB_STATE_REASONS
from common import JOB_STATES
from common import PRINTER_STATES

from openerp.modules import get_module_path
from datetime import datetime
from tempfile import mkstemp
import unicodedata
import logging
import os
import cups

from reportlab.pdfgen import canvas
import time
import pdb
from pdb import Pdb

logger = logging.getLogger('printers')


def convert(name):
    """Convert data with no accent and upper mode"""
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').replace('&', '').replace('_', '')


class printers_server(models.Model):

    """
    Manages printing servers
    """
    _name = 'printers.server'
    _description = 'List of printing servers'
    _order = 'server'
    _rec_name = 'server'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    server = fields.Char(string='Server', size=64, required=True, help="Name of the server")
    address = fields.Char(string='Address', size=15, required=True, default="127.0.0.1", help="IP address or hostname of the server")
    port = fields.Integer(string='Port', default=0, required=False, help="Port of the server")
    user = fields.Char(string='User', size=32, required=False, help="User to log in on the server")
    password = fields.Char(string='Password', size=32, required=False, help="Password to log in on the server")
    active = fields.Boolean(string='Active', default=True, help="If checked, this server is useable")
    printer_ids = fields.One2many('printers.list', 'server_id', string='Printer List', help="List of printers available on this server")
    custom_user = fields.Boolean(string='Custom User', default=False, help="Check this if you want to use Open-prod User Name instead of a specific user")

    def _openConnection(self):
        kwargs = {'host': self.address}
        if self.port:
            kwargs['port'] = int(self.port)
        return cups.Connection(**kwargs)

    @api.one
    def update_printers(self):
        try:
            connection = self._openConnection()
        except:
            logger.warning('Update cups printers : Failed to connect to cups server %s (%s:%s)' % (self.server, self.address, self.port))
            return False

        # Update Printers
        printers = connection.getPrinters()
        existing_printers = dict([(printer.code, printer.id) for printer in self.printer_ids])
        for name, printer_info in printers.iteritems():
            printer_values = {
                'name': printer_info['printer-info'],
                'code': name,
                'server_id': self.id,
                'uri': printer_info['printer-uri-supported'],
                'printer_state': str(printer_info['printer-state']),
                'printer_state_message': printer_info['printer-state-message'],
            }
            if name not in existing_printers.keys():
                self.env['printers.list'].create(printer_values)
            else:
                self.env['printers.list'].browse(existing_printers[name]).write(printer_values)

        return True

    @api.one
    def update_jobs(self):
        """
        This method empty all temporary values, scenario, step and reference_document
        Because if we want reset term when error we must use sql query, it is bad in production
        """
        self._update_jobs(which="all", first_job_id=-1)

        return True

    @api.model
    def _update_jobs(self, which='all', first_job_id=-1):
        job_obj = self.env['printers.job']
        printer_obj = self.env['printers.list']

        server_rs = self
        if server_rs.ids is None or not server_rs.ids:
            ids = self.search([])
        else:
            ids = server_rs
        # Update printers list, in order to ensure that jobs printers will be in OpenERP
        ids.update_printers()

        for server in ids:
            try:
                connection = server._openConnection()
            except:
                logger.warning('Update cups jobs : Failed to connect to cups server %s (%s:%s)' % (server.server, server.address, server.port))
                continue

            # Retrieve asked job data
            jobs_data = connection.getJobs(which_jobs=which, first_job_id=first_job_id, requested_attributes=[
                'job-name',
                'job-id',
                'printer-uri',
                'job-media-progress',
                'time-at-creation',
                'job-state',
                'job-state-reasons',
                'time-at-processing',
                'time-at-completed',
            ])
            # Retrieve known uncompleted jobs data to update them
            if which == 'not-completed':
                min_job_ids = job_obj.search([('job_state', 'not in', ('7', '8', '9')), ('active', '=', True)], limit=1, order='jobid')
                if min_job_ids:
                    min_job_id = min_job_ids.jobid
                    jobs_data.update(connection.getJobs(which_jobs='completed', first_job_id=min_job_id, requested_attributes=[
                        'job-name',
                        'job-id',
                        'printer-uri',
                        'job-media-progress',
                        'time-at-creation',
                        'job-state',
                        'job-state-reasons',
                        'time-at-processing',
                        'time-at-completed',
                    ]))

            all_cups_job_ids = set()
            for cups_job_id, job_data in jobs_data.items():
                all_cups_job_ids.add(cups_job_id)
                job_ids = job_obj.with_context(active_test=False).search([('jobid', '=', cups_job_id), ('server_id', '=', server.id)])
                job_values = {
                    'name': job_data.get('job-name', ''),
                    'active': True,
                    'server_id': server.id,
                    'jobid': cups_job_id,
                    'job_media_progress': job_data.get('job-media-progress', 0),
                    'time_at_creation': job_data.get('time-at-creation', ''),
                    'job_state': str(job_data.get('job-state', '')),
                    'job_state_reason': job_data.get('job-state-reasons', ''),
                    'time_at_creation': datetime.fromtimestamp(job_data.get('time-at-creation', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    'time_at_processing': job_data.get('time-at-processing', 0) and datetime.fromtimestamp(job_data.get('time-at-processing', 0)).strftime('%Y-%m-%d %H:%M:%S') 
                    or datetime.fromtimestamp(job_data.get('time-at-creation', '')).strftime('%Y-%m-%d %H:%M:%S'),
                    'time_at_completed': job_data.get('time-at-completed', 0) and datetime.fromtimestamp(job_data.get('time-at-completed', 0)).strftime('%Y-%m-%d %H:%M:%S')
                    or datetime.fromtimestamp(job_data.get('time-at-creation', '')).strftime('%Y-%m-%d %H:%M:%S'),
                }
                
                if not job_values.get('time_at_completed') and job_values.get('time_at_processing'):
                    job_values['time_at_completed'] = job_values['time_at_processing']
                    
                # Search for the printer in OpenERP
                printer_uri = job_data['printer-uri']
                printer_code = printer_uri[printer_uri.rfind('/') + 1:]
                printer_id = printer_obj.search([('server_id', '=', server.id), ('code', '=', printer_code)], limit=1)
                job_values['printer_id'] = printer_id.id

                if job_ids:
                    job_ids.write(job_values)
                else:
                    job_obj.create(job_values)
            
            # Deactive purged jobs
            if which == 'all' and first_job_id == -1:
                purged_job_ids = job_obj.search([('jobid', 'not in', list(all_cups_job_ids))])
                purged_job_ids.write({'active': False})

        return True


class printers_manufacturer(models.Model):

    """
    Manage printer per manufacturer
    """
    _name = 'printers.manufacturer'
    _description = 'Printer manufacturer'
    _order = 'name'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Name', size=32, required=True, help='Name of this manufacturer')
    code = fields.Char(string='Code', size=16, required=True, help='Code of this manufacturer')
    website = fields.Char(string='Website', size=128, required=True, help='Website address of this manufacturer')


class printers_type(models.Model):
    _inherit = 'printers.type'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    printer_ids = fields.One2many('printers.list', 'type_id', string='Printers')


class PrintersEncoding(models.Model):
    _name = 'printers.encoding'
    _description = 'Printer Encoding'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Name', size=64, required=True, help='Name of this encoding')
    code = fields.Char(string='Code', size=16, required=True, help='Encoding code')


class printers_list(models.Model):

    """
    Manage printers
    """
    _name = 'printers.list'
    _description = 'List of printers per server'
    _order = 'name'

    def _get_default_encoding(self):
        """
        Returns a default encoding (first found)
        Nothing if no encoding is in the database
        """
        encoding_rs = self.env['printers.encoding'].search([], limit=1)
        return encoding_rs.id

    @api.model
    def _printer_state_get(self):
        return PRINTER_STATES

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Printer Name', size=64, required=True, help='Printer\'s name')
    code = fields.Char(string='Printer code', size=64, required=True, help='Printer\'s code')
    server_id = fields.Many2one('printers.server', string='Server', required=True, ondelete='restrict', help='Printer server')
    type_id = fields.Many2one('printers.type', string='Type', required=False, ondelete='restrict', help='Printer type')
    active = fields.Boolean(string='Active', default=True, help='If checked, this link printer/server is active')
    manufacturer_id = fields.Many2one('printers.manufacturer', string='Manufacturer', required=False, ondelete='restrict', help='Printer\'s manufacturer')
    fitplot = fields.Boolean(string='Fitplot', default=False, help='If checked, scales the print file to fit on the page')
    uri = fields.Char(string='URI', size=256, required=True, help='URI of this printer')
    printer_state = fields.Selection('_printer_state_get', string='State', readonly=True, help='Current state of the printer')
    printer_state_message = fields.Char(string='State Message', size=256, required=False, readonly=True, help='Messages associated to the current state of the printer')
    encoding_id = fields.Many2one('printers.encoding', string='Encoding', required=True, default=_get_default_encoding, ondelete='restrict', help='Encoding used by this printer')

    def _command(self, print_type, print_data, pdf_to_merge=None):
        """
        Print a file on the selected CUPS server
        TODO : When available from pycups to print stdin data, rewrite the temp file part
        :param self: Liste des PDF à ajouter
        :type self: liste
        """

        # Retrieve printer
        printer = self

        try:
            connection = printer.server_id._openConnection()
        except:
            pass
            raise except_orm(_('Error'), _('Connection to the CUPS server failed\nCups server : %s (%s:%s)') % (printer.server_id.server, printer.server_id.address, printer.server_id.port))

        # Define printing options
        options = {}

        # Add the fitplot option
        if printer.fitplot:
            options['fitplot'] = 'fitplot'

        filename = None
        delete_file = False
        if print_type == 'report':
            # Retrieve data to generate the report
            report_obj = self.env['ir.actions.report.xml']
            report_data = report_obj.browse(print_data['report_id']).read(['model', 'report_name'])[0]

            datas = {'ids': print_data['print_ids'], 'model': report_data['model']}

            # Log the command to send
            logger.info('Object to print : %s (%s)' % (datas['model'], repr(datas['ids'][0])))
            logger.info('Report to print : %s (%s)' % (report_data['report_name'], print_data['report_id']))

            # The commit is necessary for Jasper find the data in PostgreSQL
            self.env.cr.commit()

            # Generate the file to print
            report_dict = self.env['report'].get_action(self.env[datas['model']].browse(print_data['print_ids']), report_data['report_name'])
            #On récupère les PDF en plus s'il y en a pour les passer dans le context de la méthode render_report
            context2 = self.env.context.copy()
            if pdf_to_merge:
                context2['pdf_to_merge'] = pdf_to_merge
                
            data_report = {'model': datas['model']}
            if 'data_jasper' in context2 and context2['data_jasper']:
                data_report['jasper'] = context2['data_jasper']
            
            try:
                (data, format) = report.render_report(self.env.cr, self.env.uid, print_data['print_ids'], report_data['report_name'], data_report, context=context2)
                fd, filename = mkstemp(suffix='.' + format, prefix='printers-')
                os.write(fd, data)
                os.close(fd)
                delete_file = True
            except:
                raise except_orm('Error', 'Please check the connection of your printers and their reporting')
            
        elif print_type == 'file':
            filename = print_data['filename']
        elif print_type == 'raw':
            # Define the raw option for cups
#             options['raw'] = 'raw'
            # Write the data into a file
            fd, filename = mkstemp(suffix='.', prefix='printers-raw')
            os.write(fd, print_data)
            os.close(fd)
            delete_file = True
        else:
            pass
#             raise osv.except_osv(_('Error'), _('Unknown command type, unable to print !'))

        # TODO : Rewrite using the cupsCreateJob/cupsStartDocument/cupsWriteRequestData/cupsFinishDocument functions, when available in pycups, instead of writing data into a temporary file
        jobid = False
        try:
            jobid = connection.printFile(printer.code, filename, self.env.context.get('jobname', 'Open-Prod'), options)
        except:
                raise except_orm('Error', 'Please check the connection of your printers and their reporting')
        finally:
            # Remove the file and free the memory
            if delete_file:
                os.remove(filename)

        # Operation successful, return True
        logger.info('Printers Job ID : %d' % jobid)
        printer.server_id._update_jobs(which='all', first_job_id=jobid)
        return jobid

    def send_printer(self, report_id, print_ids, pdf_to_merge=None):
        """
        Sends a report to a printer
        """
        return self._command('report', {'report_id': report_id, 'print_ids': print_ids}, pdf_to_merge=pdf_to_merge)

    def print_file(self, filename):
        """
        Sends a file to a printer
        """
        jname = self.env.context.get('jobname', False)
        if filename and not jname:
            jname = filename.split('/')[-1]
        return self.with_context(self.env.context, jobname=filename.split('/')[-1])._command('file', {'filename': filename})

    def print_raw_data(self, data):
        """
        Sends a file to a printer
        """
        return self._command('raw', data)

    @api.one
    def print_test(self):
        """
        Compose a PDF with printer information, and send it to the printer
        """
        printer = self

        filename = "/tmp/test-printer-open-Prod-%d.pdf" % printer.id

        c = canvas.Canvas(filename)
        c.drawString(100, 805, "Welcome to Open-prod printers module")
        c.drawString(100, 765, "Printer: %s" % printer.name)
        c.line(138, 760, 400, 760)
        c.drawString(100, 740, "Serveur: %s" % printer.server_id.server)
        c.line(145, 735, 400, 735)
        c.drawString(480, 805, time.strftime('%Y-%m-%d'))

        # Draw Rectangle
        c.line(20, 20, 570, 20)
        c.line(20, 820, 570, 820)
        c.line(20, 20, 20, 820)
        c.line(570, 820, 570, 20)

        # Titre en Haut
        c.line(20, 800, 570, 800)
        c.line(450, 800, 450, 820)

        # Add logo
        c.drawImage(os.path.join(get_module_path('printers'), 'static', 'src', 'img', 'logo.jpg'), 25, 730, 64, 64)
        c.save()

        # Send this file to the printer
        j_name = 'Open-prod Test Page (id: %d)' % printer.id
        printer.with_context(self.env.context, jobname=j_name).print_file(filename)

        return True

    @api.one
    def cancelAll(self, nothing=None, purge_jobs=False):
        connection = self.server_id._openConnection()
        connection.cancelAllJobs(name=self.code, purge_jobs=purge_jobs)
        self.server_id._update_jobs(which='completed')

        return True

    @api.one
    def enable(self):
        connection = self.server_id._openConnection()
        connection.enablePrinter(self.code)
        self.server_id._update_printers()

        return True

    @api.one
    def disable(self):
        connection = self.server_id._openConnection()
        connection.disablePrinter(self.code)
        self.server_id._update_printers()

        return True


class printers_label(models.Model):

    """
    Label board
    """
    _name = 'printers.label'
    _description = 'Label board'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    type_id = fields.Many2one('printers.type', string='Printer Type', required=True, ondelete='restrict', help='Type of printer')
    name = fields.Char(string='Name', size=64, required=True, help='Name of the label')
    width = fields.Integer(string='Width', default=0, required=False, help='Width of the label, in millimeters')
    height = fields.Integer(string='Height', default=0, required=False, help='Height of the label, in millimeters')


class printers_language(models.Model):

    """
    Language support per printer
    """
    _name = 'printers.language'
    _description = 'Printer language'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Name', size=32, required=True, translate=True, help='Name of the language')
    code = fields.Char(string='Code', size=16, required=True, help='Code of the language')


class printers_job(models.Model):
    _name = 'printers.job'
    _description = 'Printing Job'
    _order = 'jobid DESC'

    @api.model
    def _job_state_get(self):
        return JOB_STATES

    @api.model
    def _job_state_reason_get(self):
        return JOB_STATE_REASONS

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Name', size=64, required=False, help='Job name')
    active = fields.Boolean(string='Active', default=True, help='Unchecked if the job is purged from cups')
    jobid = fields.Integer(string='Job ID', default=0, required=True, help='CUPS id for this job')
    server_id = fields.Many2one('printers.server', string='Server', required=True, ondelete='restrict', help='Server which host this job')
    printer_id = fields.Many2one('printers.list', string='Printer', required=True, ondelete='restrict', help='Printer used for this job')
    job_media_progress = fields.Integer(string='Media Progress', default=0, required=True, help='Percentage of progress for this job')
    time_at_creation = fields.Datetime(string='Time At Creation', required=True, help='Date and time of creation for this job')
    time_at_processing = fields.Datetime(string='Time At Processing', required=True, help='Date and time of process for this job')
    time_at_completed = fields.Datetime(string='Time At Completed', required=True, help='Date and time of completion for this job')
    job_state = fields.Selection('_job_state_get', string='State', help='Current state of the job')
    job_state_reason = fields.Selection('_job_state_reason_get', string='State Reason', help='Reason for the current job state')

    _sql_constraints = [
        ('jobid_unique', 'UNIQUE(jobid, server_id)', 'The jobid of the printers job must be unique per server !'),
    ]

    @api.multi
    def cancel(self, purge_job=False):
        server_obj = self.env['printers.server']
        for job in self:
            connection = job.server_id._openConnection(job.server_id)
            connection.cancelJob(job.jobid, purge_job=purge_job)
            job.server_id.update_jobs(which='all', first_job_id=job.jobid)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
