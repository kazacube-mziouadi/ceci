odoo.define('web.Menu', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var Menu = Widget.extend({
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.is_bound = $.Deferred();
        this.data = {data:{children:[]}};
        this.on("menu_bound", this, function() {
            // launch the fetch of needaction counters, asynchronous
            var $all_menus = self.$el.parents('body').find('.oe_webclient').find('[data-menu]');
            var all_menu_ids = _.map($all_menus, function (menu) {return parseInt($(menu).attr('data-menu'), 10);});
            if (!_.isEmpty(all_menu_ids)) {
                this.do_load_needaction(all_menu_ids);
            }
        });
        this.hide_file_menu = true;
        /**
         * 
         * Ajout js toggle menu
         */
        $(function() {
            $('ul.dropdown-menu [data-toggle=dropdown]').on('click', function(event) {
                // Avoid following the href location when clicking
                event.preventDefault();
                // Avoid having the menu to close when clicking
                event.stopPropagation();
                // If a menu is already open we close it
                $('ul.dropdown-menu [data-toggle=dropdown]').parent().removeClass('open');
                // opening the one you clicked on
                $(this).parent().addClass('open');
            });
            $('li.dropdown-submenu a').hover(function(ev){
                if($('body').width() > 768){
                    if(ev.target.nextElementSibling && $(ev.target.nextElementSibling).offset().left + $(ev.target.nextElementSibling).width() > $("body").innerWidth()){
                        var top = $(ev.target.nextElementSibling).offset().left.top + 25;
                        var left = $(ev.target).parent().offset().left - $(ev.target.nextElementSibling).width();
                        $(ev.target.nextElementSibling).offset({ 'left' : left , 'top' : top });
                    }
                } 
            });
        });

        $('#btn_menu_toggle').click(function(ev){
            self.hide_file_menu = ! self.hide_file_menu;
            $('.oe_leftbar').toggle();
            $('.menu_drop').toggle();
            $('.menu_normal').toggle();
            self.reflow(false);
        });
        core.bus.on('do_reload_needaction', this, this.do_reload_needaction);
        core.bus.on('change_menu_section', this, this.on_change_top_menu);
    },
    start: function() {
        this._super.apply(this, arguments);
        return this.bind_menu();
    },
    do_reload: function() {
        var self = this;
        self.bind_menu();
    },
    bind_menu: function() {
        var self = this;
        this.$secondary_menus = this.$el.parents().find('.oe_secondary_menus_container');
        this.$secondary_menus.on('click', 'a[data-menu]', this.on_menu_click);
        this.$el.on('click', 'a[data-menu]', function (event) {
            event.preventDefault();
            var menu_id = $(event.currentTarget).data('menu');
            var needaction = $(event.target).is('div#menu_counter');
            if (event.target.parentNode.dataset.actionId){
                core.bus.trigger('change_menu_section', menu_id, needaction, event.target.parentNode.dataset.actionId );
            }
            else if (event.target.dataset.actionId){
                core.bus.trigger('change_menu_section', menu_id, needaction, event.target.dataset.actionId );
            }
            else {
                core.bus.trigger('change_menu_section', menu_id, needaction , false);
            }
        });

        // Hide second level submenus
        this.$secondary_menus.find('.oe_menu_toggler').siblings('.oe_secondary_submenu').hide();
        if (self.current_menu) {
            self.open_menu(self.current_menu);
        }
        this.trigger('menu_bound');

        var lazyreflow = _.debounce(this.reflow.bind(this), 200);
        core.bus.on('resize', this, function() {
            if ($(window).width() < 768 ) {
                lazyreflow('all_outside');
            } else {
                lazyreflow();
            }
        });
        core.bus.trigger('resize');
        this.is_bound.resolve();
        // affichage de l'icone des favoris pour les menu_drop
        for (var i = 0 ; i < $('ul.nav>li.menu_drop>a').length ; i++){
            if ($('ul.nav>li.menu_drop>a')[i].innerHTML.indexOf('Favorite') !== -1 ){
                $($('ul.nav>li.menu_drop>a')[i]).html('<span class="oe_menu_text fa fa-star-o" style="color: rgb(255, 255, 255); cursor: pointer; font-size: 30px;"></span>');
                $($('ul.nav>li.menu_drop>a')[i]).css({'padding' : '0px' , 'margin-top':'0px' });
                break;
            }
        }
        // affichage de l'icone des favoris pour les menus normaux
        for (var i = 0 ; i < $('ul.nav>li.menu_normal>a').length ; i++){
            if ($('ul.nav>li.menu_normal>a')[i].innerHTML.indexOf('Favorite') !== -1 ){
                $($('ul.nav>li.menu_normal>a')[i]).html('<span class="oe_menu_text fa fa-star-o" style="color: rgb(255, 255, 255); cursor: pointer; font-size: 30px;"></span>');
                $($('ul.nav>li.menu_normal>a')[i]).css({'padding' : '0px' , 'margin-top':'0px' });
                break;
            }
        }
    },
    do_load_needaction: function (menu_ids) {
        var self = this;
        menu_ids = _.compact(menu_ids);
        if (_.isEmpty(menu_ids)) {
            return $.when();
        }
        return this.rpc("/web/menu/load_needaction", {'menu_ids': menu_ids}).done(function(r) {
            self.on_needaction_loaded(r);
        });
    },
    on_needaction_loaded: function(data) {
        var self = this;
        this.needaction_data = data;
        _.each(this.needaction_data, function (item, menu_id) {
            var $item = self.$secondary_menus.find('a[data-menu="' + menu_id + '"]');
            $item.find('.badge').remove();
            if (item.needaction_counter && item.needaction_counter > 0) {
                $item.append(QWeb.render("Menu.needaction_counter", { widget : item }));
            }
        });
    },
    /**
     * Reflow the menu items and dock overflowing items into a "More" menu item.
     * Automatically called when 'menu_bound' event is triggered and on window resizing.
     *
     * @param {string} behavior If set to 'all_outside', all the items are displayed.
     * If not set, only the overflowing items are hidden.
     */
    reflow: function(behavior) {
        var self = this;
        for (var i = 0 ; i < $('header.o_statusbar_buttons').length ; i++ ){
            $($('header.o_statusbar_buttons')[i]).width($($('header.o_statusbar_buttons')[i]).parent().outerWidth() + 20 );
        }

        if ($('body').width() < 768) {
            this.hide_file_menu = false;
        }
        if (this.hide_file_menu) {
            var $more_container = this.$('#menu_more_container').hide();
            var $more = this.$('#menu_more');
            var $systray = this.$el.parents().find('.oe_systray');

            $more.children('li').insertBefore($more_container);  // Pull all the items out of the more menu

            // 'all_outside' beahavior should display all the items, so hide the more menu and exit
            if (behavior === 'all_outside') {
                // Show list of menu items
                self.$el.show();
                this.$el.find('li').show();
                $more_container.hide();
                return;
            }

            // Hide all menu items
            var $toplevel_items = this.$el.find('li.menu_normal').not($more_container).not($systray.find('li')).hide();
            // Show list of menu items (which is empty for now since all menu items are hidden)
            self.$el.show();
            self.$el.children().filter('.menu_drop').hide();
            $toplevel_items.each(function() {
                var remaining_space = self.$el.parent().width() - $more_container.outerWidth();
                self.$el.parent().children(':visible').each(function() {
                    remaining_space -= $(this).outerWidth();
                });

                if ($(this).width() >= remaining_space) {
                    return false; // the current item will be appended in more_container
                }
                $(this).show(); // show the current item in menu bar
            });
            $more.append($toplevel_items.filter(':hidden').show());
            $more_container.toggle(!!$more.children().length);
            self.$el.children("li.menu_drop:visible").hide();
            // Hide toplevel item if there is only one
            var $toplevel = self.$el.children("li.menu_normal:visible");
            if ($toplevel.length === 1) {
                $toplevel.hide();
            }
        }
        else {
            var $more_container = this.$('#menu_more_container').hide();
            var $more = this.$('#menu_more');
            var $systray = this.$el.parents().find('.oe_systray');

            $more.children('li').insertBefore($more_container);  // Pull all the items out of the more menu

            // 'all_outside' beahavior should display all the items, so hide the more menu and exit
            if (behavior === 'all_outside') {
                for (var i = 0 ; i < this.$el.find('li.dropdown-submenu').length ; i++) {
                    $(this.$el.find('li.dropdown-submenu')[i]).addClass('dropdown');
                    $(this.$el.find('li.dropdown-submenu')[i]).removeClass('dropdown-submenu'); 
                    i--;
                }
                // Show list of menu items
                self.$el.show();
                this.$el.find('li').show();
                $more_container.hide();
                return;
            }
            if (this.$el.find('li.dropdown-submenu').length === 0 ){
                // on sort de la vue mobile
                window.location.reload();
            }
            // Hide all menu items
            var $toplevel_items = this.$el.find('li.menu_drop_first').not($more_container).not($systray.find('li')).hide();
            // on enlève le submenu en cas d'élargissement du menu
            for (var i = 0 ; i < $toplevel_items.length ; i++ ){
                $($toplevel_items[i]).addClass('dropdown');
                $($toplevel_items[i]).removeClass('dropdown-submenu');
            }
            $('.dropdown-submenu').css('display','list-item');

            // Show list of menu items (which is empty for now since all menu items are hidden)
            self.$el.show();
            $toplevel_items.each(function() {
                var remaining_space = self.$el.parent().width() - $more_container.outerWidth();
                self.$el.parent().children(':visible').each(function() {
                    remaining_space -= $(this).outerWidth();
                });

                if ($(this).width() >= remaining_space) {
                    return false; // the current item will be appended in more_container
                }
                $(this).show(); // show the current item in menu bar
            });
            for (var i = 0 ; i < $toplevel_items.filter(':hidden').length ; i++ ){
                $($toplevel_items.filter(':hidden')[i]).removeClass('dropdown');
                $($toplevel_items.filter(':hidden')[i]).addClass('dropdown-submenu');
            }
            $more.append($toplevel_items.filter(':hidden').show());
            $more_container.toggle(!!$more.children().length);
            // Hide toplevel item if there is only one
            $('.menu_normal').hide();
            var $toplevel = self.$el.children("li:visible");
            if ($toplevel.length === 1) {
                $toplevel.hide();
            }
        }
    },
    /**
     * Opens a given menu by id, as if a user had browsed to that menu by hand
     * except does not trigger any event on the way
     *
     * @param {Number} id database id of the terminal menu to select
     */
    open_menu: function (id, action_id) {
        this.current_menu = id;
        session.active_id = id;
        var $clicked_menu, $sub_menu, $main_menu;
        $clicked_menu = this.$el.add(this.$secondary_menus).find('a[data-menu=' + id + ']');
        this.trigger('open_menu', id, $clicked_menu);

        if (this.$secondary_menus.has($clicked_menu).length) {
            $sub_menu = $clicked_menu.parents('.oe_secondary_menu');
            $main_menu = this.$el.find('a[data-menu=' + $sub_menu.data('menu-parent') + ']');
        } else {
            $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + $clicked_menu.attr('data-menu') + ']');
            $main_menu = $clicked_menu;
        }

        // Activate current main menu
        this.$el.find('.active').removeClass('active');
        $main_menu.parent().addClass('active');

        // Show current sub menu
        this.$secondary_menus.find('.oe_secondary_menu').hide();
        $sub_menu.show();

        // Hide/Show the leftbar menu depending of the presence of sub-items
        //this.$secondary_menus.parent('.oe_leftbar').toggle(!!$sub_menu.children().length);
        //MODIF 
        if (this.hide_file_menu){
            this.$secondary_menus.parent('.oe_leftbar').toggle(!!$sub_menu.children().length);
        }

        // Activate current menu item and show parents
        this.$secondary_menus.find('.active').removeClass('active');
        if ($main_menu !== $clicked_menu) {
            if (this.hide_file_menu){
                $clicked_menu.parents().show();
            }
            if ($clicked_menu.is('.oe_menu_toggler')) {
                $clicked_menu.toggleClass('oe_menu_opened').siblings('.oe_secondary_submenu:first').toggle();
            } else {
                $clicked_menu.parent().addClass('active');
            }
        } 
        // add a tooltip to cropped menu items
        this.$secondary_menus.find('.oe_secondary_submenu li a span').each(function() {
            $(this).tooltip(this.scrollWidth > this.clientWidth ? {title: $(this).text().trim(), placement: 'right'} :'destroy');
       });

         if (this.hide_file_menu){
             $('.menu_drop').css('display','none');
         }
         $('ul.nav > .menu_drop > ul[style="display: block;"]').parent().addClass('active');
         $('.menu_drop > ul').removeAttr( 'style' );

         var main_menu_text = $main_menu[0].children[0].innerText.trim();
         $('.menu_drop').removeClass('active_menu_drop');
         // Pour les favoris : 
         if (main_menu_text.length === 0 ){      
            for (var i = 0 ; i < $('.menu_drop').children('a').length ; i++) {
                if ($('.menu_drop').children('a')[i].innerHTML.indexOf("fa-star-o") !== -1 ){
                    $($('.menu_drop').children('a')[i].parentNode).addClass('active_menu_drop');
                }
            }
         }
         else{
            for (var i = 0 ; i < $('.menu_drop_first').children('a').length ; i++) {
                if ($('.menu_drop_first').children('a')[i].innerHTML.indexOf(main_menu_text) !== -1 ){
                    $($('.menu_drop_first').children('a')[i].parentNode).addClass('active_menu_drop');
                }
            }
         }

       if (action_id) {
            var $item = this.$el.find('a[data-menu='+id+']');
            if ($('body').width() < 768 ) {
                // le toogle du navbar
                $('.navbar-collapse').removeClass('in');
                $('.navbar-collapse')[0].setAttribute("aria-expanded", false);
            }
            this.trigger('menu_click', {
                action_id: action_id,
                needaction: false,
                id: id,
                previous_menu_id: this.current_menu // Here we don't know if action will fail (in which case we have to revert menu)
            }, $item);
       }

    },
    /**
     * Call open_menu with the first menu_item matching an action_id
     *
     * @param {Number} id the action_id to match
     */
    open_action: function (id) {
        var $menu = this.$el.add(this.$secondary_menus).find('a[data-action-id="' + id + '"]');
        var menu_id = $menu.data('menu');
        if (menu_id) {
            this.open_menu(menu_id);
        }
    },
    /**
     * Process a click on a menu item
     *
     * @param {Number} id the menu_id
     * @param {Boolean} [needaction=false] whether the triggered action should execute in a `needs action` context
     */
    menu_click: function(id, needaction) {
        if (!id) { return; }

        // find back the menuitem in dom to get the action
        var $item = this.$el.find('a[data-menu=' + id + ']');
        if (!$item.length) {
            $item = this.$secondary_menus.find('a[data-menu=' + id + ']');
        }
        var action_id = $item.data('action-id');
        // If first level menu doesnt have action trigger first leaf
        /*if (!action_id) {
            if(this.$el.has($item).length) {
                var $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + id + ']');
                var $items = $sub_menu.find('a[data-action-id]').filter('[data-action-id!=""]');
                if($items.length) {
                    action_id = $items.data('action-id');
                    id = $items.data('menu');
                }
            }
        }*/
        if (action_id) {
            this.trigger('menu_click', {
                action_id: action_id,
                needaction: needaction,
                id: id,
                previous_menu_id: this.current_menu // Here we don't know if action will fail (in which case we have to revert menu)
            }, $item);
        } else {
            console.log('Menu no action found web test 04 will fail');
        }
        this.open_menu(id);
    },
    do_reload_needaction: function () {
        var self = this;
        if (self.current_menu) {
            self.do_load_needaction([self.current_menu]).then(function () {
                self.trigger("need_action_reloaded");
            });
        }
    },
    /**
     * Change the current top menu
     *
     * @param {int} [menu_id] the top menu id
     * @param {boolean} [needaction] true to redirect to menu's needactions
     */
    on_change_top_menu: function(menu_id, needaction, action_id) {
        var self = this;
        // Fetch the menu leaves ids in order to check if they need a 'needaction'
        /*var $secondary_menu = this.$el.parents().find('.oe_secondary_menu[data-menu-parent=' + menu_id + ']');
        var $menu_leaves = $secondary_menu.children().find('.oe_menu_leaf');
        var menu_ids = _.map($menu_leaves, function (leave) {return parseInt($(leave).attr('data-menu'), 10);});

        self.do_load_needaction(menu_ids).then(function () {
            self.trigger("need_action_reloaded");
        });*/
        this.$el.parents().find(".oe_secondary_menus_container").scrollTop(0,0);
        var def = this.getParent().clear_uncommitted_changes() || $.when();
        def.then(function(){
            self.open_menu(menu_id, action_id);
            $('.home_selected').removeClass('home_selected').hide();
            $('#homepage').hide();
            $('.oe_webclient').show();
            var $application = self.getParent().$el.find('.oe_application');
            var $home = $('#homepage_menu_' + menu_id);
            $application.hide();
            $home.show().addClass('home_selected');
        })
    },
    on_menu_click: function(ev) {
        ev.preventDefault();
        this.menu_click($(ev.currentTarget).data('menu'), false);
    },
});

return Menu;
});
