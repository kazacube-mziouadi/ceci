odoo.define('web_verify_mail', function web_verify_mail(require) {
'use strict';
    var web_form_widget = require('web.form_widgets');
    var core = require('web.core');
    var _t = core._t;
    var validateEmail = function(email) {
        var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(email);
    }

    web_form_widget.WidgetButton.include({
        init: function(field_manager, node) {
            this.verify_mail = false;
            if (node && node.attrs && node.attrs.widget){
                if (node.attrs.widget === "verify_mail"){
                    this.verify_mail = true;
                }
            }
            this._super(field_manager, node);
        },
        on_click: function() {
            if (this.verify_mail) {
                var correct = true;
                var mails = "";
                var to_focus = null;
                for (var i = 0 ; i < $('.verify_mail > input, .verify_mail textarea.user-success').length; i++){
                    var mail_array = $($('.verify_mail > input, .verify_mail textarea.user-success')[i]).val().split(',');
                    for (var j=0; j < mail_array.length; j++) {
                         mail_array[j] = mail_array[j].replace(/(^\s*)|(\s*$)/g,"");
                    }
                    for (var j=0; j < mail_array.length; j++) {
                        if (! validateEmail(mail_array[j]) && mail_array[j].length > 0){
                            correct = false;
                            mails+= mail_array[j] + " ";
                            to_focus = i;
                        }
                    }
                }
                if (! correct){
                    this.do_warn(_t('Invalid e-mail adress : '), mails + '<br/>' + _t('Split up your e-mail adress with a coma'), false);
                    $($('.verify_mail > input, .verify_mail textarea.user-success')[to_focus]).focus();
                    return null;
                }
            }
            this._super();
        },
    });
    return web_form_widget;
});
