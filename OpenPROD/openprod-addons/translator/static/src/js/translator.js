'use strict';
odoo.define('translator', function(require){
	
	var ViewManager = require('web.ViewManager');
	var FormViewDialog = require('web.form_common').FormViewDialog;

    var translate_terms = function(srcElement, current_model){
        var self = this;
        var type, label, name, res_id = 0;
        var vals = {};
        
        if (srcElement.className.indexOf('oe_form_label') > -1) {
            type = 'field';
            label = srcElement.textContent.trim().split('\n')[0];
            var widget_id = srcElement.attributes.for.nodeValue;
            var field_name = $(srcElement).attr('field-name');
            if (field_name == undefined) {
                var parentNode = srcElement.parentNode;
                var parentClass = parentNode.className;
                field_name = /formview_\w+_label_([\w_]+)_\d+/.exec(parentClass)[1]
            }
            name = current_model + ',' + field_name;
            vals.type = type;
            vals.field_name = field_name;
            vals.label = label;
        } else if ($(srcElement).data('menu')) {
        	vals.type = 'menu';
            vals.label = srcElement.textContent.trim().split('\n')[0];
        	vals.res_id = $(srcElement).data('menu');
        } else if ($(srcElement.parentNode).data('menu')) {
        	vals.type = 'menu';
            vals.label = srcElement.textContent.trim().split('\n')[0];
        	vals.res_id = $(srcElement.parentNode).data('menu');
        } else if ($(srcElement).parent().prop('nodeName') == 'BUTTON'
        	|| $(srcElement).parent().hasClass('op_legend')
        	|| $(srcElement).attr('role') == 'tab'
        	) {
        	vals.type = 'view';
        	vals.label = srcElement.textContent.trim().split('\n')[0];
        	vals.res_id = this.views.form.view_id || this.views.form.controller.fields_view.view_id;
        } else if ($(srcElement).parent().parent().hasClass('oe_form_field_status')) {
        	vals.type = 'state';
        	vals.field = 'state';
        	vals.label = srcElement.textContent.trim().split('\n')[0];
        } else if ($(srcElement).parent().attr('class').indexOf('oe_list_header') > -1) {
        	vals.type = 'field';
        	vals.field_name = $(srcElement).parent().data('id');
        	vals.label = srcElement.textContent.trim().split('\n')[0];
        }
        
        vals.model = current_model;
        this.session.rpc(
            "/web/translator/get_translate_wizard",
            vals
        ).then(
            function(result) {
                if (!result.is_action){
                    return self.do_warn(_("Can't translate this string"),
                                        result.value);
                } else {
                    return self.do_action(result.value);
                }
            }
        );
    }
    
    var destroy = function() {
        this.$el.unbind('mousedown', this.translate_view);
        $(document.body).unbind('mousedown', this.fn_translate_body);
        this._super();
    }

    ViewManager.include({
        start: function() {
            var self = this;
            this.fn_translate_body = function() { return self.translate_body.apply(self, arguments); };
            this.$el.mousedown(this, this.translate_view);
            $(document.body).mousedown(this, this.fn_translate_body);
            return this._super();
        },

        translate_view: function(event){
            if(!event.ctrlKey){ return;}
            event.stopImmediatePropagation();
            event.preventDefault();
            event.data.translate_terms(event.target,
                                       event.data.dataset.model)
        },

        translate_body: function(event){
            if(!event.ctrlKey){ return;}
            event.stopImmediatePropagation();
            event.preventDefault();
            event.data.translate_terms(event.target)
        },
        
        translate_terms: translate_terms,
        destroy: destroy,
    });
    
    FormViewDialog.include({
        start: function() {
            var self = this;
            this.fn_translate_body = function() { return self.translate_body.apply(self, arguments); };
            this.$el.mousedown(this, this.translate_view);
            this._super();
        },

        translate_view: function(event){
            if(!event.ctrlKey){ return;}
            event.stopImmediatePropagation();
            event.preventDefault();
            event.data.translate_terms(event.target,
                                       event.data.dataset.model)
        },
        
        translate_terms: translate_terms,
        destroy: destroy,
    });
});
