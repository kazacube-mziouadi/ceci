# -*- coding: utf-8 -*-
from openerp import http
import simplejson
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO
from collections import deque
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HighStock(http.Controller):

    @http.route('/web_highstock/get_data', type='json', auth="user")
    def get_data(self, req, model=None, id=None, fields=None):
        obj = request.session.model(model)
        orderpoint_obj = request.session.model('stock.warehouse.orderpoint')
        e_fields = eval(fields)
        read = obj.read([id], e_fields)
         
        min_qty = 0.0
        return ('subtitle', min_qty)
#         # on recherche les règles de stock minimum et on prend la premiere
#         orderpoints = orderpoint_obj.search_read([('product_id', '=', id),('active', '=', True)], ['limit_min_manual','limit_min_computed','limit_min_type'])
#         if orderpoints:
#             if orderpoints[0]['limit_min_type'] == 'manual':
#                 min_qty = orderpoints[0]['limit_min_manual']
#  
#             else:
#                 min_qty = orderpoints[0]['limit_min_computed']
#          
#         min_qty = round(min_qty, 2)
#          
#         if read:
#             res = []
#             for f in e_fields:
#                 if read[0].get(f, False):
#                     if isinstance(read[0][f], tuple):
#                         res.append(read[0][f][1])
#                     else:
#                         res.append(read[0][f])
#                  
#             return (' --- '.join(res), min_qty)
#          
#         else:
#             return ("", min_qty)
    
    @http.route('/web_highstock/convert_uom', type='json', auth="user")
    def convert_uom(self, req, model=None, evts=None):
        obj = request.session.model(model)
        uom_obj = request.session.model('product.uom')
        product_obj = request.session.model('product.product')
        
        for evt in evts:
            #Si le move est non done et se trouve dans le passé, on le met à la date du jour + 1
            now = datetime.now()
            now_str = datetime.strftime(now, '%Y-%m-%d %H:%M:%S')
            if evt['state'] != 'done' and evt['date'] < now_str:
                date = datetime.strftime(now + relativedelta(days=1), '%Y-%m-%d %H:%M:%S')
                evt['date'] = date
                
            move_uom_id = evt['uom_id'][0]
            product_uom_id = product_obj.read([evt['product_id'][0]], ['uom_id'])[0]['uom_id'][0]
            if move_uom_id != product_uom_id:
                qty = uom_obj.compute_qty(move_uom_id, evt['uom_qty'], to_uom_id=product_uom_id)
            else:
                qty = evt['uom_qty']
             
            evt['uom_qty'] = qty
         
        return evts
        
        return True
    
#     _cp_path = '/web/highstock'
#     @openerpweb.jsonrequest
#     def get_data(self, request, model=None, id=None, fields=None):
#         obj = request.session.model(model)
#         orderpoint_obj = request.session.model('stock.warehouse.orderpoint')
#         context = request.context
#         registry = RegistryManager.get(request.session._db)
#         e_fields = eval(fields)
#         read = obj.read([id], e_fields)
#         
#         min_qty = 0.0
#         # on recherche les règles de stock minimum et on prend la premiere
#         orderpoints = orderpoint_obj.search_read([('product_id', '=', id),('active', '=', True)], ['limit_min_manual','limit_min_computed','limit_min_type'])
#         if orderpoints:
#             if orderpoints[0]['limit_min_type'] == 'manual':
#                 min_qty = orderpoints[0]['limit_min_manual']
# 
#             else:
#                 min_qty = orderpoints[0]['limit_min_computed']
#         
#         min_qty = round(min_qty, 2)
#         
#         if read:
#             res = []
#             for f in e_fields:
#                 if read[0].get(f, False):
#                     if isinstance(read[0][f], tuple):
#                         res.append(read[0][f][1])
#                     else:
#                         res.append(read[0][f])
#                 
#             return (' --- '.join(res), min_qty)
#         
#         else:
#             return ("", min_qty)
        
    
#     @openerpweb.jsonrequest
#     def convert_uom(self, request, model=None, evts=None):
#         obj = request.session.model(model)
#         uom_obj = request.session.model('product.uom')
#         product_obj = request.session.model('product.product')
#         
#         for evt in evts:
#             move_uom_id = evt['product_uom'][0]
#             product_uom_id = product_obj.read([evt['product_id'][0]], ['uom_id'])[0]['uom_id'][0]
#             if move_uom_id != product_uom_id:
#                 qty = uom_obj.compute_qty(move_uom_id, evt['product_qty'], to_uom_id=product_uom_id)
#             else:
#                 qty = evt['product_qty']
#             
#             evt['product_qty'] = qty
#         
#         return evts


