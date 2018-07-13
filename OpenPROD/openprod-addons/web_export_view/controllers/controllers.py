# -*- coding: utf-8 -*-

try:
    import json
except ImportError:
    import simplejson as json
from cStringIO import StringIO

import openerp.http as http
import re, xlwt
from openerp.http import request
from openerp.addons.web.controllers.main import ExcelExport


def get_width(num_characters, factor=300):
    return int((1 + num_characters) * factor)

class ExcelExportView(ExcelExport):
    def __getattribute__(self, name):
        if name == 'fmt':
            raise AttributeError()
        return super(ExcelExportView, self).__getattribute__(name)

    def from_data(self, fields, rows, group=None):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        title_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour yellow;")
        group_style = xlwt.easyxf('font: bold on;')
        line_style = xlwt.easyxf('align: wrap yes')
        widths = {}
        for i, fieldname in enumerate(fields):
            worksheet.write(0, i, fieldname.upper(), title_style)
            widths[i] = get_width(len(fieldname), 300)

        for row_index, row in enumerate(rows):
            style = group_style if group and row[0] != '' else line_style
            for cell_index, cell_value in enumerate(row):
                cell_value = unicode(cell_value)
                if cell_value:
                    # Si tout est en majuscule on augmente le facteur de taille
                    if cell_value == cell_value.upper():
                        w = get_width(len(cell_value), 300)
                    else:
                        w = get_width(len(cell_value))

                    if w > widths[cell_index]:
                        widths[cell_index] = w

                if isinstance(cell_value, basestring):
                    cell_value = re.sub("\r", " ", cell_value)
                if cell_value is False:
                    cell_value = None

                worksheet.write(row_index + 1, cell_index, cell_value, style)

        for k, v in widths.iteritems():
            worksheet.col(k).width = v

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @http.route('/web/export/xls_view', type='http', auth='user')
    def export_xls_view(self, data, token):
        req = http.request
        data = json.loads(data)
        model = data.get('model', [])
        columns_headers = data.get('headers', [])
        rows = data.get('rows', [])
        group = data.get('group', False)
        domain = data.get('domain', [])
        group_by = data.get('group_by', [])

        export_security_rule_obj = req.env['export.security.rule']
        export_security_rule = export_security_rule_obj.search([
            ('model_id.model', '=', model), ('criticality', '!=', 'none'), ('trace_export_current', '=', True)]
        )
        if len(export_security_rule):
            req.env['export.security.log'].create({
                'model': model,
                'user_id': req.session._uid,
                'criticality': export_security_rule.criticality,
                'name': 'ExportCurrentView',
                'filter': json.dumps(domain),
                'group_by': group_by,
                'lines_count': len(rows),
                 })

        return request.make_response(
            self.from_data(columns_headers, rows, group),
            headers=[
                ('Content-Disposition', 'attachment; filename="%s"'
                 % self.filename(model)),
                ('Content-Type', self.content_type)
            ],
            cookies={'fileToken': token}
        )
