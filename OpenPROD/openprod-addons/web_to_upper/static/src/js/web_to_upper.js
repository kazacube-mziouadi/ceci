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


// Web to upper
// ==================

// Etant donné que `formats.js` ne permet pas de surcharger les différents types de widgets
// nous allons donc *monkey patcher* les deux fonctions de *parsing* et *formatting*.

odoo.define('web_to_upper', function web_to_upper(require) {
'use strict';

    // Pour exclure un caractère de la mise en majuscules, il faut l'ajouter
    // dans l'expression régulière suivante :
    var upper_regex = /[^µ]/g

    // Exemple : l'expression /[^µ]/g ne mettra pas en majuscules le caractère "µ"

    function capitalize(str) {
        if (typeof str === 'string')
        return str.replace(upper_regex, function(txt) {
            return txt.toUpperCase();
        });
        return str;
    };


    var WebFormats = require('web.formats');
    var _ = window._;
    var parse_value = WebFormats.parse_value;
    WebFormats.parse_value = function (value, descriptor, value_if_empty){
        value = parse_value(value, descriptor, value_if_empty);
        switch (descriptor.widget || descriptor.type || (descriptor.field && descriptor.field.type)) {
	    	case 'toupper':
                if (value != false && value != "false" && typeof value !== "undefined"){
	        		value = capitalize(value);
	        	}
        } 
        return value;
    };
    var format_value = WebFormats.format_value;
    WebFormats.format_value = function (value, descriptor, value_if_empty) {
        value = format_value(value, descriptor, value_if_empty);
        switch (descriptor.widget || descriptor.type || (descriptor.field && descriptor.field.type)) {
	    	case 'toupper':
                if (value != false && value != "false" && typeof value !== "undefined"){
	        		value = capitalize(value);
	        	}
            }
        return value;
    };   
    return WebFormats;
});
