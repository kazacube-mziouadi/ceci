# coding: utf-8

from openerp import models, api, fields

class stock_config_settings(models.Model):
    _inherit = 'stock.config.settings'

    declaration_grouping_flag = fields.Boolean(default=True, help='When the flag is checked declarations can be declared by group')
    label_consumption_grouping_flag = fields.Boolean(default=True, help='When the flag is checked we can choose which label to use for consumption')
