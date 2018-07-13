# -*- coding: utf-8 -*-


from openerp import http
import itertools


class ModifyViewController(http.Controller):
    @http.route('/web_modify_view/get_view', type='json')
    def get_view(self, model, view_type, base_view_id):
        # chercher nouvelle vue
        view_obj = http.request.env['ir.ui.view']
        views = view_obj.search([('model', '=', model), ('type', '=', view_type), ('priority', '=', 3000)])
        if not base_view_id:
            base_view_id = view_obj.default_view(model, 'form')
        if len(views) == 0:
            base_view = view_obj.browse(base_view_id)
            arch = """<xpath expr="(//page)[last()]" position="after">
    <page string="Additional" />
</xpath>"""
            vals = {
                'model':model,
                'type':view_type,
                'priority':3000,
                'inherit_id':base_view_id,
                'active':True,
                'name':'Additional',
                'arch_db':arch
            }
            views = view_obj.create(vals)
            view_obj.clear_caches() 
        return views.id
