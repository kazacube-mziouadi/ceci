odoo.define('web_gantt.GanttView', function(require) {
    "use strict";
    var core = require('web.core');
    var Model = require('web.Model');
    var View = require('web.View');
    var form_common = require('web.form_common');
    var session = require('web.session');
    var _lt = core._lt;
    var QWeb = core.qweb;
    var GanttView = View.extend({
        view_type: 'gantt',
        className: 'gantt',
        icon: 'fa-tasks',
        do_search: function(domains, contexts, group_bys) {
            var self = this;
            this.last_domains = domains;
            this.last_contexts = contexts;
            this.last_group_bys = group_bys;
            if (this.scale == undefined) {
                this.scale = "days";
            }
            switch (this.scale) {
            case 'days':
                gantt.config.scale_unit = "day";
                gantt.config.date_scale = '%d %M';
                break;
            case 'weeks':
                gantt.config.scale_unit = "week";
                gantt.config.date_scale = 'Sem %W';
                break;
            case 'months':
                gantt.config.scale_unit = "month";
                gantt.config.date_scale = '%m/%y';
                break;
            }
            new Model(this.fields.model).query(['id', 'start_date', 'end_date', 'duration', 'name', 'parent_id', 'progress', 'description', 'next_ids', 'sequence', 'mo_ids', 'wo_ids', 'resource_id', 'charge', ]).filter(domains).context(_.extend({
                gantt: true
            }, contexts)).all().then(function(r) {
                var parent_ids = [];
                _.each(r, function(val) {
                    if (val.parent_id)
                        parent_ids.push(val.parent_id[0]);
                }, []);
                var links = [];
                var all_ids = _.pluck(r, 'id');
                var data = _.map(r, function(val) {
                    var type;
                    if (parent_ids.indexOf(val.id) != -1) {
                        type = gantt.config.types.project;
                    } else if (val.end_date == false && val.duration == 0) {
                        type = gantt.config.types.milestone;
                    } else {
                        type = gantt.config.types.task;
                    }
                    var formatFunc = gantt.date.str_to_date(gantt.config.xml_date);
                    _.each(val.next_ids, function(v) {
                        links.push({
                            id: _.uniqueId(),
                            source: val.id,
                            target: v,
                            type: 0
                        })
                    })
                    var ret = {
                        id: val.id,
                        start_date: val.start_date,
                        text: val.name,
                        parent: (all_ids.indexOf(val.parent_id[0]) > -1 && val.parent_id[0]) || 0,
                        progress: val.progress / 100,
                        description: val.description,
                        open: true,
                        type: type,
                        sequence: val.sequence,
                        is_wo: !!val.wo_ids.length,
                        is_mo: !!val.mo_ids.length,
                        charge: val.charge,
                        resource_id: val.resource_id[1] || '',
                    };
                    if (val.end_date) {
                        ret.end_date = formatFunc(val.end_date);
                        ret.end_date.setDate(ret.end_date.getDate() + 1);
                    } else {
                        ret.duration = val.duration;
                    }
                    return ret;
                });
                return {
                    data: data,
                    links: links
                };
            }).then(function(r) {
                gantt.clearAll();
                gantt.parse(r);
                self.do_push_state({});
            });
        },
        view_loading: function(r) {
            var target = this.$el.append('<div />');
            var self = this;
            gantt.config.xml_date = '%Y-%m-%d';
            // fonctionne pour le mode "days", à changer si on change le mode par défaut
            gantt.config.round_dnd_dates = true;
            gantt.config.time_step = 60 * 24;
            gantt.config.work_time = true;
            gantt.config.correct_work_time = true;
            gantt.config.grid_width = 500;
            gantt.config.branch_loading = true;
            gantt.config.drag_resize = false;
            gantt.config.drag_progress = false;
            gantt.config.scroll_on_click = false;
            gantt.config.order_branch = true;
            gantt.config.order_branch_free = true;
            gantt.config.lightbox.sections.push({
                name: "type",
                type: "typeselect",
                map_to: "type"
            });
            gantt.config.columns = [{
                name: "text",
                label: _lt('Task'),
                tree: true,
                width: 160
            }, {
                name: "duration",
                label: _lt('Duration'),
                resize: true,
                align: "center"
            }, {
                name: "resource_id",
                label: _lt('Resource'),
                resize: true,
                align: "center"
            }, {
                name: "charge",
                label: _lt('Charge'),
                resize: true,
                align: "center"
            }, {
                name: "sequence",
                label: _lt("Sequence"),
                align: "right"
            }, {
                name: "add"
            }, ];
            gantt.templates.task_cell_class = function(task, date) {
                if (self.scale == 'days' && !gantt.isWorkTime(date))
                    return "week_end";
                return "";
            }
            ;
            gantt.templates.scale_cell_class = function(date) {
                if (self.scale == 'days' && !gantt.isWorkTime(date))
                    return "week_end_scale";
                return "";
            }
            ;
            var events = self.events = [];
            events.push(gantt.attachEvent("onAfterTaskUpdate", this.on_task_changed));
            events.push(gantt.attachEvent("onTaskCreated", _.noop));
            events.push(gantt.attachEvent("onTaskClick", this.on_task_display));
            events.push(gantt.attachEvent("onBeforeTaskDelete", this.on_task_delete));
            events.push(gantt.attachEvent("onBeforeLinkAdd", this.on_link_add));
            events.push(gantt.attachEvent("onBeforeLinkDelete", this.on_link_delete));
            events.push(gantt.attachEvent("onEmptyClick", this.on_task_create));
            events.push(gantt.attachEvent("onRowDragStart", this.on_row_drag_start));
            events.push(gantt.attachEvent("onRowDragEnd", this.on_row_drag_end));
            events.push(gantt.attachEvent("onGanttRender", this.add_totals));
            gantt.init(this.$el[0]);
            session.rpc('project/calendar', {}).then(function(data) {
                var formatFunc = gantt.date.str_to_date(gantt.config.xml_date);
                _.each(data, function(date) {
                    date = formatFunc(date);
                    gantt.setWorkTime({
                        date: date,
                        hours: false
                    });
                });
            });
            this.fields = r;
        },
        on_row_drag_start: function(sid) {
            var task = gantt.getTask(parseInt(sid));
            return !(task.is_wo || task.is_mo);
        },
        on_row_drag_end: function(sid, pid) {
            var task = gantt.getTask(parseInt(sid));
            var prev_sibling = gantt.getPrevSibling(sid);
            var sequence = (prev_sibling && gantt.getTask(prev_sibling).sequence + 1) || 1;
            this.dataset.write(task.id, {
                parent_id: task.parent,
                sequence: sequence
            }).then(function(res) {
                task.sequence = sequence;
                gantt.render();
            });
        },
        on_task_display: function(task_id) {
            if (arguments[1].srcElement.classList.contains("gantt_add")) {
                return this.on_task_create({
                    parent: task_id,
                    start_date: gantt.getTask(task_id).start_date
                });
            }
            if (arguments[1].srcElement.classList.contains('gantt_close') || arguments[1].srcElement.classList.contains('gantt_open')) {
                return true;
            }
            var self = this;
            task_id = parseInt(task_id);
            self.open_task_id = task_id;
            new form_common.FormViewDialog(this,{
                res_model: this.dataset.model,
                res_id: task_id,
                context: this.dataset.context,
                buttons: [{
                    text: _lt("Save"),
                    classes: 'btn-primary',
                    close: true,
                    click: function() {
                        var test = this.view_form.save();
                        test.fail(function() {
                            self.reload();
                        }).then(function() {
                            self.reload();
                        });
                    }
                }, {
                    text: _lt("Delete"),
                    classes: 'btn-default',
                    close: true,
                    click: function() {
                        $.when(self.dataset.unlink([task_id])).then(function() {
                            $.when(self.dataset.remove_ids([task_id])).then(function() {
                                self.open_task_id = false;
                                self.reload();
                            });
                        });
                    }
                }, {
                    text: _lt("Close"),
                    classes: 'btn-default',
                    close: true
                }]
            }).open();
        },
        add_totals: function() {
            var $target = $('.column_totals');
            if (!$target.length) {
                $('.gantt_data_area').append('<div class="column_totals">');
                $('.gantt_grid_data').append('<div style="font-size:1.5em;text-align:right;margin-right:10px">' + _lt('Charge') + ' (h)')
                var $target = $('.column_totals');
            } else {
                $target.empty();
            }
            var cell_width = $('.gantt_task_cell').outerWidth();
            var date = moment(gantt._min_date);
            _.times(
                moment(gantt._max_date).diff(date, gantt.config.scale_unit),
                function(i) {
                    if (gantt.isWorkTime(date.toDate())) {
                        var total = _.reduce(gantt.getTaskByTime(), function(total, task) {
                            if (task.type != 'task') {
                                return total;
                            }
                            var startDate = moment.max(moment(task.start_date), date);
                            var endDate = moment.min(moment(task.end_date), date.clone().add(1, gantt.config.scale_unit));
                            var ret = gantt.calculateDuration(startDate.toDate(), endDate.toDate())
                            return total + (ret > 0 ? ret * task.charge / task.duration : 0);
                        }, 0);
                    } else {
                        var total = 0;
                    }
                    $target.append('<div style="min-width:' + cell_width + 'px">' + Math.round(total));
                    date.add(1, gantt.config.scale_unit);
                }
            )
        },
        destroy: function() {
            while (this.events.length) {
                gantt.detachEvent(this.events.pop());
            }
        },
        on_link_add: function(id, link) {
            if (link.type == 0 || link.type == 2) {
                var source = parseInt(link.source);
                var target = parseInt(link.target);
            } else {
                var target = parseInt(link.source);
                var source = parseInt(link.target);
            }
            this.dataset.write(source, {
                next_ids: [[4, target, 0]]
            }).then(_.bind(this.reload, this));
            return false;
        },
        on_link_delete: function(id, link) {
            var source = parseInt(link.source);
            var target = parseInt(link.target);
            this.dataset.write(source, {
                next_ids: [[3, target, 0]]
            }).then(_.bind(this.reload, this));
        },
        on_task_changed: function(id, obj) {
            var formatFunc = gantt.date.date_to_str(gantt.config.xml_date);
            var data = {
                start_date: formatFunc(obj.start_date),
                name: obj.text,
            };
            if (!obj.end_date) {
                data.duration = obj.duration;
            }
            var self = this;
            this.dataset.write(id, data).then(function() {
                new Model(self.fields.model).query(['start_date', 'duration', 'end_date']).filter([['id', '=', id]]).all().then(function(r) {
                    if (r.length) {
                        var id = r[0].id;
                        var task = gantt.getTask(id);
                        var formatFunc = gantt.date.str_to_date(gantt.config.xml_date);
                        task.start_date = formatFunc(r[0].start_date);
                        if (r[0].end_date) {
                            task.end_date = formatFunc(r[0].end_date);
                            task.end_date.setDate(task.end_date.getDate() + 1);
                        } else {
                            task.end_date = gantt.calculateEndDate(task.start_date, r[0].duration, 'day');
                        }
                        gantt.render();

                    }
                });
            });
        },
        on_task_delete: function(id) {
            this.dataset.unlink(id).then(_.bind(this.reload, this));
            return false;
        },
        on_task_create: function(data) {
            var self = this;
            var context = {
                default_user_id: this.dataset.context.uid
            }
            if (data && data.start_date) {
                var formatFunc = gantt.date.date_to_str(gantt.config.xml_date);
                context.default_start_date = formatFunc(data.start_date);
            }
            if (data && data.parent) {
                context.default_parent_id = parseInt(data.parent);
            }
            new form_common.FormViewDialog(this,{
                res_model: this.dataset.model,
                view_id: +this.open_popup_action,
                context: context,
                buttons: [{
                    text: _lt("Create"),
                    classes: 'btn-primary',
                    close: true,
                    click: function() {
                        this.view_form.save().then(function() {
                            self.reload();
                        });
                    }
                }, {
                    text: _lt("Close"),
                    classes: 'btn-default',
                    close: true
                }]
            }).open();
        },
        reload: function() {
            if (this.last_domains !== undefined) {
                return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
            }
        },
        render_buttons: function($node) {
            var self = this;
            this.$buttons = $('<div>\
            <button name="day" class="btn btn-primary">' + _lt('Days') + '</button>\
            <button name="month" class="btn btn-primary">' + _lt('Weeks') + '</button>\
            <button name="year" class="btn btn-primary">' + _lt('Months') + '</button>\
        </div>');
            if ($node) {
                this.$buttons.appendTo($node);
            }
            this.$buttons.on('click', '[name="day"]', function(e) {
                self.scale = 'days';
                gantt.config.round_dnd_dates = true;
                self.reload();
            });
            this.$buttons.on('click', '[name="month"]', function(e) {
                self.scale = 'weeks';
                gantt.config.round_dnd_dates = false;
                self.reload();
            });
            this.$buttons.on('click', '[name="year"]', function(e) {
                self.scale = 'months';
                gantt.config.round_dnd_dates = false;
                self.reload();
            });
        }
    });
    core.view_registry.add('gantt', GanttView);
    return GanttView;
});
