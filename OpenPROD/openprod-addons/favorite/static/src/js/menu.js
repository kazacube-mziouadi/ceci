"use strict";
odoo.define('favorite.Menu', function (require){
    var Menu = require('web.Menu');
    
    Menu.include({
        //Récupère l'événement click quand on click sur un menu 
        on_menu_click: function(ev) {
            ev.preventDefault();
            this.menu_click($(ev.currentTarget).data('menu'), false,$(ev.currentTarget).data('filter-id'));
        },
        /**
         * Process a click on a menu item
         *
         * @param {Number} id the menu_id
         * @param {Boolean} [needaction=false] whether the triggered action should execute in a `needs action` context
         * @param {Number} filter_id id du filtre à appliquer sur la vue si on applique un filtre à la vue
         */
        menu_click: function(id, needaction, filter_id) {
            if (!id) { return; }

            // find back the menuitem in dom to get the action
            var $item = this.$el.find('a[data-menu=' + id + ']');
            if (!$item.length) {
                $item = this.$secondary_menus.find('a[data-menu=' + id + ']');
            }
            var action_id = $item.data('action-id');
            // on extraie l'id du filtre
            if (filter_id) {
                filter_id = filter_id.substr(1);
                filter_id = parseInt(filter_id);
            }
            if (action_id) {
                this.trigger('menu_click', {
                    action_id: action_id,
                    needaction: needaction,
                    filter_id: filter_id, // on ajoute l'id du filtre
                    id: id,
                    previous_menu_id: this.current_menu // Here we don't know if action will fail (in which case we have to revert menu)
                }, $item);
            } else {
                console.log('Menu no action found web test 04 will fail');
            }
            this.open_menu(id);
        },
    });

    return Menu;
});