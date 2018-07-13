odoo.define('hr_timesheet_sheet.sheet', function(require) {
    "use strict";
    var core = require('web.core');
    var data = require('web.data');
    var form_common = require('web.form_common');
    var formats = require('web.formats');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var WeeklyTimesheet = form_common.FormWidget.extend(form_common.ReinitializeWidgetMixin, {
        events: {
            "click .oe_timesheet_weekly_account a": "go_to",
        },
        ignore_fields: function() {
            return ['line_id'];
        },
        init: function() {
            this._super.apply(this, arguments);
            this.set({
                sheets: [],
                date_from: false,
                date_to: false,
            });
            this.field_manager.on("field_changed:resource_timetracking_ids", this, this.query_sheets);
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({
                    "date_from": time.str_to_date(this.field_manager.get_field_value("date_from"))
                });
                this.query_sheets();
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({
                    "date_to": time.str_to_date(this.field_manager.get_field_value("date_to"))
                });
                this.query_sheets();
            });
            this.on("change:sheets", this, this.update_sheets);
            this.res_o2m_drop = new utils.DropMisordered();
            this.render_drop = new utils.DropMisordered();
            this.description_line = _t("/");
        },
        go_to: function(event) {
            var id = JSON.parse($(event.target).data("id")).split('|');
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: id[1],
                res_id: parseInt(id[0]),
                views: [[false, 'form']],
            });
        },
        query_sheets: function() {
            if (this.updating) {
                return;
            }
            var commands = this.field_manager.get_field_value("resource_timetracking_ids");
            var self = this;
            var tz_offset = new Date().getTimezoneOffset();
            this.res_o2m_drop.add(new Model(this.view.model).call(
                    "resolve_2many_commands", 
                    [
                        "resource_timetracking_ids",
                        commands,
                        [],
                        new data.CompoundContext({
                            timesheet_id:this.field_manager.get_fields_values().id,
                            date_from: time.date_to_str(this.get('date_from')),
                            date_to: time.date_to_str(this.get('date_to'))})
                    ])).done(function(result) {
                self.querying = true;
                var filter = self.filter || false;
                self.set({
                    sheets: _.filter(result, function(el) {
                        return !filter || el.activity == filter
                    })
                });
                self.querying = false;
            });
        },
        update_sheets: function() {
            if (this.querying) {
                return;
            }
            this.updating = true;
            var commands = [form_common.commands.delete_all()];
            _.each(this.get("sheets"), function(_data) {
                var data = _.clone(_data);
                if (data.id) {
                    commands.push(form_common.commands.link_to(data.id));
                    commands.push(form_common.commands.update(data.id, data));
                } else {
                    commands.push(form_common.commands.create(data));
                }
            });
            var self = this;
            this.field_manager.set_values({
                'resource_timetracking_ids': commands
            }).done(function() {
                self.updating = false;
            });
        },
        initialize_field: function() {
            form_common.ReinitializeWidgetMixin.initialize_field.call(this);
            this.on("change:sheets", this, this.initialize_content);
            this.on("change:date_to", this, this.initialize_content);
            this.on("change:date_from", this, this.initialize_content);
        },
        initialize_content: function() {
            if (this.setting) {
                return;
            }
            // don't render anything until we have date_to and date_from
            if (!this.get("date_to") || !this.get("date_from")) {
                return;
            }
            var self = this;
            var line_obj = new Model('calendar.line');
            var start_date = this.get('date_from');
            var end_date = this.get('date_to');
            var dates;
            return $.when().then(function() {
                // calculating dates
                dates = [];
                var start = self.get("date_from");
                var end = self.get("date_to");
                while (start <= end) {
                    dates.push(start);
                    var m_start = moment(start).add(1, 'days');
                    start = m_start.toDate();
                }
                self.dates = dates;
                self.field_manager.datarecord.calendar_id && line_obj.query(['real_start_date', 'real_end_date', 'real_hour']).filter([['calendar_id', '=', self.field_manager.datarecord.calendar_id[0]], ['real_start_date', '>=', start_date], ['real_end_date', '<=', moment(end_date).endOf('day').toDate()]]).all().done(function(res) {
                    var working_hours = _.map(res, function(el){
                        return {
                            start: moment(time.str_to_datetime(el.real_start_date)),
                            end: moment(time.str_to_datetime(el.real_end_date)),
                            real_hour: el.real_hour,
                        }
                    });
                    self.working_hours = _.object(_.map(working_hours, function(el){ return el.start.clone().startOf('day').format() }), working_hours)
                    var nowork = _.difference(_.map(self.dates, function(el) {
                        var date = new Date(el.getTime() - el.getTimezoneOffset() * 60000)
                        return time.datetime_to_str(date).substring(0, 10)
                    }), _.map(res, function(el) {
                        return el.real_start_date.substring(0, 10)
                    }));
                    var times = _.map(self.dates, Number);
                    var nowork_indexes = _.map(nowork, function(el) {
                        return times.indexOf(time.str_to_date(el).getTime())
                    });
                    self.set('nowork', nowork_indexes);
                }).then(function() {
                    // it's important to use those vars to avoid race conditions
                    var objects;
                    var object_names = {};
                    var nowork = self.get('nowork') || [];
                    // group by object
                    objects = _.chain(self.get("sheets")).map(_.clone).each(function(el) {
                        if (typeof (el.action_id) === "object") {
                            el.object_id = el.action_id[0];
                            el.object_model = 'calendar.event';
                        }
                        if (typeof (el.wo_id) === "object") {
                            el.object_id = el.wo_id[0];
                            el.object_model = 'mrp.workorder';
                        }
                        if (typeof (el.phase_id) === "object") {
                            el.object_id = el.phase_id[0];
                            el.object_model = 'project.phase';
                        }
                        if (typeof (el.intervention_id) === "object") {
                            el.object_id = el.intervention_id[0];
                            el.object_model = 'intervention';
                        }
                        if (typeof (el.analytic_distribution_id) === "object") {
                            el.object_id = el.analytic_distribution_id[0];
                            el.object_model = 'product.analytic.distribution';
                        }
                        if (typeof (el.issue_id) === "object") {
                            el.object_id = el.issue_id[0];
                            el.object_model = 'tracker.issue';
                        }
                        el.model_id = el.object_id + '|' + el.object_model;
                    }).groupBy("model_id").value();
                    var object_ids = _.keys(objects)
                    objects = _(objects).chain().map(function(lines, object_id) {
                        var index = {};
                        _.each(lines, function(line) {
                            var startDate = moment(time.str_to_datetime(line.start_date)).startOf('day');
                            var endDate = moment(time.str_to_datetime(line.end_date)).endOf('day');
                            while (endDate.isAfter(startDate)) {
                                var key = time.date_to_str(startDate.toDate());
                                if (!(key in index)) {
                                    index[key] = []
                                }
                                index[key].push(line);
                                startDate.add(1, 'day');
                            }
                        });
                        // temps par jour
                        var days = _.map(dates, function(date, i) {
                            var day = {
                                day: date,
                                lines: (nowork.indexOf(i) == -1) && index[time.date_to_str(date)] || []
                            };
                            day.lines.unshift({
                                time: 0,
                            });
                            return day;
                        });
                        return {
                            object_id: object_id,
                            days: days
                        };
                    }).value();
                    var model_ids = {};
                    _.each(_.pluck(objects, "object_id"), function(el) {
                        var split = el.split('|');
                        if (!(split[1]in model_ids)) {
                            model_ids[split[1]] = [];
                        }
                        model_ids[split[1]].push(parseInt(split[0]));
                    });
                    // load all activities
                    window.setTimeout(function() {
                        $('.oe_timesheet_activity').on('change', function() {
                            self.filter = this.value;
                            self.query_sheets();
                        });
                    }, 1000);
                    // we put all the gathered data in self, then we render
                    self.objects = objects;
                    self.object_names = object_names;
                    return $.when.apply($, _.map(model_ids, function(ids, model) {
                        return new Model(model).call("name_get", [ids, new data.CompoundContext()]).then(function(result) {
                            _.each(result, function(el) {
                                object_names[el[0] + '|' + model] = el[1];
                            })
                        });
                    }));
                }).then(function(result) {
                    //real rendering
                    self.display_data();
                });
            });
        },
        is_valid_value: function(value) {
            var split_value = value.split(":");
            var valid_value = true;
            if (split_value.length > 2) {
                return false;
            }
            _.detect(split_value, function(num) {
                if (isNaN(num)) {
                    valid_value = false;
                }
            });
            return valid_value;
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet_sheet.WeeklyTimesheet", {
                widget: self
            }));
            self.$el.find('.oe_timesheet_activity').val(self.filter);
            $('.oe_timesheet_weekly_box').on('click', function() {
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'wizard.create.timetracking',
                    target: 'new',
                    views: [[false, 'form']],
                    context: {
                        default_start_date: moment(self.get('date_from')).add($(this).data('day-count'), 'days').format('YYYY-MM-DD'),
                        target: $(this).parent().children().first().data('object-id'),
                        dialog_size: 'medium',
                        from_timesheet: true,
                        resource_id: self.field_manager.datarecord.resource_id[0],
                        default_resource_id: self.field_manager.datarecord.resource_id[0],
                    }
                });
            });
            _.each(self.objects, function(object) {
                _.each(_.range(object.days.length), function(day_count) {
                    self.get_box(object, day_count).html(self.sum_box(object, day_count, true));
                });
            });
            self.display_totals();
            self.display_work_days();
            if (!this.get('effective_readonly')) {
                this.init_add_account();
            }
        },
        init_add_account: function() {// passer les cases en éditable
        },
        display_work_days: function() {
            var self = this;
            var nowork = this.get('nowork');
            _.map(nowork, function(el) {
                self.$el.find('tr td:nth-child(' + (el + 2) + ')').addClass('oe_timesheet_weekly_nowork');
            });
        },
        get_box: function(object, day_count) {
            return this.$('[data-object-id="' + object.object_id + '"][data-day-count="' + day_count + '"]');
        },
        sum_box: function(account, day_count, show_value_in_hour) {
            var line_total = 0;
            var nowork = this.get('nowork');
            var self = this;
            _.each(account.days[day_count].lines, function(line) {
                var line_time = line.time;
                var line_start_date = moment(time.str_to_datetime(line.start_date));
                var line_end_date = moment(time.str_to_datetime(line.end_date));

                if (line_time == 0 || nowork.indexOf(day_count) != -1){
                    return;
                }
                var period;
                var total_time = 0;
                _.each(account.days, function(day, i){
                    if (nowork.indexOf(i) != -1) {
                        return;
                    }
                    day = day.day;
                    var hours = self.working_hours[moment(day).format()];
                    var from = moment.max(hours.start, line_start_date);
                    var to = moment.min(hours.end, line_end_date);
                    var time_to_add = to.diff(from);
                    if (time_to_add > 0) {
                        time_to_add = _.min([time_to_add, hours.real_hour * 60 * 60 * 1000])
                        total_time += time_to_add / 1000;
                    }
                })
                var tmp = self.working_hours[moment(account.days[day_count].day).format()];
                if (line_end_date.clone().startOf('day').isSame(line_start_date.clone().startOf('day'))) {
                    period = total_time;
                } else if (line_start_date.clone().startOf('day').isSame(account.days[day_count].day)) {
                    period = _.min([tmp.end.diff(line_start_date, 'seconds'), tmp.real_hour * 60 * 60]);
                } else if (line_end_date.clone().startOf('day').isSame(account.days[day_count].day)) {
                    period = _.min([line_end_date.diff(tmp.start, 'seconds'), tmp.real_hour * 60 * 60]);
                } else {
                    period = _.min([tmp.end.diff(tmp.start, 'seconds'), tmp.real_hour * 60 * 60]);
                    // full day
                }
                line_total += line.time * period / total_time;
            });
            return (show_value_in_hour && line_total !== 0) ? this.format_client(line_total) : line_total;
        },
        display_totals: function() {
            var self = this;
            var day_tots = _.map(self.dates, function() {
                return 0;
            });
            var super_tot = 0;
            _.each(self.objects, function(account) {
                var acc_tot = 0;
                _.each(_.range(self.dates.length), function(day_count) {
                    var sum = self.sum_box(account, day_count);
                    acc_tot += sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
                self.$('[data-account-total="' + account.object_id + '"]').html(self.format_client(acc_tot));
            });
            _.each(_.range(self.dates.length), function(day_count) {
                self.$('[data-day-total="' + day_count + '"]').html(self.format_client(day_tots[day_count]));
            });
            this.$('.oe_timesheet_weekly_supertotal').html(self.format_client(super_tot));
        },
        sync: function() {
            this.setting = true;
            this.set({
                sheets: this.generate_o2m_value()
            });
            this.setting = false;
        },
        //converts hour value to float
        parse_client: function(value) {
            return formats.parse_value(value, {
                type: "float_time"
            });
        },
        //converts float value to hour
        format_client: function(value) {
            return formats.format_value(value, {
                type: "float_time"
            });
        },
        generate_o2m_value: function() {
            var ops = [];
            var ignored_fields = this.ignore_fields();
            _.each(this.objects, function(account) {
                _.each(account.days, function(day) {
                    _.each(day.lines, function(line) {
                        if (line.unit_amount !== 0) {
                            var tmp = _.clone(line);
                            _.each(line, function(v, k) {
                                if (v instanceof Array) {
                                    tmp[k] = v[0];
                                }
                            });
                            // we remove line_id as the reference to the _inherits field will no longer exists
                            tmp = _.omit(tmp, ignored_fields);
                            ops.push(tmp);
                        }
                    });
                });
            });
            return ops;
        },
    });
    core.form_custom_registry.add('weekly_timesheet', WeeklyTimesheet);
});
