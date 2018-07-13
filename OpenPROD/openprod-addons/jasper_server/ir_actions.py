# -*- coding: utf-8 -*-


import openerp
from openerp import models, api
import logging
from jasper import report_jasper


_logger = logging.getLogger(__name__)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report.xml'

    @api.model
    def _add_field(self, name, field):
        res = super(IrActionReport, self)._add_field(name, field)

        if name == 'report_type':
            if 'jasper' not in zip(*field.selection)[0]:
                field.selection.append(('jasper', 'Jasper'))

        return res

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser specified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
            if not isinstance(new_report, report_jasper):
                new_report = None
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s and report_type=%s", (name, 'jasper'))
            r = cr.dictfetchone()
            if r:
                new_report = report_jasper('report.'+r['report_name'])
            else:
                new_report = None

        if new_report:
            return new_report
        else:
            return super(IrActionReport, self)._lookup_report(cr, name)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
