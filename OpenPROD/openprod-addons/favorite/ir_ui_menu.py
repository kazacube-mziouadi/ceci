# -*- coding: utf-8 -*-

from openerp import exceptions, tools
from openerp.osv import osv
from openerp import models, api, fields
from openerp.tools.translate import _
import operator

class ir_ui_menu(models.Model):
    _inherit = 'ir.ui.menu'

    # le menu correspondant à l'utilisateur
    user_id = fields.Many2one('res.users', ondelete="cascade")
    filter_id = fields.Many2one('ir.filters')

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        # retrieve all menus, and determine which ones are visible
        context = {'ir.ui.menu.full_list': True}
        menus = self.with_context(context).search([])

        groups = self.env.user.groups_id
        # first discard all menus with groups the user does not have
        menus = menus.filtered(
            lambda menu: not menu.groups_id or menu.groups_id & groups)

        # on enlève les favoris qui n'appartiennent pas à l'utilisateur
        favorite_parent = menus.filtered(lambda r: r.name == 'Favorite')
        favorite_conf = menus.filtered(lambda r: r.name == 'Configuration' and r.parent_id == favorite_parent)
        favorite_list = menus.filtered(lambda r: r.name == 'My Favorites' and r.parent_id == favorite_parent)
        list_favorite = menus.filtered(lambda r: r.parent_id ==  favorite_list and r.name != 'Configuration of my favorites' )
        list_favorite_current_user = menus.filtered(lambda r: r.parent_id == favorite_list and r.user_id == self.env.user and r.name != 'Configuration of my favorites')
        list_favorite = list_favorite - list_favorite_current_user
        menus = menus - list_favorite

        # take apart menus that have an action
        action_menus = menus.filtered(lambda m: m.action and m.action.exists())
        folder_menus = menus - action_menus
        visible = self.browse()

        # process action menus, check whether their action is allowed
        access = self.env['ir.model.access']
        model_fname = {
            'ir.actions.act_window': 'res_model',
            'ir.actions.report.xml': 'model',
            'ir.actions.server': 'model_id',
        }
        for menu in action_menus:
            fname = model_fname.get(menu.action._name)
            if not fname or not menu.action[fname] or \
                    access.check(menu.action[fname], 'read', False):
                # make menu visible, and its folder ancestors, too
                visible += menu
                menu = menu.parent_id
                while menu and menu in folder_menus and menu not in visible:
                    visible += menu
                    menu = menu.parent_id

        return set(visible.ids)

    #Ajout du filtre lors du chargement de la vue depuis un menu
    @api.cr_uid_context
    @tools.ormcache_context('uid', 'debug', keys=('lang',))
    def load_menus(self, cr, uid, debug, context=None):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon_data', 'description', 'filter_id']
        menu_root_ids = self.get_user_roots(cr, uid, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids, fields, context=context) if menu_root_ids else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'all_menu_ids': menu_root_ids,
        }
        if not menu_roots:
            return menu_root

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menu_ids = self.search(cr, uid, [('id', 'child_of', menu_root_ids)], 0, False, False, context=context)
        menu_items = self.read(cr, uid, menu_ids, fields, context=context)
        # adds roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots)
        menu_root['all_menu_ids'] = menu_ids  # includes menu_root_ids!

        # make a tree using parent_id
        menu_items_map = dict(
            (menu_item["id"], menu_item) for menu_item in menu_items)
        for menu_item in menu_items:
            if menu_item['parent_id']:
                parent = menu_item['parent_id'][0]
            else:
                parent = False
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(
                key=operator.itemgetter('sequence'))

        return menu_root