openerp.binary_attachment = function (instance) {
    var _t = instance.web._t;
    instance.web.Sidebar.include({
        init : function(){
            this._super.apply(this, arguments);
        },
        do_attachement_update: function(dataset, model_id, args) {
            var self = this;
            this.dataset = dataset;
            this.model_id = model_id;
            if (args && args[0].error) {
                this.do_warn(_t('Uploading Error'), args[0].error);
            }
            if (!model_id) {
                this.on_attachments_loaded([]);
            } else {
//            	var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']] ];
                var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']], ['is_binary_field', '=', false] ];
                var ds = new instance.web.DataSetSearch(this, 'ir.attachment', dataset.get_context(), dom);
                ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(this.on_attachments_loaded);
            }
        }
    });
};
