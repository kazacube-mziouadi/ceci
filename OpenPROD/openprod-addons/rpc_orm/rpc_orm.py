from openerp.osv import osv


def osv_search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=None):
    if 'active' in self._columns:
        if args:
            args.extend(['|', ('active', '=', False), ('active', '=', True)])
        else:
            args = ['|', ('active', '=', False), ('active', '=', True)]
        
    return osv.osv.search(self, cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
    
osv.osv.osv_search = osv_search