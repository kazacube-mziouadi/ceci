# -*- coding: utf-8 -*-
from openerp import models, fields, api


class TranslateWizard(models.TransientModel):

    _name = 'translator.translate.wizard'
    _description = u"Transient model to translate odoo terms"

    label = fields.Char(u"Label", help=u"Label to translate, where you clicked")
    model = fields.Char(u"Label's model",
                              help=u"Reference model to restricted results,\n"
                                   u"this is used to accurate string to "
                                   u"translate")
    lang = fields.Char(u"Translating lang.",
                            help=u"Translating language",
                            default=lambda self: self.env.context.get('lang', False))
    new_value = fields.Char(u'New value')
    source_id = fields.Many2one('ir.translation')
    reference_value = fields.Char(u'Reference value')
    ref_lang = fields.Many2one('res.lang', string=u"Reference lang.")
    translation_line_ids = fields.Many2many('ir.translation', string="Selection values")
    help_text = fields.Text(string="Help text")
    help_text_reference = fields.Text(string="Help text in ref. lang")
    help_text_id = fields.Many2one('ir.translation')
    
    @api.model
    def create(self, vals):
        source_id = self.env['ir.translation'].browse(vals['source_id'])
        ref_lang_id = self.env.user.company_id.reference_lang_id
        ref_value_id = self.env['ir.translation'].search([
                                                          ('lang', '=', ref_lang_id.code),
                                                          ('src', '=', source_id.src),
                                                          ('name', '=', source_id.name),
                                                          ('res_id', '=', source_id.res_id),
                                                          ('module', '=', source_id.module),
                                                          ('type', '=', source_id.type),
                                                          ])
        if len(ref_value_id):
            ref_value = ref_value_id.value
        else:
            ref_value = source_id.src
        if vals.get('help_text_id', False):
            help_text_id = self.env['ir.translation'].browse(vals['help_text_id'])
            help_text_ref_id = self.env['ir.translation'].search([
                                                          ('lang', '=', ref_lang_id.code),
                                                          ('src', '=', help_text_id.src),
                                                          ('name', '=', help_text_id.name),
                                                          ('res_id', '=', help_text_id.res_id),
                                                          ('module', '=', help_text_id.module),
                                                          ('type', '=', help_text_id.type),
                                                          ])
            if len(help_text_ref_id):
                vals['help_text_reference'] = help_text_ref_id.value
            else:
                vals['help_text_reference'] = help_text_id.src
        vals['ref_lang'] = ref_lang_id.id
        vals['reference_value'] = ref_value
        res = super(TranslateWizard, self).create(vals)
        return res

    @api.multi
    def translate(self):
        if self.new_value:
            self.source_id.write({'value':self.new_value})
        if self.help_text:
            self.help_text_id.write({'value':self.help_text})
        self.env['ir.translation'].clear_caches()
        self.env['ir.translation'].clear_caches()
        self.env['ir.ui.view'].clear_caches()
        self.env['ir.ui.menu'].clear_caches()
        return {'type': 'ir.actions.client', 'tag': 'reload', } 
        
    def translate_no_reload(self, cr, uid, ids, context=None):
        self.translate(cr, uid, ids, context)
        return {}

