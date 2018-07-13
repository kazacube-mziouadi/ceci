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

odoo.define('web_tree_field_color', function (require) {
	"use strict";

	var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;
    var ListView = require('web.ListView');
	
	var fn_color = function(record, column){
		if (column.colors)
		{
			
		  var test = _(column.colors.split(';')).chain()
          .compact()
          .map(function(color_pair) {
              var pair = color_pair.split(':'),
                  color = pair[0],
                  expr = pair[1];
              return [color, py.parse(py.tokenize(expr)), expr];
          }).value();
		  var context = _.extend({}, record.attributes, {
				uid: this.session.uid,
				current_date: new Date().toString('yyyy-MM-dd')
			});
		  for(var i=0, len=test.length; i<len; ++i) {
	            var pair = test[i];
	            var color = pair[0];
	            var expression = pair[1];
	            if (py.evaluate(expression, context).toJSON()) {
	                return 'background-color: ' + color + ';';
	            }
		  }
		};
	};

    ListView.include({ 

        init: function(){
            this._super.apply(this, arguments);
            this.group_colors = null;
            this.list_widget_registry = core.list_widget_registry;
        },
        load_list: function(data) {
            if (this.fields_view.arch.attrs.group_colors) {
                this.group_colors = _(this.fields_view.arch.attrs.group_colors.split(';')).chain()
                    .compact()
                    .map(function(color_pair) {
                        var pair = color_pair.split(':'),
                            color = pair[0],
                            expr = pair[1];
                        return [color, py.parse(py.tokenize(expr)), expr];
                    }).value();
            }
            this._super(data);
        },
        /** la seule modif de la fonction est l'avg_group
         * Computes the aggregates for the current list view, either on the
         * records provided or on the records of the internal
         * :js:class:`~instance.web.ListView.Group`, by calling
         * :js:func:`~instance.web.ListView.group.get_records`.
         *
         * Then displays the aggregates in the table through
         * :js:method:`~instance.web.ListView.display_aggregates`.
         *
         * @param {Array} [records]
         */
        compute_aggregates: function (records) {
            var columns = _(this.aggregate_columns).filter(function (column) {
                return column['function']; });
            if (_.isEmpty(columns)) { return; }

            if (_.isEmpty(records)) {
                records = this.groups.get_records();
            }
            records = _(records).compact();

            var count = 0, sums = {};
            _(columns).each(function (column) {
                switch (column['function']) {
                    case 'max':
                        sums[column.id] = -Infinity;
                        break;
                    case 'min':
                        sums[column.id] = Infinity;
                        break;
                    default:
                        sums[column.id] = 0;
                }
            });
            _(records).each(function (record) {
                count += record.count || 1;
                _(columns).each(function (column) {
                    var field = column.id,
                        value = record.values[field];
                    switch (column['function']) {
                        case 'sum':
                            if (!isNaN(value)) {
                                sums[field] += Number(value);
                            }
                            break;
                        case 'avg':
                            sums[field] += record.count * value;
                            break;
                        case 'min':
                            if (sums[field] > value) {
                                sums[field] = value;
                            }
                            break;
                        case 'max':
                            if (sums[field] < value) {
                                sums[field] = value;
                            }
                            break;
                    }
                });
            });

            var aggregates = {};
            _(columns).each(function (column) {
                if (column.label) {
                    var field = column.id;
                    switch (column['function']) {
                        case 'avg':
                            aggregates[field] = {value: sums[field] / count};
                            break;
                        case 'avg_group':  // la seule modif de la fonction est l'avg_group
                            aggregates[field] = {value: eval(column.avg_func)};
                            break;
                        default:
                            aggregates[field] = {value: sums[field]};
                    }
                }
            });

            this.display_aggregates(aggregates);
        },
    });

	ListView.List.include({
		init: function (group, opts){
			this._super(group, opts);
			this.columns.get_display_color = fn_color;
		},
		get_display_color: fn_color,
		render: function () {
	        this.$current.empty().append(
	            QWeb.render('ListView.rows', _.extend({
	                    render_cell: function () {
	                        return self.render_cell.apply(self, arguments); },
	                    get_display_color: function(){
	                    	return self.fn_color.apply(self, arguments);
	                    },
	                    readonly: this.view.getParent() && this.view.getParent().getParent().get('effective_readonly'),
	                }, this)));
	        this.pad_table_to(4);
	    },
	    render_record: function (record) {
	        var self = this;
	        var index = this.records.indexOf(record);
	        var columns = this.columns;
	        var ret = QWeb.render('ListView.row', {
	            columns: columns,
	            options: this.options,
	            record: record,
	            row_parity: (index % 2 === 0) ? 'even' : 'odd',
	            view: this.view,
	            render_cell: function () {
	                return self.render_cell.apply(self, arguments); },
		        get_display_color: function(){
		        	return fn_color.apply(self, arguments);
		        }
	        });
	        var ret2 = $(ret);
	        _.each(self.columns, function(column) {
            	if (column.column_invisible) {
            		if (!self.view.getParent()) {
            			return true;
            		}
					var fm = self.view.getParent().getParent()._ic_field_manager;
                    var invisible = fm.compute_domain(py.eval(column.column_invisible));
                    if (invisible) {
                        ret2.find('[data-field='+column.name+']').hide();
                    } else {
                        ret2.find('[data-field='+column.name+']').show();
                    }
					return !invisible;
            	} else {
            		return true;
            	}
	        });
	        return ret2[0].outerHTML;
	    },	
	});

	ListView.Groups.include({
    	render_groups: function (datagroups) {
            var self = this;
            var placeholder = this.make_fragment();
            
            var group_colors = self.view.group_colors;
            
            _(datagroups).each(function (group) { 
            	
            	// create dictionnary with
            	// key = tree field in the group
            	// value = list of dictionnary with {'color': color, 'expression': expression}
            	var group_colors_parsed = new Object();
            	_(group_colors).each(function (groupe) {
            		var obje = new Object();
            		var g = groupe[1];
            		obje['expression'] = groupe[2] 
            		obje['color'] = groupe[0] 
            		_(g.expressions).each(function (exp){
            			if ($.inArray(exp.value, _.keys(group.aggregates)) >= 0){
            				if (group_colors_parsed[exp.value] == undefined){
            					group_colors_parsed[exp.value] = [];
            				}
            				group_colors_parsed[exp.value].push(obje);
            			}
            		})
            	});
                if (self.children[group.value]) {
                    self.records.proxy(group.value).reset();
                    delete self.children[group.value];
                }
                var child = self.children[group.value] = new (self.view.options.GroupsType)(self.view, {
                    records: self.records.proxy(group.value),
                    options: self.options,
                    columns: self.columns
                });
                self.bind_child_events(child);
                child.datagroup = group;
                var $row = child.$row = $('<tr class="oe_group_header">');
                if (group.openable && group.length) {
                    $row.click(function (e) {
                        if (!$row.data('open')) {
                            $row.data('open', true)
                                .find('span.ui-icon')
                                    .removeClass('ui-icon-triangle-1-e')
                                    .addClass('ui-icon-triangle-1-s');
                            child.open(self.point_insertion(e.currentTarget));
                        } else {
                            $row.removeData('open')
                                .find('span.ui-icon')
                                    .removeClass('ui-icon-triangle-1-s')
                                    .addClass('ui-icon-triangle-1-e');
                            child.close();
                        }
                    });
                }
                placeholder.appendChild($row[0]);

                var $group_column = $('<th class="oe-group-name">').appendTo($row);
                // Don't fill this if group_by_no_leaf but no group_by
                if (group.grouped_on) {
					var row_data = {};
					row_data[group.grouped_on] = group;
					var group_label = _t("Undefined");
					var group_column = _(self.columns).detect(function (column) {
						return column.id === group.grouped_on; });
					if (group_column) {
						try {
							group_label = group_column.format(row_data, {
								value_if_empty: _t("Undefined"),
								process_modifiers: false
							});
						} catch (e) {
							group_label = _.str.escapeHTML(row_data[group_column.id].value);
						}
					} else {
						group_label = group.value;
						if (group_label instanceof Array) {
							group_label = group_label[1];
						}
						if (group_label === false) {
							group_label = _t('Undefined');
						}
						group_label = _.str.escapeHTML(group_label);
					}
						
					// group_label is html-clean (through format or explicit
					// escaping if format failed), can inject straight into HTML
					$group_column.html(_.str.sprintf(_t("%s (%d)"),
						group_label, group.length));

					if (group.length && group.openable) {
						// Make openable if not terminal group & group_by_no_leaf
						$group_column.prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
					} else {
						// Kinda-ugly hack: jquery-ui has no "empty" icon, so set
						// wonky background position to ensure nothing is displayed
						// there but the rest of the behavior is ui-icon's
						$group_column.prepend('<span class="ui-icon" style="float: left; background-position: 150px 150px">');
					}
				} 
                self.indent($group_column, group.level); 
                if (self.options.selectable) {
                    $row.append('<td>');
                }
                if (self.options.isClarkGable) {
                    $row.append('<td>');
                }
                _(self.columns).chain()
                .filter(function (column) { return column.invisible !== '1'; })
                .each(function (column) {
                    if (column.meta) {
                        // do not do anything
                    } else if (column.id in group.aggregates) {
                        var r = {};
                        r[column.id] = {value: group.aggregates[column.id]};
                        var td_create = $('<td class="oe_number">')
                            .html(column.format(r, {process_modifiers: false}))
                            .appendTo($row);
                        // parse color, evaluate Python expression and add add css-class to the td element
                        if ($.inArray(column.id, _.keys(group_colors_parsed)) >= 0){
                            var g = group_colors_parsed[column.id];
                            _(group_colors_parsed[column.id]).each(function (g){
                                var expression = g.expression.replace(column.id, group.aggregates[column.id].toString());
                                if (py.eval(expression)) {
                                    td_create.css('background-color', g.color);
                                }
                            })
                        }
                    } else {
                        $row.append('<td>');
                    }
                });
                if (self.options.deletable) {
                    $row.append('<td class="oe-group-pagination">');
                }
            });
            return placeholder;  
        },
    });

	core.list_widget_registry.map.field.include({
		/**
         * Sets up the listview's columns: merges view and fields data, move
         * grouped-by columns to the front of the columns list and make them all
         * visible.
         *
         * @param {Object} fields fields_view_get's fields section
         * @param {Boolean} [grouped] Should the grouping columns (group and count) be displayed
         */
        to_aggregate: function () {
            if (this.type !== 'integer' && this.type !== 'float' && this.type !== 'monetary' && this.type !== 'text') {
                return {};
            }
            var aggregation_func = this['group_operator'] || this['avg_group'] || this['avg'] || 'sum';
            var C = function (fn, label, avg_func) {
                this['function'] = fn;
                this.label = label;
                this.avg_func = avg_func;
            };
            C.prototype = this;
            // Ajout de l'avg et de l'avg_group
            if(this.avg){
                return new C('avg', 'avg' , null);
            }
            if (this.avg_group){
                return new C('avg_group', 'avg_group' , aggregation_func);
            }
            return new C(aggregation_func, this[aggregation_func], null);
        },
	});

	return ListView;
});
