# -*- coding: utf-8 -*-
from openerp import http
from openerp.tools.translate import _


class TranslatorController(http.Controller):

    @http.route('/web/translator/get_translate_wizard', type='json', auth='user')
    def get_translate_wizard(self, request, **values):
        
        # on traduit pas de 'non valeur'
        if not values.get('label', False):
            return {'value': _("Label not found"), 'is_action': False}
        
        user_id = request.env.user
        group_ok = user_id.has_group('translator.group_translate')
        if not group_ok:
            return {'value': _('You can\'t translate'), 'is_action': False}

        # teste si la langue est éditable
        lang_id = request.env['res.lang'].search([('code', '=', request.session.context['lang'])])
        if lang_id.editable_in_interface == False:
            return {'value': _("Lang not editable"), 'is_action': False}
        
        trans_obj = request.env['ir.translation']
        model = values.get('model', False)
        if model:
            model_obj = request.env[model]
            module = model_obj._original_module
        
        if values['type'] == 'field':
            field = values['field_name']
            field_id = request.env['ir.model.fields'].search([('model', '=', model), ('name', '=', field)])
            source_id = trans_obj.search([
                                                           ('name', '=', 'ir.model.fields,field_description'),
                                                           ('type', '=', 'model'),
                                                           ('lang', '=', lang_id.code),
                                                           ('res_id', '=', field_id.id)])
            if not len(source_id):
                source_id = trans_obj.create({
                                                'lang':lang_id.code,
                                                'src':field_id.field_description,
                                                'name':'ir.model.fields,field_description',
                                                'type':'model',
                                                'res_id':field_id.id,
                                                'value':field_id.field_description,})
            # add help_text if any
            help_text_id = trans_obj.search([
                                             ('name', '=', 'ir.model.fields,help'),
                                             ('res_id', '=', source_id.res_id),
                                             ('lang', '=', lang_id.code),
                                             ])
        elif values['type'] == 'menu':
            source_id = trans_obj.search([
                                          ('res_id', '=', values['res_id']),
                                          ('name', '=', 'ir.ui.menu,name'),
                                          ('lang', '=', lang_id.code),
                                          ('type', '=', 'model'),
                                          ])
            if not len(source_id):
                menu_id = request.env['ir.ui.menu'].browse(values['res_id'])
                source_id = trans_obj.create({
                                                'lang':lang_id.code,
                                                'src':menu_id.name,
                                                'name':'ir.ui.menu,name',
                                                'type':'model',
                                                'res_id':menu_id.id,
                                                'value':menu_id.name,})
        elif values['type'] == 'view':
            source_id = trans_obj.search([
                                          ('res_id', '=', values['res_id']),
                                          ('name', '=', 'ir.ui.view,arch_db'),
                                          ('lang', '=', lang_id.code),
                                          ('type', '=', 'model'),
                                          ('value', '=', values['label'])
                                          ])
            if not len(source_id):
                child_view_ids = request.env['ir.ui.view'].search([
                                                                   ('inherit_id', '=', values['res_id'])
                                                                   ])
                source_id = trans_obj.search([
                                              ('res_id', 'in', child_view_ids.ids),
                                              ('name', '=', 'ir.ui.view,arch_db'),
                                              ('lang', '=', lang_id.code),
                                              ('type', '=', 'model'),
                                              ('value', '=', values['label'])
                                              ])
                if not len(source_id):
                    source_id = trans_obj.create({
                                                    'lang':lang_id.code,
                                                    'src':values['label'],
                                                    'name':'ir.ui.view,arch_db',
                                                    'type':'model',
                                                    'res_id':values['res_id'],
                                                    'value':values['label'],})
        elif values['type'] == 'state':
            source_id = trans_obj.search([
                                          ('type', '=', 'code'),
                                          ('value', '=', values['label']),
                                          ('lang', '=', lang_id.code),
                                          ('module', '=', module)
                                          ])
            if not len(source_id):
                source_id = trans_obj.search([
                                              ('type', '=', 'selection'),
                                              ('name', '=', '%s,state' % model),
                                              ('value', '=', values['label']),
                                              ('lang', '=', lang_id.code),
                                              ])
                if not len(source_id):
                    source_id = trans_obj.create({
                                                    'lang':lang_id.code,
                                                    'src':values['label'],
                                                    'name':'',
                                                    'type':'code',
                                                    'res_id':0,
                                                    'module':module,
                                                    'value':values['label'],})
        else:
            return Warning('Not found')
                
        res_vals = {
                    'label': source_id[0].value,
                    'model': model,
                    'lang': lang_id.code,
                    'new_value': source_id[0].value,
                    'source_id': source_id[0].id,
                    }
        if values['type'] == 'field' and len(help_text_id) == 1:
            res_vals['help_text_id'] = help_text_id.id
            res_vals['help_text'] = help_text_id.value
        if values['type'] == 'field' and field_id.ttype == 'selection':
            selection_values = [y for x, y in model_obj._fields[field]._description_selection(request.env)]
            selection_translation_ids = trans_obj.search([
                                          ('type', '=', 'code'),
                                          ('lang', '=', lang_id.code),
                                          ('module', '=', module),
                                          ('value', 'in', selection_values)
                                          ])
            if not len(selection_translation_ids):
                selection_translation_ids = trans_obj.search([
                                                  ('type', '=', 'selection'),
                                                  ('name', '=', '%s,%s' % (model,field)),
                                                  ('lang', '=', lang_id.code),
                                                  ])
            res_vals['translation_line_ids'] = [(6, 0, selection_translation_ids.ids)]
        res_id = request.env['translator.translate.wizard'].create(res_vals)
        
        view = request.env.ref('translator.translator_form')
        
        return {'value': {'name': _('Translator'),
                          'type': 'ir.actions.act_window',
                          'view_type': 'form',
                          'view_mode': 'form',
                          'res_model': 'translator.translate.wizard',
                          'views': [(view.id, 'form')],
                          'view_id': view.id,
                          'res_id': res_id.id,
                          'target': 'new',
                          'context': request.env.context},
                'is_action': True}

