# -*- coding: utf-8 -*-
import math
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from HTMLParser import HTMLParser

class myhtmlparser(HTMLParser):
    def __init__(self):
        self.reset()
        self.NEWTAGS = []
        self.NEWATTRS = []
        self.HTMLDATA = []
    def handle_starttag(self, tag, attrs):
        self.NEWTAGS.append(tag)
        self.NEWATTRS.append(attrs)
    def handle_data(self, data):
        self.HTMLDATA.append(data)
    def clean(self):
        self.NEWTAGS = []
        self.NEWATTRS = []
        self.HTMLDATA = []


def get_form_view(self, action, res_id=False, view_mode='form,tree', target='current'):
    """
        Retourne une action avec la vue form par défaut en fonction du type
        :type self: stock.picking
        :return: Action
        :rtype: dict
    """
    res = False
    action = self.env.ref(action)
    if action:
        res = action.read(['name', 'type', 'res_model', 'view_type'])[0]
        if res_id:
            res['res_id'] = res_id
            
        res['view_mode'] = view_mode
        res['target'] = target

    return res


def rounding(f, r):
    #arrondie openerp r rounding 
    if not r:
        return f
    return round(f / r) * r


def roundingUp(f, r):
    #arrondie openerp r rounding mais au superieur
    if not r:
        return f
    
    return math.ceil(f / r) * r


def hash_list(arg_list, multiple, manage_rest=True):
    res = []
    list_len = len(arg_list)
    # Création d'une liste de liste
    for i in range(list_len / multiple):
        res.append(arg_list[:multiple])
        del arg_list[:multiple]
    # Ajout du reste
    if arg_list and manage_rest:
        res.append(arg_list)
        
    return res


def _get_month_start(year, month):
    # Retourne une date de la première seconde de la première minute de la première heure du premier jour du mois passé en paramètre
    return datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def _get_month_stop(year, month):
    # Retourne une date de la dernière seconde de la dernière minute de la dernière heure du dernier jour du mois passé en paramètre
    return datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0) + relativedelta(months=1) - relativedelta(seconds=1)


def calendar_id2real_id(calendar_id=None, with_date=False):
    """
    Convert a "virtual/recurring event id" (type string) into a real event id (type int).
    E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
    @param calendar_id: id of calendar
    @param with_date: if a value is passed to this param it will return dates based on value of withdate + calendar_id
    @return: real event id
    """
    if calendar_id and isinstance(calendar_id, (basestring)):
        if calendar_id.startswith('one2many'):
            return False
        
        res = calendar_id.split('-')
        if len(res) >= 2:
            real_id = res[0]
            if with_date:
                real_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(res[1], "%Y%m%d%H%M%S"))
                start = datetime.strptime(real_date, DEFAULT_SERVER_DATETIME_FORMAT)
                end = start + timedelta(hours=with_date)
                return (int(real_id), real_date, end.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            
            return int(real_id)
        
    return calendar_id and int(calendar_id) or calendar_id

#===============================================================================
# DÉCORATEURS
#===============================================================================


def print_log(fonction):
    """
        Affiche le temps les ids et le résultat de la fonction
    """
    def fct_print_log(*args, **kwargs):
        print '=' * 50, '[', 'START: ', fonction.__name__, ']', '=' * 50
        start = time.time()
        res = fonction(*args, **kwargs)
        end = time.time() - start
        print 'Fonction: %s'%(fonction.__name__)
        try:
            print 'Ids: %s'%(args[0].ids)
        except:
            pass
            
        print 'Time: %s'%(end)
         
        try:
            print 'Result: %s'%(res)
        except:
            pass
         
        print '=' * 50, '[', 'END: ', fonction.__name__, ']', '=' * 50
        return res
   
    return fct_print_log
     