# coding: utf-8
'''
Created on 5 may 2017

@author: barnabas et Sylvain
'''

from openerp import http
from openerp.addons.planning.controllers import controller

class Planning(controller.Planning):

    @http.route('/planning/change_primary_resource', type='json')
    def change_primary_resource(self, wo_id, new_resource_id , is_sandbox=False ):
        env = http.request.env
        wo = env['mrp.workorder'].search([('id', '=', wo_id)], limit=1)
        wo_resource = env['mrp.wo.resource'].search([('wo_id', '=', wo_id)], order="sequence ASC", limit=1)
        resource = env['mrp.resource'].search([('id', '=', new_resource_id)])
        if wo_resource.resource_category_id not in resource.category_resource_ids :
            return False
        if is_sandbox :
            wo.write({'sandbox_first_resource_id' : new_resource_id , 'asynchronous' : True })
        else :
            super(Planning , self).change_primary_resource( wo_id, new_resource_id)
        return True