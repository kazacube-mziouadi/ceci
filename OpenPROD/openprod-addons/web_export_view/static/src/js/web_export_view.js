//  @@@ web_export_view custom JS @@@
//#############################################################################
//    
//    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
//    Copyright (C) 2012 Therp BV (<http://therp.nl>)
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as published
//    by the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
//#############################################################################
odoo.define('web_export_view', function(require) {
"use strict";
var core = require('web.core');
var Sidebar = require('web.Sidebar');
var formats = require('web.formats');

var _t = core._t,
    QWeb = core.qweb;
var py = window.py;

Sidebar.include({
	add_toolbar: function (toolbar) {
        var self = this;
        this._super(toolbar);
        var view = self.getParent();
        var view_manager = view.getParent();
        var action = view_manager.action;
        var security_rule = action && action.security_rule;

        if (!security_rule) {
            return;
        }

        if (_.isObject(security_rule) && !security_rule.is_admin && !(security_rule.can_export && security_rule.show_export_current)) {
            return;
        }
        self.add_items("other", [{
            label:_t("Export Current View"),
            callback: self.on_sidebar_export_view_xls
        }]);
	},

    on_sidebar_export_view_xls: function () {
        // Select the first list of the current (form) view
        // or assume the main view is a list view and use that
        var self = this,
            view = this.getParent(),
            children = view.getChildren();
        if (children) {
            children.every(function (child) {
                if (child.field && child.field.type == 'one2many') {
                    view = child.viewmanager.views.list.controller;
                    return false; // break out of the loop
                }
                if (child.field && child.field.type == 'many2many') {
                    view = child.list_view;
                    return false; // break out of the loop
                }
                return true;
            });
        }
        var export_columns_keys = [];
        var export_columns_names = [];
        $.each(view.visible_columns, function () {
            if (this.tag == 'field') {
                // non-fields like `_group` or buttons
                export_columns_keys.push(this.id);
                export_columns_names.push(this.string);
            }
        });
        var rows = view.$el.find('.oe_list_content > tbody > tr');
        var export_rows = [];
        var group = !!view.$el.find('.oe_group_header').length;
        if (group)
        	export_columns_names.unshift(_t('Group'));
        $.each(rows, function () {
        	var $row = $(this);
        	// find only rows with data
        	if($row.attr('data-id')){
        		var export_row = [];
                if (group)
                	export_row.push('');
        		var checked = $row.find('th input[type=checkbox]').prop("checked");
        		if (children && checked) {
        			$.each(export_columns_keys, function () {
        				var cell = $row.find('td[data-field="' + this + '"]').get(0);
        				var text = cell.text || cell.textContent || cell.innerHTML || "";
        				if (cell.classList.contains("oe_list_field_float")) {
        					export_row.push(formats.parse_value(text, {'type': "float"}));
        				}
        				else if (cell.classList.contains("oe_list_field_boolean")) {
        					var data_id = $('<div>' + cell.innerHTML + '</div>');
        					if (data_id.find('input').get(0).checked) {
        						export_row.push(_t("True"));
        					}
        					else {
        						export_row.push(_t("False"));
        					}
        				}
        				else if (cell.classList.contains("oe_list_field_integer")) {
        					var tmp2 = text;
        					do {
        						var tmp = tmp2;
        						tmp2 = tmp.replace(_t.database.parameters.thousands_sep, "");
        					} while (tmp !== tmp2);

        					export_row.push(parseInt(tmp2));
        				}
        				else {
        					export_row.push(text.trim());
        				}
        			});
        			export_rows.push(export_row);
        		}
        	} else {
        		var $header = $row.find('th.oe_list_group_name').get(0);
        		if ($header) {
        			export_row = [];
        			export_row.push($header.textContent);
        			var dataRows = $row.find('td');
        			dataRows = dataRows.slice(dataRows.length - export_columns_keys.length, dataRows.length);
        			_.each(dataRows, function(e) {
        				export_row.push(e.textContent);
        			});
        			export_rows.push(export_row);
        		}
        	}
        });
        $.blockUI();
        var group_by = view.getParent().searchview.build_search_data().groupbys;
        var domain = _.reduce(
            _.map(
                this.getParent().getParent().searchview.build_search_data().domains,
                function(domain){
                    if (_.isString(domain)) {
                        // Pour le filtre date echeance depasse, permet de resoudre le probleme du datetime de l'interpreteur python
                        domain = domain.replace("[('date_due','<=',(datetime.date.today().strftime('%Y-%m-%d'))), ('state', 'not in', ['paid','cancel'])]" , 
                        "[('date_due','<=','"+ moment().format('YYYY-MM-DD') +"'), ('state', 'not in', ['paid','cancel'])]");
                        return py.eval(domain);
                    } else if (_.isArray(domain)) {
                        return domain;
                    } else {
                        return domain.eval();
                    }
                }),
            function(memo, num) {return Array.prototype.concat(memo, num);},
            []);
        domain.concat(this.getParent().dataset.domain);
        view.session.get_file({
            url: '/web/export/xls_view',
            data: {data: JSON.stringify({
                model: view.model,
                headers: export_columns_names,
                rows: export_rows,
                group: group,
                group_by: group_by,
                domain: domain,
            })},
            complete: $.unblockUI
        });
    }
});

});
