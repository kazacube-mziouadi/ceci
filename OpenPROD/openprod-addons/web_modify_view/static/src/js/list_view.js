odoo.define('web.ListViewModifiedView', function (require) {
"use strict";
var Model = require('web.DataModel');
var ListView = require('web.ListView');

ListView.include({
    view_loading: function(r) { // on ajoute this.is_modify_view = true à la liste view si il s'aggit d'une vue liste modifié
        this.is_modify_view = false;
        var self = this;
        if (this.view_id){
            var IRUIView = new Model('ir.ui.view');
            return IRUIView.query(['id', 'is_override'])
                    .filter([['id', '=', this.view_id]])
                    .first().then(function (view_actual) {
                        if (view_actual.is_override) 
                            self.is_modify_view = true; 
                        return self.load_list(r);
                    });
        }
        else {             
        return this.load_list(r);
        }
    },
    do_activate_record: function (index, id, dataset, view) { // fonction appelé lors du clique sur un record de la liste view
        if (this.is_modify_view){    // s'il s'agit d'une modify_view on redirige vers l'utilisateur vers la bonne vue forme en utilisant l'url
            var getParameterByName = function(name, url) {
                if (!url) url = window.location.href;
                name = name.replace(/[\[\]]/g, "\\$&");
                var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
                    results = regex.exec(url);
                if (!results) return null;
                if (!results[2]) return '';
                return decodeURIComponent(results[2].replace(/\+/g, " "));
            }
            var url = new URL(window.location.href);
            var model = getParameterByName('model', url);
            var action = getParameterByName('action', url);
            var new_adress = window.location.origin + window.location.pathname +  window.location.search +'#id=' + id + '&view_type=form&model=' + model + '&action=' + action ;
           window.location.replace(new_adress);
           window.location.reload();
        }
        else {
            this.dataset.ids = dataset.ids;
            this.select_record(index, view);
        }
    },

});

return ListView;

});