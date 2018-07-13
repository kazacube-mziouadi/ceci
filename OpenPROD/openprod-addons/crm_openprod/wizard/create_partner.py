# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view


class create_new_crm_partner(models.TransientModel):
    """ 
        Wizard to create new partner from an opportunity
    """
    _name = 'create.new.crm.partner'
    _description = 'Wizard to create new partner from an opportunity'
    
    def _default_calendar_id(self):
        today = fields.Date.today()
        res = self.env['calendar'].search([('start_date', '<=', today), ('end_date', '>=', today)], limit=1)
        if not res:
            res = self.env['calendar'].search([], limit=1)
            
        return res
    
    @api.model
    def _invoicing_trigger_get(self):
        return [
                ('picking', _('To the delivery')),
                ('manual', _('On demand')),
                ('postpaid', _('On the order')),
                       ]
    
    @api.model
    def _invoiced_on_get(self):
        return [
                ('order', _('Ordered quantities')),
                ('delivery', _('Delivered quantities')),
                       ]
    
    
    @api.model
    def _invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
    
    @api.model
    def _lang_get(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Customer name', required=False)
    calendar_id = fields.Many2one('calendar', string='Calendar', required=False, ondelete='cascade', default=_default_calendar_id,
                                   help='The calendar specify the work days, holidays... of the partner. It\'s used in most of date calculation')
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='cascade', 
                                  default=lambda self: self.env.ref('base.EUR'))
    lang = fields.Selection('_lang_get', string='Lang', default=lambda self: self.env.user.lang, required=True)
    street = fields.Char(string='Street', size=128, required=False)
    street2 = fields.Char(string='Street 2', size=128, required=False)
    street3 = fields.Char(string='Street 3', size=128, required=False)
    zip = fields.Char(string='Zip', size=24, required=False)
    city = fields.Char(string='City', size=128, required=False)
    region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='cascade')
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='cascade')
    phone = fields.Char(string='Phone', size=20, required=False)
    email = fields.Char(string='Email', size=128, required=False)
    salesman_id = fields.Many2one('res.users', string='Salesman', required=True, ondelete='cascade')
    b2c_crm = fields.Boolean(string='B2C', default=False)
    
    @api.model
    def default_get(self, fields_list):
        res = super(create_new_crm_partner, self).default_get(fields_list=fields_list)
        crm_id = self.env.context.get('active_id')
        if crm_id:
            crm = self.env['crm'].browse(crm_id)
            res2 = {'name': crm.customer_name,
                    'street': crm.street,
                    'street2': crm.street2,
                    'street3': crm.street3,
                    'zip': crm.zip,
                    'city': crm.city,
                    'region_id': crm.region_id and crm.region_id.id or False,
                    'country_id': crm.country_id.id,
                    'phone': crm.phone,
                    'email': crm.email,
                    'salesman_id': crm.salesman_id.id,
                    'currency_id': crm.currency_id.id,
                    'b2c_crm': crm.b2c_flag}
            res.update(res2)
            
        return res
    
    
    @api.multi
    def create_new_partner(self):
        """
            Fonction permettant de créer un nouveau partenaire
        """
        context = self.env.context
        if context.get('active_id', False):
            crm = self.env['crm'].browse(context['active_id'])
            if crm:
                company = False
                partner_data = {
                                'lang': self.lang,
                                'can_order': True,
                                'can_be_delivered': True,
                                'can_be_charged': True,
                                'can_paid': True,
                                'name': self.name,
                                'state': 'prospect',
                                'phone': self.phone,
                                'email': self.email,
                                'address': {'name': self.name,
                                            'street': self.street,
                                            'street2': self.street2,
                                            'street3': self.street3,
                                            'zip': self.zip,
                                            'city': self.city,
                                            'region_id': self.region_id and self.region_id.id or False,
                                            'country_id': self.country_id.id,
                                            },
                                'country_id': self.country_id.id,
                                }
                if not crm.b2c_flag:
                    company = True
                    partner_data2 = {
                                    'calendar_id': self.calendar_id.id,
                                    'currency_id': self.currency_id.id,
                                    'name': self.name,
                                    'state': 'prospect',
                                    'corporate_name': self.name,
                                    'seller_id': self.salesman_id.id,
                                    }
                    partner_data.update(partner_data2)
                    
                new_partner = self.env['res.partner'].create_partner(company, ['customer'], partner_data)
                crm.customer_id = new_partner and new_partner.id or False
                crm._onchange_customer_id()
                if new_partner:
                    action_dict = get_form_view(self, 'partner_openprod.partner_openprod_see_form')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()
                        action_struc[0]['res_id'] = new_partner.id
                        action_struc = action_struc[0]
                          
                    return action_struc
                else:
                    return  {'type': 'ir.actions.act_window_close'}
        else:
            return  {'type': 'ir.actions.act_window_close'}