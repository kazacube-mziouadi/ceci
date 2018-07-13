# coding: utf-8

from openerp import http
from collections import OrderedDict


class Charge(http.Controller):

    @http.route('/charge/per_resource', type="json")
    def per_resource(self, start_date, end_date, domain, group_period):
        env = http.request.env
        resource_ids = env['mrp.resource'].search(domain)
        calendar_line_obj = env['calendar.line']
        capacity = {resource_id.name: [resource_id.name,
                                     calendar_line_obj.read_group(
                                         [('real_start_date', '>=', start_date),
                                          ('real_end_date', '<=', end_date),
                                          ('calendar_id', '=', resource_id.calendar_id.id)],
                                         ['real_hour', 'real_start_date'],
                                         ['real_start_date:' + group_period],
                                         orderby='real_start_date:' + group_period
                                     )
                                     ]
                    for resource_id in resource_ids}
        loading = {resource_id.name: [resource_id.name,
                                    env['calendar.loading'].read_group([('start_date', '>=', start_date),
                                                                        ('start_date', '<=', end_date),
                                                                        ('resource_id', '=', resource_id.id)],
                                                                       ['resource_id', 'loading',
                                                                        'start_date'],
                                                                       ['start_date:' + group_period],
                                         orderby='start_date:' + group_period, lazy=False)]
                   for resource_id in resource_ids}
        ret = OrderedDict()
        for res_id, res_groups in capacity.iteritems():
            if res_id not in ret:
                ret[res_id] = OrderedDict()
            for time_slice in res_groups[1]:
                if time_slice['real_start_date:' + group_period] not in ret[res_id]:
                    ret[res_id][time_slice['real_start_date:' + group_period]] = OrderedDict()
                ret[res_id][time_slice['real_start_date:' + group_period]]['capacity'] = time_slice['real_hour']
        for res_id, res_groups in loading.iteritems():
            if res_id not in ret:
                ret[res_id] = OrderedDict()
            for time_slice in res_groups[1]:
                if time_slice['start_date:' + group_period] not in ret[res_id]:
                    ret[res_id][time_slice['start_date:' + group_period]] = OrderedDict()
                ret[res_id][time_slice['start_date:' + group_period]]['loading'] = time_slice['loading']
        return ret

    @http.route('/charge/per_resource_category', type="json")
    def per_resource_category(self, start_date, end_date, domain, group_period):
        env = http.request.env
        resource_category_ids = env['mrp.resource.category'].search(domain)
        calendar_line_obj = env['calendar.line']
        capacity = {}
        ret = OrderedDict()
        for resource_category_id in resource_category_ids:
            resource_ids = resource_category_id.resource_ids
            capacity_res = {resource_id.name: calendar_line_obj.read_group(
                                             [('real_start_date', '>=', start_date),
                                              ('real_end_date', '<=', end_date),
                                              ('calendar_id', '=', resource_id.calendar_id.id)],
                                             ['real_hour', 'real_start_date'],
                                             ['real_start_date:' + group_period],
                                             orderby='real_start_date:' + group_period,
                                             lazy=False
                                         )
                        for resource_id in resource_ids}
            if resource_category_id.name not in ret:
                ret[resource_category_id.name] = OrderedDict()
            for line in capacity_res.values():
                for line2 in line:
                    key = line2['real_start_date:' + group_period]
                    if key not in ret[resource_category_id.name]:
                        ret[resource_category_id.name][key] = {}
                        ret[resource_category_id.name][key]['capacity'] = 0
                    ret[resource_category_id.name][key]['capacity'] += line2['real_hour']
        loading = {resource_category_id.name: env['calendar.loading'].read_group([('start_date', '>=', start_date),
                                                                        ('start_date', '<=', end_date),
                                                                        ('resource_id', '=', resource_category_id.id)],
                                                                       ['resource_category_id', 'loading',
                                                                        'start_date'],
                                                                       ['start_date:' + group_period],
                                         orderby='start_date:' + group_period, lazy=False)
                   for resource_category_id in resource_category_ids}
        for res_id, res_groups in loading.iteritems():
            if res_id not in ret:
                ret[res_id] = OrderedDict()
            for time_slice in res_groups:
                if time_slice['start_date:' + group_period] not in ret[res_id]:
                    ret[res_id][time_slice['start_date:' + group_period]] = OrderedDict()
                ret[res_id][time_slice['start_date:' + group_period]]['loading'] = time_slice['loading']
        return ret
