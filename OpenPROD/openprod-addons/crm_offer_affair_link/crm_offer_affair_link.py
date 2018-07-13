# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view, myhtmlparser
from openerp.addons.base_openprod import utils
    
    
class crm_state(models.Model):
    """ 
        States for customer relationship management 
    """
    
    _inherit = 'crm.state'
    def _auto_init(self, cursor, context=None):
        """
            Un seul enregistrement avec is_offer_creation_state
        """
        res = super(crm_state, self)._auto_init(cursor, context=context)
        cursor.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'only_one_is_offer_creation_state\'')
        if not cursor.fetchone():
            cursor.execute('CREATE UNIQUE INDEX only_one_is_offer_creation_state ON crm_state (is_offer_creation_state) WHERE is_offer_creation_state')
             
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_offer_creation_state = fields.Boolean(default=False, help='State in which the record will pass when an offer will be created')


    
class crm(models.Model):
    _inherit = 'crm'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Historique
    specific_offer_ids = fields.One2many('specific.offer', 'crm_id',  string='Specific offers')
    
    
    @api.multi
    def create_new_offer(self):
        """
            Fonction qui permet de créer une offre à partir d'une opportunité
        """
        spec_offer_obj = self.env['specific.offer']
        state = self.env['crm.state'].search([('is_offer_creation_state', '=', True)], limit=1)
        for crm in self:
            description = ''
            if crm.description:
                parser = myhtmlparser()
                parser.feed(crm.description)
                data = parser.HTMLDATA
                parser.clean()
                for text in data:
                    description += text + ' '
                    
            new_offer = spec_offer_obj.create({'name': crm.name,
                                               'description': description,
                                               'partner_id': crm.customer_id.id,
                                               'crm_id': crm.id})
            if new_offer and state:
                crm.write({'state_id': state.id})
                action_dict = get_form_view(self, 'specific_offer.act_specific_offer_view_only_form')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['res_id'] = new_offer.id
                    action_struc = action_struc[0]
                    return action_struc



class specific_offer(models.Model):
    _inherit = 'specific.offer'
     
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='restrict')
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')
     
    @api.multi
    def create_affair_from_offer(self):
        """
            Fonction qui permet de créer une affaire à partir d'une offre
        """
        affair_obj = self.env['affair']
        for offer in self:
            if offer.partner_id:
                if not offer.partner_id.seller_id:
                    raise ValidationError(_('There is no seller for this customer, please choose a seller '
                                          'in the customer details'))
                     
                vals = {'customer_id': offer.partner_id.id,
                        'responsible_id': offer.partner_id.seller_id.id,
                        'description': offer.description}
                new_affair = affair_obj.create(vals)
                offer.write({'affair_id': new_affair.id})
            else:
                raise ValidationError(_('You need to select a partner to create an affair'))
                 
            return True
    
    
    def add_product_line_values(self, offer):
        """
            Surcharge de la fonction de l'offre spécific afin d'ajouter
        """
        values = {}
        if offer.affair_id:
            values['affair_id'] = offer.affair_id.id
            
        return values