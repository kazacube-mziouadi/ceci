# coding: utf-8

from openerp import models, fields, api, _
from lxml import etree
import cPickle as pickle
import re
from openerp.osv.orm import setup_modifiers


def OPERATORS():
    return {
             'numerical': [('>', '>'), ('<', '<'), ('=', '='), ('<>', '<>')],
             'string': [('ilike', _('Like')), ('not ilike', _('Not Like'))],
             }
    
    
    
class search_select_characteristic_category(models.TransientModel):
    _name = 'search.select.characteristic.category'
    
    characteristic_category_ids = fields.Many2many('characteristic.type', string='Type', required=True, ondelete='cascade', relation='search_wiz_characteristic_categ_rel')
    
    @api.multi
    def validate(self):
        return {'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'search.characteristics',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'context': {'default_type_ids': [x.id for x in self[0].characteristic_category_ids], 
                            'prev_id': self[0].id,
                            'prev_model': 'search.select.characteristic.category', 
                            'dialog_size': 'large'}}
        
        
        
class search_characteristics_select_category(models.TransientModel):
    _name = "search.characteristics.select.category"
    
    category_id = fields.Many2one('product.category', string='Category', required=True, ondelete='cascade', domain="[('type', '=', 'normal')]")
    
    @api.multi
    def validate(self):
        return {
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'search.characteristics',
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'context': {'default_category_id': self.category_id.id,
                                'prev_id': self.id,
                                'prev_model': 'search.characteristics.select.category', 'dialog_size': 'large',
                                'sidebar': self.env.context.get('sidebar_without_id'),
                                },
                }



