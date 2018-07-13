"use strict";
odoo.define('favoritemain', function favoritemain(require){

    var translation = require('web.translation');
    var _t = translation._t;
    var Model = require('web.DataModel');
    var pyeval = require('web.pyeval');
    var session = require('web.session');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var ActionManager = require('web.ActionManager');
    var WebClient = require('web.WebClient');
    var View = require('web.View');
    
    var module = Widget.include({
        events: {
            'click #fav-list .favorite-item' : 'showFavorite' ,
            'click #fav-list .remove-favorite' : 'deleteFavorite',
            'click .reload_filter' : function(){
                location.reload();
            }
        },
        showFavorite : function(ev){
            var Filter = new Model('ir.filters');
            var filter_id = parseInt( $(ev.target).attr('data-id').split(",")[0]); 
            var self = this;
            Filter.query().filter([['id','=', filter_id]]).first().then( function(filter){
                var context = py.eval(filter.context);
                var action_id = filter.action_id;
                var domain = filter.domain;
                var sort = filter.sort;
                var options = {additionnal_context: context, clear_breadcrumbs: true  };
                return self.rpc("/web/action/load", { action_id: action_id[0], additional_context : context}).then(function(result) {
                    result.filter = filter;
                    result.domain = domain;
                    result.context = context;
                    self.do_action(result, options).then(function(){
                        var searchview = self.action_manager.get_inner_widget().searchview;
                        searchview.do_search(filter);

                        // Ajout temporaire du facet, a modifier dès qu'on comprend le fonctionnement
                        var n = $(
                            '<div class="oe_tag oe_searchview_facet" tabindex="0"><span class="oe_facet_remove reload_filter">x</span> '+
                            '<span class="label label-default fa fa-star"> </span><span class="oe_facet_values"><span class="oe_facet_value">'+filter.name+'</span></span> </div>' +
                            '<div class="oe_searchview_input" contenteditable="true" tabindex="0"></div>');
                        searchview.$facets_container[0].appendChild(n[0]);
                    });
                });;

            });
            return false;
        },
        deleteFavorite : function(ev) {
            var Favorite = new Model('favorite');
            var favorite_id = parseInt( $(ev.target).attr('data-id').split(",")[0]); 
            var self = this;
            Favorite.call('unlink',[favorite_id]).then(function(result){
                self.do_notify('Success',_t('Your favorite has been deleted'), true );
                location.reload();
            });
            return false;
        }
   
    })      
    return module;

});


