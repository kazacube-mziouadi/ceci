/*
Barnabas Mercredi 14 juin 2017
Enlève les espaces en début et en fin de texte dans les champs de recherche de la liste view
On vient surcharger le fonction change_list_filters qui est appelé lorsque qu'on appuie sur la touche entré de la liste de recherche
*/

odoo.define('web_char_trim_list_view', function web_char_trim(require) {
'use strict';
    var ListView = require('web.ListView');
    var time = require('web.time');
    ListView.include({
        change_list_filters: function(ev) {
            // si il s'agit d'une multi select on n'effectue pas la recherche lors du clique sur un élément mais quand on quitte la zone de drop-down
            // pour cela on retourne null dans les 2 premiers if
            if (ev.target.tagName === 'SELECT' && ! ev.target.outerHTML.match(/☑/)  && ! ev.target.className.match(/select_search_bar/) ) {
                return null; 
            }
            if (ev.target.offsetParent && ev.target.offsetParent.className.match(/ms-drop/)){
                return null;
            }
            var val = ev.target.value;
            if (ev.target.type == 'datetime-local') {
                val = time.datetime_to_str(new Date(ev.target.value));
            }
            if (ev.target.type == 'text' || ev.target.type == 'char' ) { // c'est ici qu'on vien enlever les espaces en début et en fin de ligne dans la barre de recherche des list views
                val = $.trim(val);
            }
            var field_name = ev.target.dataset.colname || ev.target.parentNode.dataset.colname || ev.target.parentNode.parentNode.dataset.colname;
            var op = 'ilike';
            if (ev.target.parentNode.dataset.colname || ev.target.parentNode.parentNode.dataset.colname) {
                // there is an operator selector
                op = ev.target.lastElementChild && ev.target.lastElementChild.value || ev.target.parentNode.lastElementChild.value;
            }
            if (ev.target.tagName == 'SELECT') {
                var label = $(ev.target).find(':selected').text();
                op = '=';
            }
            this.ViewManager.searchview.query.add(this.facet_for(this.fields_view.fields[field_name], field_name, val, op, label));
        }
    });
    return ListView;
});