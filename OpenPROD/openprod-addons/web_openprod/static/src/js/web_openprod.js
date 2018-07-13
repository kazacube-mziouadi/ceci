//##############################################################################
//#
//#    OpenERP, Open Source Management Solution
//#    Copyright (C) 2015 Objectif-PI ([http://www.objectif-pi.com]).
//#       Damien CRIER [damien.crier@objectif-pi.com]
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

odoo.define('web_openprod', function(require) {
    var ActionManager = require('web.ActionManager');
    var core = require('web.core');

    ActionManager.include({
    	ir_actions_act_window_noclose: function(){
    	},
    	ir_actions_act_window_next: function(action, options){
    	    var model = action.context.model;
    	    core.bus.trigger('act_next', model);
    	},
    	ir_actions_act_window_dialog_reload: function(action, options){
    		var widget = this.dialog_widget_stack[this.dialog_widget_stack.length - 1] || this.dialog_widget;
        	widget.views.form.controller.reload();
    	},
    	ir_actions_act_add_domain: function(action, options) {
    			window.new_domain = action.domain;
        		this.dialog_stop();
    	},
    	ir_actions_act_window_dialog_parent_reload: function(action, options){
            var widget = this.dialog_widget;
            widget.views.form.controller.reload();
        this.dialog_stop();
        },
    });
    
    $(window.document).on('focus', '.oe_list_header_search input', function(ev){
    	var t = $(ev.target);
    	var old_selected = $('.input_selected').toggleClass('input_selected');
    	t.toggleClass('input_selected');
    });
    
    $(window.document).on('blur', '.oe_list_header_search input', function(ev){
    	var t = $(ev.relatedTarget || document.activeElement);
    	if (!t.hasClass('search_type')){
        	$(ev.target).removeClass('input_selected');
    	}
    });
});
