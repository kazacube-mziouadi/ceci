# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class communication_rectification(models.TransientModel):
    _name = 'communication.rectification'
    
    @api.multi
    def go(self):
        """
            Fonction permettant de créer des enregistrements de communication en fonction des données des partenaires
            A utiliser juste après l'installation de multi_communications
        """
        multi_com = self.env['ir.module.module'].search([('name', '=', 'multi_communications')], limit=1)
        if multi_com and multi_com.state == 'installed':
            communication_obj = self.env['multi.communication']
            communication_type_obj = self.env['multi.communication.type']
            partner_obj = self.env['res.partner']
            #On récupère les types de communication
            phone_type = communication_type_obj.search([('type', '=', 'phone')], limit=1)
            mobile_type = communication_type_obj.search([('type', '=', 'mobile')], limit=1)
            fax_type = communication_type_obj.search([('type', '=', 'fax')], limit=1)
            email_type = communication_type_obj.search([('type', '=', 'email')], limit=1)
            #Pour chaque partner, on récupère les valeurs des communications et on crée la ligne correspondante
            for partner in partner_obj.search():
                vals_phone = {}
                vals_mobile = {}
                vals_fax = {}
                vals_email = {}
                #Téléphone
                if partner.phone and phone_type:
                    phone = partner.phone
                    if phone[0] == '+':
                        phone_int = phone[1:3]
                        phone_ind = phone[3]
                        phone_num = phone[4:]
                    else:
                        phone_int = '33'
                        phone_ind = phone[1]
                        phone_num = phone[2:]
                    
                    try:
                        phone_int = int(phone_int)
                        phone_ind = int(phone_ind)
                    except ValueError:
                        phone_int = 0
                        phone_ind = 0
                    
                    vals_phone = {
                                  'name': 'Phone',
                                  'sequence': 1,
                                  'partner_id': partner.id,
                                  'communication_type_id': phone_type.id,
                                  'type': 'phone',
                                  'international': phone_int,
                                  'indicative': phone_ind,
                                  'number': phone_num,
                                  }
                
                #Portable
                if partner.mobile and mobile_type:
                    mobile = partner.mobile
                    if mobile[0] == '+':
                        mobile_int = int(mobile[1:3])
                        mobile_ind = mobile[3]
                        mobile_num = mobile[4:]
                    else:
                        mobile_int = '33'
                        mobile_ind = mobile[1]
                        mobile_num = mobile[2:]
                    
                    try:
                        phone_int = int(phone_int)
                        phone_ind = int(phone_ind)
                    except ValueError:
                        phone_int = 0
                        phone_ind = 0
                          
                    vals_mobile = {
                                  'name': 'Mobile',
                                  'sequence': 1,
                                  'partner_id': partner.id,
                                  'communication_type_id': mobile_type.id,
                                  'type': 'mobile',
                                  'international': mobile_int,
                                  'indicative': mobile_ind,
                                  'number': mobile_num,
                                  }
                
                #Fax
                if partner.fax and fax_type:
                    fax = partner.fax
                    vals_fax = {
                                  'name': 'Fax',
                                  'sequence': 1,
                                  'partner_id': partner.id,
                                  'communication_type_id': fax_type.id,
                                  'type': 'fax',
                                  'value': fax,
                                  }
                
                #Email
                if partner.email and email_type:
                    email = partner.email
                    vals_email = {
                                  'name': 'Email',
                                  'sequence': 1,
                                  'partner_id': partner.id,
                                  'communication_type_id': email_type.id,
                                  'type': 'email',
                                  'value': email,
                                  }
                
                if vals_phone:
                    communication_obj.create(vals_phone)
                if vals_mobile:
                    communication_obj.create(vals_mobile)
                if vals_fax:
                    communication_obj.create(vals_fax)
                if vals_email:
                    communication_obj.create(vals_email)
        
        return {'type': 'ir.actions.act_window_close'}
    
