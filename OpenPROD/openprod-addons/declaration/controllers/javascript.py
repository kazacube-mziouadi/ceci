# -*- coding: utf-8 -*-
from openerp.exceptions import AccessError
from openerp.http import Controller
from openerp.http import route
from openerp.http import Response


class JavascriptController(Controller):
    @route('/declaration/javascript', auth='public', csrf=False, type="http")
    def handler(self, *args, **kwargs):
        return ""