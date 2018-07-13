# coding: utf-8
'''
Created on 23 juin 2015

@author: sylvain
'''

from openerp import http


class Planning(http.Controller):
    
    @http.route('/planning/loading', type='json')
    def loading(self, start_date, end_date, resource_ids):
        cr = http.request.env.cr
        sql = """select id, coalesce(sum(loading), 0) loading, sum(real_hour) real_hour
from (
    select mr.id, sum(loading) loading, real_hour
    from calendar_line li
    join mrp_resource mr on li.calendar_id = mr.calendar_id
    left join calendar_loading lo on lo.calendar_line_id = li.id and lo.resource_id = mr.id
    where real_start_date between %s and %s
    and mr.id = ANY(%s)
    group by li.id, real_start_date, real_hour, mr.id
) as f
group by id;"""
        cr.execute(sql, (start_date, end_date, resource_ids))
        return cr.dictfetchall()
    
    @http.route('/planning/change_primary_resource', type='json')
    def change_primary_resource(self, wo_id, new_resource_id ):
        env = http.request.env
        wo = env['mrp.workorder'].search([('id', '=', wo_id)], limit=1)
        wo_resource = env['mrp.wo.resource'].search([('wo_id', '=', wo_id)], order="sequence ASC", limit=1)
        resource = env['mrp.resource'].search([('id', '=', new_resource_id)])
        if wo_resource.resource_category_id not in resource.category_resource_ids :
            return False
        wo.change_resource(wo_resource, resource, wo_resource.rl_resource_category_id)
        return True

    @http.route('/planning/get_all_neighbours', type='json')
    def get_all_neighbours_route(self, wo_id):
        neighbours = self.get_all_neighbours(wo_id, set())[0]
        return list(neighbours)
    
    def get_all_neighbours(self, wo_id, exclude):
        cr = http.request.env.cr
        wo_id = int(wo_id)
        neighbours = self.get_neighbours_left(wo_id).union(self.get_neighbours_right(wo_id))
        neighbours_ids = {item for sublist in neighbours for item in sublist}
        neighbours_ids.add(wo_id)
        sql = "select prev_id, next_id from mrp_workorder where id = ANY(%s)"
        close_ids = set()
        cr.execute(sql, (list(neighbours_ids), ))
        for line in cr.fetchall():
            if line[0] > 0:
                close_ids.add(line[0])
            if line[1] > 0:
                close_ids.add(line[1])
        for x in close_ids - neighbours_ids - exclude:
            neighbours |= self.get_all_neighbours(x, neighbours_ids | exclude)[0]
        return neighbours, neighbours_ids | exclude
    
    def get_neighbours_left(self, wo_id):
        cr = http.request.env.cr
        sql = """select sm2.wo_outgoing_id
from stock_move sm
join stock_move_cover_rel cr on sm.id = cr.out_move_id
join stock_move sm2 on cr.in_move_id = sm2.id
where sm.supply_method = 'produce'
and sm.wo_incoming_id=%s
and in_cover_percent > 0
and sm2.wo_outgoing_id is not null;"""
        cr.execute(sql, (wo_id,))
        next_ids = [x[0] for x in cr.fetchall()]
        next = {(x, wo_id) for x in next_ids}
        for x in next_ids:
            next = next.union(self.get_neighbours_left(x))
        return next
    
    def get_neighbours_right(self, wo_id):
        cr = http.request.env.cr
        sql = """select sm2.wo_incoming_id
from stock_move sm
join stock_move_cover_rel cr on sm.id = cr.in_move_id
join stock_move sm2 on cr.out_move_id = sm2.id
where sm.supply_method = 'produce'
and sm.wo_outgoing_id=%s
and in_cover_percent > 0
and sm2.wo_incoming_id is not null;"""
        cr.execute(sql, (wo_id,))
        next_ids = [x[0] for x in cr.fetchall()]
        next = {(wo_id, x) for x in next_ids}
        for x in next_ids:
            next = next.union(self.get_neighbours_right(x))
        return next
    
    @http.route('/planning/prev_next', type='json')
    def get_prev_next(self, wo_ids):
        cr = http.request.env.cr
        sql = """select wo3.id, sm2.wo_outgoing_id as prev_id, wo.planned_end_date as prev_date, sm4.wo_incoming_id as next_id, wo2.planned_start_date as next_date
from mrp_workorder wo3
left outer join stock_move sm on wo3.id = sm.wo_incoming_id and sm.supply_method = 'produce'
left outer join stock_move_cover_rel cr on sm.id = cr.out_move_id 
and cr.in_cover_percent > 0
left outer join stock_move sm2 on cr.in_move_id = sm2.id
left outer join mrp_workorder wo on wo.id = sm2.wo_outgoing_id

left outer join stock_move sm3 on sm3.wo_outgoing_id = wo3.id and sm3.supply_method = 'produce'
left outer join stock_move_cover_rel cr2 on sm3.id = cr2.in_move_id
and cr2.in_cover_percent > 0
left outer join stock_move sm4 on cr2.out_move_id = sm4.id
left outer join mrp_workorder wo2 on wo2.id = sm4.wo_incoming_id

where wo3.id = ANY(%s)
order by wo.planned_end_date desc, wo2.planned_start_date desc"""
        cr.execute(sql, (wo_ids,))
        results = cr.dictfetchall()
        return results