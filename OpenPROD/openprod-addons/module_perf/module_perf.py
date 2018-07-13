# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.exceptions import except_orm, ValidationError


class perf_char(models.Model):
    """ 
    description 
    """
    _name = 'perf.char'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Char(required=False, size=256)
    name2 = fields.Char(required=False, size=256)
    name3 = fields.Char(required=False, size=256)
    name4 = fields.Char(required=False, size=256)
    name5 = fields.Char(required=False, size=256)
    name6 = fields.Char(required=False, size=256)
    name7 = fields.Char(required=False, size=256)
    name8 = fields.Char(required=False, size=256)
    name9 = fields.Char(required=False, size=256)
    name10 = fields.Char(required=False, size=256)
    name11 = fields.Char(required=False, size=256)
    name12 = fields.Char(required=False, size=256)
    name13 = fields.Char(required=False, size=256)
    name14 = fields.Char(required=False, size=256)
    name15 = fields.Char(required=False, size=256)
    name16 = fields.Char(required=False, size=256)
    name17 = fields.Char(required=False, size=256)
    name18 = fields.Char(required=False, size=256)
    name19 = fields.Char(required=False, size=256)
    name20 = fields.Char(required=False, size=256)
    name21 = fields.Char(required=False, size=256)
    name22 = fields.Char(required=False, size=256)
    name23 = fields.Char(required=False, size=256)
    name24 = fields.Char(required=False, size=256)
    name25 = fields.Char(required=False, size=256)
    name26 = fields.Char(required=False, size=256)
    name27 = fields.Char(required=False, size=256)
    name28 = fields.Char(required=False, size=256)
    name29 = fields.Char(required=False, size=256)
    name30 = fields.Char(required=False, size=256)
    name31 = fields.Char(required=False, size=256)
    name32 = fields.Char(required=False, size=256)
    name33 = fields.Char(required=False, size=256)
    name34 = fields.Char(required=False, size=256)
    name35 = fields.Char(required=False, size=256)
    name36 = fields.Char(required=False, size=256)
    name37 = fields.Char(required=False, size=256)
    name38 = fields.Char(required=False, size=256)
    name39 = fields.Char(required=False, size=256)
    name40 = fields.Char(required=False, size=256)
    name_one2many_id = fields.Many2one('perf.one2many', string='string', required=False, ondelete='restrict')
    

class perf_float(models.Model):
    """ 
    description 
    """
    _name = 'perf.float'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Float(required=False, default=0.0)
    name2 = fields.Float(required=False, default=0.0)
    name3 = fields.Float(required=False, default=0.0)
    name4 = fields.Float(required=False, default=0.0)
    name5 = fields.Float(required=False, default=0.0)
    name6 = fields.Float(required=False, default=0.0)
    name7 = fields.Float(required=False, default=0.0)
    name8 = fields.Float(required=False, default=0.0)
    name9 = fields.Float(required=False, default=0.0)
    name10 = fields.Float(required=False, default=0.0)
    name11 = fields.Float(required=False, default=0.0)
    name12 = fields.Float(required=False, default=0.0)
    name13 = fields.Float(required=False, default=0.0)
    name14 = fields.Float(required=False, default=0.0)
    name15 = fields.Float(required=False, default=0.0)
    name16 = fields.Float(required=False, default=0.0)
    name17 = fields.Float(required=False, default=0.0)
    name18 = fields.Float(required=False, default=0.0)
    name19 = fields.Float(required=False, default=0.0)
    name20 = fields.Float(required=False, default=0.0)
    name21 = fields.Float(required=False, default=0.0)
    name22 = fields.Float(required=False, default=0.0)
    name23 = fields.Float(required=False, default=0.0)
    name24 = fields.Float(required=False, default=0.0)
    name25 = fields.Float(required=False, default=0.0)
    name26 = fields.Float(required=False, default=0.0)
    name27 = fields.Float(required=False, default=0.0)
    name28 = fields.Float(required=False, default=0.0)
    name29 = fields.Float(required=False, default=0.0)
    name30 = fields.Float(required=False, default=0.0)
    name31 = fields.Float(required=False, default=0.0)
    name32 = fields.Float(required=False, default=0.0)
    name33 = fields.Float(required=False, default=0.0)
    name34 = fields.Float(required=False, default=0.0)
    name35 = fields.Float(required=False, default=0.0)
    name36 = fields.Float(required=False, default=0.0)
    name37 = fields.Float(required=False, default=0.0)
    name38 = fields.Float(required=False, default=0.0)
    name39 = fields.Float(required=False, default=0.0)
    name40 = fields.Float(required=False, default=0.0)



