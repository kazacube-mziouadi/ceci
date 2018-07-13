# -*- coding: utf-8 -*-

from openerp.tools.translate import _
from openerp import models, fields,  api, _
import os, os.path ,glob
import csv
import tempfile
from datetime import datetime
import time
from openerp.exceptions import except_orm, Warning, RedirectWarning

class bank_operation(models.Model):
    _name="bank.operation"

    code=fields.Char(string="Code",required=True)
    name=fields.Char(string="Type d'opération",required=True)
    type=fields.Selection([('D','Débit'),('C','Crédit'),('R','Réservé')],string='Type',required=False)

bank_operation()
