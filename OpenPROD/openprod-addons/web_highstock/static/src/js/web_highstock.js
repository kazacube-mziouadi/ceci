openerp.web_highstock = function(instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('highstock', 'instance.web_highstock.HighstockView');
instance.web_highstock.HighstockView = instance.web.View.extend({
    display_name: _lt('Highstock'),
    view_type: "highstock",
    searchable: false, // si true, la vue search est affichée au dessus
    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.ready = $.Deferred();
        this.set_default_options(options);
        this.dataset = dataset;
        this.model = dataset.model;
        this.fields_view = {};
        this.view_id = view_id;
        this.has_been_loaded = $.Deferred();
        this.creating_event_id = null;
        this.dataset_events = [];
        this.COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
             '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
             '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
             '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900' ];
        this.color_map = {};
        this.last_search = [];
        this.range_start = null;
        this.range_stop = null;
//        this.update_range_dates(Date.today());
        this.selected_filters = [];
        this.chart = null;
        this.ids_search = [];
        
        this.title = '';
        this.title_model = '';
		this.title_fields_to_read = '';
        this.x_axis_name = '';
        this.x_axis_field = '';
        this.y_axis_name = '';
        this.y_axis_field = '';
        
        Highcharts.setOptions({
        	lang: {
        		months: Date.CultureInfo.abbreviatedMonthNames,//['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'],
        		weekdays: Date.CultureInfo.dayNames,//['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
        	}
        });
        
        this.config_chart = {
        		xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: {
                        second: '%Y-%m-%d<br/>%H:%M:%S',
                        minute: '%Y-%m-%d<br/>%H:%M',
                        hour: '%Y-%m-%d<br/>%H:%M',
                        day: '%Y<br/>%m-%d',
                        week: '%Y<br/>%m-%d',
                        month: '%Y-%m',
                        year: '%Y'
                    },
        	    	plotLines: [{
        	    		value: Date.now(),
        	    		width: 2,
        	    		color: 'red',
        	    		dashStyle: 'dash',
        	    		label: {
        	    			text: '',
        	    			align: 'right',
        	    			y: 25,
        	    			x: 0
        	    		}
        	    	}]
                },
                scrollbar: {
                    enabled: false
                },
                navigator: {
                	xAxis: {
                		type: 'datetime',
                        dateTimeLabelFormats: {
                            second: '%Y-%m-%d<br/>%H:%M:%S',
                            minute: '%Y-%m-%d<br/>%H:%M',
                            hour: '%Y-%m-%d<br/>%H:%M',
                            day: '%Y<br/>%m-%d',
                            week: '%Y<br/>%m-%d',
                            month: '%Y-%m',
                            year: '%Y'
                        },
                	},
                },
                rangeSelector: {
//                    inputEnabled: $('#container').width() > 480,
//                    selected: 1
                    enabled: false,
                },

                title: {
                	text: this.title
                },
                subtitle: {
                	text: ''
                },

                series: [{
//                    name: 'AAPL Stock Price',
//                    data: data,
                    step: true,
                    tooltip: {
                        valueDecimals: 2,
                    }
                }]
            };
    },
    start: function() {
        this._super();
        return this.rpc("/web/view/load", {"model": this.model, "view_id": this.view_id, "view_type":"highstock", 'toolbar': true}, this.on_loaded);
    },
    stop: function() {
        this._super();
    },
    on_loaded: function(data) {
    	this.fields_view = data;
    	this.parse_fields(this, this.fields_view.arch.children, this.fields_view.fields);
    	this.color_values = [];
    	this.info_fields = [];
    	
    	this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
    	this.view_id = this.fields_view.view_id;
    	
    	// mode, one of month, week or day
    	this.mode = this.fields_view.arch.attrs.mode;
    	
    	this.fields =  this.fields_view.fields;
    	
    	for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
    		this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
    	}
    	this.$element.html(QWeb.render("HighstockView", {"fields_view": this.fields_view}));
    	
        if (this.dataset.ids.length == 0){
//        	var aa = this.do_search(this.dataset.domain, context);
//        	this.ids = this.do_search_domain(this.dataset.domain, this);
        	this.dataset.ids = this.dataset.context.active_ids;
        	this.last_search[0] = this.dataset.domain;
        	this.do_ranged_search();
        }
        else{
        	this.ids = this.dataset.ids;
//        	this.last_search[0] = this.dataset.domain;
//        	this.do_ranged_search();
        }

