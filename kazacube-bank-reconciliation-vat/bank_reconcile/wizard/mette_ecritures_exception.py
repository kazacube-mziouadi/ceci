# -*- encoding: utf-8 -*-
from openerp import netsvc ,models, fields, api, exceptions, _
import time
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_line_exception(models.TransientModel):
    
    _name = 'account.line.exception'

    @api.multi
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        company_id = False
        if self._ids and self._context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(self._ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    def _get_period(self, cr, uid, context=None):
        print "_get_period"
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'account.period':
            company_id = self.pool.get('account.period').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        periods = self.pool.get('account.period').search(cr, uid, domain, limit=1)
        return periods and periods[0] or False


    def _get_account(self, cr, uid, context=None):
        print "_get_account"
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'account.account':
            company_id = self.pool.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        type_ids = self.pool.get('account.account.type').search(cr, uid,[('code','=','bank')])
        domain = [('company_id', '=', company_id),('user_type', 'in',type_ids)]
        accounts = self.pool.get('account.account').search(cr, uid, domain, limit=1)
        return accounts and accounts[0] or False

   
    
    
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Exercice comptable', required=True,default=_get_fiscalyear)
    periode_id = fields.Many2one(comodel_name='account.period',string='Periode',required=True,domain=[('special','=',False)])
    account_id = fields.Many2one(comodel_name='account.account',string='Compte',required=True,)
    move_lines = fields.One2many(comodel_name='account.move.exception',inverse_name='wiz_id',string='Ecritures Comptable')
    state= fields.Selection([('draft', 'New'),('open','Open')],
                   string='Status', required=True, readonly="1",default="draft")

    _defaults={
        'periode_id':_get_period,
        'account_id':_get_account,
    }

    @api.multi
    def edit_lines(self):
        fiscalyear_id = self.fiscalyear_id.id
        periode_id = self.periode_id.id
        account_id = self.account_id.id
        move_line_obj = self.env["account.move.line"]
        move_obj = self.env["account.move"]
        journal_obj = self.env["account.journal"]
        journaux_ids = journal_obj.search([('type','=','bank')])
        move_ids = move_obj.search([('journal_id','in',journaux_ids._ids),('period_id','=',periode_id),('state','=','posted')])
        move_line_ids = move_line_obj.search([('reconciliation_id','=',False),('move_id','in',move_ids._ids),('period_id','=',periode_id),
                                              ('state','=','valid'),('account_id','=',account_id),('rapprocher','=',False),('exception','=',False)])
        if move_line_ids :
            for line in move_line_ids :
                vals={}
                vals['date']=line.date
                vals['name']=line.name
                vals['partner_id']=line.partner_id.id
                vals['account_id']=line.account_id.id
                vals['debit']=line.debit
                vals['credit']=line.credit
                vals['exception']=line.exception
                vals['move_id']=line.id
                vals['wiz_id']=self.id
                self.env['account.move.exception'].create(vals)
            self.state="open"
        else :
             raise except_orm(_('Pas de lignes comptables  pour la période et le compte chosis'),_("Période : %s - Compte : %s"%(self.periode_id.code,self.account_id.code)))
        return {
        'context': self.env.context,
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'account.line.exception',
        'res_id': self.id,
        'view_id': False,
        'type': 'ir.actions.act_window',
        'target': 'new',
    }
    @api.multi
    def action_reset(self):
        self.move_lines=None
        self.state="draft"
        return {
        'context': self.env.context,
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'account.line.exception',
        'res_id': self.id,
        'view_id': False,
        'type': 'ir.actions.act_window',
        'target': 'new',
    }

    @api.multi
    def action_move_line_excep(self):
        for line in self.move_lines :
             if line.exception :
                line.move_id.state1='exception'
                line.move_id.exception=True
        return True


    # def onchange_fiscalyear_id(self,cr,uid,ids,fiscalyear_id,context=None):
    #
    #     period_ids = self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','=',fiscalyear_id),('special','=',False)])
    #     period_domain=[('id','in',period_ids)]
    #     now = time.strftime('%Y-%m-%d')
    #     company_id = False
    #     #ids = context.get('active_ids', [])
    #     if ids and context.get('active_model') == 'account.period':
    #         company_id = self.pool.get('account.period').browse(cr, uid, ids[0], context=context).company_id.id
    #     else:  # use current company id
    #         company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    #     domain = [('fiscalyear_id','=',fiscalyear_id),('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
    #     periods = self.pool.get('account.period').search(cr, uid, domain, limit=1)
    #     return {'value':{'periode_id':periods[0]},'domain':{'periode_id':period_domain}}
    #
    # def onchange_periode_id(self,cr,uid,ids,fiscalyear_id,periode_id,context=None):
    #
    #    if not fiscalyear_id:
    #        raise except_orm(_('Veuiller choisir un Exercice Comptable'),_(""))
    #    account_type_ids = self.pool.get('account.account.type').search(cr,uid,['|',('code','=','bank'),('code','=','cash'),])
    #    account_ids = self.pool.get('account.account').search(cr,uid,[('user_type','in',account_type_ids),])
    #    account_domain=[('id','in',account_ids)]
    #    now = time.strftime('%Y-%m-%d')
    #    company_id = False
    #    if ids and context.get('active_model') == 'account.account':
    #        company_id = self.pool.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
    #    else:  # use current company id
    #        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    #    type_ids = self.pool.get('account.account.type').search(cr, uid,[('code','=','bank')])
    #    domain = [('company_id', '=', company_id),('user_type', 'in',type_ids)]
    #    accounts = self.pool.get('account.account').search(cr, uid, domain, limit=1)
    #    return {'value':{'account_id':accounts[0]},'domain':{'account_id':account_domain}}
    #
    # def onchange_account_id(self,cr,uid,ids,fiscalyear_id,periode_id,account_id,context=None):
    #     lines=[]
    #     value={}
    #     if not periode_id :
    #        raise except_orm(_('Veuiller choisir une Periode '),_(""))
    #     move_line_obj = self.pool.get("account.move.line")
    #     move_obj = self.pool.get("account.move")
    #     journal_obj = self.pool.get("account.journal")
    #     journaux_ids = journal_obj.search(cr,uid,[('type','=','bank')])
    #     move_ids = move_obj.search(cr,uid,[('journal_id','in',journaux_ids),('period_id','=',periode_id),('state','=','posted')])
    #     print "onchange_account_id",move_ids
    #     move_line_ids = move_line_obj.search(cr,uid,[('reconciliation_id','=',False),('move_id','in',move_ids),('account_id','=',account_id),
    #                                                  ('rapprocher','=',False)])
    #     if not move_line_ids:
    #         wiz_id=self.browse(cr,uid,ids)
    #         if wiz_id :
    #             cr.execute("delete from account_move_exception where exception_id=%s"%wiz_id.id)
    #             wiz_id.write({'account_move_line_ids':None})
    #         raise except_orm(_('Il n\'y a aucune écritures pour le compte et la periode choisie' ),_(""))
    #     lines.append((6,0,move_line_ids))
    #     value.update(account_move_line_ids=lines)
    #     return {'value':value}




account_line_exception()


class account_move_exception(models.TransientModel):

    _name = 'account.move.exception'

    date = fields.Date(string='Date')
    name = fields.Char(string='Description', size=256)
    partner_id = fields.Many2one(comodel_name='res.partner',string='Partenaire')
    account_id = fields.Many2one(comodel_name='account.account',string='Compte')
    debit = fields.Float(string='Débit')
    credit = fields.Float(string='Crédit')
    exception = fields.Boolean(string='Exception?')
    move_id =fields.Many2one(comodel_name='account.move.line',string='Ecriture comptable')
    wiz_id = fields.Many2one(comodel_name='account.line.exception',string='Exception wiz')


account_move_exception()


