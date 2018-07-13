# coding: utf-8

from openerp import http
from dateutil.rrule import rrule, DAILY
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import string

class Chart(http.Controller):
    @http.route('/charts/calendar', type='json')
    def calendar(self, start_date, end_date, group_by):
        end_date = end_date + " 23:59:59"
        group_model = string.replace(group_by[0], '.', '_')
        group_field = group_by[1]
        measure = group_by[2]
        sql = """
            select distinct real_start_date::date as date, sum({})
            from calendar_line ci
            left outer join {} t2 on ci.id = t2.{}
            where real_start_date::date >= %s
            and real_end_date::date <= %s
            group by real_start_date::date
            order by real_start_date::date""".format(measure, group_model, group_field)
        http.request.env.cr.execute(sql, (start_date, end_date))
        res = http.request.env.cr.fetchall()
        return res