//        this.init_highstock();
        this.has_been_loaded.resolve();
    },
    parse_fields: function(self, f_arch, f_obj){
    	_.each(f_arch, function(f){
    		if (f.attrs.usage == 'x'){
    			self.x_axis_field = f.attrs.name;
    			self.x_axis_name = f.attrs.label;
    		}
    		else if (f.attrs.usage == 'y'){
    			self.y_axis_field = f.attrs.name;
    			self.y_axis_name = f.attrs.label;
    		}
    		else if (f.attrs.usage == 'title'){
    			self.title_obj_name = f.attrs.name;
    			self.title_model = f_obj[f.attrs.name].relation;
    			self.title_id = f_obj[f.attrs.name].id;
    			self.title_fields_to_read = f.attrs.fields_to_read;
    		}
    	});
    },
    do_search_domain: function(domain, self){
    	aaa = self.dataset.read_slice(['id'], {
            offset: 0,
            domain: domain,
            context: self.last_search[1]
        }).then(function(ids_read){
    		self.do_toto(self, ids_read);
    	});
    },
    do_toto: function(self, ids_read){
    	_.each(ids_read, function(ev){
    		self.ids_search.push(ev.id);
    	});
    },
    init_highstock: function() {
    	var self = this;
    	this.chart = $('#openerp_highstock_container').highcharts('StockChart', this.config_chart);
    },
    on_events_loaded: function(events, fn_filter, no_filter_reload) {
        var self = this;
        
        var res_events = [],
            sidebar_items = {},
        	in_moves = [],
        	out_moves = [];
        
        var td = new Date();
        td.setDate(td.getDate() + 1)
        
        
        // Conversion d'uom
        this.rpc("/web_highstock/convert_uom", {"model": this.model, "evts": events}).then(function(datas) {
        	events = datas;
        
        
        
        
        var states = ['assigned', 'waiting', 'confirmed'];
        _.each(events, function(event){
        	if (event[self.x_axis_field] <= td.format('%Y-%m-%d') & $.inArray(event['state'], states) >= 0 ){
        		event[self.x_axis_field] = td.format('%Y-%m-%d %H:%M:%S')
        	}
        });
        
        // group by date
        events_sorted_date = _(events).sortBy(function(a) {return a[self.x_axis_field].substr(0,10);});
        var moves_by_date = _.groupBy(events_sorted_date, function(evt){ return evt[self.x_axis_field].substr(0,10); });
        
        
        var in_out_by_date = []
        var total = 0;
        var total_assigned = 0;
        
        _.each(_.keys(moves_by_date), function(k){
        	events_date = moves_by_date[k];
        	var ins = [];
        	var outs = [];
        	_.each(events_date, function(evt){
//        		if (evt['date'] <= td.format('%Y-%m-%d %H:%M:%S') & $.inArray(evt['state'], states) >= 0 ){
//        			if (evt['type'] == 'in'){
//        				total_assigned += evt[self.y_axis_field]
//        			}
//        			else if (evt['type'] == 'out'){
//        				total_assigned -= evt[self.y_axis_field]
//        			}
////        			if ($.inArray(evt['state'], states) >= 0 ){
////        				if (evt['type'] == 'in'){
////        					total_assigned += evt[self.y_axis_field]
////        				}
////        				else if (evt['type'] == 'out'){
////        					total_assigned -= evt[self.y_axis_field]
////        				}
////        			}
////        			else{
////        				if (evt['type'] == 'in'){
////            				ins.push(evt[self.y_axis_field]);
////            			}
////            			
////            			else if (evt['type'] == 'out'){
////            				outs.push(evt[self.y_axis_field]);
////            			}
////        			}
//        		}
//        		else{
        			if (evt['type'] == 'in'){
        				ins.push(evt[self.y_axis_field]);
        			}
        			
        			else if (evt['type'] == 'out'){
        				outs.push(evt[self.y_axis_field]);
        			}
//        		}
        	});
        	k_list = k.split("-")
        	k_d = new Date(parseInt(k_list[0]), parseInt(k_list[1])-1, parseInt(k_list[2]))
        	var v_ins = _(ins).reduce(function(memo, i) {return memo + i}, 0);
        	var v_outs = _(outs).reduce(function(memos, i) {return memos + i}, 0);
        	total += v_ins - v_outs
        	in_out_by_date.push([k_d.getTime(), total])
        });
//        if (total_assigned != 0){
//        	var new_event = [td.setDate(td.getDate() + 1), total_assigned]
//        	in_out_by_date.push(new_event);
//        }
//        
//        var in_out_by_date2 = _(in_out_by_date).sortBy(function(a) {return a[0];});
//        
//        var index = $.inArray(new_event, in_out_by_date2)
//        if (index > 0){
//        	in_out_by_date2[index][1] += in_out_by_date2[index-1][1];
//        }
//        
        
        
        
        if (events[0]){
        self.rpc("/web_highstock/get_data", {model: self.title_model, id: events[0][self.title_obj_name][0], fields: self.title_fields_to_read}).then(function(datas) {
        			self.config_chart.title.text = events[0].product_id[1];
        		
        		self.config_chart.subtitle.text = datas[0]
            	
            	self.config_chart.series = [{data: in_out_by_date,
            		name: 'Stock',
            		step: true,
            		tooltip: {
            			valueDecimals: 2,
            			xDateFormat: "%Y-%m-%d",
            		}
            	}];
            	
            	self.config_chart.yAxis = {
                    plotLines: [{
        	    		value: datas[1],
        	    		width: 2,
        	    		color: 'green',
        	    		dashStyle: 'dash',
        	    		label: {
        	    			text: datas[1],
        	    			align: 'left',
        	    			y: -5,
        	    			x: 10
        	    		}
        	    	}]
                }
            	self.chart = $('#openerp_highstock_container').highcharts('StockChart', self.config_chart);
        
        });
        }
        else{
        	self.config_chart.title.text = "No moves for this product";
        	self.chart = $('#openerp_highstock_container').highcharts('StockChart', self.config_chart);
        }
        });

    },
    do_create_event: function(event_id, event_obj) {
        var self = this,
            data = this.get_event_data(event_obj);
        this.dataset.create(data, function(r) {
            var id = r.result;
            self.dataset.ids.push(id);
            scheduler.changeEventId(event_id, id);
            self.refresh_minical();
            self.reload_event(id);
        }, function(r, event) {
            event.preventDefault();
            self.do_create_event_with_formdialog(event_id, event_obj);
        });
    },
    do_search: function(domain, context, group_by) {
        this.last_search = arguments;
        this.do_ranged_search();
    },
    do_ranged_search: function() {
        var self = this;
//        scheduler.clearAll();
//        $.when(this.ready).then(function() {
        fields_to_read = _.keys(self.fields)
        fields_to_read.push("type")
        fields_to_read.push("state")
            self.dataset.read_slice(fields_to_read, {
                offset: 0,
                domain: self.get_range_domain(),
                context: self.last_search[1]
            }).then(function(events) {
                self.dataset_events = events;
                self.on_events_loaded(events);
            });
//        });
    },
    get_range_domain: function() {
//        var format = instance.web.date_to_str,
            domain = this.last_search[0];
//        domain.unshift([this.date_start, '>=', format(this.range_start.clone().addDays(-6))]);
//        domain.unshift([this.date_start, '<=', format(this.range_stop.clone().addDays(6))]);
        return domain;
    },
    do_show: function () {
        var self = this;
        $.when(this.has_been_loaded).then(function() {
            self.$element.show();
            if (self.sidebar) {
                self.sidebar.$element.show();
            }
            self.do_push_state({});
        });
    },
    do_hide: function () {
        this._super();
//        if (this.sidebar) {
//            this.sidebar.$element.hide();
//        }
    },
    get_selected_ids: function() {
        // no way to select a record anyway
        return [];
    }
});
};