class perf_integer(models.Model):
    """ 
    description 
    """
    _name = 'perf.integer'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Integer(required=False, default=0)
    name2 = fields.Integer(required=False, default=0)
    name3 = fields.Integer(required=False, default=0)
    name4 = fields.Integer(required=False, default=0)
    name5 = fields.Integer(required=False, default=0)
    name6 = fields.Integer(required=False, default=0)
    name7 = fields.Integer(required=False, default=0)
    name8 = fields.Integer(required=False, default=0)
    name9 = fields.Integer(required=False, default=0)
    name10 = fields.Integer(required=False, default=0)
    name11 = fields.Integer(required=False, default=0)
    name12 = fields.Integer(required=False, default=0)
    name13 = fields.Integer(required=False, default=0)
    name14 = fields.Integer(required=False, default=0)
    name15 = fields.Integer(required=False, default=0)
    name16 = fields.Integer(required=False, default=0)
    name17 = fields.Integer(required=False, default=0)
    name18 = fields.Integer(required=False, default=0)
    name19 = fields.Integer(required=False, default=0)
    name20 = fields.Integer(required=False, default=0)
    name21 = fields.Integer(required=False, default=0)
    name22 = fields.Integer(required=False, default=0)
    name23 = fields.Integer(required=False, default=0)
    name24 = fields.Integer(required=False, default=0)
    name25 = fields.Integer(required=False, default=0)
    name26 = fields.Integer(required=False, default=0)
    name27 = fields.Integer(required=False, default=0)
    name28 = fields.Integer(required=False, default=0)
    name29 = fields.Integer(required=False, default=0)
    name30 = fields.Integer(required=False, default=0)
    name31 = fields.Integer(required=False, default=0)
    name32 = fields.Integer(required=False, default=0)
    name33 = fields.Integer(required=False, default=0)
    name34 = fields.Integer(required=False, default=0)
    name35 = fields.Integer(required=False, default=0)
    name36 = fields.Integer(required=False, default=0)
    name37 = fields.Integer(required=False, default=0)
    name38 = fields.Integer(required=False, default=0)
    name39 = fields.Integer(required=False, default=0)
    name40 = fields.Integer(required=False, default=0)



class perf_date(models.Model):
    """ 
    description 
    """
    _name = 'perf.date'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Date(required=False)
    name2 = fields.Date(required=False)
    name3 = fields.Date(required=False)
    name4 = fields.Date(required=False)
    name5 = fields.Date(required=False)
    name6 = fields.Date(required=False)
    name7 = fields.Date(required=False)
    name8 = fields.Date(required=False)
    name9 = fields.Date(required=False)
    name10 = fields.Date(required=False)
    name11 = fields.Date(required=False)
    name12 = fields.Date(required=False)
    name13 = fields.Date(required=False)
    name14 = fields.Date(required=False)
    name15 = fields.Date(required=False)
    name16 = fields.Date(required=False)
    name17 = fields.Date(required=False)
    name18 = fields.Date(required=False)
    name19 = fields.Date(required=False)
    name20 = fields.Date(required=False)
    name21 = fields.Date(required=False)
    name22 = fields.Date(required=False)
    name23 = fields.Date(required=False)
    name24 = fields.Date(required=False)
    name25 = fields.Date(required=False)
    name26 = fields.Date(required=False)
    name27 = fields.Date(required=False)
    name28 = fields.Date(required=False)
    name29 = fields.Date(required=False)
    name30 = fields.Date(required=False)
    name31 = fields.Date(required=False)
    name32 = fields.Date(required=False)
    name33 = fields.Date(required=False)
    name34 = fields.Date(required=False)
    name35 = fields.Date(required=False)
    name36 = fields.Date(required=False)
    name37 = fields.Date(required=False)
    name38 = fields.Date(required=False)
    name39 = fields.Date(required=False)
    name40 = fields.Date(required=False)



