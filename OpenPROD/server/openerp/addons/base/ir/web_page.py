# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.http import request


class web_page(models.Model):
    """
    Multi-part web page
    """
    _name = 'web.page'
    _description = 'Multi-part web page'

    @api.one
    def _compute_path(self):
        action_id = self.env.ref('base.act_view_web_page')
        self.path = '/web#id=%d&view_type=form&model=web.page&action=%s' % (
                self.id,
                action_id.id,
            )

    def get_default_inner_content(self):
        if self.env.context.get('prev_page_id', False):
            action_id = self.env.ref('base.act_view_web_page')
            return '''<div class="row">
            <div class="col-md-12 col-sm-12 col-xs-12 column">
            <a href="/web#id=%d&view_type=form&model=web.page&action=%s">%s</a>
            </div>
            </div>''' % (
                self.env.context['prev_page_id'],
                action_id.id,
                _('Previous page'),
            )
        return '<div class="row"></div>'

    def get_default_write_user_ids(self):
        if self.env.context.get('prev_page_id', False):
            prev_id = self.browse(self.env.context['prev_page_id'])
            return [(6, 0, prev_id.write_user_ids.ids)]

    def get_default_write_group_ids(self):
        if self.env.context.get('prev_page_id', False):
            prev_id = self.browse(self.env.context['prev_page_id'])
            return [(6, 0, prev_id.write_group_ids.ids)]

    #==========================================================================
    # COLUMNS
    #==========================================================================
    name = fields.Char(required=True)
    content = fields.Text(string='Content', compute='get_html')
    inner_content = fields.Text(default=get_default_inner_content)
    path = fields.Char(string='Path for link', compute='_compute_path')
    write_user_ids = fields.Many2many('res.users', 'web_page_user_rel',
                                       'page_id', 'user_id',
                                       string="Authorized users", default=get_default_write_user_ids)
    write_group_ids = fields.Many2many('res.groups', 'web_page_group_rel',
                                        'page_id', 'group_id',
                                        string="Authorized groups", default=get_default_write_group_ids)

    @api.depends('inner_content')
    def get_html(self):
        for page in self:
            parts_html = page.inner_content or '<div class="row"></div>'
            page.content = u'''{}{}'''.format(
                parts_html, page.get_edit_button())

    def get_edit_button(self):
        user = self.env['res.users'].browse(request.uid)
        authorized = (user in self.write_user_ids or
                      user.groups_id & self.write_group_ids or
                      request.uid == 1)
        if authorized:
            return u'''<button class="edit_page btn btn-default fa fa-edit" data-page-id="{}"></button>'''.format(self.id)
        else:
            return u''

    @api.multi
    def write(self, vals):
        res = super(web_page, self).write(vals)
        self.env['ir.ui.view'].clear_caches()
        return res


class web_part(models.Model):
    """
    Part of a web page
    """
    _name = 'web.part'
    _description = 'Part of a web page'
    _order = 'sequence'

    @api.model
    def _type_get(self):
        return [
            ('editor', _('Editor')),
            ('raw', _('Raw HTML')),
            ('menu', _('Menu')),
        ]

    #==========================================================================
    # COLUMNS
    #==========================================================================
    type = fields.Selection('_type_get', string='Type', default='editor',
                            required=True)
    name = fields.Char(string='Name')
    content_html = fields.Html()
    content_raw = fields.Text()
    width = fields.Char(default='100%')
    page_id = fields.Many2one('web.page', string='Page', required=True,
                              ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    link_ids = fields.One2many('web.link', 'part_id',  string='Menus')

    def get_html(self):
        return u'''<div style="width: {}">{}</div>'''.format(
            self.width, self.get_content())

    def get_content(self):
        if self.type == 'editor':
            return self.content_html
        elif self.type == 'raw':
            return self.content_raw
        elif self.type == 'menu':
            if len(self.link_ids):
                links_html = '\n'.join(x.get_html() for x in self.link_ids)
                return u'<ul>{}</ul>'.format(links_html)
        else:
            return ''

    @api.model
    def create(self, vals):
        if not vals['sequence']:
            part_ids = self.env['web.page'].browse(vals['page_id']).part_ids
            if part_ids:
                max_sequence = max(x.sequence for x in part_ids)
                vals['sequence'] = max_sequence + 1
        return super(web_part, self).create(vals)


class web_link(models.Model):
    """
    Web link
    """
    _name = 'web.link'
    _description = 'Web link'

    #==========================================================================
    # COLUMNS
    #==========================================================================
    url = fields.Char(related='page_id.path')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    part_id = fields.Many2one('web.part')
    page_id = fields.Many2one('web.page')

    @api.model
    def create(self, vals):
        if not vals['sequence']:
            part_ids = self.env['web.part'].browse(vals['part_id']).link_ids
            if part_ids:
                max_sequence = max(x.sequence for x in part_ids)
                vals['sequence'] = max_sequence + 1
        return super(web_link, self).create(vals)

    def get_html(self):
        return u'<li><a href="{}">{}</a></li>'.format(
            self.url,
            self.page_id.name
        )
