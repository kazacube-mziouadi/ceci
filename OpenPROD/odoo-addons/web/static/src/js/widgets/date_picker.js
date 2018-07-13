odoo.define('web.datepicker', function(require) {
    webshim.setOptions('forms-ext', {
        replaceUI: true,
        types: 'date time datetime-local',
        "widgets": {
            "startView": 2,
            "calculateWidth": false,
            "classes": "hide-spinbtns",
        }
    });
    webshim.setOptions('basePath', '/web/static/lib/js-webshim/minified/shims/');
    webshim.polyfill('forms forms-ext');
    
    var core = require('web.core');
    var formats = require('web.formats');
    var time = require('web.time');
    var Widget = require('web.Widget');
    
    var _t = core._t;
    
    var DateWidget = Widget.extend({
        template: "web.datepicker",
        type_of_date: "date",
        events: {
            'dp.change': 'change_datetime',
            'dp.show': 'set_datetime_default',
            'change .o_datepicker_input': 'change_datetime',
        },
        init: function(parent, options) {
            this._super.apply(this, arguments);
            
            var l10n = _t.database.parameters;
            
            this.name = parent.name;
        },
        start: function() {
            this.$input = this.$('input.o_datepicker_input');
            this.set_readonly(false);
            this.$input.updatePolyfill();
        },
        set_value: function(value) {
            this.set({
                'value': value
            });
            var local_val = moment.utc(value).local();
            var formatted_value = formats.parse_value(local_val, {widget:this.type_of_date});
            if (this.type_of_date == 'datetime') {
                var moment_value = moment.utc(value).local().format("YYYY-MM-DDTHH:mm:ss");
            } else {
                var moment_value = moment.utc(value).local().format("YYYY-MM-DD");
            }
            this.$input.val((value) ? moment_value : '');
        },
        get_value: function() {
            return formats.parse_value(this.get('value'), {widget:this.type_of_date});
        },
        set_value_from_ui: function() {
            var value = this.parse_client(this.$input.val()) || false;
            this.set({
                'value': value
            });
        },
        set_readonly: function(readonly) {
            this.readonly = readonly;
            this.$input.prop('readonly', this.readonly);
        },
        is_valid: function() {
            var value = this.$input.val();
            if (value === "") {
                return true;
            } else {
                try {
                    this.parse_client(value);
                    return true;
                } catch (e) {
                    return false;
                }
            }
        },
        parse_client: function(v) {
            if (!v) {
                return v;
            }
            return moment(v).utc();
        },
        format_client: function(v) {
            var format_spec = this.type_of_date == "datetime" ? "YYYY-MM-DD HH:MM:SS" : "YYYY-MM-DD";
            return moment(v).format(format_spec);
        },
        set_datetime_default: function() {
            //when opening datetimepicker the date and time by default should be the one from
            //the input field if any or the current day otherwise
            var value = moment().second(0);
            if (this.$input.val().length !== 0 && this.is_valid()) {
                value = this.$input.val();
            }
           
        },
        change_datetime: function(e) {
            if (this.is_valid()) {
                this.set_value_from_ui();
                this.trigger("datetime_changed");
            }
        },
        commit_value: function() {
            this.change_datetime();
        },
        destroy: function() {
            //this.picker.destroy();
            this._super.apply(this, arguments);
        },
    });
    
    var DateTimeWidget = DateWidget.extend({
        type_of_date: "datetime"
    });
    
    return {
        DateWidget: DateWidget,
        DateTimeWidget: DateTimeWidget,
    };

});