class perf_datetime(models.Model):
    """ 
    description 
    """
    _name = 'perf.datetime'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Datetime(required=False)
    name2 = fields.Datetime(required=False)
    name3 = fields.Datetime(required=False)
    name4 = fields.Datetime(required=False)
    name5 = fields.Datetime(required=False)
    name6 = fields.Datetime(required=False)
    name7 = fields.Datetime(required=False)
    name8 = fields.Datetime(required=False)
    name9 = fields.Datetime(required=False)
    name10 = fields.Datetime(required=False)
    name11 = fields.Datetime(required=False)
    name12 = fields.Datetime(required=False)
    name13 = fields.Datetime(required=False)
    name14 = fields.Datetime(required=False)
    name15 = fields.Datetime(required=False)
    name16 = fields.Datetime(required=False)
    name17 = fields.Datetime(required=False)
    name18 = fields.Datetime(required=False)
    name19 = fields.Datetime(required=False)
    name20 = fields.Datetime(required=False)
    name21 = fields.Datetime(required=False)
    name22 = fields.Datetime(required=False)
    name23 = fields.Datetime(required=False)
    name24 = fields.Datetime(required=False)
    name25 = fields.Datetime(required=False)
    name26 = fields.Datetime(required=False)
    name27 = fields.Datetime(required=False)
    name28 = fields.Datetime(required=False)
    name29 = fields.Datetime(required=False)
    name30 = fields.Datetime(required=False)
    name31 = fields.Datetime(required=False)
    name32 = fields.Datetime(required=False)
    name33 = fields.Datetime(required=False)
    name34 = fields.Datetime(required=False)
    name35 = fields.Datetime(required=False)
    name36 = fields.Datetime(required=False)
    name37 = fields.Datetime(required=False)
    name38 = fields.Datetime(required=False)
    name39 = fields.Datetime(required=False)
    name40 = fields.Datetime(required=False)
    


class perf_many2one(models.Model):
    """ 
    description 
    """
    _name = 'perf.many2one'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name2 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name3 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name4 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name5 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name6 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name7 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name8 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name9 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name10 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name11 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name12 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name13 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name14 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name15 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name16 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name17 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name18 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name19 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name20 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name21 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name22 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name23 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name24 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name25 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name26 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name27 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name28 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name29 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name30 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name31 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name32 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name33 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name34 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name35 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name36 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name37 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name38 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name39 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    name40 = fields.Many2one('perf.char', required=False, ondelete='restrict')
    


