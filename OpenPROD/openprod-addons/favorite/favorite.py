# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp import http

class Favorite(models.Model):
    _name = 'favorite'

    name = fields.Char()
    filter = fields.Many2one(comodel_name='ir.filters' , string='Favorite filter' , ondelete='cascade' )
    menu = fields.Many2one(comodel_name='ir.ui.menu' , string='Menu' , ondelete='cascade' )
    user = fields.Integer(string="User")

    def create(self, cr, uid, vals, context=None):   
        filter = http.request.env['ir.filters'].browse(vals['filter'])
        #On passe par sudo pour qu'un utilisateur normal aie les droits sur les menus
        favorite_parent_menu = http.request.env['ir.ui.menu'].sudo().search([('name', '=', 'Favorite') , ('parent_id','=', None)])
        favorite_list_menu = http.request.env['ir.ui.menu'].sudo().search([('name', '=', 'Mes favoris') , ('parent_id','=', favorite_parent_menu.id)])
        if not favorite_list_menu.id :
            favorite_list_menu = http.request.env['ir.ui.menu'].sudo().search([('name', '=', 'My Favorites') , ('parent_id','=', favorite_parent_menu.id)])
        menu = http.request.env['ir.ui.menu'].sudo().create({ 'parent_id' : favorite_list_menu.id , 
                                                'action' : 'ir.actions.act_window,' + str(filter.action_id.id) , 
                                                'name' : vals['name'] ,
                                                'user_id' : http.request.env.user.id ,
                                                'filter_id' : filter.id })
        vals['user'] = http.request.env.user.id
        vals['menu'] = menu.id
        res = super(Favorite, self).create(cr, uid, vals, context=context)
        return res

    @api.multi
    def unlink(self):
        self.menu.sudo().unlink()
        return super(Favorite,self).unlink()
