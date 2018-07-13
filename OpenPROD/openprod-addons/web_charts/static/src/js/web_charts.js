odoo.define('web_charts', function(require) {
	"use strict";

	var core = require('web.core');
	var View = require('web.View');
	var Model = require('web.DataModel');
	var session = require('web.session');
	var _t= core._t;
	var _lt = core._lt;


	var ChartView = View.extend({
		view_type: 'chart',
		display_name: 'chart',
		icon: 'fa-bar-chart',
		init: function(parent, dataset, view_id, options) {
			this._super(parent, dataset, view_id, options);
			this.model = new Model(dataset.model, {group_by_no_leaf: true});
			this.start_date = moment().format('YYYY-MM-DD');
			this.end_date = moment().add(3, 'w').format('YYYY-MM-DD');
			this.tempo = 'week';
			this.when_loaded = $.Deferred();
		},
		view_loading: function (fvg) {
			var self = this;
			this.name = this.ViewManager.title;
			this.columns = [];
			this.column_colors = [];
			this.endpoint = fvg.arch.attrs.action;
			_.each(fvg.arch.children, function(field) {
				if (field.attrs.type == 'measure') {
					self.columns.push(field.attrs.name);
				}
				if ('color' in field.attrs) {
					self.column_colors[field.attrs.name] = field.attrs.color;
				}
			});
			this.rows = [];
			_.each(fvg.arch.children, function(field) {
				if (field.attrs.type == 'row') {
					self.rows.push(field.attrs.name);
				}
			});
		},
		do_search: function (domain, context) {
			this.domain = domain;
			this.context = context;
			this.load_data(domain, context);
		},
		events: {
			'click .group_day': 'group_day',
			'click .group_week': 'group_week',
			'click .group_month': 'group_month',
			'click .validate_date': 'validate_date',
			'change .start_date': 'change_start_date',
			'change .end_date': 'change_end_date',
		},
		load_data: function(domain, context) {
			domain = domain.slice();
			var group_by = this.rows.slice();
			group_by[0] += ':' + this.tempo;
			this.when_loaded = session.rpc(this.endpoint, {
				start_date: this.start_date,
				end_date: this.end_date,
				domain: domain,
				group_period: this.tempo,
			})
			this.do_show();
		},
		do_show: function() {
			var self = this;
			this.when_loaded.then(function(calendar) {
				self.do_push_state({});
				self.$el.empty();
				var controls = $("<div>\
						<h4>" + _t('Group by') + "</h4>\
						<button class='group_day btn oe_button'>" + _t('Day') + "</button>\
						<button class='group_week btn oe_button'>" + _t('Week') + "</button>\
						<button class='group_month btn oe_button'>" + _t('Month') + "</button>\
						<span>" + _t('Start') + " :</span><input type='date' class='start_date' />\
						<span>" + _t('End') + " :</span><input type='date' class='end_date' />\
						<button class=\"validate_date\">" + _t('Ok') + "</button>\
				</div>");
				var chart = $("<div></div>");
				controls.appendTo(self.$el);
				chart.appendTo(self.$el);
				self.$('.start_date').val(self.start_date);
				self.$('.end_date').val(self.end_date);
				var aggregated_dates = _.uniq(_.keys(_.values(calendar)[0]));
				var series = self.get_series(calendar);
				chart.highcharts({
					chart: { type: 'column' },
					xAxis: { categories: aggregated_dates },
					yAxis: [{min: 0, title: ''}],
					plotOptions: {
						column: {
							grouping: false,
							shadow: false,
							borderWidth: 0
						}
					},
					series: series,
					title: {
						text: self.name,
						style: {
							fontSize:'24px',
							fontWeight: 'bold',
						},
					},
					legend: {
						enabled: false,
					},
				})
			})
		},
		get_series: function(cal) {
			var data = {};
			var self = this;
			var second_keys = [];
			for (var col_k in this.columns ){
				var col = this.columns[col_k];
				for (var res in cal) {
					var key = res + ' / ' + col;
					if (!(key in data)) {
						data[key] = {};
					}
					for (var period in cal[res]) {
						data[key][period] = cal[res][period][col] || 0;
						second_keys.push(res);
					}
				}
			}
			second_keys = _.uniq(second_keys);
			var series = _.map(data, function(val, key, l) {
				var measure = key.split(' / ')[1];
				var second_unit = key.split(' / ')[0];
				var l = second_keys.length;
				var serie = {
						name: key,
						pointPadding: 0.5* (1 - 1 / (l * (1 + _.indexOf(self.columns, measure)/self.columns.length))),
						pointPlacement:  -0.5 + _.indexOf(second_keys, second_unit)/l + 0.5/l,
						data: _.values(val),
				}
				if (measure in self.column_colors) {
					serie.color = self.column_colors[measure];
				};
				return serie;
			})
			return series;
		},
		group_day: function(ev) {
			this.tempo = 'day';
			this.load_data(this.domain, this.context);
		},
		group_week: function(ev) {
			this.tempo = 'week';
			this.load_data(this.domain, this.context);
		},
		group_month: function(ev) {
			this.tempo = 'month';
			this.load_data(this.domain, this.context);
		},
		validate_date: function(ev) {
			this.load_data(this.domain, this.context);
		},
		aggregate_dates: function(calendar, period) {
			var format = "";
			switch (period) {
			case 'day':
				format = "DD MMM YYYY";
				break;
			case 'week':
				format = "[W]w YYYY";
				break;
			case 'month':
				format = "MMMM YYYY";
				break;
			}
			var ret = _.uniq(_.map(calendar, function(day){
				return moment(day[0]).format(format);
			}), true);
			return ret;
		},
		change_start_date: function() {
			this.start_date = this.$('.start_date').val();
		},
		change_end_date: function() {
			this.end_date = this.$('.end_date').val();
		},
	});

	var QualityChartView = View.extend({
	/*	view_type: 'qualitychart',*/
		display_name: 'qualitychart',
		icon: 'fa-area-chart',
		multi_record: false,
		searchable: false,
		view_type:'form',
		events: {
			"change #prod_select":"on_filters_change",
			"change #graph_start_date":"on_filters_change",
			"change #graph_end_date":"on_filters_change",
		},
		form_template: function() {
			return _t("Product") + ":\
			<select id='prod_select'>\
				<option>&nbsp</option>\
				<% _.each(products, function(prod) { %><option value='<%= prod[0] %>'><%= prod[1] %></option><% }); %>\
			</select>" + 
			_t("Start date") + ":<input type='date' id='graph_start_date'/>" +
			_t("End date") + ":<input type='date' id='graph_end_date' />"},
		init: function(parent, dataset, view_id, options) {
			var self = this;
			this._super(parent, dataset, view_id, options);
			this.has_been_loaded = $.Deferred();

			Highcharts.setOptions({
				global: {
					useUTC: false
				}
			});
		},
		view_loading: function(r) {
	        this.has_been_loaded.resolve();
		},
		do_show: function(options, product_id, sdate, edate, no_del_products) {
			var self = this;
			options = options || {};
			this._super();

			var shown = this.has_been_loaded;
			if (options.reload !== false) {
				shown = shown.then(function() {
					var Lines = new Model('quality.control.declaration.line.result');
					var domain = [['control_id', '=', self.dataset.ids[self.dataset.index]]];
					if (product_id) {
						domain.push(['product_id', '=', product_id])
					}
					if (sdate) {
						domain.push(['date', '>=', sdate])
					}
					if (edate) {
						domain.push(['date', '<=', edate])
					}
					var query = Lines.query([]).filter(domain).all();
					query.then(function (res) {
						self.do_push_state({});
						self.$el.empty();
						if (!no_del_products) {
							delete self.products;
						}
						self.$el.append(self.get_form(res));
						self.$('#prod_select option[value=' + product_id + ']').prop('selected', true);
						self.$('#graph_start_date').val(sdate);
						self.$('#graph_end_date').val(edate);
						var chart = $("<div></div>");
						chart.appendTo(self.$el);
						var values = {}, minmax = [];
						_.each(res, function(line) {
							var date = openerp.web.str_to_datetime(line.date).getTime();
							if (!values.hasOwnProperty(line.product_id[0])) {
								values[line.product_id[0]] = []
							}
							values[line.product_id[0]].push([date, parseInt(line.value_target)])
							minmax.push([date, parseInt(line.min), parseInt(line.max)])
						});
						var series = _.map(values, function(el) {
							return {
									name: _t('Values'),
									data: el,
									type: 'scatter',
								}
						});
						series.push({
							name: 'MinMax',
							data: minmax,
							type: 'arearange',
							linkedTo: ':previous',
						});
						chart.highcharts({
							series: series,
							xAxis: {
								type: 'datetime',
							},
							title: {
								text:'',
							},
							plotOptions: {
								arearange: {
									fillOpacity: 0.1,
								}
							}
						});
					})
				});
			}
		},
		get_form: function(data) {
			if (!('products' in this)) {
			//if (data.length) {
				var products = _.uniq(_.map(data, function(line) { return line.product_id }), function(el){ return el[0] });
				this.products = products;
			} else {
				var products = this.products;
			}
			return _.template(this.form_template())({products: products});
		},
		on_filters_change: function(ev) {
			var product_id = parseInt(this.$('#prod_select').val());
			var start_date = this.$('#graph_start_date').val();
			var end_date = this.$('#graph_end_date').val();
			this.do_show({}, product_id, start_date, end_date, true)
		},
	});



	core.view_registry.add('chart', ChartView);
	core.view_registry.add('qualitychart', QualityChartView);

});