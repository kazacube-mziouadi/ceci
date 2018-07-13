# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class address(models.Model):
    _inherit = 'address'
    
    
    def _auto_init(self, cursor, context=None):
        """
            On passe les adresses principales en type 'principal'
        """
        res = super(address, self)._auto_init(cursor, context=context)
        cursor.execute('UPDATE address SET address_type=( CASE '
                            'WHEN id in (SELECT address_id FROM res_partner WHERE'
                            ' address_id IS NOT Null) THEN \'principal\''
                            'ELSE \'secondary\''
                        'END)')
        
        return res

    
    @api.model
    def default_get(self, fields_list):
        res = super(address, self).default_get(fields_list=fields_list)
        is_company = self.env.context.get('is_company')
        name = self.env.context.get('default_name')
        first_name = self.env.context.get('first_name')
        if not is_company:
            res['name'] = '%s %s'%(name or '', first_name or '')
        elif name:
            res['name'] = name
            
        return res
    
    
    @api.model
    def _address_type_get(self):
        return [
                ('principal', _('Principal')),
                ('secondary', _('Secondary')),
                       ]
    
    
    @api.multi
    @api.depends('name', 'address_type')
    def name_get(self):
        result = []
        for address in self:
            name = '[%s]'%(address.sequence)
            if address.name and address.address_type:
                name = '%s %s (%s)'%(name, address.name, address.address_type)
            else:    
                name = '%s %s'%(name, address.name)
                 
            result.append((address.id, name))
             
        return result
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(string='Sequence', default=0, required=True, help="Used in the name. Allow you to easily identify the address.")
    address_type = fields.Selection('_address_type_get', string='Type', required=True, default='secondary')
    partner_address_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade', compute=False)
    
    
    
class res_partner(models.Model):
    _inherit = 'res.partner'
    
    def _auto_init(self, cursor, context=None):
        """
            On rempli les adresses des contacts liés aux partenaires
        """
        res = super(res_partner, self)._auto_init(cursor, context=context)
        
        cursor.execute('UPDATE res_partner SET parent_address_id=(SELECT '
                       'partner.address_id FROM res_partner partner WHERE partner.id=(res_partner.parent_id)), '
                       'address_id=(SELECT partner.address_id FROM res_partner partner WHERE partner.id=(res_partner.parent_id)) '
                       'WHERE is_company=False AND company_address=True')
                
        return res
    
    @api.one
    @api.depends('address_ids', 'company_address', 'parent_id')
    def _compute_address_id(self):
        #Fonction permettant de récupérer l'adresse principale
        if not self.is_company:
            if self.company_address:
                if self.parent_id and self.parent_address_id:
                    self.address_id = self.parent_address_id.id
                else:
                    self.address_id = self.env['address']
                    
        if self.is_company or not self.company_address:
            if not self.address_ids:
                self.address_id = False
            else:
                for address in self.address_ids:
                    if address.address_type == 'principal':
                        self.address_id = address.id
                        break
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    address_id = fields.Many2one('address', string='Address', required=False, ondelete='set null', compute='_compute_address_id', store=True)
    address_ids = fields.One2many('address', 'partner_address_id',  string='Address')
    parent_address_id = fields.Many2one('address', string='Address', required=False, ondelete='set null')
    
    @api.one
    @api.constrains('address_ids')
    def _check_unique_principal(self):
        #Permet de vérifier que le partenaire dispose d'une seule adresse de type "principale"
        count = 0
        if self.is_company or not self.company_address:
            for address in self.address_ids:
                if address.address_type == 'principal':
                    count += 1
        else:
            if self.parent_address_id:
                count = 1
        
        if count > 1:
            raise Warning(_('Error ! You can\'t have more than one principal address for a partner.'))
        elif count <= 0 :
            raise Warning(_('Error ! You need a principal address for the partner.'))
            
    
    @api.onchange('corporate_name')
    def _onchange_corporate_name(self):
        """
            Pour les entreprises, lorsqu'on change le corporate name, on va venir changer le nom de l'adresse
        """
        if not self.company_address and self.is_company:
            for address in self.address_ids:
                address.name = self.corporate_name
            
    
    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        """
            Pour les contacts, lorsqu'on change la société liée, on vide le champ d'adresse sélectionnée
        """
        if not self.is_company:
            self.parent_address_id = False
                
                
    @api.model
    def create(self, vals):
        """
            On modifie le context pour ne pas surcharger le create dans res_partner
            et on passe une valeur au pays (pays de la société de l'utilisateur)
        """
        context2 = {'multi_address': True}
        context2.update(self.env.context)
        if not vals.get('country_id'):
            company = self.env.user.company_id
            partner = company and company.partner_id or False
            country = partner and partner.country_id or False
            vals['country_id'] = country and country.id or False
            
        return super(res_partner, self.with_context(context2)).create(vals=vals)
    
    
                
