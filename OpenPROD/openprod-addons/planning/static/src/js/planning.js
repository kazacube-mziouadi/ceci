"use strict";
odoo.define('planning', function planning(require) {
	var Model = require('web.DataModel');
	var session = require('web.session');
	var translation = require('web.translation');
	var resourcesCalendar = {};
	var strToDate = scheduler.date.str_to_date("%Y-%m-%d %H:%i:%s", true);
	var dateToStr = scheduler.date.date_to_str("%Y-%m-%d %H:%i:%s", true);
	var percents = {};
	var resourceIds;
	var arrows = {close:[], far:[]};
	var core = require('web.core');
	var _t = translation._t;
	
	return session.session_reload().then(function(){
	return _t.database.load_translations(session, ['web', 'planning','sandbox'], session.user_context.lang).then(function() {
	$('body').append(_.template($('#body_t').html())({_t:_t}));
	
	scheduler.locale.labels.dhx_cal_today_button = _t('Today');

	var module = {};

	module.strToDate = strToDate;

	module.init = function(){
		loadLists();
		initScheduler();
		module.loadEvents();
		loadResources([]);
	}

	// retourne les elements du clique droit spécifique à planning
	module.getRightClick = function(){ 
		return [ {text:_t("Finish Planning"), action:finishPlanning} ] ;
	}

	module.getLineWorkorder = function(wo, hours, minutes) {
		return { id: wo['id'],
				sequence: wo['sequence'],
				name: wo['mo_id'][1],
				time: hours + ":" + minutes,
				start_date: wo['planned_start_date'],
				end_date: wo['planned_end_date'],
				section_id: wo['first_resource_id'][0].toString(),
				MP: wo['availability_date_rm'],
				client_date: wo['client_date'],
				prev: wo['prev_step'],
				next: wo['next_step'],
				prev_id: wo['prev_id'],
				next_id: wo['next_id'],
				sale: wo['sale_order_id'][1],
				fp: wo['final_product_id'][1],
				state: wo['state'],
				delay:wo['availability_delay_rm'],
				simulation:wo['availability_simulation'],
				readonly: true,
				prev_id_close: wo['prev_id'],
				next_id_close: wo['next_id'],
				operation_name: wo.name,
				group_wo_id: wo.group_wo_id,
			};
	}
	

	module.getFieldsWorkorder = function(){
		return [ 'sequence', 'mo_id', 'name', 'planned_start_date',
				  'total_time_theo', 'planned_end_date',
				  'first_resource_id', 'availability_date_rm',
				  'availability_delay_rm', 'availability_simulation',
				  'client_date', 'prev_step', 'next_step', 'prev_id', 'next_id',
				  'sale_order_id', 'final_product_id', 'state', 'group_wo_id'];
	}

	/**
	 * Vérifie si le workorder a bien une date de début et de fin
	 */
	module.checkStartEndDateWorkorder = function(wo){
		return wo.planned_start_date && wo.planned_end_date
	}

	module.getChangeResourceAditionalParameter = function(){
		return {};
	}

	module.state_not_in = ['draft', 'done', 'cancel'];

	module.loadEvents = function(filter) {
		if (!$.isArray(filter)) {
			filter = [];
		}
		filter.push(['state', 'not in', module.state_not_in ]);
		scheduler.clearAll();

		var WorkOrder = new Model('mrp.workorder');
		WorkOrder.query(module.getFieldsWorkorder()).filter(
						  filter).all().done(function(wos) {
							  var lines = [];
							  var line_ids = [];
							  for ( var w in wos) {
								  if (wos.hasOwnProperty(w)) {
									  var wo = wos[w];
									  var hours = Math.floor(wo['total_time_theo']);
									  var minutes = Math.round((wo['total_time_theo'] - hours) * 60);
									  if (!( module.checkStartEndDateWorkorder(wo) )) {
										  // Si le workorder n'a pas de date de début ou de fin on n'a pas les infos pour l'afficher donc on saute au workorder suivant
										  continue;
									  }
									  lines[wo['id']] = module.getLineWorkorder(wo, hours, minutes);
									  line_ids.push(wo['id']);
								  }
							  }

							  return session.rpc('/planning/prev_next', {wo_ids: line_ids}).done(function(r){
								  for (var i in r) {
									  if (r.hasOwnProperty(i)){
										  if (r[i].prev_date && (!lines[r[i].id].prev || lines[r[i].id].prev < r[i].prev_date)){
											  lines[r[i].id].prev = r[i].prev_date;
											  lines[r[i].id].prev_id = r[i].prev_id;
										  }
										  if (r[i].next_date && (!lines[r[i].id].next || lines[r[i].id].next > r[i].next_date)){
											  lines[r[i].id].next = r[i].next_date;
											  lines[r[i].id].next_id = r[i].next_id;
										  }
									  }
								  }
								  scheduler.parse(lines, "json");
								drawArrows();
							  });
						  });
	}

	function changeDate() {
		if (typeof resourceIds == "undefined") {
			return true;
		}
		loadLoading();
		loadCalendar();
		return true;
	}

	function loadLoading() {
		var state = scheduler.getState();
		return session.rpc('/planning/loading', {start_date:state.min_date, end_date:state.max_date, resource_ids:resourceIds}).done(function(data){
			percents = [];
			for (var i in data) {
				if (data.hasOwnProperty(i)){
					percents[data[i]['id']] = Math.round(100 * data[i]['loading'] / data[i]['real_hour']);
				}
			}
		});
	}

	function loadCalendar() {
		var state = scheduler.getState();
		var CalendarLines = new Model('calendar.line');
		CalendarLines
		.query(['real_start_date', 'real_end_date', 'calendar_id'])
		.filter([['real_start_date', '>=', state.min_date], ['real_end_date', '<=', state.max_date]])
		.order_by('real_start_date')
		.all()
		.done(function(lines) {
			scheduler.deleteMarkedTimespan();
			var calendar_ids = Object.keys(resourcesCalendar);
			var start_date = [];
			var end_date = []; 
			calendar_ids.forEach(function(i){start_date[i] = scheduler.getState().min_date});
			for (var i in lines) {
				if (lines.hasOwnProperty(i)){
					var line = lines[i];
					var calendar_id = line.calendar_id[0];
					end_date[calendar_id] = strToDate(line.real_start_date);
					scheduler
					.addMarkedTimespan({
						start_date : start_date[calendar_id],
						end_date : end_date[calendar_id],
						css : "marked",
						sections : {
							timeline : resourcesCalendar[calendar_id]
						}
					});
					start_date[calendar_id] = strToDate(line.real_end_date);
				}
			}
			calendar_ids.forEach(function(i){
				scheduler.addMarkedTimespan({
					start_date : start_date[i],
					end_date : scheduler.getState().max_date,
					css : "marked",
					sections : {
						timeline : resourcesCalendar[i]
					}
				});
			});
		}).done(function(){
			scheduler.updateView();
		});
	}

	function initScheduler() {
		scheduler.locale.labels.timeline_tab = "Timeline";
		scheduler.config.multisection = true;
		scheduler.config.xml_date = "%Y-%m-%d %g:%i";
		scheduler.config.dblclick_create = false;
		scheduler.config.drag_create = false;
		scheduler.config.check_limits = false;
		scheduler.config.drag_resize = false;
		scheduler.config.server_utc = true;
		scheduler.templates.event_bar_text = function(start, end, event) {
			var MP = event.MP && strToDate(event.MP);
			var client = event.client_date && strToDate(event.client_date);
			var prev = event.prev && strToDate(event.prev);
			var next = event.next && strToDate(event.next);
			var alertMP = (MP && start < MP) ? " class='alert_date'" : "";
			var alertClient = (client && start > client) ? " class='alert_date'" : "";
			var alertPrev = (prev && start < prev) ? " class='alert_date'" : "";
			var alertNext = (next && end > next) ? " class='alert_date'" : "";;
			return "[" + event.sequence + "] " + event.name +
			" " + _t('FP') + " : " + event.fp +
			"<br /><span" + alertMP + ">" + _t('MP') + " : " + (event.MP?event.MP.substr(5,5):"") +
			"</span> <span " + alertClient + ">" + _t('Client') + " : " + (event.client_date?event.client_date.substr(5,5):"") +
			"</span><span> " + (event.simulation?(_t('Simulate') + " : " + event.simulation.substr(5,5)):(_t('Delay') + " : " + event.delay)) +
			"</span><br />" + "<span" + alertPrev + ">" + _t('prev') + " : " + (event.prev ? event.prev.substr(5,5) : "") +
			"</span> <span" + alertNext + ">" + _t('next') + " : " +
			(event.next ? event.next.substr(5,5) : "") + "</span>";
		};
		scheduler.templates.event_class = function(start, end, event) {
			var next = event.next && strToDate(event.next);
			var prev = event.prev && strToDate(event.prev);
			var MP = event.MP && strToDate(event.MP);
			var client = event.client_date && strToDate(event.client_date);
			var classes = []
			var sale = $('#sales').val() || undefined;
			var mo = $('#manufacturing_orders').val() || undefined;
			var finalProduct = $('#final_products').val() || undefined;
			var finalProductRegex = new RegExp(finalProduct, 'i');
			var color;

			if (['ready', 'progress', 'pause', 'plan'].indexOf(event.state) > -1) {
				color = 'yellow';
			}

			if ((mo || sale || finalProduct) && (!mo || event.name.indexOf(mo) > -1) && (!sale || event.sale && event.sale.indexOf(sale) > -1) && (!finalProduct || event.fp.search(finalProductRegex) > -1)) {
				color = 'green';
			}
			
			if (event.group_wo_id) {
			    color = 'orange';
			}

			if (color){
				classes.push('event_' + color);
			}

			if ((next && end > next) || (prev && start < prev) || (MP && start < MP)) {
				classes.push('alert_next');
			}
			if (client && end > client) {
				classes.push('alert_client');
			}
			return classes.join([' ']);
		};

		scheduler.templates.tooltip_text = function(start,end,ev){
		    var first_line = "<strong>" + ev.operation_name + "</strong><br />";
			return first_line + scheduler.templates.event_bar_text(start, end, ev);
		}

		scheduler.showLightbox = function(id){
			var ev = scheduler.getEvent(id);
			var popupWorkOrder = $('#popup_workorder');
			var url = session.server + '/web#id=' + ev.id + '&view_type=form&model=mrp.workorder';
			var iframe = popupWorkOrder.find('iframe');
			scheduler.startLightbox(id, popupWorkOrder[0]);
			if (iframe.attr('src') == url) {
				iframe[0].contentWindow.location.reload();
			} else {
				iframe.attr('src', url);
			}
		};

		scheduler.createTimelineView({
			name : "timeline",
			x_unit : "day",// measuring unit of the X-Axis.
			x_date : "%d %M", // date format of the X-Axis
			x_step : 1, // X-Axis step in 'x_unit's
			x_size : 31, // X-Axis length specified as the total number of 'x_step's
			x_start : 0, // X-Axis offset in 'x_unit's
			x_length : 31, // number of 'x_step's that will be scrolled at a time
			y_unit : scheduler.serverList("sections"),
			y_property : "section_id", // mapped data property
			render : "bar", // view mode
			dy : 70,
			event_min_dy : 65,
		});
		initCallbacks();
		scheduler.init('scheduler', new Date(), "timeline");

		scheduler.templates.timeline_scale_label = function(key, label) {
			if (_.keys(percents).length === 0) {
				return label;
			}
			var capacity = percents[key];
			var color;
			if (capacity >= 85){
				color = 'red';
			} else if (capacity >= 75){
				color = 'orange';
			} else {
				color = 'green';
			}
			return label + "<div class='capacity capacity_" + color + "' style='max-width:" + capacity + "%'><span>" + capacity + "%</span></div>";
		};

		context.init();
		context.attach('.dhx_cal_event_line', 
				[{text:_t("Show neighbours"), action:function(){
					var eventId = parseInt(menuEvent);
					addNeighbours(eventId);
					drawArrows();
				}},
				{text:_t("Show all neighbours"), action:function(){
					var eventId = parseInt(menuEvent);
					session.rpc('/planning/get_all_neighbours', {wo_id: eventId})
					.done(function(result){
						arrows.far = arrows.far.concat(result);
						addNeighbours(eventId);
						_.each(_.flatten(result), addNeighbours);
						drawArrows();
					});
				}},
				{text:_t("Simulate"), action:function(){
					var WorkOrder = new Model('mrp.workorder');
					WorkOrder.call('button_availability_simulation_compute', [parseInt(menuEvent)])
					.done(function(date){
						scheduler.getEvent(parseInt(menuEvent)).simulation=date;
						scheduler.updateView();
					});
				}},
				].concat(module.getRightClick() )
		);
	}

	function addNeighbours(eventId) {
		var event = scheduler.getEvent(eventId);
		if (!event) {
			return;
		}
		if (event.prev_id && !inArray(arrows.close, [event.prev_id, eventId])) {
			arrows.close.push([event.prev_id, eventId]);
			addNeighbours(event.prev_id);
		}
		if (event.next_id && !inArray(arrows.close, [eventId, event.next_id])) {
			arrows.close.push([eventId, event.next_id])
			addNeighbours(event.next_id);
		}
	}
	
	function inArray(array, item) {
		for (var i = 0; i < array.length; i++) {
			if (array[i][0] == item[0] && array[i][1] == item[1]) {
				return true;
			}
		}
		return false;
	}

	function updatePrevNext(id){
		var ev = scheduler.getEvent(id);
		if (ev.prev_id > 0) {
			var prev = scheduler.getEvent(ev.prev_id);
			if (prev) {
				prev.next = dateToStr(ev.start_date);
			}
			scheduler.updateEvent(ev.prev_id);
		}
		if (ev.next_id > 0) {
			var next = scheduler.getEvent(ev.next_id);
			if (next) {
				next.prev = dateToStr(ev.end_date);
			}
			scheduler.updateEvent(ev.next_id);
		}
		return true;
	}
	
	function updatePrevNextReal() {
		var event_ids = _.map(scheduler.getEvents(), function(ev){return ev.id});
		session.rpc('/planning/prev_next', {wo_ids: event_ids}).done(function(r){
			_.map(scheduler.getEvents(), function(ev){
				ev.prev_id = ev.prev_id_close;
				if (ev.prev_id !== 0) {
					var ev_prev = scheduler.getEvent(ev.prev_id);
					if (ev_prev != undefined)
						ev.prev = dateToStr(ev_prev.end_date);
				} else {
					ev.prev = false;
				}
				ev.next_id = ev.next_id_close;
				if (ev.next_id !== 0) {
					var ev_next = scheduler.getEvent(ev.next_id);
					if (ev_next != undefined)
						ev.next = dateToStr(ev_next.start_date);
				} else {
					ev.next = false;
				}
				scheduler.updateEvent(ev.id);
			});
			for (var i in r){
				if (r.hasOwnProperty(i)){
					var ev = scheduler.getEvent(r[i].id);
					var update = false;
					if (r[i].prev_date && (!ev.prev || r[i].prev_date > ev.prev)) {
						ev.prev = r[i].prev_date;
						ev.prev_id = r[i].prev_id;
						update = true;
					}
					if (r[i].next_date && (!ev.next || r[i].next_date < ev.next)) {
						ev.next = r[i].next_date;
						ev.next_id = r[i].next_id;
						update = true;
					}
					if (update) {
						scheduler.updateEvent(ev.id);
					}
				}
			}
		});
	}

	function initCallbacks() {
		$("#close_popup_workorder").on("click", function(){
			scheduler.endLightbox(false, $('#popup_workorder')[0]);
		});

		scheduler.attachEvent("onBeforeEventChanged", function(ev, e, is_new,
				original) {
			var load;
			var def = new $.Deferred();
			def.resolve();
			if (ev.section_id != original.section_id) {
				def = session.rpc('/planning/change_primary_resource', _.extend({wo_id: ev.id, new_resource_id:ev.section_id}, module.getChangeResourceAditionalParameter() ));
			}
			def.done(function(result){
				if (result === false) {
					ev.section_id = original.section_id;
					ev.start_date = original.start_date;
					ev.end_date = original.end_date;
					scheduler.updateEvent(ev.id);
					scheduler.updateView();
				}
				if (ev.start_date != original.start_date) {
					var WorkOrder = new Model('mrp.workorder');
					WorkOrder.call('reschedule',
							[ ev.id, dateToStr(ev.start_date), dateToStr(ev.end_date) ] , module.getChangeResourceAditionalParameter() ).done(
									function(data) {
									    _.each(data, function(wo) {
    										var start_date = strToDate(wo.start_date);
    										var end_date = strToDate(wo.end_date);
    										scheduler.getEvent(wo.wo_id).start_date = start_date;
    										scheduler.getEvent(wo.wo_id).end_date = end_date;
    										scheduler.updateEvent(wo.wo_id);
    									});
										updatePrevNextReal();
										var load = loadLoading();
										load.done(function(){
											scheduler.updateView();
										});
									});
				}});
			return true;
		});

		scheduler.attachEvent("onViewChange", changeDate);
		scheduler.attachEvent("onDragEnd", updatePrevNext);
		scheduler.attachEvent("onDragEnd", drawArrows);
		scheduler.attachEvent("onSchedulerResize", drawArrows);
		scheduler.attachEvent("onViewChange", drawArrows);
		scheduler.attachEvent("onAfterUpdateView", drawArrows);
        scheduler.attachEvent("onBeforeDrag", function() {
			if (document.getElementById('arrows')) {
				var ctx = document.getElementById('arrows').getContext('2d');
				var canvas = ctx.canvas;
				ctx.clearRect(0,0,canvas.width, canvas.height);
				return true;
			}
		});

		$('#areas').on('change', filterWorkorders);
		$('#filter').on('click', filterWorkorders);
		$('.highlight').on('change', function(){
			scheduler.updateView();
		});

		$('#scheduler').on('dblclick', '.dhx_matrix_cell', function(event){
			var data = scheduler.getActionData(event);
			scheduler.startLightbox(data.section + "|" + data.date.valueOf(), $("#popup_calendar")[0]);
		});

		$('#calendar_apply_week').on("click", saveWeek);
		$('#calendar_apply_day').on("click", saveDay);
		$('#calendar_cancel').on("click", closePopup);
		
		$('#day_selector').on("change", function(){
			var date = strToDate(this.value);
			if (!isNaN(date.getTime())) {
				scheduler.setCurrentView(date);
			}
		});

		$('#days').on("click", days);
		$('#weeks').on("click", weeks);
		$('#months').on("click", months);
		$('#3months').on("click", threemonths);

		$('#prev_day').on('click', prevDay);
		$('#next_day').on('click', nextDay);
		$('#clean-arrows').on('click', function(){arrows.close=[];arrows.far=[];drawArrows();});
	}


	function loadResources(filter){
		var Resource = new Model('mrp.resource');
		return Resource.query().filter(filter).all().done(function(resources) {
			var lines = [];
			resourceIds = [];
			for ( var r in resources) {
				if (resources.hasOwnProperty(r)) {
					var resource = resources[r];
					resourceIds.push(resource.id);
					lines.push({
						key : resource.id.toString(),
						label : resource.display_name,
					});
					var id = resource.calendar_id[0];
					if (resourcesCalendar[id] === undefined) {
						resourcesCalendar[id] = [];
					}
					resourcesCalendar[id].push(resource.id.toString());
				}
			}

			scheduler.updateCollection("sections", lines);
		});
	}

	function closePopup() {
		scheduler.endLightbox(false, $('#popup_calendar')[0]);
	}

	function saveDay() {
		var split = scheduler.getState().lightbox_id.split('|');
		var section = split[0];
		var timestamp = split[1];
		var targetDay = new Date(parseInt(timestamp));
		split = $('#start_time').val().split(':');
		var start_hour = split[0];
		var start_minute = split[1];
		var start_time = new Date(targetDay);
		start_time.setHours(start_hour);
		start_time.setMinutes(start_minute);
		split = $('#end_time').val().split(':');
		var end_hour = split[0];
		var end_minute = split[1];
		var end_time = new Date(targetDay);
		end_time.setHours(end_hour);
		end_time.setMinutes(end_minute);
		var duration = parseInt($('#duration').val());
		var calendar_id;
		ok: for (var i in resourcesCalendar){
			if (resourcesCalendar.hasOwnProperty(i)){
				for (var j in resourcesCalendar[i]){
					if (resourcesCalendar[i].hasOwnProperty(j)){
						if (resourcesCalendar[i][j] == section){
							calendar_id = parseInt(i);
							break ok;
						}
					}
				}
			}
		}
		var data_to_save = {};
		if (start_time.getTime()) data_to_save.start_date_exception = start_time;
		if (end_time.getTime()) data_to_save.end_date_exception = end_time;
		if (duration) data_to_save.hour_exception = duration;
		if (!Object.keys(data_to_save).length) {
			closePopup();
		}
		var Calendar = new Model('calendar.line');
		Calendar.query().filter([['real_start_date', '<', targetDay], ['real_end_date', '>', targetDay], ['calendar_id', '=', calendar_id]])
		.all().done(function(calendar_line) {
			if (calendar_line.length) {
				Calendar.call('write', [calendar_line[0].id, data_to_save]).done(loadCalendar);
			}
		});
		closePopup();
	}

	function saveWeek() {
		var split = scheduler.getState().lightbox_id.split('|');
		var section = split[0];
		var timestamp = split[1];
		var targetDay = new Date(parseInt(timestamp));
		var duration = parseInt($('#duration').val());
		var endWeek = moment(targetDay).day(8).startOf('day');
		var startWeek = moment(endWeek).add(-1, 'weeks');
		var calendar_id;
		ok: for (var i in resourcesCalendar){
			if (resourcesCalendar.hasOwnProperty(i)){
				for (var j in resourcesCalendar[i]){
					if (resourcesCalendar[i].hasOwnProperty(j)){
						if (resourcesCalendar[i][j] == section){
							calendar_id = parseInt(i);
							break ok;
						}
					}
				}
			}
		}
		var Calendar = new Model('calendar.line');
		
		Calendar.query().filter([['real_start_date', '<=', endWeek], ['real_end_date', '>', startWeek], ['calendar_id', '=', calendar_id]])
		.all().done(function(calendar_line) {
			var defWrite;
			if (calendar_line.length) {
				for (var i in calendar_line){
					if (calendar_line.hasOwnProperty(i)) {
						var start_time = strToDate(calendar_line[i].start_date);
						split = $('#start_time').val().split(':');
						var start_hour = split[0];
						var start_minute = split[1];
						start_time.setHours(start_hour);
						start_time.setMinutes(start_minute);
						split = $('#end_time').val().split(':');
						var end_hour = split[0];
						var end_minute = split[1];
						var end_time = strToDate(calendar_line[i].end_date);
						end_time.setHours(end_hour);
						end_time.setMinutes(end_minute);
						var data_to_save = {};
						if (start_time.getTime()) data_to_save.start_date_exception = start_time;
						if (end_time.getTime()) data_to_save.end_date_exception = end_time;
						if (duration) data_to_save.hour_exception = duration;
						if (!Object.keys(data_to_save).length) {
							return;
						}
						defWrite = Calendar.call('write', [calendar_line[i].id, data_to_save]);
					}
				}
				defWrite.done(loadCalendar);
			}
		});
		closePopup();
	}

	function days() {
		var t = scheduler.matrix.timeline;
		t.x_unit = "hour";
		t.x_date = "%H:%i";
		t.x_step = 1;
		t.x_size = 24;
		t.x_start = 0;
		t.x_length = 24;
		scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(
				t.x_date || scheduler.config.hour_date, false);
		scheduler.setCurrentView();
	}

	function weeks() {
		var t = scheduler.matrix.timeline;
		t.x_unit = "day";
		t.x_date = "%d %M";
		t.x_step = 1;
		t.x_size = 7;
		t.x_start = 0;
		t.x_length = 7;
		scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(
				t.x_date || scheduler.config.hour_date, false);
		scheduler.setCurrentView();
	}

	function months() {
		var t = scheduler.matrix.timeline;
		t.x_unit = "day";
		t.x_date = "%d %m";
		t.x_step = 1;
		t.x_size = 31;
		t.x_start = 0;
		t.x_length = 31;
		scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(
				t.x_date || scheduler.config.hour_date, false);
		scheduler.setCurrentView();
	}

	function threemonths() {
		var t = scheduler.matrix.timeline;
		t.x_unit = "day";
		t.x_date = "%d %m";
		t.x_step = 2;
		t.x_size = 46;
		t.x_start = 0;
		t.x_length = 46;
		scheduler.templates[t.name + '_scale_date'] = scheduler.date.date_to_str(
				t.x_date || scheduler.config.hour_date, false);
		scheduler.setCurrentView();
	}

	function prevDay() {
		scheduler.setCurrentView(scheduler.date.add(scheduler._date, -1, 'day'));
	}

	function nextDay() {
		scheduler.setCurrentView(scheduler.date.add(scheduler._date, 1, 'day'));
	}

	function filterWorkorders() {
		var filter = [];
			var filterArea = [];

		var area = parseInt($('#areas').val());
		if (area) {
			filter.push([ 'first_resource_id.area_id', '=', area ]);
			filterArea.push(['area_id', '=', area]);
		}

		var resources = _.map($('#resources_select').val(), function(e){ return parseInt(e); });
		if (resources.length) {
			filter.push([ 'first_resource_id', 'in', resources ]);
			filterArea.push(['id', 'in', resources]);
		}

		module.loadEvents(filter);

		if (filterArea) {
			loadResources(filterArea);
		} else {
			loadResources([]);
		}
	}

	function highlightWorkorders() {
		var sale = $('#sales').val();
		var mo = $('#manufacturing_orders').val();
		var finalProduct = $('#final_products').val();
	}

	function finishPlanning(e){
		var WorkOrder = new Model('mrp.workorder');
		WorkOrder.call('plannification_wo_done', [parseInt(menuEvent), true])
		.done(function(state){
			scheduler.getEvent(parseInt(menuEvent)).state = state;
			scheduler.updateView();
		});
	}

	function drawArrows() {
		if (!document.getElementById('arrows')) {
			$('.dhx_cal_data > table').prepend('<canvas id="arrows" />');
		}
		var ctx = document.getElementById('arrows').getContext('2d');
		var canvas = ctx.canvas;
		canvas.width = canvas.parentElement.clientWidth;
		canvas.height = canvas.parentElement.clientHeight;
		ctx.strokeStyle = "blue";
		ctx.fillStyle = "blue";
		for (var i in arrows.close) {
			if (arrows.close.hasOwnProperty(i)) {
				drawArrow(arrows.close[i][0], arrows.close[i][1], ctx);
			}
		}
		ctx.strokeStyle = "black";
		ctx.fillStyle = "black";
		for (var i in arrows.far) {
			if (arrows.far.hasOwnProperty(i)) {
				drawArrow(arrows.far[i][0], arrows.far[i][1], ctx);
			}
		}
	}

	function drawArrow(idStart, idEnd, ctx) {
		var minLineLength = 30;

		var startA = $('div[event_id=' + idStart + ']');
		var endB = $('div[event_id=' + idEnd + ']');
		if (!(startA.length || endB.length)) {
			return;
		}
		var scrollTop = $('.dhx_cal_data').scrollTop();
		if (!startA.length){
			var eventA = scheduler.getEvent(idStart);
			if (!eventA){
				return;
			}
			var sectionLabelA = _.find(scheduler.matrix['timeline'].y_unit, function(x){return x.key==eventA.section_id}).label;
			var sectionA = $('td.dhx_matrix_scell:contains("' + sectionLabelA + '")');
			var startPointX = sectionA.position().left + sectionA.outerWidth();
			var startPointY = sectionA.position().top + sectionA.height() / 2 + scrollTop;
		} else {
			var startPointX = startA.position().left + startA.parent().position().left + startA.outerWidth();
			var startPointY = startA.position().top + startA.parent().position().top + startA.height() / 2 + scrollTop;
		}
		if (!endB.length){
			var eventB = scheduler.getEvent(idEnd);
			if (!eventB){
				return;
			}
			var sectionLabelB = _.find(scheduler.matrix['timeline'].y_unit, function(x){return x.key==eventB.section_id}).label;
			var sectionB = $('tr:contains("' + sectionLabelB + '")');
			var endPointX = sectionB.position().left + sectionB.outerWidth();
			var endPointY = sectionB.position().top + sectionB.height() / 2 + scrollTop;
		} else {
			var endPointX = endB.position().left + endB.parent().position().left;
			var endPointY = endB.position().top + endB.parent().position().top + endB.height() / 2 + scrollTop;
		}
		if (startPointY == endPointY && (endPointX - startPointX) < 30) {
			return;
		}
		ctx.beginPath();
		ctx.moveTo(startPointX, startPointY);
		if (endPointX - startPointX > 2*minLineLength){
			ctx.lineTo(startPointX + (endPointX - startPointX) / 2, startPointY);
			ctx.lineTo(startPointX + (endPointX - startPointX) / 2, endPointY);
		} else {
			ctx.lineTo(startPointX + minLineLength, startPointY);
			ctx.lineTo(startPointX + minLineLength, startPointY + (endPointY - startPointY) / 2);
			ctx.lineTo(endPointX - minLineLength, startPointY + (endPointY - startPointY) / 2);
			ctx.lineTo(endPointX - minLineLength, endPointY);
		}
		ctx.lineTo(endPointX, endPointY);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(endPointX, endPointY);
		ctx.lineTo(endPointX - 20, endPointY + 8);
		ctx.lineTo(endPointX - 20, endPointY - 8);
		ctx.fill();
	}
	
	function loadLists() {
		new Model('mrp.area').query(['id', 'display_name']).all().done(function(r){
			$.each(r, function (i, area) {
			    $('#areas').append($('<option>', { 
			        value: area.id,
			        text : area.display_name, 
			    }));
			});
			}
		)
		
		new Model('mrp.resource').query(['id', 'display_name']).all().done(function(r){
			$.each(r, function (i, resource) {
			    $('#resources_select').append($('<option>', { 
			        value: resource.id,
			        text : resource.display_name, 
			    }));
			    $("#resources_select").selectpicker('refresh')
			});
			}
		)
	}

	return module;
	});
	})	
});
