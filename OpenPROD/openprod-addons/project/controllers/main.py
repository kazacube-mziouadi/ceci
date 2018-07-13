# coding: utf-8

from openerp import http
from dateutil.rrule import rrule, DAILY
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class Planning(http.Controller):
    @http.route('/project/calendar', type='json')
    def calendar(self):
        calendar_id = http.request.env.user.company_id.partner_id.calendar_id
        start_date = datetime.strptime(calendar_id.calendar_template_id.start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(calendar_id.calendar_template_id.end_date, DEFAULT_SERVER_DATE_FORMAT)
        line_ids = http.request.env['calendar.line'].search([('calendar_id', '=', calendar_id.id)], order='real_start_date')
        res = []
        i = 0
        line_ids_len = len(line_ids)
        for day in rrule(DAILY, dtstart=start_date, until=end_date):
            d = line_ids[i].real_start_date[:-9]
            d = datetime.strptime(d, DEFAULT_SERVER_DATE_FORMAT)
            if d == day:
                i = i + 1
                if i >= line_ids_len:
                    break
            else:
                res.append(datetime.strftime(day, DEFAULT_SERVER_DATE_FORMAT))
        return res