class perf_one2many(models.Model):
    """ 
    description 
    """
    _name = 'perf.one2many'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.One2many('perf.char', 'name_one2many_id')
    name2 = fields.One2many('perf.char', 'name_one2many_id')
    name3 = fields.One2many('perf.char', 'name_one2many_id')
    name4 = fields.One2many('perf.char', 'name_one2many_id')
    name5 = fields.One2many('perf.char', 'name_one2many_id')
    name6 = fields.One2many('perf.char', 'name_one2many_id')
    name7 = fields.One2many('perf.char', 'name_one2many_id')
    name8 = fields.One2many('perf.char', 'name_one2many_id')
    name9 = fields.One2many('perf.char', 'name_one2many_id')
    name10 = fields.One2many('perf.char', 'name_one2many_id')
    name11 = fields.One2many('perf.char', 'name_one2many_id')
    name12 = fields.One2many('perf.char', 'name_one2many_id')
    name13 = fields.One2many('perf.char', 'name_one2many_id')
    name14 = fields.One2many('perf.char', 'name_one2many_id')
    name15 = fields.One2many('perf.char', 'name_one2many_id')
    name16 = fields.One2many('perf.char', 'name_one2many_id')
    name17 = fields.One2many('perf.char', 'name_one2many_id')
    name18 = fields.One2many('perf.char', 'name_one2many_id')
    name19 = fields.One2many('perf.char', 'name_one2many_id')
    name20 = fields.One2many('perf.char', 'name_one2many_id')
    name21 = fields.One2many('perf.char', 'name_one2many_id')
    name22 = fields.One2many('perf.char', 'name_one2many_id')
    name23 = fields.One2many('perf.char', 'name_one2many_id')
    name24 = fields.One2many('perf.char', 'name_one2many_id')
    name25 = fields.One2many('perf.char', 'name_one2many_id')
    name26 = fields.One2many('perf.char', 'name_one2many_id')
    name27 = fields.One2many('perf.char', 'name_one2many_id')
    name28 = fields.One2many('perf.char', 'name_one2many_id')
    name29 = fields.One2many('perf.char', 'name_one2many_id')
    name30 = fields.One2many('perf.char', 'name_one2many_id')
    name31 = fields.One2many('perf.char', 'name_one2many_id')
    name32 = fields.One2many('perf.char', 'name_one2many_id')
    name33 = fields.One2many('perf.char', 'name_one2many_id')
    name34 = fields.One2many('perf.char', 'name_one2many_id')
    name35 = fields.One2many('perf.char', 'name_one2many_id')
    name36 = fields.One2many('perf.char', 'name_one2many_id')
    name37 = fields.One2many('perf.char', 'name_one2many_id')
    name38 = fields.One2many('perf.char', 'name_one2many_id')
    name39 = fields.One2many('perf.char', 'name_one2many_id')
    name40 = fields.One2many('perf.char', 'name_one2many_id')



class perf_text(models.Model):
    """ 
    description 
    """
    _name = 'perf.text'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Text(required=False)
    name2 = fields.Text(required=False)
    name3 = fields.Text(required=False)
    name4 = fields.Text(required=False)
    name5 = fields.Text(required=False)
    name6 = fields.Text(required=False)
    name7 = fields.Text(required=False)
    name8 = fields.Text(required=False)
    name9 = fields.Text(required=False)
    name10 = fields.Text(required=False)
    name11 = fields.Text(required=False)
    name12 = fields.Text(required=False)
    name13 = fields.Text(required=False)
    name14 = fields.Text(required=False)
    name15 = fields.Text(required=False)
    name16 = fields.Text(required=False)
    name17 = fields.Text(required=False)
    name18 = fields.Text(required=False)
    name19 = fields.Text(required=False)
    name20 = fields.Text(required=False)
    name21 = fields.Text(required=False)
    name22 = fields.Text(required=False)
    name23 = fields.Text(required=False)
    name24 = fields.Text(required=False)
    name25 = fields.Text(required=False)
    name26 = fields.Text(required=False)
    name27 = fields.Text(required=False)
    name28 = fields.Text(required=False)
    name29 = fields.Text(required=False)
    name30 = fields.Text(required=False)
    name31 = fields.Text(required=False)
    name32 = fields.Text(required=False)
    name33 = fields.Text(required=False)
    name34 = fields.Text(required=False)
    name35 = fields.Text(required=False)
    name36 = fields.Text(required=False)
    name37 = fields.Text(required=False)
    name38 = fields.Text(required=False)
    name39 = fields.Text(required=False)
    name40 = fields.Text(required=False)
    


