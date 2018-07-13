# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64
import StringIO


class AccountFrFec(models.TransientModel):
    _name = 'account.fr.fec'
    _description = 'Ficher Echange Informatise'

    fiscalyear_id = fields.Many2one(
        'account.fiscalyear', string='Fiscal Year', required=False, ondelete='cascade')
    period_ids = fields.Many2many('account.period', 'account_fr_fec_period_fec_rel', 'fec_id', 'period_id', domain=[('state','<>','done')], required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id)
    type = fields.Selection([
        ('is_ir_bic', 'I.S. or BIC @ I.R.'),
        ], string='Company Type', default='is_ir_bic')
    fec_data = fields.Binary('FEC File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], string='State', default='draft')
    export_type = fields.Selection([
        ('official', 'Official FEC report (posted entries only)'),
        (
            'nonofficial',
            'Non-official FEC report (posted and unposted entries)'),
        ], string='Export Type', required=True, default='official')
    
    
    
    @api.onchange('fiscalyear_id')
    def _onchange_sec_uom_qty(self):
        if self.fiscalyear_id:
            self.period_ids = self.fiscalyear_id.period_ids
            self.company_id = self.fiscalyear_id.company_id.id
    
    @api.multi
    def generate_fec(self):
        import unicodecsv
        self.ensure_one()
        assert self.period_ids,\
            'It must have periods'
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        header = [
            'JournalCode',    # 0
            'JournalLib',     # 1
            'EcritureNum',    # 2
            'EcritureDate',   # 3
            'CompteNum',      # 4
            'CompteLib',      # 5
            'CompAuxNum',     # 6  We use partner.id
            'CompAuxLib',     # 7
            'PieceRef',       # 8
            'PieceDate',      # 9
            'EcritureLib',    # 10
            'Debit',          # 11
            'Credit',         # 12
            'EcritureLet',    # 13
            'DateLet',        # 14
            'ValidDate',      # 15
            'Montantdevise',  # 16
            'Idevise',        # 17
            ]

        company = self.company_id

        sql_query = '''
        SELECT
            replace(aj.code, '|', '/') AS JournalCode,
            replace(aj.name, '|', '/') AS JournalLib,
            replace(am.name, '|', '/') AS EcritureNum,
            am.date AS EcritureDate,
            aa.code AS CompteNum,
            replace(aa.name, '|', '/') AS CompteLib,
            CASE WHEN rp.reference IS null OR rp.reference = ''
            THEN 'ID ' || rp.id
            ELSE rp.reference
            END
            AS CompAuxNum,
            replace(rp.name, '|', '/') AS CompAuxLib,
            CASE WHEN am.ref IS null OR am.ref = ''
            THEN '-'
            ELSE replace(am.ref, '|', '/')
            END
            AS PieceRef,
            am.date AS PieceDate,
            replace(aml.name, '|', '/') AS EcritureLib,
            aml.debit AS Debit,
            aml.credit AS Credit,
            replace(amr.name, '|', '/') AS EcritureLet,
            amr.create_date::timestamp::date AS DateLet,
            am.date AS ValidDate,
            aml.amount_currency AS Montantdevise,
            rc.name AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            LEFT JOIN account_move_reconcile amr ON amr.id = aml.reconcile_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
        WHERE
            am.period_id IN %s
            AND am.company_id = %s
            AND (aml.debit != 0 OR aml.credit != 0)
        '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
            AND am.state = 'posted'
            '''

        sql_query += '''
        ORDER BY
            am.date,
            CASE aj.type WHEN 'situation' THEN 1 ELSE 2 END,
            aml.id
        '''
        self._cr.execute(
            sql_query, (tuple(self.period_ids.ids), company.id))

        fecfile = StringIO.StringIO()
        w = unicodecsv.writer(fecfile, encoding='utf-8', delimiter='|')
        w.writerow(header)

        while 1:
            self._cr.arraysize = 100
            rows = self._cr.fetchmany()
            if not rows:
                break
            for row in rows:
                # We can't write in a tuple, so I convert to a list
                listrow = list(row)
                # Empty amount_currency i.e. remplace 0.0 by empty field
                if not listrow[16]:
                    listrow[16] = ''
                # Could we set the date format in the SQL query to avoid this?
                listrow[3] = listrow[3].replace('-', '')
                listrow[9] = listrow[9].replace('-', '')
                if listrow[14]:
                    listrow[14] = listrow[14].replace('-', '')
                listrow[15] = listrow[15].replace('-', '')
                # Decimal separator must be a coma
                listrow[11] = ('%.2f' % listrow[11]).replace('.', ',')
                listrow[12] = ('%.2f' % listrow[12]).replace('.', ',')
                if listrow[16]:
                    listrow[16] = ('%.2f' % listrow[16]).replace('.', ',')
                w.writerow(listrow)
        
        siren = False
        if company.partner_id.tva_rate_ids:
            for tva_rate in company.partner_id.tva_rate_ids:
                if tva_rate.country_id and tva_rate.country_id.code == 'FR':
                    siren = tva_rate.name
                    break
                
        if company.partner_id.siret_number and not siren:
            siren = company.siret[0:9]
        elif not siren:
            raise Warning(_(
                "Missing VAT number and SIRET for company %s") % company.name)
        
        last_period_rcs = self.env['account.period'].search([('id', 'in', self.period_ids.ids)], order='date_stop desc', limit=1)
        fy_end_date = last_period_rcs.date_stop.replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'
        fecvalue = fecfile.getvalue()
        self.write({
            'state': 'done',
            'fec_data': base64.encodestring(fecvalue),
            'filename': '%sFEC%s%s.csv' % (siren, fy_end_date, suffix),
            # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
            })
        fecfile.close()

        action = {
            'name': 'FEC',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
            }
        return action
