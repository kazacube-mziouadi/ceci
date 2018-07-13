# -*- coding: utf-8 -*-


from openerp import models
from openerp import fields
from openerp import api
from openerp import _
from openerp.exceptions import except_orm
import traceback
import logging
import time


logger = logging.getLogger('printers')


class ir_actions_server(models.Model):
    _inherit = 'ir.actions.server'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    printing_source = fields.Char(string='Source', size=256, required=False, default=False, help='Add condition to found the id of the printer, use:\n- c for context\n- o for object\n- time for date and hour\n- u for user\n eg: o.warehouse_id.printer_id.id')
    printing_function = fields.Char(string='Function', size=64, required=False, default=False, help='Name of the function to launch for printing.\nDEPRECATED')
    printing_report_id = fields.Many2one('ir.actions.report.xml', string='Report', ondelete='restrict', company_dependent=True, help='The report which will be printed')
    model_name = fields.Char(string='Model Name', size=32, related='model_id.model', required=False, help='Name of the model, used to filter ir.actions.report.xml', readonly=True)
    printing_jobname = fields.Char(string='JobName', size=256, required=False, help='Add Job Name base on browse on the object use:\n- c for context\n- o for object\n- time for date and hour\n- u for user\n eg: o.number on invoice')

    def _get_states(self, cr, uid, context=None):
        """ Override me in order to add new states in the server action. Please
        note that the added key length should not be higher than already-existing
        ones. """
        action_list = super(ir_actions_server, self)._get_states(cr, uid, context=context)

        if 'printing' not in [key for key, value in action_list]:
            action_list.append(('printing', 'Printing'))

        return action_list

    @api.one
    def run(self):
        """
        Executed by workflow
        """

        result = False
        # Loop on actions to run
        action = self
        logger.debug('Action : %s' % action.name)

        ctx = self.env.context.copy()
        # Check if there is an active_id (this situation should not appear)
        if not self.env.context.get('active_id', False):
            logger.warning('active_id not found in context')
            return False

        # Retrieve the model related object
        action_model_obj = self.env[action.model_id.model]
        action_model = action_model_obj.browse(self.env.context['active_id'])

        # Check the action condition
        values = {
            'context': self.env.context,
            'object': action_model,
            'time': time,
            'cr': self.env.cr,
            'pool': self.pool,
            'uid': self.env.uid,
        }
        expression = eval(str(action.condition), values)
        if not expression:
            logger.debug('This action doesn\'t match with this object : %s' % action.condition)
            return False

        # If state is 'printing', execute the action
        if action.state == 'printing':
            # Get the printer id
            user = self.env.user
            values = {
                'c': self.env.context,
                'o': action_model,
                'time': time,
                'u': user,
            }
            try:
                # Retrieve the printer id
                printer_id = eval(str(action.printing_source), values)

                # Check if the printer was found
                if not printer_id:
                    raise except_orm(_('Error'), _('Printer not found !'))

            except Exception:
                logger.error(traceback.format_exc())
                raise except_orm(_('Error'), _('Printer not found !'))

            try:
                jobname = eval(str(action.printing_jobname), values)
                if jobname:
                    ctx['jobname'] = jobname
            except Exception:
                logger.error(traceback.format_exc())
                raise except_orm(_('Error'), _('Job Name expression error !'))

            # Get the report id
            # TODO : Check for a specific function, on action_model, which will return False or a report id. If False is returned, use the report put in the printing_report_id.
            # Prototype of the function : def get_printing_report_id(self, cr, uid, ids, context=None)
            # report_id = False
            # if getattr(action_model, 'get_printing_report_id', None) and callable(action_model.get_printing_report_id):
            #     report_id = action_model.get_printing_report_id()[action_model.id]
            #
            # if not report_id:
            report_id = action.printing_report_id.id

            # Log the printer and report id
            logger.debug('ID of the printer : %s' % str(printer_id))
            logger.debug('ID of the report : %s' % str(report_id))

            # Print the requested ir.actions.report.xml
            if report_id:
                self.env['printers.list'].browse(printer_id).with_context(ctx).send_printer(report_id, [action_model.id])
            else:
                raise except_orm(_('Error'), _('Report to print not found !'))

        # If the state is not 'printing', let the server action run itself
        else:
            result = super(ir_actions_server, action).run()

        return result

    @api.onchange('model_id')
    def onchange_model_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        return {'value': {'model_name': self.model_id.model}}

#     def onchange_model_id(self, cr, uid, ids, model_id, context=None):
#         model_obj = self.pool.get('ir.model')
#         model = model_obj.browse(cr, uid, model_id, context=context)
#         return {'value': {'model_name': model.model}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
