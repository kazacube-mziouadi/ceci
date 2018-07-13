"use strict";
odoo.define('favorite', function favorite(require){

    var translation = require('web.translation');
    var _t = translation._t;
    var Model = require('web.DataModel');
    var pyeval = require('web.pyeval');
    var session = require('web.session');
    var core = require('web.core');

    var FavoriteMenu = require('web.FavoriteMenu');
    FavoriteMenu.include({
        init: function (parent, query, target_model, action_id) {
            this._super.apply(this, arguments);
            this.my_favorite = new Model('favorite');
        },
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.$save_favorite = this.$('.oe-save-favorite');
            this.$save_favorite_name = this.$('.oe-save-favorite-name');
            var this_ = this;
            var event_favorite_toggle = this.$('.oe-save-favorite a');
            var event_favorite_keyup = this.$('.oe-save-favorite-name input');
            var event_save_favorite = this.$('.oe-save-favorite-name button');
            event_favorite_toggle.on('click', function(){ 
                this_.toggle_save_favorite_menu();
            });
            event_favorite_keyup.on('keyup', function(ev){  
                if (ev.which === $.ui.keyCode.ENTER) {
                    this_.save_my_favorite();
                }
            });
            event_save_favorite.on('click', function(){
                this_.save_my_favorite();
            })
            this.$inputs_favorite = this.$save_favorite_name.find('input');
        },
         toggle_save_favorite_menu: function (is_open) {
            this.$save_favorite
                .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
                .toggleClass('o_open_menu', is_open);
            this.$save_favorite_name.toggle(is_open);
            if (this.$save_favorite.hasClass('o_open_menu')) {
                this.$save_favorite_name.find('input').first().focus();
            }
        },
        save_my_favorite: function(){
            var self = this,
                favorite_name = this.$inputs_favorite[0].value;
            if (!favorite_name.length){
                this.do_warn(_t("Error"), _t("Favorite name is required."));
                this.$inputs_favorite.first().focus();
                return;
            }
            if (_.chain(this.filters)
                    .pluck('name')
                    .contains(favorite_name).value()) {
                this.do_warn(_t("Error"), _t("Filter with same name already exists. Favorites and filters can't have the same name"));
                this.$inputs._favorite.first().focus();
                return;
            }
            var search = this.searchview.build_search_data(),
                view_manager = this.findAncestor(function (a) {
                    // HORRIBLE HACK. PLEASE SAVE ME FROM MYSELF (BUT IN A PAINLESS WAY IF POSSIBLE)
                    return 'active_view' in a;
                }),
                view_context = view_manager ? view_manager.active_view.controller.get_context() : {},
                results = pyeval.sync_eval_domains_and_contexts({
                    domains: search.domains,
                    contexts: search.contexts.concat(view_context || []),
                    group_by_seq: search.groupbys || [],
                });
            if (!_.isEmpty(results.group_by)) {
                results.context.group_by = results.group_by;
            }
            if (!_.isEmpty(results.group_by)) {
                results.context.group_by = results.group_by;
            }
            // Don't save user_context keys in the custom filter, otherwise end
            // up with e.g. wrong uid or lang stored *and used in subsequent
            // reqs*
            var ctx = results.context;
            _(_.keys(session.user_context)).each(function (key) {
                delete ctx[key];
            });
            var filter = {
                name: favorite_name,
                user_id: session.uid,
                model_id: this.searchview.dataset.model,
                context: results.context,
                domain: results.domain,
                sort: JSON.stringify(this.searchview.dataset._sort),
                is_default: false,
                action_id: this.action_id,
            };
            return this.model.call('create_or_replace_favorite', [filter]).done(function (id) {
                filter.id = id;
                self.do_notify('Success',_t('Your filter has been added to the favorite'), true );
                self.my_favorite.call('create', [{'name' : self.$save_favorite_name.find('input').first().val() , 'filter' : id }] ).done(function (data) {
          //          self.toggle_filter(filter,true);
                    location.reload();
                });
            });

        },
    });

});