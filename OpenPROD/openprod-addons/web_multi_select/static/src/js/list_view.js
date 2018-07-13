odoo.define('web_multi_select_list_view', function web_multi_select_list_view(require) {
'use strict';
    var ListView = require('web.ListView');
    ListView.include({
        /**
         * On lance la recherche quand l'utilisateur quite la liste de drop-down avec la souris
         * Pour plus d'infos sur la multipleSelect voire http://wenzhixin.net.cn/p/multiple-select/docs/
         */
        mouse_leave_ms_drop: function(ev){
            // Si l'utilisateur n'a séléctionné aucun élément on ne lance pas la recherche
            var selected = -1;
            if ($(".oe_list_header_search select[multiple]").length > 0) {
                for (var i = 0 ; i < $(".oe_list_header_search select[multiple]").length ; i++){
                    if ($($(".oe_list_header_search select[multiple]")[i]).multipleSelect("getSelects").length > 0 ){
                        selected = i;
                    }
                }
                if (selected === -1){
                    return null;
                }
            }
            // le nom du champ sur lequel la recherche aura lieu
            var field_name;
            if (ev.target.parentNode.parentNode.previousElementSibling && ev.target.parentNode.parentNode.previousElementSibling.dataset.colname)
                field_name = ev.target.parentNode.parentNode.previousElementSibling.dataset.colname;
            else if (ev.target.parentNode.parentNode.parentNode.previousElementSibling && ev.target.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname)
                field_name = ev.target.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname;
            else if (ev.target.parentNode.parentNode.parentNode.parentNode.previousElementSibling && ev.target.parentNode.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname)
                field_name = ev.target.parentNode.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname;
            else if (ev.target.parentNode.parentNode.parentNode.parentNode.parentNode.previousElementSibling && ev.target.parentNode.parentNode.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname)
                field_name = ev.target.parentNode.parentNode.parentNode.parentNode.parentNode.previousElementSibling.dataset.colname;
            else if (ev.target.previousElementSibling && ev.target.previousElementSibling.dataset.colname)
                field_name = ev.target.previousElementSibling.dataset.colname;
            else field_name = ev.target.parentNode.previousElementSibling.dataset.colname;
            // l'opérateur de la recherche
            var op = 'in';
            // liste des values de options sélectionnées, en anglais pour la recherche
            var val = $($(".oe_list_header_search select[multiple]")[selected]).multipleSelect("getSelects");
            // liste des textes sélectionnés pour la facet de la searchview, dans la langue de l'utilisateur
            var label = $($(".oe_list_header_search select[multiple]")[selected]).multipleSelect("getSelects","text").toString();
            // la field_view utilisé pour la facet
            var fields_view = this.fields_view.fields[field_name];
            // la fermeture de la dropdown liste
            $($(".oe_list_header_search select[multiple]")[selected]).multipleSelect("close");
             // on lance la recherche
            this.ViewManager.searchview.query.add(this.facet_for(fields_view, field_name, val, op, label));
    },
    });
    return ListView;
});