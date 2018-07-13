
# Modif 01  : Remplacer  l10n_ma par l10n_ma
##############################################################################

import time
from openerp.report import report_sxw

class base_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(base_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            '_load': self._load,
            '_get_variable': self._get_variable,
            '_set_variable': self._set_variable,
        })
        self.context = context

    def _load(self,name,form):
        fiscalyear=self.pool.get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear'])
        fiscalyear2=self.pool.get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear2'])

        period_ids=self.pool.get('account.period').search(self.cr, self.uid,[('fiscalyear_id','=',form['fiscalyear'])])
        period_ids2=self.pool.get('account.period').search(self.cr, self.uid,[('fiscalyear_id','=',form['fiscalyear2'])])

       	if period_ids:
            self.cr.execute("SELECT MIN(date_start) AS date_start, MAX(date_stop) AS date_stop FROM account_period WHERE id = ANY(%s)", (period_ids,))
            dates = self.cr.dictfetchall()
        else:
            dates = False
        if dates:
            self._set_variable('date_start', dates[0]['date_start'])
            self._set_variable('date_stop', dates[0]['date_stop'])

        self.cr.execute("SELECT l10n_ma_line.code,definition FROM l10n_ma_line LEFT JOIN l10n_ma_report ON l10n_ma_report.id=report_id WHERE l10n_ma_report.code=%s",(name,))
        datas = self.cr.dictfetchall()
        for line in datas:
            self._load_accounts(form,line['code'],eval(line['definition']),fiscalyear,period_ids)
        #######################################################################################################"

      	#if period_ids2:
            #self.cr.execute("SELECT MIN(date_start) AS date_start, MAX(date_stop) AS date_stop FROM account_period WHERE id = ANY(%s)", (period_ids2,))
            #dates = self.cr.dictfetchall()
        #else:
         #   dates = False
        #if dates:
            #self._set_variable('date_start', dates[0]['date_start'])
            #self._set_variable('date_stop', dates[0]['date_stop'])

        self.cr.execute("SELECT l10n_ma_line.code,definition FROM l10n_ma_line LEFT JOIN l10n_ma_report ON l10n_ma_report.id=report_id WHERE l10n_ma_report.code=%s",(name,))
        datas = self.cr.dictfetchall()
        for line in datas:
            self._load_accounts2(form,line['code'],eval(line['definition']),fiscalyear2,period_ids2)

        ##########################################################################################################   
    def _set_variable(self, variable, valeur):
        self.localcontext.update({variable:valeur})

    def _get_variable(self, variable):
        return self.localcontext[variable]

    def _load_accounts(self, form, code, definition, fiscalyear, period_ids):
        accounts = {}
        for x in definition['load']:
            p = x.split(":")
            accounts[p[1]] = [p[0],p[2]]
        sum = 0.0
        if fiscalyear.state != 'done' or not code.startswith('bpcheck'):
            query_params = []
            query_cond = "("
            for account in accounts:
                query_cond += "aa.code LIKE '" + account + "%%' OR "
            query_cond = query_cond[:-4]+")"

            if len(definition['except'])>0:
                query_cond = query_cond+" and ("
                for account in definition['except']:
                    query_cond += "aa.code NOT LIKE '"+account+"%' AND "
                query_cond = query_cond[:-5]+")"

            closed_cond = ""
            if fiscalyear.state == 'done':
                closed_cond=" AND (aml.move_id NOT IN (SELECT account_move.id as move_id FROM account_move WHERE period_id = ANY(%s) AND journal_id=(SELECT res_id FROM ir_model_data WHERE name='closing_journal' AND module='l10n_ma')) OR (aa.type != 'income' AND aa.type !='expense'))"
                query_params.append(list(period_ids))

            query = "SELECT aa.code AS code, SUM(debit) as deb, SUM(credit) as cred " \
                " FROM account_move_line aml LEFT JOIN account_account aa ON aa.id=aml.account_id "\
                " WHERE "+query_cond+closed_cond+" AND aml.state='valid' AND aml.period_id = ANY(%s) GROUP BY code"
            query_params.append(list(period_ids))

            self.cr.execute(query, query_params)

            lines =self.cr.dictfetchall()
            for line in lines:
                for account in accounts:
                    if(line["code"].startswith(account)):
                        operator=accounts[account][0]
                        type=accounts[account][1]
                        value=line["deb"]-line["cred"]
                        if(operator=='+'):
                            sum+=value
                        else:
                            sum-=value
                        break
        self._set_variable(code, sum)

##############################################################################################################################

    def _load_accounts2(self, form, code, definition, fiscalyear2, period_ids2):
        accounts = {}
        for x in definition['load']:
            p = x.split(":")
            accounts[p[1]] = [p[0],p[2]]
        sum = 0.0
        if fiscalyear2.state != 'done' or not code.startswith('bpcheck'):
            query_params = []
            query_cond = "("
            for account in accounts:
                query_cond += "aa.code LIKE '" + account + "%%' OR "
            query_cond = query_cond[:-4]+")"

            if len(definition['except'])>0:
                query_cond = query_cond+" and ("
                for account in definition['except']:
                    query_cond += "aa.code NOT LIKE '"+account+"%' AND "
                query_cond = query_cond[:-5]+")"

            closed_cond = ""
            if fiscalyear2.state == 'done':
                closed_cond=" AND (aml.move_id NOT IN (SELECT account_move.id as move_id FROM account_move WHERE period_id = ANY(%s) AND journal_id=(SELECT res_id FROM ir_model_data WHERE name='closing_journal' AND module='l10n_ma')) OR (aa.type != 'income' AND aa.type !='expense'))"
                query_params.append(list(period_ids2))

            query = "SELECT aa.code AS code, SUM(debit) as debit, SUM(credit) as credit " \
                " FROM account_move_line aml LEFT JOIN account_account aa ON aa.id=aml.account_id "\
                " WHERE "+query_cond+closed_cond+" AND aml.state='valid' AND aml.period_id = ANY(%s) GROUP BY code"
            query_params.append(list(period_ids2))
            self.cr.execute(query, query_params)

            lines =self.cr.dictfetchall()
            for line in lines:
                for account in accounts:
                    if(line["code"].startswith(account)):
                        operator=accounts[account][0]
                        type=accounts[account][1]
                        value=line["debit"]-line["credit"]
                        if(operator=='+'):
                            sum+=value
                        else:
                            sum-=value
                        break
        old="old"+code
        self._set_variable(old, sum)
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

