# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import _

import xmlrpclib

class RPCProxyOne(object):
    def __init__(self, base, ressource=False):
        self.base = base
        local_url = 'http://%s:%d/xmlrpc/common'%(base.server_id.ip_address, base.server_id.port)
        rpc = xmlrpclib.ServerProxy(local_url, allow_none=True)
        self.uid = rpc.login(base.name, base.login, base.password)
        local_url = 'http://%s:%d/xmlrpc/object'%(base.server_id.ip_address, base.server_id.port)
        self.rpc = xmlrpclib.ServerProxy(local_url, allow_none=True)
        self.ressource = ressource
    
    
    def __getattr__(self, name):
        res = lambda cr, uid, *args, **kwargs: self.rpc.execute(self.base.name, self.uid, self.base.password, self.ressource, name, *args)
        return res


class RPCProxy(object):
    def __init__(self, base):
        self.base = base

    
    def get(self, ressource):
        return RPCProxyOne(self.base, ressource)
    
class db_synchro_server(osv.osv):
    _name = 'db.synchro.server'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'ip_address': fields.char('IP address', size=64, required=True),
        'port': fields.integer('Port', size=64, required=True),
        }
    
        
class db_synchro_base(osv.osv):
    _name = 'db.synchro.base'
    _columns = {
        'server_id': fields.many2one('db.synchro.server', string='Server', required=True, ondelete='restrict'),
        'name': fields.char('Database name', size=64, required=True),
        'login': fields.char('User Name', size=50, required=True),
        'password': fields.char('Password', size=64, required=True),
        }


    def test_connection(self, cr, uid, ids, context=None):
        res = self.rpc_connection(cr, uid, ids[0], context=context)
        if res:
            if res.uid:
                raise osv.except_osv(_('OK'), _('It works.')) 
            else:
                raise osv.except_osv(_('Error'), _('Login error.')) 
                
        else:
            raise osv.except_osv(_('Error'), _('Connection error.')) 
        
        return True

    
    def rpc_connection(self, cr, uid, base, context=None):
        if isinstance(base, int):
            base = self.browse(cr, uid, base, context=context)
        
        try:
            res = RPCProxyOne(base)
        except:
            res = False
        
        return res
    
    
    def name_get(self, cr, uid, ids, context=None):
        if ids:
            res = []
            for base in self.browse(cr, uid, ids, context=context):
                name = base.name
                if base.server_id:
                    name = '%s - %s'%(base.server_id.name, name)
                    
                res.append((base.id, name))
        else:
            res = []
            
        return res
    