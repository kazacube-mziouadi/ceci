# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp.exceptions import except_orm
import re
from openerp.addons.base_openprod.common import get_form_view

onchange_v7 = re.compile(r"^(\w+)\((.*)\)$")

class create_label_wizard(models.TransientModel):
    """ 
    Create label
    """
    _name = 'create.label.wizard'
    _description = 'Create label'
    _rec_name = 'move_id'
    
    
    @api.one
    @api.depends('uom_qty', 'number_of_label', 'sec_uom_qty')
    def _compute_total_qty(self):
        self.total_qty = self.uom_qty * self.number_of_label 
        self.sec_total_qty = self.sec_uom_qty * self.number_of_label 
    

    @api.one
    @api.depends('product_id')
    def _compute_variable_doule_unit(self):
        product_datas = self.product_id.read(['dual_unit', 'dual_unit_type'], load='_classic_write')
        self.is_variable_double_unit = product_datas and product_datas[0]['dual_unit'] and product_datas[0]['dual_unit_type'] == 'variable' or False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', ondelete='cascade')
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', ondelete='cascade')
    label_template_id = fields.Many2one('stock.label.template', string='Label template', required=True, ondelete='cascade', domain=[('type', '=', 'uc')])
    uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'))
    sec_uom_qty = fields.Float(string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    new_auto_lot = fields.Boolean(string='New automatic lot', default=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='cascade')
    supplier_lot_number = fields.Char(size=64)
    number_of_label = fields.Integer(default=0, required=False)
    total_qty = fields.Float(string='Total qty', digits=dp.get_precision('Product quantity'), compute='_compute_total_qty')
    sec_total_qty = fields.Float(string='Total qty', digits=dp.get_precision('Product quantity'), compute='_compute_total_qty')
    expiry_date = fields.Date(default=False)
    removal_date = fields.Date(default=False)
    is_manual_expiry_date = fields.Boolean(default=False)
    is_variable_double_unit = fields.Boolean(compute='_compute_variable_doule_unit')
    line_ids = fields.One2many('create.label.wizard.line', 'wizard_id',  string='Lines')
    new_auto_um = fields.Boolean(string='New automatic UM', default=False)
    label_um_id = fields.Many2one('stock.label', string='Label UM', required=False, ondelete='cascade')
    label_um_number = fields.Char(size=64)
    label_template_um_id = fields.Many2one('stock.label.template', string='Label UM template', required=False, ondelete='cascade', domain=[('type', '=', 'um')])
    move_uom_qty = fields.Float(string='UoM qty', related='move_id.uom_qty', readonly=True)
    move_uom_id = fields.Many2one('product.uom', string='UoM', related='move_id.uom_id', readonly=True)
    move_product_id = fields.Many2one('product.product',string='Product', related='move_id.product_id', readonly=True)
            
    @api.model
    def default_get(self, fields_list):
        res = super(create_label_wizard, self).default_get(fields_list=fields_list)
        move = self.env['stock.move'].browse(self.env.context.get('active_id'))
        if move:
            product = move.product_id
            res['move_id'] = move.id
            res['product_id'] = product.id
            res['uom_id'] = product.uom_id.id
            res['sec_uom_id'] = product.sec_uom_id.id
            res['label_template_id'] = product.label_template_id.id
            res['is_manual_expiry_date'] = product.is_expiry_date and product.expiry_type == 'manual'
            
        return res
    
    
    @api.multi
    def create_label(self):
        res = True
        move_label_obj = self.env['stock.move.label']
        move_label_rs = self.env['stock.move.label']
        label_obj = self.env['stock.label']
#         move_label_rs = self.move_id.create_label(self.move_id.product_id, self.label_template_id, self.uom_qty, self.sec_uom_qty, self.number_of_label, self.new_auto_lot, self.supplier_lot_number, self.lot_id, self.expiry_date, self.removal_date, self.is_variable_double_unit)
        if not self.line_ids:
            self.visualization()
        
        if self.new_auto_um:
            name_um = self.label_um_number or self.label_template_um_id.sequence_id.next_by_id()
            label_vals = {'template_id': self.label_template_um_id.id,
                          'name': name_um,
                          }
            um_label_id = label_obj.create(label_vals).id
        else:
            um_label_id = self.label_um_id and self.label_um_id.id or False
        
        for line in self.line_ids:
            vals = {'move_id': self.move_id.id,
                    'uom_qty': line.uom_qty,
                    'sec_uom_qty': line.sec_uom_qty,
                    'label_id': line.label_id.id,
                    'uom_id': line.uom_id.id,
                    'sec_uom_id': line.sec_uom_id.id,
                    'is_variable_double_unit': self.is_variable_double_unit}
            
            write_label = {'um_label_id': um_label_id}
            if line.label_name and line.label_id:
                write_label['name'] = line.label_name
                
            line.label_id.write(write_label)
            move_label_rs |= move_label_obj.create(vals)
        
        if self.product_id.get_common_attribute_ids() and move_label_rs:
            res = {
                'name': _('Create attributes'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'create.label.attribute.wizard',
                'type': 'ir.actions.act_window',
                'context': {'common_product_id': self.product_id.id, 'default_create_label_id': self.id, 'default_move_label_ids': move_label_rs.ids},
                'target': 'new'
            }
            
        return res
    
    
    @api.onchange('uom_id', 'product_id', 'uom_qty', 'move_id', 'is_variable_double_unit')
    def onchange_partner_id(self):
        if self.move_id and self.product_id:
            self.sec_uom_id = self.move_id.sec_uom_id.id
            if not self.is_variable_double_unit:
                qtys = self.product_id.get_qtys(self.uom_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.move_id.sec_uom_id, 
                                 uoi_id=False, 
                                 by_field='uom', 
                                 dual_unit=self.move_id.dual_unit, 
                                 dual_unit_type=self.move_id.dual_unit_type, 
                                 factor=self.move_id.factor, 
                                 divisor=self.move_id.divisor,
                                 with_raise=True)
                
                self.sec_uom_qty = 'sec_uom_qty' in qtys and qtys['sec_uom_qty'] or 0.0
              
        else:
            self.sec_uom_id = False
            self.sec_uom_qty = 0.0

    
    @api.multi
    def visualization(self):
        """
            Création d'un move label avec son étiquette en draft
        """
        wizard_line_obj = self.env['create.label.wizard.line']
        wizard_line_rs = self.env['create.label.wizard.line']
        label_obj = self.env['stock.label']
        lot_obj = self.env['stock.lot']
        if self.new_auto_lot:
            vals = {'product_id': self.product_id.id}
            if self.supplier_lot_number:
                vals['supplier_lot_number'] = self.supplier_lot_number
            
            if self.expiry_date:
                vals['expiry_date'] = self.expiry_date

            if self.removal_date:
                vals['removal_date'] = self.removal_date
            
            lot_rs = lot_obj.create(vals)
        else:
            lot_rs = self.lot_id
            
        number_of_label = self.number_of_label
        while number_of_label:
            label_vals = {
                'template_id': self.label_template_id.id,
                'lot_id': lot_rs and lot_rs.id or False,
                'product_id': self.product_id.id,
                'uom_id': self.product_id.uom_id.id,
                'sec_uom_id': self.sec_uom_id.id,
                'is_variable_double_unit': self.is_variable_double_unit,
                'uom_qty': 0.0,
                'sec_uom_qty': 0.0,
            }
            if self.label_template_id.generate_label_in_advance:
                label_vals.update({
                    'name': self.label_template_id.sequence_id.next_by_id(),
                    'printed_qty': self.uom_qty,
                    'location_id': self.move_id.location_dest_id.id,
                })
                
            label_rc = label_obj.create(label_vals)
            wizard_line_rs |= wizard_line_obj.create({
                'wizard_id': self.id,
                'product_id': self.product_id.id,
                'uom_qty': self.uom_qty,
                'sec_uom_qty': self.sec_uom_qty,
                'label_id': label_rc.id,
                'uom_id': self.product_id.uom_id.id,
                'sec_uom_id': self.sec_uom_id.id or self.move_id.sec_uom_id.id,
                'is_variable_double_unit': self.is_variable_double_unit,
                'generate_label_in_advance': self.label_template_id.generate_label_in_advance,
            })
            number_of_label -= 1
            
        return get_form_view(self, 'stock.act_create_label_wizard', res_id=self.id, view_mode='form', target='new')
        
        
    @api.multi
    def remove(self):
        self.line_ids.unlink()
        return get_form_view(self, 'stock.act_create_label_wizard', res_id=self.id, view_mode='form', target='new')

        
    
class create_label_wizard_line(models.TransientModel):
    """ 
    Create label
    """
    _name = 'create.label.wizard.line'
    _description = 'Create label line'
    _rec_name = 'wizard_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('create.label.wizard', string='Wizard', required=True, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade', select=True)
    uom_qty = fields.Float(string='UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, ondelete='cascade')
    sec_uom_qty = fields.Float(string='Second UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', readonly=True, ondelete='cascade')
    is_variable_double_unit = fields.Boolean()
    product_id = fields.Many2one('product.product', string='Product', readonly=False, ondelete='cascade')
    label_name = fields.Char(required=False, help='Allows to force the label name')
    generate_label_in_advance = fields.Boolean(default=False)
    
    
    @api.multi
    def print_label(self):
        for line_rc in self:
            line_rc.label_id.write({'printed_qty': line_rc.uom_qty})
            report_datas = {'data_jasper': {'QTY_PRINTED': True}}
            line_rc.label_id.with_context(report_datas).do_print_label()
        
        return {'type': 'ir.actions.act_window_dialog_reload'}
        
    
    
    
class wo_declaration_produce(models.TransientModel):
    """ 
        WorkOrder Declaration Produce
    """
    _name = 'wo.declaration.produce'
    _description = 'WorkOrder Declaration Produce'
    
    
    
class create_label_attribute_wizard(models.TransientModel):
    """ 
    Create label
    """
    _name = 'create.label.attribute.wizard'
    _description = 'Create label attribute'
    _rec_name = 'create_label_id'
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    create_label_id = fields.Many2one('create.label.wizard', string='Create label', required=False, ondelete='cascade')
    wo_declaration_id = fields.Many2one('wo.declaration.produce', string='WO declaration', required=False, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    all_attr = fields.Text()
    all_unique_attr = fields.Text()
    all_ro_attr = fields.Text()
    all_compute_attr = fields.Text()
    line_ids = fields.One2many('create.label.attribute.line', 'wizard_id',  string='Lines')
    move_label_id = fields.Many2one('stock.move.label', string='Label line', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')


    @api.multi
    def onchange(self, values, field_name, field_onchange):
        """ Perform an onchange on the given field.
 
            :param values: dictionary mapping field names to values, giving the
                current state of modification
            :param field_name: name of the modified field, or list of field
                names (in view order), or False
            :param field_onchange: dictionary mapping field names to their
                on_change attribute
        """
        if isinstance(field_name, list):
            names = field_name
        elif field_name:
            names = [field_name]
        else:
            names = []
            
        todo = list(names) or list(values)
        done = set()
        result = {}
        while todo:
            name = todo.pop(0)
            if name in done:
                continue
            
            done.add(name)
            with self.env.do_in_onchange():
                if field_onchange.get(name):
                    match = onchange_v7.match(field_onchange[name])
                    if match:
                        method, params = match.groups()
                        params = eval("[%s]" % params, values)
                        args = (self._cr, self._uid, self.ids) + tuple(params)
                        try:
                            result = getattr(self._model, method)(*args, context=self._context)
                        except TypeError:
                            result = getattr(self._model, method)(*args)
                            
        return result
    
    
    def false_in_filter(self, domain):
        if domain:
            for item in domain:
                if isinstance(item, tuple) and not item[-1]:
                    return True
            
        return False


    def attr_search(self, cr, uid, attr, table=False, domain=False, field=False):
        res = False
        pool = self.pool.get(table)
        # La table est déclarée par l'ORM
        if pool:
            if field == 'id' or field in pool._columns.keys():
                res_ids = pool.search(cr, uid, domain, limit=1)
                if res_ids:
                    res = pool.read(cr, uid, res_ids, [field], load='_classic_write')[0][field]
                else:
                    if not self.false_in_filter(domain):
                        raise except_orm(_('%s haven\'t any result')%(domain))
            else:
                raise except_orm(_('Field %s is not in table %s')%(field, table))

        # La table n'est pas déclarée par l'ORM
        else:
            exp = re.compile("""attr\[['"][^'"]{0,}['"]\]{1}""")
            where = domain
            attrs = exp.findall(where)
            if attrs:
                attrs = list(set(attrs))
                for attibute in attrs:
                    value = eval(attibute)
                    if isinstance(value, bool):
                        value = "''"
                    else:
                        value = "'%s'"%(value)
                        
                    where = where.replace(attibute, value)
                    
            query = 'SELECT %s FROM %s WHERE %s'%(field, table, where)
            cr.execute(query)
            query_res = cr.fetchone()
            res = query_res and query_res[0] or False
            
        return res
    
    
    def execute_function(self, function, const):
        exp = re.compile("""attr\[['"][^'"]{0,}['"]\]{1}""")
        attrs = exp.findall(function)
        if attrs:
            attrs = list(set(attrs))
             
#         if 'attr[\'%s\']'%(col_name) in attrs or 'attr["%s"]'%(col_name) in attrs:
        if 'table_search' in function:
            function = function.replace('table_search(', 'self.attr_search(cr, uid, attr, ')
            
        return eval(function)
    
    
    def onchange_dynamic(self, cr, uid, ids, col_name, create_label_id, move_id, ro_args, functions, args_dict, *args):
        v = {}
        if functions and args_dict:
            ro_args = eval(ro_args)
            # Variables utilisées dynamiquement dans la boucle
            attr = eval(args_dict.replace('$$', ','))
            const = self.pool.get('stock.move').browse(cr, uid, move_id).get_attributes_const()
            for field, function in eval(functions).iteritems():
                function_res = self.execute_function(function, const)
                v[field] = function_res
                if field in ro_args:
                    ro_args[field] = function_res
             
            v['all_ro_attr'] = str(ro_args)
            
        return {'value': v}
    
    
    @api.multi
    def validate_attributes(self):
        attr_obj = self.env['common.attribute']
        product_attr_obj = self.env['common.attribute.model']
        return_list = []
        wizard = self[0]
        attr_values = []
        product_id = False
        attrs = eval(wizard.all_ro_attr)
        attrs.update(eval(wizard.all_attr))
        for att_name, att_value in attrs.iteritems():
            attr_values.append(({'name': att_name[5:],
                                 'value': att_value}))
        
        for line in wizard.line_ids:
            line.attribute_ids.unlink()
            for attr_value in attr_values:
                attr_value['uc_label_id'] = line.uc_label_id.id
                attr_value['product_id'] = product_id = line.uc_label_id.product_id.id
                attr = product_attr_obj.search([('name', '=', attr_value.get('name', False)),
                                                ('product_ids', 'in', [product_id])])
                if attr and attr.label:
                    attr_value['label'] = attr.label
                else:
                    attr_value['label'] = attr_value.get('name', '')
                    
                return_list.append(line.uc_label_id.id)
                attr_obj.create(attr_value)
                
#         return {'type': 'ir.actions.act_window_noclose'}
        ctx = {'common_product_id': product_id, 'default_move_label_ids': return_list}
        if self.create_label_id:
            ctx['default_create_label_id'] = self.create_label_id.id
        elif self.wo_declaration_id:
            ctx['default_wo_declaration_id'] = self.wo_declaration_id.id
            
        return {
                'name': _('Create attributes'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'create.label.attribute.wizard',
                'type': 'ir.actions.act_window',
                'res_id': wizard.id,
                'context': ctx,
                'target': 'new'
            }
    
    
    @api.multi
    def cancel(self):
        for wizard in self:
            if not wizard.move_label_id:
                move_label_rs = self.env['stock.move.label']        
                for line in wizard.line_ids:
                    move_label_rs |= line.move_label_id
            
                if move_label_rs:
                    move_label_rs.unlink()
            
        return True
    
    
    @api.multi
    def create_label(self):
        for wizard in self:
            if wizard.wo_declaration_id:
                wizard.with_context({'without_attributes': True}).wo_declaration_id.action_validate()
            
        return False
    
    
    @api.multi
    def create_label_unit(self):
        attr_obj = self.env['common.attribute']
        product_attr_obj = self.env['common.attribute.model']
        for wizard in self:
            attr_values = []
            attrs = eval(wizard.all_ro_attr)
            attrs.update(eval(wizard.all_attr))
            for att_name, att_value in attrs.iteritems():
                attr_values.append(({'name': att_name[5:],
                                     'value': att_value}))
            
            # Wizard pour une ligne
            if wizard.label_id:
                # Delete des anciens
                wizard.label_id.attribute_ids.unlink()
                for attr_value in attr_values:
                    attr_value['uc_label_id'] = wizard.label_id.id
                    attr_value['product_id'] = wizard.label_id.product_id.id
                    attr = product_attr_obj.search([('name', '=', attr_value.get('name', False)),
                                                    ('product_ids', 'in', [wizard.label_id.product_id.id])])
                    if attr and attr.label:
                        attr_value['label'] = attr.label
                    else:
                        attr_value['label'] = attr_value.get('name', '')

                    attr_obj.create(attr_value)
                    
        return {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def return_wo_declaration(self):
        for wiz in self:
            if wiz.wo_declaration_id:
                return {
                            'name': _('Declaration Produce'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'wo.declaration.produce',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'res_id': wiz.wo_declaration_id.id,
                            'nodestroy': True,
                            }
        
        
    @api.model
    def default_get(self, fields):
        res = super(create_label_attribute_wizard, self).default_get(fields)
        move_label_obj = self.env['stock.move.label']
        label_obj = self.env['stock.label']
        if self.env.context.get('default_label_id'):
            label = label_obj.browse(self.env.context['default_label_id'])
        else:
            label = False
            
        if self.env.context.get('common_move_label_id'):
            move_label = move_label_obj.browse(self.env.context['common_move_label_id'])
            label = move_label.label_id
            move = move_label.move_id
        elif self.env.context.get('default_create_label_id'):
            create_label_rs = self.env['create.label.wizard'].browse(self.env.context['default_create_label_id'])
            move = create_label_rs.move_id
            move_label = False
        elif self.env.context.get('default_wo_declaration_id'):
            wo_declaration_id = self.env['wo.declaration.produce'].browse(self.env.context['default_wo_declaration_id'])
            move = wo_declaration_id.move_id
            move_label = False
        else:
            move = False
            move_label = False
            
        if move:
            product = move.product_id
            default_attributes = move.get_common_attributes(label=label)
            # Champs statiques
            res['product_id'] = product.id
            res['move_id'] = move.id
            ro_attrs = {}
            compute_attrs = {}
            unique_attrs = []
            # Champs dynamiques
            for attribute in product.get_common_attribute_ids():
                col_name = 'attr_%s'%(attribute.name)
                # Gestion des attributs uniques
                if attribute.is_unique:
                    unique_attrs.append(col_name)
                    
                if attribute.name in default_attributes.keys():
                    default_value = default_attributes[attribute.name]
                else:
                    default_value = attribute.default_value
                
                if attribute.is_quantity:
                    res['quantity_field'] = col_name
                    res[col_name] = float(default_value)
                elif attribute.type == 'float':
                    res[col_name] = float(default_value)
                else:
                    res[col_name] = default_value
                
                if attribute.is_readonly:
                    ro_attrs[col_name] = res[col_name]
                
                if attribute.function:
                    function_attribute = attribute.function.replace('attr[\'', 'attr[\'attr_')
                    if attribute.is_compute:
                        compute_attrs[col_name] = function_attribute
                    elif attribute.is_default_compute:
                        res[col_name] = self.execute_function(function_attribute, move.get_attributes_const())
            
            # Remplissage d'un champ text pour les champs qui seront en readonly (ils ne sont pas passés dans le create ensuite)
            res['all_ro_attr'] = str(ro_attrs)
            res['all_compute_attr'] = str(compute_attrs)
            if unique_attrs:
                res['all_unique_attr'] = ','.join(unique_attrs)
                
            # Remplissage du tableau des étiquettes
            if not label:
                lines = []
                for move_label in self.env.context.get('default_move_label_ids') and move_label_obj.browse(self.env.context['default_move_label_ids']) or move.move_label_ids:
                    lines.append((0, 0, {'uc_label_id': move_label.label_id.id,
                                         'uom_qty': move_label.uom_qty,
                                         'product_id': move_label.label_id.product_id.id,
                                         'move_label_id': move_label.id,
                                         'attribute_ids': move_label.label_id.attribute_ids.ids}))
                
                label_qtys = self.env.context.get('label_qtys', {}) 
                for uc_label in self.env.context.get('default_label_ids') and label_obj.browse(self.env.context['default_label_ids']) or []:
                    lines.append((0, 0, {'uc_label_id': uc_label.id,
                                         'uom_qty': label_qtys.get(uc_label.id, label_qtys.get(str(uc_label.id), 0.0)),
                                         'product_id': uc_label.product_id.id,
                                         'attribute_ids': uc_label.attribute_ids.ids}))
                
                res['line_ids'] = lines
            
        return res
    
        
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # Construction de la vue dynamique
        result = super(create_label_attribute_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        production = purchase = False
        if self.env.context.get('default_create_label_id'):
            production = False 
            purchase = True
        elif self.env.context.get('default_wo_declaration_id'):
            production = True 
            purchase = False
        elif self.env.context.get('active_model') == 'create.label.attribute.line' and self.env.context.get('active_id'):
            wiz = self.env[self.env.context['active_model']].browse(self.env.context['active_id']).wizard_id
            production = bool(wiz.wo_declaration_id) 
            purchase = bool(wiz.create_label_id)
        else:
            production = False 
            purchase = False
            
        if view_type == 'form':
            if self.env.context.get('common_product_id'):
                all_fields = result.get('fields', {})
                doc = etree.XML(result['arch'])
                nodes = doc.xpath("//group[@name='attributes']")
                if nodes:
                    product = self.env['product.product'].browse(self.env.context['common_product_id'])
                    # Champs dynamiques
                    common_attribute_ids = product.get_common_attribute_ids()
                    all_col = str([str("attr_%s"%(attribute.name)) for attribute in common_attribute_ids]).replace("'", '').replace("[", '').replace("]", '')
                    all_col_name = str({str("-attr_%s-"%(attribute.name)): str('args[%d]'%(list(common_attribute_ids).index(attribute))) for attribute in common_attribute_ids}).replace("'", '').replace("-", '"').replace(',', '$$')
                    for attribute in common_attribute_ids:
                        col_name = 'attr_%s'%(attribute.name)
                        # Float
                        if attribute.type == 'float':
                            all_fields[col_name] = {'type': 'float', 'digits': dp.get_precision("Production Precision")(self.env.cr), 'string': attribute.label, 'compute': 'test', 'inverse': 'test'}
                        # Char
                        else:
                            all_fields[col_name] = {'type': 'char', 'size': 128, 'string': attribute.label, 'compute': 'test', 'inverse': 'test'}
                         
                        display = {'name': col_name, 'colspan': '2'}
                        # Gestion des attributs (invisible, required, readonly)
                        if not attribute.is_visible or (purchase and not attribute.receipt) or (production and not attribute.production):
                            display['invisible'] = '1'
                        else:
                            if attribute.is_required or attribute.is_quantity:
                                display['required'] = '1'
                            if attribute.is_readonly:
                                display['readonly'] = '1'
                         
                        display['on_change'] = 'onchange_dynamic(\'%s\', create_label_id, move_id,  all_ro_attr, all_compute_attr, \'%s\', %s)'%(col_name, all_col_name, all_col)
                        f = etree.SubElement(nodes[0], 'field', display)
                        setup_modifiers(f, display)

                result['fields'] = all_fields
                result['arch'] = etree.tostring(doc)
             
        return result
    
    
    @api.multi
    def read(self, fields, load='_classic_read'):
        res = super(create_label_attribute_wizard, self).read(fields, load=load)
        for rec in res:
            if 'all_attr' in rec:
                for k, v in eval(rec['all_attr']).iteritems():
                    rec[k] = v
            
        return res
    
    
    @api.model
    def create(self, values):
        # Remplissage d'un champ text pour tous les attributs dynamiques
        values['all_attr'] = str({k: v for k, v in values.iteritems() if (not isinstance(v, bool) or v) and k.startswith('attr_')})
        return super(create_label_attribute_wizard, self).create(values)
    
    
    @api.multi
    def write(self, values):
        # Remplissage d'un champ text pour tous les attributs dynamiques
        all_attr = self.all_attr and eval(self.all_attr) or {}
        all_attr.update({k: v for k, v in values.iteritems() if (not isinstance(v, bool) or v) and k.startswith('attr_')})
        values['all_attr'] = all_attr
        return super(create_label_attribute_wizard, self).write(values)
    
    
    
class create_label_attribute_line(models.TransientModel):
    """ 
    Create label
    """
    _name = 'create.label.attribute.line'
    _description = 'Create label attribute line'
    _rec_name = 'wizard_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('create.label.attribute.wizard', string='Wizard', required=True, ondelete='cascade')
    uc_label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade')
    move_label_id = fields.Many2one('stock.move.label', string='Label line', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True, related='uc_label_id.product_id')
    uom_qty = fields.Float(string='UoM qty', required=False, readonly=False, digits=dp.get_precision('Product quantity'), related='move_label_id.uom_qty')
    label_uom_qty = fields.Float(string='UoM qty', required=False, readonly=True, digits=dp.get_precision('Product quantity'), related='uc_label_id.uom_qty')
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, related='uc_label_id.uom_id')
    attribute_ids = fields.One2many('common.attribute', string='Attributes', related='uc_label_id.attribute_ids')

    
    @api.multi
    def change_attributes(self):
        return {
                'name': _('Change attributes'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'create.label.attribute.wizard',
                'type': 'ir.actions.act_window',
                'context': {'common_product_id': self.product_id.id, 
                            'common_move_label_id': self.move_label_id.id,
                            'default_wo_declaration_id': self.wizard_id.wo_declaration_id.id,
                            'common_modification': True,
                            'default_move_label_id': self.move_label_id.id,
                            'default_label_id': self.uc_label_id.id,
                            'default_create_label_id': self.wizard_id.create_label_id.id},
                'target': 'stack'
            }
    
    
    @api.model
    def create(self, values):
        # Évite un bug qui supprimer les attributs avant d'essayer de les affecter à la ligne
        return super(create_label_attribute_line, self.with_context(without_unlink_attributes=True)).create(values)
    
        
        
class create_label_um_wizard(models.TransientModel):
    """ 
    Create label um
    """
    _name = 'create.label.um.wizard'
    _description = 'Create label um'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=128, required=False)
    label_template_id = fields.Many2one('stock.label.template', string='Label template', required=True, ondelete='cascade', domain=[('type', '=', 'um')])
    
    @api.multi
    def validate(self):
        for wiz in self:
            if wiz.name:
                data = {'name': wiz.name}
                
            label_rcs = self.env['stock.label'].create_um(label_template_rs=wiz.label_template_id, data=data)
            return {
                        'name': _('Label'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.label',
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'res_id': label_rcs.id,
                    }
            
        
        
    