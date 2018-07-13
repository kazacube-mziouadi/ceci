# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from base64 import b64encode
from os import urandom
from openerp import http
from penapi.pentaho import (
    Pentaho,
    PentahoBasicAuth
)
import requests
import cookielib

class res_users(models.Model):
    _inherit = 'res.users'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    password_pentaho = fields.Char( string='Password pentaho', required=False)
    @api.model
    def create(self, vals):
        random_bytes = urandom(128)
        password = b64encode(random_bytes).decode('utf-8')
        vals['password_pentaho'] = password
        server_pentaho = self.env['bi.server'].search([('id', '=', 1)])
        adresse_pentaho = server_pentaho.pentaho_server_address
        pentaho = Pentaho(pentaho_base_url=adresse_pentaho + '/pentaho')
        admin = self.env['res.users'].sudo().search([('login', '=', 'admin')] )
        admin_password = admin.password_pentaho
        try:
            pentaho.set_auth_method(PentahoBasicAuth('admin', admin_password))
            res = pentaho.users.create(username=vals['login']+admin.env.cr.dbname,password=password)
        except :
            print "Pentaho is not running"
        return super(res_users, self).create(vals)