# -*- coding: utf-8 -*-


from openerp.osv import orm


class IrModelFields(orm.Model):
    _inherit = 'ir.model.fields'

#     def search(
#             self, cr, uid, args, offset=0, limit=0, order=None, context=None,
#             count=False):
#         model_domain = []
#         for domain in args:
#             if (len(domain) > 2 and
#                     domain[0] == 'model_id' and
#                     isinstance(domain[2], basestring)):
#                 model_domain += [
#                     ('model_id', 'in', map(int, domain[2][1:-1].split(',')))
#                 ]
#             else:
#                 model_domain.append(domain)
#         return super(IrModelFields, self).search(
#             cr, uid, model_domain, offset=offset, limit=limit, order=order,
#             context=context, count=count
#         )
