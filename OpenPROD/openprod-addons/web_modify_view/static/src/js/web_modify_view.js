odoo.define("web.modify_view", function(require) {
	"use strict";
	var Sidebar = require("web.Sidebar");
	var ViewEditor = require('web_view_editor.view_editor');
	var session = require('web.session');
	var Model = require('web.Model');
	var core = require('web.core');
	var _t = core._t;
	var _ = window._;

	Sidebar.include({
        init : function(){
            this._super.apply(this, arguments);
            if (this.getParent().view_type == "tree"){
                this.sections.splice(1, 0, { 'name' : 'views', 'label' : _t('Views'), });
            }
            this.items.views = [];
        },
		add_toolbar: function (toolbar) {
			var self = this;
			this._super(toolbar);
			var inherit_id = self.getParent().inherit_id || self.getParent().view_id;
            new Model('ir.ui.view').query().context({search_override:true}).
                filter([
                    ['model', '=', self.getParent().dataset.model],
                    ['type', '=', 'tree'],
                ]).
                all().
                then(function(res) {
                _.each(res, function(view){self.add_items("views", [{
                    label: view.name,
                    view_id: view.id,
                    callback: function(view_info){
                        var action;
                    	var last_action = self.getParent().ViewManager.action_manager.action_stack.slice(-1)[0];
                    	if (last_action){
                    		action = _.clone(last_action.action_descr);
                    		action.views = [[view_info.view_id, 'list']];
                    	} else {
							action = {
								res_model: self.getParent().dataset.model,
								type: 'ir.actions.act_window',
								views: [[view_info.view_id, 'list']],
							};
                    	}
                        self.do_action(action);
                    },
                }]);});
            });
			var Users = new Model('res.users');
			Users.call('has_group', ['web_modify_view.group_view']).done(function(can_modify) {
				if (can_modify) {
					self.add_items("other", [{
						label:_t("Modify view"),
						callback: function(e){
							var parent = this.getParent();
							if (parent.view_type == "form") {
								var parent_model = parent.dataset.model;
								var base_view_id = parent.ViewManager.active_view.view_id;
								if (base_view_id === undefined) {
									base_view_id = null;
								}
								session.rpc('/web_modify_view/get_view', {
									model: parent_model,
									view_type: 'form',
									base_view_id: base_view_id,
								}).then(function(r){
									var view_editor = new ViewEditor(parent, parent.$el, parent.dataset);
									view_editor.start();
									view_editor.main_view_id = r;
									view_editor.get_arch();
								});
							} else {
								this.do_action({
									type: 'ir.actions.act_window',
									res_model: 'edit.tree.wizard',
									views: [[false, 'form']],
									target:'new',
									context: {
										model: parent.dataset.model,
										tree_view_id: parent.ViewManager.active_view.view_id || 0,
									}
								});
							}
						}
					}]);
					if (self.getParent().view_type == 'tree') {
					    self.add_items("other", [{
					        label: _t("Add new view"),
					        callback: function(e){
					            this.do_action({
                                    type: 'ir.actions.act_window',
                                    res_model: 'edit.tree.wizard',
                                    views: [[false, 'form']],
                                    target:'new',
                                    context: {
                                        model: self.getParent().dataset.model,
                                        tree_view_id: self.getParent().ViewManager.active_view.view_id || 0,
                                        new_view: true,
                                    }
                                });
					        },
					    }, {
					        label: _t('Delete View'),
					        callback: function(e){
					            new Model('ir.ui.view').call('unlink', [self.getParent().ViewManager.active_view.view_id]).then(function() {
    					            self.do_action({
                                        res_model: self.getParent().dataset.model,
                                        type: 'ir.actions.act_window',
                                        views: [[null, 'list']],
                                    });
    					        });
    					    },
					    }]);
					}
				}
			});
		}});
});