class search_characteristics(models.TransientModel):
    _name = 'search.characteristics'
    
    result_count = fields.Integer(string="Count")
    dynamic_vals = fields.Char()
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(search_characteristics, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        all_fields = res['fields']
        form_el = etree.Element('form', {'string':_('Search products')})
        
        if self.env.context.get('default_category_id'):
            categ_id = self.env['product.category'].browse(self.env.context['default_category_id'])
            characteristic_object_rss = categ_id.characteristic_category_ids
            already_type = False
        elif self.env.context.get('default_type_ids'):
            characteristic_object_rss = self.env['characteristic.type'].browse(self.env.context['default_type_ids'])
            already_type = True
        else:
            characteristic_object_rss = []
            already_type = False

        count_line_group = etree.SubElement(form_el, 'group', {'col': "6"})
        count_group = etree.SubElement(count_line_group, 'group', {'col': '4', 'colspan': '2', 'string':_('Number of results'), 'col': '6'})
        etree.SubElement(count_line_group, 'group', {'col': '4', 'colspan': '4'})
        etree.SubElement(count_group, 'button', {'string':_('Compute'), 'type': 'object', 'name': 'count', 'class': 'btn btn-primary'})
        etree.SubElement(count_group, 'field', {'string':_('Count'), 'name': 'result_count', 'nolabel': '1', 'invisible': '1'})

        # header
        modifiers = {
                     'col': "6",
                     'invisible': '1',
                    }
        header_group = etree.SubElement(form_el, 'group', modifiers)
        setup_modifiers(header_group, modifiers)
        etree.SubElement(header_group, 'field',
                         {
                          'name': 'global_operator',
                          'string': _('Operator'),
                          'colspan': '2',
                          'readonly': '1',
                         })
        all_fields['global_operator'] = {
                                         'type': 'selection',
                                         'selection': [
                                                       ('&', 'AND'),
                                                       ('|', 'OR')
                                                      ],
                                        }

        # chaque caractéristique
        for i, charac_object in enumerate(characteristic_object_rss):
            if not already_type:
                charact_type = charac_object.type_id
            else:
                charact_type = charac_object

            group_el = etree.SubElement(form_el, 'group',
                                        {
                                         'string': charact_type.name,
                                         'col': '4',
                                        })
            op_name = 'operator_%s' % charact_type.id
            subgroup_right = etree.SubElement(group_el, 'group', {'colspan':'3', 'col': '4'})
            subgroup_left = etree.SubElement(group_el, 'group', {'colspan':'1'})
            all_fields[op_name] = {
                                   'type': 'selection',
                                   'selection': [('&', 'AND'), ('|', 'OR')],
                                   }
            if charact_type.format != 'list':
                modifiers = {
                             'name': op_name,
                             'invisible': '1',
                             'string': _('Search')
                            }
                node = etree.SubElement(subgroup_left, 'field', modifiers)
                setup_modifiers(node, modifiers)
                # gestion unité pour type numerique
                if charact_type.format == 'numerical':
                    uom_category_id = charac_object.uom_id.category_id if already_type else charac_object.type_id.uom_id.category_id
                    all_uom_ids = self.env['product.uom'].search([('category_id', '=', uom_category_id.id)])
                    all_fields["%s_uom" % op_name] = {
                                                      'type': 'selection',
                                                      'selection': [(x.id, x.name) for x in all_uom_ids],
                                                      }
                    etree.SubElement(subgroup_left, 'field', {
                                                              'name': "%s_uom" % op_name,
                                                              'string': _('UoM'),
                                                              })
                all_fields["%s_operator_%s" % (op_name, "1")] = {'type': 'selection', 'selection': OPERATORS()[charact_type.format],}
                all_fields["%s_value_%s" % (op_name, "1")] = {'type': 'char'}
                etree.SubElement(subgroup_right, 'field', {
                                                     'name': "%s_operator_%s" % (op_name, "1"),
                                                     'string': _('Operator %s') % 1,
                                                     })
                etree.SubElement(subgroup_right, 'field', {
                                                     'name': "%s_value_%s" % (op_name, "1"),
                                                     'string': _('Value %s') % 1
                                                     })

                if charact_type.format == 'numerical':
                    all_fields["%s_operator_%s" % (op_name, "2")] = {'type': 'selection', 'selection': OPERATORS()[charact_type.format],}
                    all_fields["%s_value_%s" % (op_name, "2")] = {'type': 'char'}
                    etree.SubElement(subgroup_right, 'field', {
                                                         'name': "%s_operator_%s" % (op_name, "2"),
                                                         'string': _('Operator %s') % 2,
                                                         })
                    etree.SubElement(subgroup_right, 'field', {
                                                         'name': "%s_value_%s" % (op_name, "2"),
                                                         'string': _('Value %s') % 2
                                                         })

            else:
                all_fields["%s_list" % (op_name)] = {
                                                     'type': 'many2many',
                                                     'relation': 'characteristic.value',
                                                     'domain': [('type_id', '=', charact_type.id)]
                                                     }
                etree.SubElement(subgroup_right, 'field', {
                                                     'name': "%s_list" % (op_name),
                                                     'string': _('List'),
                                                     'nolabel': '1',
                                                     })
        # footer
        footer = etree.SubElement(form_el, 'footer')
        etree.SubElement(footer, 'button', {'string':_('OK'), 'type': 'object', 'name': 'validate', 'class': 'oe_highlight'})
        span = etree.SubElement(footer, 'span')
        span.text = '  ' + _('Or')
        etree.SubElement(footer, 'button', {'string':_('Back'), 'type': 'object', 'name': 'back', 'class': 'oe_link'})
        res['arch'] = etree.tostring(form_el)
        res['fields'] = all_fields
        return res
    
    @api.model
    def default_get(self, fields_list):
        res = super(search_characteristics, self).default_get(fields_list)
        for field in fields_list:
            if field.endswith('_uom'):
                if self.env.context.get('default_category_id'):
                    categ_id = self.env['product.category'].browse(self.env.context['default_category_id'])
                    characteristic_object_rss = categ_id.characteristic_category_ids
                    already_type = False
                elif self.env.context.get('default_type_ids'):
                    characteristic_object_rss = self.env['characteristic.type'].browse(self.env.context['default_type_ids'])
                    already_type = True
                else:
                    characteristic_object_rss = []
                    already_type = False
                charac_object = characteristic_object_rss.search([
                                                                  ('type_id', '=', int(re.search("operator_(\d+)_uom", field).group(1))),
                                                                  ('category_id', '=', categ_id.id),
                                                                  ])
                uom_id = charac_object.uom_id.category_id if already_type else charac_object.type_id.uom_id
                res[field] = uom_id.id
            elif field.startswith('operator_') and len(field) == 10:
                res[field] = '&'
        return res
    
    @api.multi
    def back(self):
        return {
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': self.env.context['prev_model'],
                    'res_id': self.env.context['prev_id'],
                    'context': {'dialog_size':'small'},
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                }
    
    
    # que des champs "virtuels"
    @api.model
    def create(self, vals):
        return super(search_characteristics, self).create({'dynamic_vals': pickle.dumps(vals)})
    
    
    # idem, permet de supprimer les warnings
    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(search_characteristics, self).read(fields={}, load=load)
        vals = pickle.loads(str(res[0]['dynamic_vals']))
        res[0].update(vals)
        res[0].pop('dynamic_vals')
        return res

    @api.multi
    def write(self, vals):
        old_vals = pickle.loads(str(self.dynamic_vals))
        old_vals.update(vals)
        return super(search_characteristics, self).write({'dynamic_vals': pickle.dumps(old_vals)})

    @api.multi
    def count(self):
        if self.env.context.get('prev_model') == 'search.select.characteristic.category':
            count = self.env['stock.label'].search_count(self.build_domain('label_id'))
        else:
            count = self.env['product.product'].search_count(self.build_domain('product_id'))

        self.result_count = count
        return {'type': 'act_window_noclose'}

    def build_domain(self, field):
        vals = pickle.loads(str(self.dynamic_vals))
        domain = []
        if field == 'product_id':
            category_id = self.env['product.category'].browse(self.env.context['default_category_id'])
            categ_ids = category_id.characteristic_category_ids
            type_ids = [x.type_id for x in categ_ids]
            with_categ = True
        elif field == 'label_id':
            type_ids = self.env['characteristic.type'].browse(self.env.context.get('default_type_ids', []))
            with_categ = False

        def filter_by_op(charac_ids, op, value):
            for charac in charac_ids:
                charac_value = float(charac.uom_value)
                # converti la valeur en uom parent si nécessaire
                if op == '>' and charac_value > value:
                    yield charac
                elif op == '<' and charac_value < value:
                    yield charac
                elif op == '=' and charac_value == value:
                    yield charac
                elif op == '<>' and charac_value != value:
                    yield charac
        
        for i, type_id in enumerate(type_ids):
            sub_domain = []
            if 'operator_%s_operator_1' % (type_id.id) in vals:
                # type = numeric ou char
                for j in range(1, 3): # 3 est exclu
                    if vals.get('operator_%s_operator_%s' % (type_id.id, j)):
                        # on cherche des produits qui ont une carac avec categ_ids[i] comme parent et (carac.value, %op%, %value%)
                        if with_categ:
                            charac_domain = [('category_id', '=', categ_ids[i].id)]
                        else:
                            charac_domain = []

                        if type_id.format == 'string':
                            charac_domain.append((
                                'value.name',
                                vals['operator_%s_operator_%s' % (type_id.id, j)],
                                vals['operator_%s_value_%s' % (type_id.id, j)] or ''))

                        charac_ids = self.env['characteristic'].search(charac_domain)
                        if type_id.format == 'numerical':
                            uom_id = int(vals['operator_%s_uom' % type_id.id])
                            uom_value = float(vals['operator_%s_value_%s' % (type_id.id, j)] or '')
                            if uom_id != type_id.uom_id.id:
                                uom_value = self.env['product.uom']._compute_qty_obj(self.env['product.uom'].browse(uom_id), uom_value, type_id.uom_id)
                            charac_ids = filter_by_op(
                                charac_ids,
                                vals['operator_%s_operator_%s' % (type_id.id, j)],
                                uom_value,
                            )

                        sub_domain.append(('id', 'in', [x[field].id for x in charac_ids]))

            elif 'operator_%s_list' % type_id.id in vals and len(vals['operator_%s_list' % type_id.id]) and len(vals['operator_%s_list' % type_id.id][0][2]):
                # type = list
                value_ids = vals['operator_%s_list' % type_id.id][0][2]
                car_args = [('value', 'in', value_ids)]
                if with_categ: 
                    car_args.append(('category_id', '=', categ_ids[i].id))
                    
                charact_ids = self.env['characteristic'].search(car_args)
                sub_domain.append(('id', 'in', [x[field].id for x in charact_ids]))
            
            len_sub = len(sub_domain)
            if len_sub == 1:
                # on retourne le sous domaine tel quel
                domain.append(sub_domain)
            elif len_sub == 2:
                domain.append([vals['operator_%s' % type_id.id] or '|'] + sub_domain)
            else:
                # pas de domaine, ne rien faire
                pass
            
        if vals['global_operator'] != '|':
            return [('categ_id', '=', self.env.context.get('default_category_id'))] + [x for sub in domain for x in sub]
        else:
            def joinit(iterable, delimiter):
                last = iterable[-1]
                it = iter(iterable)
                for x in it:
                    if x != last:
                        yield delimiter
                    for y in x:
                        yield y
                        
            return [('categ_id', '=', self.env.context.get('default_category_id'))] + list(joinit(domain, '|'))
    
    
    def include_downstram(self, domain):
        new_domain = []
        for arg in domain:
            if isinstance(arg, tuple) and arg[0] == 'id' and arg[-1]:
                arg = list(arg)
                arg[-1].extend(self.env['stock.label'].browse(arg[-1]).recursion_traceability_downstream())
                arg = tuple(arg)
                
            new_domain.append(arg)
                
        return new_domain
    
    
    @api.multi
    def validate(self):
        if self.env.context.get('prev_model') == 'search.select.characteristic.category':
            domain = self.build_domain('label_id')
            domain = self.include_downstram(domain)
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.label',
                'domain': domain,
                }
        else:
            domain = self.build_domain('product_id')
            if self.env.context.get('select_create'):
                return {
                        'type': 'ir.actions.act_add_domain',
                        'domain': domain,
                        }
            else:
                return {
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'product.product',
                        'domain': domain,
                        'add_domain': True,
                        }
        