odoo.define('oee', function(require) {
    var core = require('web.core');
    var Model = require('web.Model');
    var View = require('web.View');
    var _lt = core._lt;
    var _t = core._t;
    var OEEView = View.extend({
        view_type: 'oee',
        display_name: 'OEE',
        icon: 'fa-dashboard',
        className: 'oee',
        events: {
            'click .btn_days': 'days',
            'click .btn_weeks': 'weeks',
            'click .btn_months': 'months',
            'click .btn_hours': 'hours',
            'click .btn_plusone': 'nextDay',
            'click .btn_minusone': 'prevDay',
        },
        start: function() {
            this.$el.html(main_template({
                _t: _t
            }));
            this._super.apply(this, arguments);
        },
        view_loading: function(r) {
            var self = this;
            scheduler.config.xml_date = '%Y-%m-%d %H:%i:%s';
            scheduler.config.readonly = true;
            scheduler.config.server_utc = true;
            scheduler.config.time_step = 1/60;
            scheduler.locale.labels.dhx_cal_today_button = _t('Today');
            scheduler.templates.event_class = function(start, end, event) {
                return 'activity_' + event.activity;
            }
            scheduler.attachEvent('onViewChange', function(mode, date) {
                //self.updateTotals();
                return true;
            });
            scheduler.filter_timeline = function(id, event){
                 var pixel_per_minute = $(scheduler.matrix.timeline._scales['1']).find('table').outerWidth()
                                       * 60000
                                       / (scheduler.getState().max_date - scheduler.getState().min_date);
                 var event_duration_minutes = (event.end_date - event.start_date) / 60000;
                 var min_box_size = 12; // 10 de padding + 2 de border
                 if (event_duration_minutes * pixel_per_minute > min_box_size) {
                     return true;
                 }
                 return false;
            };
            scheduler.createTimelineView({
                name: "timeline",
                x_unit: "day",
                x_date: "%d %M",
                x_step: 1,
                x_size: 31,
                x_start: 0,
                x_length: 31,
                y_unit: [],
                y_property: "resource_id",
                render: "bar",
                dy: 100,
                event_min_dy: 65,
            });
            scheduler.templates.timeline_scale_label = function(key, label, section) {
                return scale_label_template({
                    key: key,
                    label: label,
                    section: section
                });
            }
            scheduler.init(self.$el[0], new Date(), "timeline");
            self.getParent().on('switch_mode', this, function(view_type) {
                if (view_type == 'oee') {
                    scheduler.updateView();
                }
            });
            self.do_push_state({});
            scheduler.updateView();
        },
        do_search: function(domains, contexts, group_bys) {
            domains = JSON.parse(JSON.stringify(domains));
            var self = this;
            var area_filters = [];
            this.last_domains = domains;
            _.each(domains, function(domain) {
                if (_.isArray(domain) && domain[0] == 'area_id') {
                    domain[0] = 'resource_id.area_id';
                    area_filters.push(['area_id', domain[1], domain[2]])
                } else if (_.isArray(domain) && domain[0] == 'resource_id') {
                    area_filters.push(['name', domain[1], domain[2]])
                }
            })
            this.last_contexts = contexts;
            this.last_group_bys = group_bys;
            var resource_def = new Model('mrp.resource').query().filter(area_filters).all();
            var tt_def = new Model('resource.timetracking').query().filter(domains).all();
            $.when(resource_def, tt_def).done(function(resources, tts) {
                scheduler.matrix["timeline"].y_unit = _.map(resources, function(resource) {
                    return {
                        key: resource.id,
                        label: resource.display_name
                    };
                });
                scheduler.callEvent("onOptionsLoad", []);
                var parse_values = _.map(tts, function(tt) {
                    return {
                        start_date: tt.start_date,
                        end_date: tt.end_date || new Date(),
                        text: tt.display_name,
                        resource_id: tt.resource_id[0],
                        activity: tt.activity,
                    }
                });
                scheduler.clearAll();
                scheduler.parse(parse_values, 'json');
                //self.updateTotals();
            });
        },
        reload: function() {
            if (this.last_domains !== undefined) {
                return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
            }
        },
        updateTotals: function(start_date) {
            var state = scheduler.getState();
            var min_date = state.min_date;
            var max_date = state.max_date;
            new Model('oee').call('get_timetracking_totals', [min_date, max_date]).done(function(totals) {
                _.each(totals, function(total, resource_id) {
                    _.each(total, function(value, activity) {
                        var div = self.$('[data-resource=' + resource_id + '] .activity_' + activity);
                        div.text(value + '%');
                        div.width(value + '%');
                    });
                });
            })
        },
        days: function() {
            var t = scheduler.matrix.timeline;
            t.x_unit = "hour";
            t.x_date = "%H:%i";
            t.x_step = 1;
            t.x_size = 24;
            t.x_start = 0;
            t.x_length = 24;
            scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(t.x_date || scheduler.config.hour_date, false);
            scheduler.setCurrentView();
        },
        weeks: function() {
            var t = scheduler.matrix.timeline;
            t.x_unit = "day";
            t.x_date = "%d %M";
            t.x_step = 1;
            t.x_size = 7;
            t.x_start = 0;
            t.x_length = 7;
            scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(t.x_date || scheduler.config.hour_date, false);
            scheduler.setCurrentView();
        },
        months: function() {
            var t = scheduler.matrix.timeline;
            t.x_unit = "day";
            t.x_date = "%d %m";
            t.x_step = 1;
            t.x_size = 31;
            t.x_start = 0;
            t.x_length = 31;
            scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(t.x_date || scheduler.config.hour_date, false);
            scheduler.setCurrentView();
        },
        hours: function() {
            var t = scheduler.matrix.timeline;
            t.x_unit = "minute";
            t.x_date = "%H:%i";
            t.x_step = 10;
            t.x_size = 12;
            t.x_start = 0;
            t.x_length = 12;
            scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(t.x_date || scheduler.config.hour_date, false);
            scheduler.setCurrentView();
        },
        prevDay: function() {
            scheduler.setCurrentView(scheduler.date.add(scheduler._date, -1, 'day'));
        },
        nextDay: function() {
            scheduler.setCurrentView(scheduler.date.add(scheduler._date, 1, 'day'));
        }
    });
    var scale_label_template = _.template("<h3><%= label %></h3>\
    <div class='line_totals' data-resource='<%= key %>'>\
        <div class='activity_waiting'></div>\
        <div class='activity_setting'></div>\
        <div class='activity_production'></div>\
        <div class='activity_cleaning'></div>\
        <div class='activity_stop'></div>\
    </div>");
    var main_template = _.template('\
		<div id="planning_container" style="height:100%">\
			<div id="scheduler" class="dhx_cal_container">\
				<div class="dhx_cal_navline">\
					<div>\
						<button class="btn btn-default btn_hours"><%= _t("Hours") %></button>\
						<button class="btn btn-default btn_days"><%= _t("Days") %></button>\
						<button class="btn btn-default btn_weeks"><%= _t("Weeks") %></button>\
						<button class="btn btn-default btn_months"><%= _t("Months") %></button>\
						<button class="btn btn-default btn_minusone"><%= _t("-1D") %></button>\
						<button class="btn btn-default btn_plusone"><%= _t("+1D") %></button>\
						</div>\
					<div class="dhx_cal_prev_button"></div>\
					<div class="dhx_cal_next_button"></div>\
					<div class="dhx_cal_today_button"></div>\
					<div class="dhx_cal_date"></div>\
				</div>\
				<div class="dhx_cal_header">\
				</div>\
				<div class="dhx_cal_data">\
				</div>\
			</div>\
		</div>');
    core.view_registry.add('oee', OEEView);
});
