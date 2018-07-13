odoo.define('calendar', function(require) {
    "use strict";
    var CalendarView = require('web_calendar.CalendarView');
    var Model = require('web.DataModel');
    var widgets = require('web_calendar.widgets');
    var core = require('web.core');
    var _t = core._t;
    
    widgets.SidebarFilter.include({
        events_loaded: function() {
            var res = this._super();
            var self = this;
            var res2 = new Model('mrp.resource')
            				.query()
            				.filter([
            				         ['calendar_id', '=', parseInt(Object.keys(this.view.all_filters)[0])]
            				         ])
            				.all()
            				.then(function(res) {
                self.view.$('.resource_list').remove();
                self.view.$('.o_calendar_sidebar').append('\
                		<div class="resource_list">\
                			<h3>' + _t('Resources') + '</h3>\
                			<ul>' 
                				+ _.map(res, function(resource) {
                						return '<li>' + resource.name + '</li>';
                				}).join('') + 
                			'</ul>\
                		</div>');
            });
            return res;
        }
    });
});
