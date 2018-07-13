odoo.define('web_mail_autocomplete', function(require) {
	var core = require('web.core');
	var Model = require('web.Model');
	
	var MultiMail = core.form_widget_registry.get('char').extend({
	    render_value: function() {
	    	if (this.get("effective_readonly")) {
				this._super();
			} else {
				var self = this;
				this._super();
				$input = this.$el.find('input');
				$input.autocomplete({
					source: self.get_search_result,
					select: self.select
				});
			}
	    },

	    get_search_result: function(req, resp) {
	        var search_val = req.term;
	        var val_array = search_val.split(', ');
	        search_val = val_array[val_array.length - 1];
	    	var Partner = new Model('res.partner');
	    	Partner.query(['email']).filter([['email', 'like', search_val]]).limit(7).all().done(function(res){
	    		resp(_.pluck(res, 'email'));
	    	});
	    },

	    select: function(ev, ui) {
	        var val_array = ev.target.value.split(', ');
	        val_array[val_array.length - 1] = ui.item.value;
	        ev.target.value = val_array.join(', ');
	        return false;
	    },

	});

	core.form_widget_registry.add('multimail', MultiMail);
});

