"use strict";
odoo.define('favorite.WebClient', function (require){
    var WebClient = require('web.WebClient');
    var Model = require('web.DataModel');

    WebClient.include({
        // on vient modifier l'action du menu du webclient pour prendre en compte le filtre 
        on_menu_action: function(options) {
        var self = this;
        return this.menu_dm.add(this.rpc("/web/action/load", { action_id: options.action_id }))
            .then(function (result) {
                // si on a un filtre à appliquer à la vue on vient modifier le contexte
                if (options.filter_id){
                    var Filter = new Model('ir.filters');
                    Filter.query().filter([['id','=',options.filter_id]]).first().then(function(filter){
                        result.context = filter.context;
                        result.domain = filter.domain;
                        result.name = filter.name;
                        result.display_name = filter.name;
                        
                        return self.action_mutex.exec(function() {
                            if (options.needaction) {
                                result.context = new data.CompoundContext(result.context, {
                                    search_default_message_needaction: true,
                                    search_disable_custom_filters: true,
                                });
                            }
                            var completed = $.Deferred();
                            $.when(self.action_manager.do_action(result, {
                                clear_breadcrumbs: true,
                                action_menu_id: self.menu.current_menu,
                            })).fail(function() {
                                self.menu.open_menu(options.previous_menu_id);
                            }).always(function() {
                                completed.resolve();
                            });
                            setTimeout(function() {
                                completed.resolve();
                            }, 2000);
                            completed.then(function() {
                                if (['new', 'stack'].indexOf(result.target) == -1) {
                                    var searchview = self.action_manager.get_inner_widget().searchview;
                                    // Ajout temporaire du facet, a modifier dès qu'on comprend le fonctionnement
                                    var n = $(
                                    '<div class="oe_tag oe_searchview_facet" tabindex="0"><span class="oe_facet_remove reload_filter">x</span> '+
                                    '<span class="label label-default fa fa-star"> </span><span class="oe_facet_values"><span class="oe_facet_value">'+result.name+'</span></span> </div>' +
                                    '<div class="oe_searchview_input" contenteditable="true" tabindex="0"></div>');
                                    searchview.$facets_container[0].appendChild(n[0]);

                                    $('.home_selected').removeClass('home_selected').hide();
                                    $('.oe_application').show();
                                }
                            });
                            // We block the menu when clicking on an element until the action has correctly finished
                            // loading. If something crash, there is a 2 seconds timeout before it's unblocked.
                            return completed;
                        });
  

                    });       
                }
                else {
                    return self.action_mutex.exec(function() {
                        if (options.needaction) {
                            result.context = new data.CompoundContext(result.context, {
                                search_default_message_needaction: true,
                                search_disable_custom_filters: true,
                            });
                        }
                        var completed = $.Deferred();
                        $.when(self.action_manager.do_action(result, {
                            clear_breadcrumbs: true,
                            action_menu_id: self.menu.current_menu,
                        })).fail(function() {
                            self.menu.open_menu(options.previous_menu_id);
                        }).always(function() {
                            completed.resolve();
                        });
                        setTimeout(function() {
                            completed.resolve();
                        }, 2000);
                        completed.then(function() {
                            if (['new', 'stack'].indexOf(result.target) == -1) {
                                $('.home_selected').removeClass('home_selected').hide();
                                $('.oe_application').show();
                            }
                        });
                        // We block the menu when clicking on an element until the action has correctly finished
                        // loading. If something crash, there is a 2 seconds timeout before it's unblocked.
                        return completed;
                    });
                }
            });
        },
    });

    return WebClient;
});