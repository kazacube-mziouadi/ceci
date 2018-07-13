'''
Created on 10 april 2017

@author: barnabas
'''

from openerp import http
import requests
import cookielib
from base64 import b64encode
from os import urandom
from  openerp.addons.web.controllers import main 
from openerp.http import request
from penapi.pentaho import (
    Pentaho,
    PentahoBasicAuth
)
import logging
_logger = logging.getLogger(__name__)


class BI(http.Controller):
    
    @http.route('/bi/connect', type='http')
    def connect(self): 
        session = requests.Session()
        if http.request.env.user.login == 'admin' :
            options = {'j_password':http.request.env.user.password_pentaho,'j_username': http.request.env.user.login }
            pentaho_server = http.request.env['bi.server'].sudo().search([('id','=',1)])
        else :
            options = {'j_password':http.request.env.user.password_pentaho,'j_username': http.request.env.user.login + http.request.env.cr.dbname }
            pentaho_server = http.request.env['bi.server'].sudo().search([('id','=',1)])       
        try :  
            r = session.post(pentaho_server.pentaho_server_address+'pentaho/j_spring_security_check', data=options)
            print "check 2"
            if r.status_code == 200:
                print "if 200"
                if '<title>User Console Pentaho</title>' in r.text:
                    headers = {
                            'Status': 200 ,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate',
                            'Set-Cookie' : 'JSESSIONID='+session.cookies['JSESSIONID']+'; Path=/pentaho',
                            'Location': '/web'
                    }
                    content = '<meta http-equiv="refresh" content="0; url='+pentaho_server.pentaho_server_address+'pentaho/" />'
                    return  http.request.make_response(content, headers=headers )
        except : 
            _logger.error("Pentaho server is not running")    
        return #http.request.make_response('<meta http-equiv="refresh" content="0; url="/web" />')   



class Home(main.Home):
       
    @http.route()
    def web_login(self, redirect=None, **kw):
        response = super(Home, self).web_login(redirect = redirect, **kw)
        if request.httprequest.method == 'POST':
            session = requests.Session()
            if request.params['login_success'] == True:
                user = http.request.env['res.users'].search([('login','=',request.params['login'])])
#si l'utilisateur dispose d'un compte pentaho
                if not user.password_pentaho :
                    #creation de l utilisateur
                    try :
                        server_pentaho = http.request.env['bi.server'].sudo().search([('id', '=', 1)] )
                        adresse_pentaho = server_pentaho.pentaho_server_address
                        pentaho = Pentaho(pentaho_base_url= adresse_pentaho + '/pentaho')
                        new_admin = False

                        pentaho.set_auth_method(PentahoBasicAuth('admin', 'password' ))
                        if user.login == "admin" :
                            user.sudo().write(  {'password_pentaho' : 'password' })
                        else :          
                            random_bytes = urandom(128)
                            password = b64encode(random_bytes).decode('utf-8')
                            user.sudo().write(  {'password_pentaho' : password })
                            res = pentaho.users.create(username=user.login + user.env.cr.dbname,password=password)
                    except : 
                        _logger.error("Pentaho server is not running")
                
                pentaho_server = http.request.env['bi.server'].sudo().search([('id','=',1)])
                if user.login == 'admin' :
                    options = {'j_password':user.password_pentaho,'j_username':user.login }
                else :   
                    options = {'j_password':user.password_pentaho,'j_username':user.login + user.env.cr.dbname  }
                try: 
                    r = session.post(pentaho_server.pentaho_server_address+'pentaho/j_spring_security_check', data=options)
                    if r.status_code == 200:
                        if '<title>User Console Pentaho</title>' in r.text:
                            headers = {
                                    'Status': 200 ,
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Language': 'en-US,en;q=0.5',
                                    'Accept-Encoding': 'gzip, deflate',
                                    'Set-Cookie' : 'JSESSIONID='+session.cookies['JSESSIONID']+'; Path=/pentaho',
                                    'Location': '/web'
                            }
                            content = '<meta http-equiv="refresh" content="0; url=/web" />'
                            _logger.info("Connection to pentaho server established")
                            return  http.request.make_response(content, headers=headers )
                except :  
                    _logger.error("Pentaho server is not running")
        return response
