# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID, api, models
from openerp.exceptions import MissingError
from openerp.osv import expression
import logging
_logger = logging.getLogger(__name__)
@api.cr_uid_context
def search_group(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, fields=False, groupby=False, sum=False, return_dict=False, without_order=False, min=False, max=False):
    """ search_group(args[, offset=0][, limit=None][, order=None][, count=False])

    Searches for records based on the ``args``
    :ref:`search domain <reference/orm/domains>`.

    :param args: :ref:`A search domain <reference/orm/domains>`. Use an empty
                 list to match all records.
    :param int offset: number of results to ignore (default: none)
    :param int limit: maximum number of records to return (default: all)
    :param str order: sort string
    :param bool count: if ``True``, the call should return the number of
                       records matching ``args`` rather than the records
                       themselves.
    :returns: at most ``limit`` records matching the search criteria

    :raise AccessError: * if user tries to bypass access rules for read on the requested object.
    """
    return self._search_group(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count, fields=fields, groupby=groupby, sum=sum, return_dict=return_dict, without_order=without_order, min=min, max=max)


def _search_group(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, fields=False, groupby=False, sum=False, return_dict=False, without_order=False, min=False, max=False, access_rights_uid=None):
    """
    Private implementation of _search_group() method, allowing specifying the uid to use for the access right check.
    This is useful for example when filling in the selection list for a drop-down and avoiding access rights errors,
    by specifying ``access_rights_uid=1`` to bypass access rights check, but not ir.rules!
    This is ok at the security level because this method is private and not callable through XML-RPC.

    :param access_rights_uid: optional user ID to use when checking access rights
                              (not for ir.rules, this is only for ir.model.access)
    """
    if context is None:
        context = {}
    self.check_access_rights(cr, access_rights_uid or user, 'read')

    # For transient models, restrict acces to the current user, except for the super-user
    if self.is_transient() and self._log_access and user != SUPERUSER_ID:
        args = expression.AND(([('create_uid', '=', user)], args or []))

    query = self._where_calc(cr, user, args, context=context)
    self._apply_ir_rules(cr, user, query, 'read', context=context)
    if groupby:
        order_by = order and self._generate_order_by(order, query) or ''
    else:
        if without_order:
            order_by = ''
        else:
            order_by = self._generate_order_by(order, query)
    
    from_clause, where_clause, where_clause_params = query.get_sql()

    where_str = where_clause and (" WHERE %s" % where_clause) or ''

    if count:
        # Ignore order, limit and offset when just counting, they don't make sense and could
        # hurt performance
        query_str = 'SELECT count(1) FROM ' + from_clause + where_str
        cr.execute(query_str, where_clause_params)
        res = cr.fetchone()
        return res[0]
    
    limit_str = limit and ' limit %d' % limit or ''
    offset_str = offset and ' offset %d' % offset or ''
    groupby_str = groupby and ' group by %s' %(', '.join(groupby)) or ''
    select_clause = ', '.join([sum and f in sum and 'SUM("%s".%s) AS %s'%(self._table, f, f) or \
                               min and f in min and 'MIN("%s".%s) AS %s'%(self._table, f, f) or \
                               max and f in max and 'MAX("%s".%s) AS %s'%(self._table, f, f) or \
                               '"%s".%s'%(self._table, f) for f in fields])
    query_str = 'SELECT %s FROM ' % select_clause + from_clause + where_str + groupby_str + order_by + limit_str + offset_str
    cr.execute(query_str, where_clause_params)
    if return_dict:
        return cr.dictfetchall()
    
    res = cr.fetchall()
    # TDE note: with auto_join, we could have several lines about the same result
    # i.e. a lead with several unread messages; we uniquify the result using
    # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
    def _uniquify_list(seq):
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]

    return _uniquify_list([x[0] for x in res])


models.BaseModel.search_group = search_group
models.BaseModel._search_group = _search_group


@api.v7
def read_light(self, cr, user, ids, fields=None, context=None):
    records = self.browse(cr, user, ids, context)
    result = models.BaseModel.read(records, fields)
    return result if isinstance(ids, list) else (bool(result) and result[0])

@api.v8
def read_light(self, fields=None):
    """ read_light(fields)

    Read light to avoid performance issues
    """
    # check access rights
    self.check_access_rights('read')
    fields = self.check_field_access_rights('read', fields)
    fields.append('id')
    fields = set(fields)
    select_clause = ', '.join(['"%s".%s'%(self._table, f) for f in fields])
    query = 'SELECT %s FROM %s '%(select_clause, self._table) + 'WHERE id IN %s'
    self.env.cr.execute(query, (tuple(self.ids, ), ))
    return self.env.cr.dictfetchall()


models.BaseModel.read_light = read_light