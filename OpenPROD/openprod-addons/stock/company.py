# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import pytz




class res_company(models.Model):
    _inherit = 'res.company'


    # Cover
    @api.model
    def _cover_sorting_date_get(self):
        return [
                ('priority_date', _('Priority date')),
                ('date_expected', _('Need date')),
                ('date', _('Creation date')),
                       ]
    
    @api.model
    def _tz_get(self):
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    cover_sorting_date = fields.Selection('_cover_sorting_date_get', default='priority_date')
    horizon = fields.Integer(default=10)
    limit_modif_move = fields.Date(string='The deadline for changing movements')
    tz = fields.Selection('_tz_get', string='Timezone', help="The partner's timezone, used to output proper date and time values inside printed reports. "
                "It is important to set a value for this field. You should use the same timezone "
                 "that is otherwise used to pick and render date and time values: your computer's timezone.")
