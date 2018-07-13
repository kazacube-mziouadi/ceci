# -*- coding: utf-8 -*-


from openerp.report.interface import report_int
from openerp.osv.osv import except_osv

from report.report_soap import Report
from report.report_exception import JasperException

import logging

_logger = logging.getLogger(__name__)


class report_jasper(report_int):
    """
    Extend report_int to use Jasper Server
    """

    def create(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug('Call %s' % self.name)
        try:
            return Report(self.name, cr, uid, ids, data, context).execute()
        except JasperException, e:
            raise except_osv(e.title, e.message)

report_jasper('report.print.jasper.server')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
