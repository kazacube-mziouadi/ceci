# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class res_company(models.Model):
    _inherit = 'res.company'
    
    @api.one
    @api.depends('partner_id.image')
    def _compute_logo(self):
        if self.partner_id:
            self.logo = self.partner_id.image
        else:
            self.logo = False
    
    
    def _default_calendar_id(self):
        today = fields.Date.today()
        res = self.env['calendar'].search([('start_date', '<=', today), ('end_date', '>=', today)], limit=1)
        if not res:
            res = self.env['calendar'].search([], limit=1)
            
        return res
    
    @api.model
    def create(self, vals):
        if not vals.get('name', False) or vals.get('partner_id', False):
            self.cache_restart()
            return super(res_company, self).create(vals)
        
        obj_partner = self.env['res.partner']
        partner_rcs = obj_partner.create({'name': vals['name'], 
                                         'is_company':True, 
                                         'image': vals.get('logo', False),
                                         'is_customer': True,
                                         'is_supplier': True,
                                         'reference': self.env['ir.sequence'].get('res.partner'),
        
                                         })
        vals.update({'partner_id': partner_rcs.id})
        self.cache_restart()
        company_rcs = super(res_company, self).create(vals)
        partner_rcs.write({'company_id': company_rcs.id})
        return company_rcs
    
            
    logo = fields.Binary(string='Logo', compute='_compute_logo', store=True, 
                         help='This field holds the image used as avatar for this contact, limited to 1024x1024px')
    transport_calendar_id = fields.Many2one('calendar', string='Transport calendar', required=True, ondelete='restrict',
                                            default=_default_calendar_id)
    
    
    @api.multi
    def unlink(self):
        """
            On empêche la suppression de l'option si elle est utilisée dans une vente
        """
        for company in self:
            ctx = self.env.context.copy()
            ctx['delete_partner_company'] = True
            company.partner_id.with_context(ctx).unlink()
            
        res = super(res_company, self).unlink()
        return res
    
    