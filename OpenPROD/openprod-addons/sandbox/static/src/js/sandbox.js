"use strict";
odoo.define('sandbox', function sandbox(require){

    var translation = require('web.translation');
    var _t = translation._t;
    var Model = require('web.DataModel');

    var modulePlanning = require('planning');
    modulePlanning.getFieldsWorkorder = function(){
		return [ 'sequence', 'mo_id', 'name', 'sandbox_planned_start_date',
				  'total_time_theo', 'sandbox_planned_end_date',
				  'sandbox_first_resource_id', 'availability_date_rm',
				  'availability_delay_rm', 'availability_simulation',
				  'client_date', 'prev_step', 'next_step', 'prev_id', 'next_id',
				  'sale_order_id', 'final_product_id', 'state', 'group_wo_id'];
	}

    modulePlanning.getLineWorkorder = function(wo, hours, minutes) {
		return { id: wo['id'],
				sequence: wo['sequence'],
				name: wo['mo_id'][1],
				time: hours + ":" + minutes,
				start_date: wo['sandbox_planned_start_date'],
				end_date: wo['sandbox_planned_end_date'],
				section_id: wo['sandbox_first_resource_id'][0].toString(),
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
	},

	modulePlanning.state_not_in = ['done', 'cancel'];

    modulePlanning.checkStartEndDateWorkorder = function(wo){
		return wo.sandbox_planned_start_date && wo.sandbox_planned_end_date && wo.sandbox_first_resource_id
	}

    modulePlanning.getChangeResourceAditionalParameter = function(){
		return { 'is_sandbox' : true };
	}

    var validateSandbox = function(e) {
        var WorkOrder = new Model('mrp.workorder');
        var eventId = parseInt(menuEvent);
        WorkOrder.call('sandbox_validate', [ eventId ]);
    }

    var resetSandbox = function(e) {
        var WorkOrder = new Model('mrp.workorder');
        var eventId = parseInt(menuEvent);
        WorkOrder.call('sandbox_reset', [ eventId ])
        .done(function(res){
			var new_wo = scheduler.getEvent(eventId);
            new_wo.start_date = modulePlanning.strToDate(res.sandbox_planned_start_date );
            new_wo.end_date = modulePlanning.strToDate(res.sandbox_planned_end_date );
			new_wo.section_id = res.sandbox_first_resource_id;
			scheduler.updateEvent(eventId);
			scheduler.updateView();
		});
    }

    modulePlanning.getRightClick = function(){ 
		return [ {text:_t("Validate Sandbox"), action:validateSandbox} ,
                 {text:_t("Reset Sandbox"), action:resetSandbox} , ] ;
	}

	$('#reset-sandbox').on('click', function(){
		var WorkOrder = new Model('mrp.workorder');
		WorkOrder.call('sandbox_reset_all')
		.done(function(liste_wo){
			liste_wo.forEach(function(res) {
				var new_wo = scheduler.getEvent(res.wo_id);
				if (new_wo){
					new_wo.start_date = modulePlanning.strToDate(res.start_date );
					new_wo.end_date = modulePlanning.strToDate(res.end_date );
					new_wo.section_id = res.first_resource_id;
					scheduler.updateEvent(res.wo_id);
				}
			}, this);
			scheduler.updateView();
		});
	});

	$('#validate-sandbox').on('click', function(){
		var WorkOrder = new Model('mrp.workorder');
		WorkOrder.call('sandbox_validate_all');
	});

    return modulePlanning;
});