class perf_html(models.Model):
    """ 
    description 
    """
    _name = 'perf.html'
    _description = 'description'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Html(required=False)
    name2 = fields.Html(required=False)
    name3 = fields.Html(required=False)
    name4 = fields.Html(required=False)
    name5 = fields.Html(required=False)
    name6 = fields.Html(required=False)
    name7 = fields.Html(required=False)
    name8 = fields.Html(required=False)
    name9 = fields.Html(required=False)
    name10 = fields.Html(required=False)
    name11 = fields.Html(required=False)
    name12 = fields.Html(required=False)
    name13 = fields.Html(required=False)
    name14 = fields.Html(required=False)
    name15 = fields.Html(required=False)
    name16 = fields.Html(required=False)
    name17 = fields.Html(required=False)
    name18 = fields.Html(required=False)
    name19 = fields.Html(required=False)
    name20 = fields.Html(required=False)
    name21 = fields.Html(required=False)
    name22 = fields.Html(required=False)
    name23 = fields.Html(required=False)
    name24 = fields.Html(required=False)
    name25 = fields.Html(required=False)
    name26 = fields.Html(required=False)
    name27 = fields.Html(required=False)
    name28 = fields.Html(required=False)
    name29 = fields.Html(required=False)
    name30 = fields.Html(required=False)
    name31 = fields.Html(required=False)
    name32 = fields.Html(required=False)
    name33 = fields.Html(required=False)
    name34 = fields.Html(required=False)
    name35 = fields.Html(required=False)
    name36 = fields.Html(required=False)
    name37 = fields.Html(required=False)
    name38 = fields.Html(required=False)
    name39 = fields.Html(required=False)
    name40 = fields.Html(required=False)
    
    

class perf_selection(models.Model):
    """ 
    description 
    """
    _name = 'perf.selection'
    _description = 'description'
    
    @api.model
    def _name_get(self):
        return [
                ('key', 'value'),
                ('key1', 'value1'),
                ('key2', 'value2'),
                ('key3', 'value3'),
                ('key4', 'value4'),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Selection('_name_get', required=False)
    name2 = fields.Selection('_name_get', required=False)
    name3 = fields.Selection('_name_get', required=False)
    name4 = fields.Selection('_name_get', required=False)
    name5 = fields.Selection('_name_get', required=False)
    name6 = fields.Selection('_name_get', required=False)
    name7 = fields.Selection('_name_get', required=False)
    name8 = fields.Selection('_name_get', required=False)
    name9 = fields.Selection('_name_get', required=False)
    name10 = fields.Selection('_name_get', required=False)
    name11 = fields.Selection('_name_get', required=False)
    name12 = fields.Selection('_name_get', required=False)
    name13 = fields.Selection('_name_get', required=False)
    name14 = fields.Selection('_name_get', required=False)
    name15 = fields.Selection('_name_get', required=False)
    name16 = fields.Selection('_name_get', required=False)
    name17 = fields.Selection('_name_get', required=False)
    name18 = fields.Selection('_name_get', required=False)
    name19 = fields.Selection('_name_get', required=False)
    name20 = fields.Selection('_name_get', required=False)
    name21 = fields.Selection('_name_get', required=False)
    name22 = fields.Selection('_name_get', required=False)
    name23 = fields.Selection('_name_get', required=False)
    name24 = fields.Selection('_name_get', required=False)
    name25 = fields.Selection('_name_get', required=False)
    name26 = fields.Selection('_name_get', required=False)
    name27 = fields.Selection('_name_get', required=False)
    name28 = fields.Selection('_name_get', required=False)
    name29 = fields.Selection('_name_get', required=False)
    name30 = fields.Selection('_name_get', required=False)
    name31 = fields.Selection('_name_get', required=False)
    name32 = fields.Selection('_name_get', required=False)
    name33 = fields.Selection('_name_get', required=False)
    name34 = fields.Selection('_name_get', required=False)
    name35 = fields.Selection('_name_get', required=False)
    name36 = fields.Selection('_name_get', required=False)
    name37 = fields.Selection('_name_get', required=False)
    name38 = fields.Selection('_name_get', required=False)
    name39 = fields.Selection('_name_get', required=False)
    name40 = fields.Selection('_name_get', required=False)
    
    
    
class perf_many2many(models.Model):
    """ 
    description 
    """
    _name = 'perf.many2many'
    _description = 'description'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name1 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name2 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name3 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name4 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name5 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name6 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name7 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name8 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name9 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name10 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name11 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name12 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name13 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name14 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name15 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name16 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name17 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name18 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name19 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name20 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name21 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name22 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name23 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name24 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name25 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name26 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name27 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name28 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name29 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name30 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name31 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name32 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name33 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name34 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name35 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name36 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name37 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name38 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name39 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)
    name40 = fields.Many2many('perf.char', 'perf_name_perf_many2many_rel', 'name_id', 'many2many_id', required=False)    
    