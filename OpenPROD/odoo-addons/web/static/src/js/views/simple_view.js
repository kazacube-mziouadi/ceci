odoo.define('web.SimpleView', function (require) {
"use strict";
/*---------------------------------------------------------
 * A simple view to render Qweb template
 *---------------------------------------------------------*/

var core = require('web.core');
var data = require('web.data');
var formats = require('web.formats');
var pyeval = require('web.pyeval');
var session = require('web.session');
var View = require('web.View');
var Model = require('web.DataModel');

var _lt = core._lt;
var QWeb = core.qweb;

var SimpleView = View.extend({
    // name displayed in view switchers probablement pas utilisé mais on le met au cas ou
    display_name: _lt('Simple'),
    // define a view type for each view to allow automatic call to fields_view_get.
    view_type: 'simple',
    searchview_hidden: true,
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable : false,
    view_loading: function(r) {
        return this.load_template(r);
    },
    load_template : function(data){
        var MyView = new Model('ir.ui.view');
        var self = this;
        // on va checher le contenu de l'arch de la vue
        MyView.query().filter([['id', '=' ,this.ViewManager.action.view_id[0] ]]).first().then(function(data) {
            // le modèle de la vue
            var IterateOver = new Model(data.model);
            QWeb.add_template(data.arch);
            // on récupère le nom du template
            var template_name = data.arch;
            template_name = template_name.replace('<simple>','');
            template_name = template_name.replace('</simple>','');
            template_name = template_name.replace(/\s+/g, '');
            IterateOver.query().all().then(function (model){
                // le rendere du template, on lui passe le modèle en paramètre
                self.$el.html(QWeb.render(template_name, {model : model}));
            });
            
        }); 

        
    },

    
});


core.view_registry.add('simple', SimpleView);

return SimpleView;

});