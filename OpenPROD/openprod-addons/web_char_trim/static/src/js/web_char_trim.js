//# -*- coding: utf-8 -*-
//##############################################################################
//#
//#    OpenERP, Open Source Management Solution
//#    Copyright (C) 2015 Objectif-PI ([http://www.objectif-pi.com]).
//#       Damien CRIER <damien.crier@objectif-pi.com>
//#
//#    This program is free software: you can redistribute it and/or modify
//#    it under the terms of the GNU Affero General Public License as
//#    published by the Free Software Foundation, either version 3 of the
//#    License, or (at your option) any later version.
//#
//#    This program is distributed in the hope that it will be useful,
//#    but WITHOUT ANY WARRANTY; without even the implied warranty of
//#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//#    GNU Affero General Public License for more details.
//#
//#    You should have received a copy of the GNU Affero General Public License
//#    along with this program.  If not, see [http://www.gnu.org/licenses/].
//#
//##############################################################################


// Web char trim
// ==================

// Etant donné que `formats.js` ne permet pas de surcharger les différents types de widgets
// nous allons donc *monkey patcher* les deux fonctions de *parsing* et *formatting*.

odoo.define('web_char_trim', function web_char_trim(require) {
'use strict';
    var WebFormats = require('web.formats');
    var _ = window._;
    var parse_value = WebFormats.parse_value;
    WebFormats.parse_value = function (value, descriptor, value_if_empty){
            if ((descriptor.field && descriptor.field.type == 'char') || (descriptor.field && descriptor.field.type == 'text') || descriptor.type == 'char' || descriptor.type == 'text') {
        	    if (value != false && value != "false"){
                    value = $.trim(value);
                    return value;    
                }
            }
            return parse_value(value, descriptor, value_if_empty);
    };
    var format_value = WebFormats.format_value;
    WebFormats.format_value = function (value, descriptor, value_if_empty) {
            if ( (descriptor.field && descriptor.field.type == 'char') || (descriptor.field && descriptor.field.type == 'text') || descriptor.type == 'char' || descriptor.type == 'text') {
            	if (value != false && value != "false"){
            		value = $.trim(value);
                    return value;
        	    }
            }
            return format_value(value, descriptor, value_if_empty);
    };   
    return WebFormats;
});
