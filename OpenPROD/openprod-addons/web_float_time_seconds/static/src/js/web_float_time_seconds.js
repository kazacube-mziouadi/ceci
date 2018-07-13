// Float time seconds
// ==================

// Etant donné que `formats.js` ne permet pas de surcharger les différents types de widgets
// nous allons donc *monkey patcher* les deux fonctions de *parsing* et *formatting*.
odoo.define('web_float_time_seconds', function(require) {
	var core = require('web.core');
	var QWeb = core.qweb;
	var formats = require('web.formats');
	var format_to_hms = function(value){
		var pattern = '%02d:%02d:%02d';
        if (value < 0) {
            value = Math.abs(value);
            pattern = '-' + pattern;
        }
        var sec = Math.round((value % 1) * 3600);
        var minutes = Math.floor(sec / 60);
        var seconds = sec % 60;
        var formatted = _.str.sprintf(pattern,
                Math.floor(value),
                minutes,
                seconds);
        // Nous retournous notre valeur formattée avec les secondes.
        return formatted;
	}

    // Voici donc notre nouveau type de widget qui sera donc à utiliser avec l'attribut `@widget`
    // d'un tag field comme ceci:
    // ```xml
    // <field name="duration" widget="float_time_seconds"/>
    // ```
    var new_type = 'float_time_seconds';

    // Nous gardons une référence des anciennes fonctions que nous allons substituer.
    var old_format_value = formats.format_value;
    var old_parse_value = formats.parse_value;

    // Nous redéfinissons la foncton de *formatting*
    formats.format_value = function (value, descriptor, value_if_empty) {
        // Ici nous appelons la fonction d'origine.
        value = old_format_value.apply(formats, arguments);

        // Nous vérifions ici si l'attribut `@widget` correspond à notre nouveau type.
        // Le contenu de cette condition est en gros un copier/coller du **case** `float_time`
        // de `formats.js` légèrement adapté pour afficher les secondes.
        if (descriptor.widget == new_type || descriptor.type == new_type) {
//            var pattern = '%02d:%02d:%02d';
//            if (value < 0) {
//                value = Math.abs(value);
//                pattern = '-' + pattern;
//            }
//            var sec = Math.round((value % 1) * 3600);
//            var minutes = Math.floor(sec / 60);
//            var seconds = sec % 60;
//            var formatted = _.str.sprintf(pattern,
//                    Math.floor(value),
//                    minutes,
//                    seconds);
//            // Nous retournous notre valeur formattée avec les secondes.
//            return formatted;
        	return format_to_hms(value);
        }
        
        if (descriptor.widget == "datetime_time" || descriptor.type == "datetime_time") {
            return old_format_value(value, 'float_time')
        }
        // Pour les autres types de widgets, nous retournons la valeur calculée par la
        // fonction d'origine afin de ne pas altérer son comportement.
        return value;
    };

    // Nous redéfinissons la foncton de *parsing*
    formats.parse_value = function (value, descriptor, value_if_empty) {
        // Ici nous appelons la fonction d'origine.
        value = old_parse_value.apply(formats, arguments);

        // Même principe que précédemment: le contenu de cette condition est également
        // un copier/coller du **case** `float_time` de `formats.js` légèrement adapté
        // pour prendre en compte les secondes.
        if (descriptor.widget == new_type || descriptor.type == new_type) {
        	var factor = 1;
        	if (value[0] === '-') {
        		value = value.slice(1);
        		factor = -1;
        	}
        	var float_time_seconds = value.split(":");
        	if (float_time_seconds.length != 3)
        		return factor * formats.parse_value(value, {type: "float"});
        	var hours = formats.parse_value(float_time_seconds[0], {type: "integer"});
        	var minutes = formats.parse_value(float_time_seconds[1], {type: "integer"});
        	var seconds = formats.parse_value(float_time_seconds[2], {type: "integer"});
        	var parsed = factor * (hours + (minutes / 60) + (seconds / 3600));
        	// Retour de la valeur calculée
        	return parsed;
        }

        if (descriptor.widget == "datetime_time" || descriptor.type == "datetime_time") {
            var factor = 1;
            if (value[0] === '-') {
                value = value.slice(1);
                factor = -1;
            }
            var float_time_seconds = value.split(":");
            if (float_time_seconds.length != 3)
                return factor * old_parse_value(value, {type: "float_time"});
            var hours = formats.parse_value(float_time_seconds[0], {type: "integer"});
            var minutes = formats.parse_value(float_time_seconds[1], {type: "integer"});
            var seconds = formats.parse_value(float_time_seconds[2], {type: "integer"});
            var parsed = factor * (hours + (minutes / 60) + (seconds / 3600));
            // Retour de la valeur calculée
            return parsed;
        }
        
        

        // Retourn de la valeur calculée par la fonction d'origine afin de ne pas
        // altérer son comportement.
        return value;
    };

    // Enfin nous ajoutons une entrée dans la registy de la vue form afin d'enregistrer notre
    // nouveau type de widget. Celui-ci pointera vers `openerp.web.form.FieldFloat` à l'instar
    // du widget `float_time`.
    core.form_widget_registry.add(new_type, openerp.web.form.FieldFloat);

    

    // ajout pour compatibilité avec la vue Kanban

    var kanban_widgets = require('web_kanban.widgets');
    var AbstractField = kanban_widgets.AbstractField;
    var fields_registry = kanban_widgets.registry;
    var FloatTimeSecondsWidget = AbstractField.extend({
        init: function(parent, field, $node) {
            this._super.apply(this, arguments);
            this.name = $node.attr('name')
            this.parent = parent;
        },
        renderElement: function() {
            var self = this;
            this.record_id = self.parent.id;
            
            var value = format_to_hms(this.field.raw_value)

            var text_field = this.field.string;
            var attr_f = this.$node[0].attributes.getNamedItem("string");

            if (attr_f != undefined )
            {
            	text_field = attr_f.nodeValue;
            }
            text_field = text_field + " : ";
            var html = $("<div />").append(
            		$("<b />", {
            			text: text_field
            		})).append(
            				$('<span />', {text: value}));
            var html = $("<div />", {class: 'op_no_padding oe_fold_column oe_kanban_record', text: value});
            this.$el = html;
        },
        reload_record: function() {
            this.do_reload();
        },
    });

    fields_registry.add("float_time_seconds", FloatTimeSecondsWidget);
    return {
	    FloatTimeSecondsWidget: FloatTimeSecondsWidget,
};

});

