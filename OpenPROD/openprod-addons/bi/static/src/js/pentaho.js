odoo.define('bi.PentahoView', function(require) {
    "use strict";
    var core = require('web.core');
    var Model = require('web.Model');
    var View = require('web.View');
    var form_common = require('web.form_common');
    var session = require('web.session');
    var _lt = core._lt;
    var QWeb = core.qweb;
    var PentahoView = View.extend({
        view_type: 'pentaho',
        className: 'pentaho',
        icon: 'fa-tasks',
        do_search: function(domains, contexts, group_bys) {
        },
        view_loading: function(r) {
            var Server = new Model('bi.server');
            var Dashboard = new Model('bi.dashboard');
            var server_adress = {};
            var dashboard_adress = {};
	        var base_location_r = {};
            var db_name_r = {};
            var self = this;
            $.when(
            Server.query(['pentaho_server_address']).first(),
            Server.query(['db_name']).first(),
            Server.query(['base_location']).first(),
            Dashboard.query(['dashboard_address']).filter([['name', '=', r.name ]]).first()

            ).then ( function(server, db_name, base_location,  dashboard) {
                dashboard_adress = dashboard['dashboard_address'] ;
                server_adress = server['pentaho_server_address'];
		        db_name_r = db_name['db_name'];
                base_location_r = base_location['base_location'];
            self.$el.html('<iframe src="'+ server_adress + base_location_r + db_name_r + dashboard_adress + '" class="dashboard-pentaho" height="956px" style="margin-top:-16px;padding: 0;border: none;width:100%;"></iframe>'+
                  " <script>$(function(){ $('.oe-control-panel').hide();$('.openerp .oe-view-manager').css('overflow-y','hidden'); $('dashboard-pentaho').css('height',$( window ).height() - 34 +'px');"+
                      " $('nav').click(function(){$('.oe-control-panel').show()});$('.oe_leftbar').click(function(){$('.oe-control-panel').show()});}); </script>")
            });
            return ;
        },

        on_dashboard_display: function(dashboard_id) {    
        },

        reload: function() {
            if (this.last_domains !== undefined) {
                return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
            }
        },
    });
    core.view_registry.add('pentaho', PentahoView);
    return PentahoView;
});
