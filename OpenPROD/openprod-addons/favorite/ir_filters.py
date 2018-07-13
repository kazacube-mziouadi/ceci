# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import exceptions
from openerp.osv import osv
from openerp import models, api, fields
from openerp.tools.translate import _

class ir_filters(models.Model):
    _inherit = 'ir.filters'

    #vaut vrai si le filtre est dans les favoris
    favorite = fields.Boolean(string='Favorite', default=False)

    def create_or_replace_favorite(self, cr, uid, vals, context=None):
        lower_name = vals['name'].lower()
        vals['favorite'] = True
        action_id = vals.get('action_id')
        current_filters = self.get_favorite(cr, uid, vals['model_id'], action_id)
        matching_filters = [f for f in current_filters
                                if f['name'].lower() == lower_name
                                # next line looks for matching user_ids (specific or global), i.e.
                                # f.user_id is False and vals.user_id is False or missing,
                                # or f.user_id.id == vals.user_id
                                if (f['user_id'] and f['user_id'][0]) == vals.get('user_id', False)]

        if vals.get('is_default'):
            if vals.get('user_id'):
                # Setting new default: any other default that belongs to the user
                # should be turned off
                action_domain = self._get_action_domain(cr, uid, action_id)
                act_ids = self.search(cr, uid, action_domain + [
                        ('model_id', '=', vals['model_id']),
                        ('user_id', '=', vals['user_id']),
                        ('is_default', '=', True),
                    ], context=context)
                if act_ids:
                    self.write(cr, uid, act_ids, {'is_default': False}, context=context)
            else:
                self._check_global_default(
                    cr, uid, vals, matching_filters, context=None)

        # When a filter exists for the same (name, model, user) triple, we simply
        # replace its definition (considering action_id irrelevant here)
        if matching_filters:
            self.write(cr, uid, matching_filters[0]['id'], vals, context)
            return matching_filters[0]['id']

        return self.create(cr, uid, vals, context)

    def get_filters(self, cr, uid, model, action_id=None, context=None):
        """Obtain the list of filters available for the user on the given model excluding favorites.

        :param action_id: optional ID of action to restrict filters to this action
            plus global filters. If missing only global filters are returned.
            The action does not have to correspond to the model, it may only be
            a contextual action.
        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_id`` (m2o tuple),
            ``action_id`` (m2o tuple) and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        context = self.pool['res.users'].context_get(cr, uid)
        action_domain = self._get_action_domain(cr, uid, action_id)
        filter_ids = self.search(cr, uid, action_domain +
            [('model_id','=',model),('user_id','in',[uid, False]),('favorite','=',False)])
        my_filters = self.read(cr, uid, filter_ids,
            ['name', 'is_default', 'domain', 'context', 'user_id', 'sort'], context=context)
        return my_filters

    
    def get_favorite(self, cr, uid, model, action_id=None, context=None):
        """Obtain the list of filters available for the user on the given model excluding favorites.

        :param action_id: optional ID of action to restrict filters to this action
            plus global filters. If missing only global filters are returned.
            The action does not have to correspond to the model, it may only be
            a contextual action.
        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_id`` (m2o tuple),
            ``action_id`` (m2o tuple) and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL),
        # and filters for the action (action_id=action_id) or global (action_id=NULL)
        context = self.pool['res.users'].context_get(cr, uid)
        action_domain = self._get_action_domain(cr, uid, action_id)
        filter_ids = self.search(cr, uid, action_domain +
            [('model_id','=',model),('user_id','in',[uid, False]),('favorite','=',True)])
        my_filters = self.read(cr, uid, filter_ids,
            ['name', 'is_default', 'domain', 'context', 'user_id', 'sort'], context=context)
        return my_filters

