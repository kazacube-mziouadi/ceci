var odoo = window.odoo;
odoo.define('declaration', function declaration(require) {
'use strict';
var Backbone = window.Backbone;
var Model = require('web.DataModel');
var session = require('web.session');
window.app = {};
var app = window.app;
var alert = window.alert;
var _ = window._;
var translation = require('web.translation');
var core = require('web.core');
var time = require('web.time');

var _t = translation._t;
var _lt = translation._lt;
var ENTER_KEY = 13;

/*  ======
    Models
    ======
*/
app.Workorder = Backbone.Model.extend({
    sync: function(method, model, options) {
        var self = this;
        var WO = new Model('mrp.workorder');
        switch (method) {
        case 'read':
            return WO.query([
            'id',
            'display_name',
            'first_resource_id',
            'final_product_id',
            'quantity',
            'state_timetracking',
            'name',
            'workorder_produce_ids',
            'declare_tablet_product',
            'declare_tablet_cons',
            'rm_draft_ids',
            'workorder_consumption_ids',
            'advancement',
            'declaration_note',
            'additional_resource_ids',
            'allow_operator_add',
            'planned_start_date',
            ]).filter([
                ['id', '=', options.id],
                ['state', 'not in', ['draft', 'waiting', 'done', 'cancel']],
            ]).first().done(function(){
                if (arguments[0]) {
                    var args = arguments;
                    $.when(
                        self.loadConsumptions(args[0].workorder_consumption_ids),
                        self.loadAdditionalResources(args[0].additional_resource_ids),
                        self.loadProductions(args[0].workorder_produce_ids)
                    ).then(function(){options.success.apply(self, args);});
                } else {
                    alert(_t('Unknown or invalid Workorder'));
                }
            });
        case 'patch':
            return WO.call('write', [model.id, options.attrs]).done(options.success);
        }
    },
    loadTimetracking: function() {
        if (typeof this.timetracking == 'undefined') {
            this.timetracking = new app.Timetracking();
        }
        return this.timetracking.fetch({
            wo_id: this.get('id')
        });
    },
    loadAdditionalResources: function(ids, options) {
        var res = new Model('mrp.wo.additional.resource').
                    query().
                    filter([['id', 'in', ids], ['end_date', '=', null]]).
                    all();
        res.then(function(res){
                        app.workorder.set('additional_resources', res, options || {silent: true});
                    });
        return res;
    },
    loadFirstResource: function() {
        this.firstResource = new app.WOResource();
        return this.firstResource.fetch({
            wo_id: this.get('id')
        });
    },
    loadRawMaterials: function() {
        this.rawMaterial = new app.StockMoveCollection();
        return this.rawMaterial.fetch({
            wo_id: this.get('id'),
            remove: false,
        });
    },
    loadLabels: function() {
        if (typeof this.labels == 'undefined') {
            this.labels = new app.LabelConsumedCollection();
        }
        return this.labels.fetch({
            wo_id: this.get('id')
        });
    },
    loadConsumptions: function(ids) {
        var self = this;
        var consumptionObj = new Model('mrp.wo.consumption');
        return consumptionObj.query([])
                      .filter([['id', 'in', ids], ['state', '!=', 'cancel']])
                      .all()
                      .then(function(res) {
                        self.consumptions = res;
                      });
    },
    loadProductions: function(ids) {
        var self = this;
        var produceObj = new Model('mrp.wo.produce');
        return produceObj.query([])
                      .filter([['id', 'in', ids], ['state', '!=', 'cancel']])
                      .all()
                      .then(function(res) {
                        self.produce = res;
                      });
    },
    initialize: function() {
        this.listenToOnce(this, "change", this.loadTimetracking);
        this.listenToOnce(this, "change", this.loadFirstResource);
        this.listenToOnce(this, "change", this.loadRawMaterials);
        this.listenToOnce(this, "change", this.loadLabels);
    },
});

app.GroupWorkorders = Backbone.Collection.extend({model:app.Workorder});
app.group_workorders = new app.GroupWorkorders();
app.workorder = new app.Workorder();

app.Resource = Backbone.Model.extend({
    sync: function(method, model, options) {
        switch (method) {
        case 'read':
            var Resource = new Model('mrp.resource');
            return Resource.query().filter([['id', '=', options.id]]).first().done(options.success);
        }
    },
});
app.resource = new app.Resource();

app.WOResource = Backbone.Model.extend({
    sync: function(method, model, options) {
        switch (method) {
        case 'read':
            var WO = new Model('mrp.wo.resource');
            return WO.query().filter([['wo_id', '=', options.wo_id]]).first().done(options.success);
        }
    },
});

app.Timetracking = Backbone.Model.extend({
    defaults: {
        prep_time: 0,
        prod_time: 0,
        cleaning_time: 0,
    },
    sync: function(method, model, options) {
        switch (method) {
        case 'read':
            var Timetracking = new Model('resource.timetracking');
            return Timetracking.query().filter([['wo_id', '=', options.wo_id]]).order_by(['-start_date']).all().done(options.success);
        }
    },
    parse: function(data) {
        var ret = {
            prep_time: 0,
            prod_time: 0,
            cleaning_time: 0
        };
        _.each(data, function(e) {
            if (e.activity == 'setting') {
                ret.prep_time += e.time;
            } else if (e.activity == 'production') {
                ret.prod_time += e.time;
            } else if (e.activity == 'cleaning') {
                ret.cleaning_time += e.time;
            }
        }
        );
        return ret;
    },
});

app.StockMove = Backbone.Model.extend({
    sync: function(method, model, options) {
        var Moves = new Model('stock.move');
        switch (method) {
        case 'patch':
            Moves.call('write', [model.get('id'), options.attrs]).done(options.success);
            break;
        case 'read':
            return Moves.query(['track_label_product', 'name', 'uom_qty', 'product_id', 'consumed_qty', 'sec_uom_qty', 'is_variable_double_unit']).filter([['id', '=', this.get('id')], ['state', 'not in', ['cancel']], ['not_usable', '=', true]]).first().done(options.success);
        case 'delete':
            Moves.call('wkf_cancel', [model.get('id')]).done(options.success).fail(options.error);
            break;
        }
    },
    change_product: function() {
        var Moves = new Model('stock.move');
        var self = this;
        app.group_workorders.map(function(wo) {
            var other_rm = app.get_equivalent_rm(self, wo);
            return Moves.call('change_product', [other_rm.id, self.product_id]).done(function(r) {
                other_rm.fetch().done(function() {
                    other_rm.trigger('change_product');
                });
            });
        });
    },
});

app.LabelConsumed = Backbone.Model.extend({
    defaults: {
        label_id: '',
        quantity: 0,
        use_consumption: app.label_consumption_grouping_flag,
    },
    sync: function(method, model, options) {
        var Label = new Model('mrp.label.consumption');
        switch (method) {
        case 'read':
            return Label.query().filter([['label_id', '=', options.label_id]]).first().done(options.success);
        case 'create':
            return Label.call('create', [model.toJSON()]).done(options.success).fail(options.error);
        case 'update':
            return Label.call('write', [model.get('id'), model.pick('quantity')]).done(options.success);
        case 'delete':
            return Label.call('unlink', [model.get('id')]).done(options.success);
        }
    },
});

app.Declaration = Backbone.Model.extend({
    sync: function(method, model, options) {
        switch (method) {
        case 'patch':
            var Declaration = new Model('wo.declaration.produce');
            Declaration.call('write', [model.get('id'), options.attrs]).done(options.success);
            break;
        }
    },
    action_validate: function(model, response, options) {
        var Declaration = new Model('wo.declaration.produce');
        var self = this;
        Declaration.call('action_validate', [model.get('id')], {context:{return_false:true}}).done(function(res) {
            if (_.isObject(res)) {
                new Model('wo.declaration.produce').query().filter([['id', '=', res.res_id]]).
                    first().
                    done(self.action_validate_success).
                    fail(function(r){alert(r.data.message);});
            } else {
                app.declaration_ok = true;
                app.router.view.cancel();
            }
        }
        ).fail(function(r){
            alert(r.data.message);
        });
    },
    action_validate_success: function(s) {
        app.declaration = new app.Declaration(s);
        app.router.loadView(new app.DeclarationView({
            model: app.declaration
        }));
    },
});

app.ProduceLabel = Backbone.Model.extend({
    sync: function(method, model, options) {
        var Declaration = new Model('assign.label.wo.produce');
        switch (method) {
        case 'patch':
            return Declaration.call('write', [model.get('id'), options.attrs]);
        case 'update':
            return Declaration.call('write', [model.get('id'), {quantity:model.get('quantity'),for_quarantine:model.get('for_quarantine')}]);
        }
    },
});

/*  ===========
    Collections
    ===========
*/
app.StockMoveCollection = Backbone.Collection.extend({
    model: app.StockMove,
    sync: function(method, model, options) {
        switch (method) {
        case 'read':
            var Moves = new Model('stock.move');
            return Moves.query(['track_label_product', 'name', 'uom_qty', 'sec_uom_qty', 'product_id', 'consumed_qty', 'state', 'is_variable_double_unit'])
                        .filter([
                            ['wo_incoming_id', '=', options.wo_id],
                            ['state', 'not in', ['cancel']],
                            ['not_usable', '=', false],
                            ])
                        .all()
                        .done(function(res) {
                            var moves = _.map(_.groupBy(res, 'product_id'), function(el){
                                return _.reduce(el, function(list, value) {
                                    list.consumed_qty += value.consumed_qty;
                                    list.uom_qty += value.uom_qty;
                                    if (list.state == 'done' && value.state != 'done') {
                                        list.id = value.id;
                                    }
                                    return list;
                                });
                            });
                            options.success(moves);
                        });
        }
    },
});

app.LabelConsumedCollection = Backbone.Collection.extend({
    model: app.LabelConsumed,
    sync: function(method, model, options) {
        switch (method) {
        case 'read':
            var Labels = new Model('mrp.label.consumption');
            var self = this;
            return Labels.query().filter([['wo_id', '=', options.wo_id]])
                .all()
                .done(options.success)
                .done(function(){
                    if (self.length) {
                        $('#traceability').removeClass('btn-primary');
                        $('#traceability').addClass('btn-success');
                    }
                });
        }
    },
    save: function() {
        var deferreds = _.flatten(this.map(function(label_cons){
            return app.group_workorders.map(function(wo) {
                if (label_cons.get('label_id')) {
                    var dfd = $.Deferred();
                    label_cons.save({wo_id: wo.id}).always(function(){dfd.resolve();});
                    return dfd;
                } else {
                    return $.Deferred().resolve();
                }
            });
        }), true);
        return $.when.apply($, deferreds);
    },
});

app.ProduceLabelCollection = Backbone.Collection.extend({
    model: app.ProduceLabel,
});

/*  =====
    Views
    =====
*/
app.HomeView = Backbone.View.extend({
    tagName: 'div',
    className: 'form',
    template: _.template($('#t_home').html()),
    events: {
        'keypress #resource_input': 'onResourceKey',
        'keypress #workorder_input': 'onWOKey',
        'click #validate': 'onValidateClick',
        'click #quit': 'onQuitClick',
    },
    initialize: function() {
        $('body').append(this.$el);
        this.render();
        this.resourceView = new app.ResourceView({
            model: app.resource
        });
        this.workorderView = new app.WorkorderView({
            collection: app.group_workorders
        });
        $('#resource_input').focus();
    },
    render: function() {
        this.$el.html(this.template({_t:_t}));
    },
    onResourceKey: function(e) {
        if (e.which === ENTER_KEY) {
            app.resource.fetch({
                id: e.target.value
            }).done(function(r){
                if (r) {
                    $('#workorder_input').focus();
                } else {
                    alert(_t('Invalid resource'));
                }
            }).fail(function(){
                alert(_t('Invalid resource'));
            });
        }
    },
    onWOKey: function(e) {
        var self = this;
        if (e.which === ENTER_KEY) {
            if (!app.resource.id) {
                alert(_t('Select a resource first'));
                return;
            }
            new app.Workorder().fetch({
                id: e.target.value,
                success: function(res) {
                    app.group_workorders.add([res]);
                    $("#validate").prop('disabled', false);
                },
            });
            return false;
        }
    },
    onValidateClick: function(e) {
        var def;
        if (app.group_workorders.length > 1) {
            var vals = {
                resource_id: app.workorder.get('first_resource_id')[0],
                planned_start_date: app.workorder.get('planned_start_date'),
            };
            def = new Model('mrp.group.wo').call('create', [vals]).then(function(res) {
                app.workorder_group_id = res;
                return new Model('mrp.group.wo').call('add_wo_to_group', [res, app.group_workorders.pluck('id')]);
            });
            def.fail(function(r){alert(r.data.message);});
        } else {
            def = $.when();
        }
        def.then(function(){
            if (app.group_workorders.length > 1) {
                app.router.main('g' + app.workorder_group_id);
            }
            else {
                 app.router.main(app.workorder.id);
            }      
        });
        return false;
    },
    
    onQuitClick: function(e) {
        window.close();
    },
    
    remove: function() {
        this.resourceView.remove();
        this.workorderView.remove();
        Backbone.View.prototype.remove.call(this);
    }
});

app.WorkorderView = Backbone.View.extend({
    el: '#workorder',
    template: _.template($('#t_workorderview').html()),
    initialize: function() {
        var StockConfigSettings = new Model('stock.config.settings');
        var self = this;
        StockConfigSettings.query(['declaration_grouping_flag']).first().done( function (data) {
            self.declaration_grouping_flag = data.declaration_grouping_flag;
            self.collection.on("add remove", self.render , self);
        });
    },
    render: function() {
        if (app.workorder.isNew()) {
            app.workorder = app.group_workorders.first();
        }
        this.$el.html(this.template({workorders: this.collection.toJSON(), _t:_t , declaration_grouping_flag: this.declaration_grouping_flag }));
        this.$('#workorder_input').focus();
    },
    events: {
        'click .deleteWO': 'deleteWOClick',
    },
    deleteWOClick : function(e){
        e.preventDefault();
        app.group_workorders.remove(e.target.dataset.woId);
        if (app.group_workorders.length > 0 ) {
            app.workorder = app.group_workorders.first();
        }
        else {
            app.workorder = new app.Workorder();
        }
    },
});

app.ResourceView = Backbone.View.extend({
    el: '#resource',
    template: _.template("<h2><%= name %></h2>"),
    initialize: function() {
        this.model.on("change", this.render, this);
    },
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
    },
});

app.TimetrackingView = Backbone.View.extend({
    tagName: 'div',
    template: _.template($('#t_timetracking').html()),
    initialize: function() {
        this.model.on("change", this.render, this);
        app.workorder.on("change:state_timetracking", this.render, this);
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
        this.$el.removeClass();
        this.$el.addClass(app.workorder.get('state_timetracking'));
    },
});

app.WOResourceView = Backbone.View.extend({
    tagName: 'div',
    template: _.template($('#t_wo_resource').html()),
    initialize: function() {
        this.model.on("change", this.render, this);
        if (this.model.get('id')) {
            this.render();
        }
    },
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
    },
});

app.RawMaterialsView = Backbone.View.extend({
    tagName: 'ul',
    childViews: [],
    initialize: function() {
        this.collection.on("add", this.addOne, this);
        if (this.collection.length > 0) {
            this.collection.forEach(this.addOne, this);
        }
    },
    addOne: function(rm) {
        var rmView = new app.RMView({
            model: rm
        });
        this.childViews.push(rmView);
        this.$el.append(rmView.$el);
    },
    remove: function() {
        _.each(this.childViews, function(x) {
            x.remove();
        }
        );
        Backbone.View.prototype.remove.call(this);
    }
});

app.RMView = Backbone.View.extend({
    tagName: 'li',
    template: _.template($('#t_rawmaterial').html()),
    childViews: [],
    events: {
        'click': 'onClick',
    },
    initialize: function() {
        this.model.on("change", this.render, this);
        this.render();
    },
    render: function() {
        var self = this;
        var total_qty = app.group_workorders.map(function(el){
                            return el.rawMaterial.reduce(function(memo, rm){
                                return memo + (rm.get('product_id')[0] == self.model.get('product_id')[0] ? rm.get('uom_qty') : 0);
                            }, 0);
                        }).reduce(function(el, memo){ return el + memo;}, 0);
        this.$el.html(this.template(_.defaults({uom_qty: total_qty}, this.model.toJSON(), {_t:_t, is_grouped: app.group_workorders.length > 1})));
        this.$el.append(new app.LabelConsumedView({
            model: this.model
        }).$el);
    },
    onClick: function(e) {
        app.router.loadView(new app.EditRMView({
            model: this.model
        }));
    },
});

app.EditRMView = Backbone.View.extend({
    tagName: 'div',
    className: 'form space',
    template: _.template($('#t_editrm').html()),
    initialize: function() {
        $('body').append(this.$el);
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t, declare_tablet_cons: app.workorder.get('declare_tablet_cons')})));
    },
    events: {
        'click #cancel': 'cancel',
        'click #no_traceability_btn': 'noTraceability',
        'click #replacement_btn': 'replacement',
        'keyup #replacement': 'completeReplacement',
        'click #complete li': 'selectComplete',
    },
    cancel: function(e) {
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        }     
    },
    noTraceability: function(e) {
        var cause = this.$('#no_traceability').val();
        var self = this;
        app.group_workorders.map(function(wo) {
            var rm = app.get_equivalent_rm(self.model, wo);
            return rm.save({
                note: cause + '\n',
                track_label_product: false,
            }, {
                patch: true
            });
        });
        this.cancel();
    },
    replacement: function(e) {
        if (this.model.product_id) {
            this.model.change_product();
            this.cancel();
        }
    },
    completeReplacement: function(e) {
        var val = e.target.value;
        var Product = new Model('product.product');
        var self = this;
        Product.query(['name']).filter([['name', 'ilike', val]]).limit(10).order_by('-name').all().done(function(r) {
            var html = _.reduce(r, function(html, e) {
                return html + '<li product_id="' + e.id + '">' + e.name + '</li>';
            }, '');
            self.$('#complete').html(html);
        }
        );
    },
    selectComplete: function(e) {
        var target = $(e.target);
        var product_id = parseInt(target.attr('product_id'));
        this.model.product_id = product_id;
        this.$('#complete li').removeClass('complete-selected');
        target.addClass('complete-selected');
    },
});

app.LabelConsumedView = Backbone.View.extend({
    tagName: 'div',
    className: 'labels',
    initialize: function() {
        app.workorder.labels.on('update add remove destroy', this.render, this);
        this.render();
    },
    events: {
        'click': 'onClick',
    },
    labels: {},
    template: _.template('<div class="label" label_id="<%= label_id[0] %>"><%= label_id[1] %><br /> ' + _t('qty') + ' : <%= quantity %></div>'),
    render: function() {
        this.$el.empty();
        app.workorder.labels.each(function(label) {
            if (label.get('product_id')[0] == this.model.get('product_id')[0]) {
                this.$el.append(this.template(_.defaults(label.toJSON(), {_t:_t, max_qty: this.model.get('uom_qty')})));
                this.labels[label.get('label_id')[0]] = label;
            }
        }, this);
    },
    onClick: function(e) {
        var label_id = e.target.getAttribute('label_id');
        app.router.loadView(new app.EditLabelConsumedView({
            model: this.labels[label_id]
        }));
    },
});
app.UnassignedLabelsView = app.LabelConsumedView.extend({
    render: function() {
        this.$el.empty();
        var product_ids = app.workorder.rawMaterial.map(function(el) {
            return el.get('product_id')[0];
        }
        );
        _.each(app.workorder.labels.filter(function(label) {
            return !_.contains(product_ids, label.get('product_id')[0]);
        }, this), function(label) {
            this.$el.append(this.template(_.defaults(label.toJSON(), {_t:_t})));
            this.labels[label.get('label_id')[0]] = label;
        }, this);
    },
});

app.EditLabelConsumedView = Backbone.View.extend({
    tagName: 'div',
    className: 'form space',
    initialize: function() {
        $('body').append(this.$el);
        this.render();
    },
    events: {
        'click #cancel': 'cancel',
        'click #validate': 'saveLabel',
        'click #delete': 'deleteLabel',
    },
    template: _.template($('#t_editlabelconsumed').html()),
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
    },
    cancel: function(e) {
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
            app.router.main(app.workorder.id);
        } 
    },
    saveLabel: function(e) {
        var self = this;
        _.map(app.group_workorders.models.reverse(), function(wo) {
            var other_label = app.get_equivalent_label(self.model, wo);
            other_label.set({
                quantity: self.$('#quantity').val()
            });
            other_label.save();
        });
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        } 
    },
    deleteLabel: function(e) {
        var self = this;
        _.map(app.group_workorders.models.reverse(), function(wo) {
            var other_label = app.get_equivalent_label(self.model, wo);
            return other_label.destroy();
        });
        //this.model.destroy();
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        } 
    }
});

app.TraceabilityView = Backbone.View.extend({
    tagName: 'div',
    className: 'form space',
    events: {
        'click #cancel': 'cancel',
        'click #validate': 'saveCollection',
    },
    childViews: [],
    initialize: function() {
        $('body').append(this.$el);
        this.render();
        this.collection.on("add", this.addOne, this);
        if (this.collection.length === 0) {
            this.collection.add(new app.LabelConsumed());
        }
    },
    render: function() {
        this.$el.html('<ul id="labels" /><div class="actions space"><button id="validate">' + _t('Validate') + '</button><button id="cancel">' + _t('Cancel') + '</button></div>');
        this.$labels = this.$('#labels');
    },
    addOne: function(label) {
        var labelView = new app.LabelView({
            model: label
        });
        this.childViews.push(labelView);
        this.$labels.append(labelView.$el);
        labelView.$('[name="label"]').focus();
    },
    cancel: function(e) {
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
            app.router.main(app.workorder.id);
        } 
    },
    remove: function() {
        _.each(this.childViews, function(x) {
            x.remove();
        }
        );
        Backbone.View.prototype.remove.call(this);
    },
    saveCollection: function(e) {
        var collectionSaved = this.collection.save();
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
            app.router.main(app.workorder.id);
        } 
        collectionSaved.done(_.bind(app.workorder.loadLabels, app.workorder));
    }
});

app.LabelView = Backbone.View.extend({
    tagName: 'li',
    events: {
        'keypress [name="label"]': 'onLabelKeypress',
        'keyup [name="quantity"]': 'onQuantityKeyup',
        'click .remove_line': 'remove',
    },
    template: _.template($('#t_labelview').html()),
    initialize: function() {
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
    },
    onLabelKeypress: function(e) {
        if (e.which === ENTER_KEY) {
            var Label = new Model('stock.label');
            var self = this;
            Label.query().filter([['name', '=', this.$('[name="label"]').val()]]).first().done(function(r) {
                if (r){
                    self.$('[name="quantity"]').val(r.uom_qty);
                    self.model.set({
                        wo_id: app.workorder.get('id'),
                        label_id: r.id,
                        quantity: r.uom_qty,
                        use_consumption: app.label_consumption_grouping_flag
                    });
                    self.model.collection.add(new app.LabelConsumed());
                    self.$el.append('<button class="remove_line">X</button>');
                } else {
                    alert('Etiquette non trouvée');
                    self.$('[name="label"]').val('');
                }
            }
            );
        }
    },
    onQuantityKeyup: function(e) {
        this.model.set({
            quantity: this.$('[name="quantity"]').val()
        });
    },
});

app.MainView = Backbone.View.extend({
    tagName: 'div',
    className: 'wrapper-col',
    template: _.template($('#t_main').html()),
    events: {
        'click #declaration_buttons button': 'onButtonClick',
        'click #traceability': 'onTraceabilityClick',
        'click #declaration-btn': 'onDeclarationClick',
        'click #exit-btn': 'onExitClick',
        'click #conso-btn': 'onConsoClick',
        'click #note-btn': 'onNoteClick',
        'click #add-resource-btn': 'onAddResourceClick',
        'click #resources-list .btn': 'toggleAdditionalResource',
    },
    render: function() {
        var consumptions = {};
        this.$el.html(this.template({
            workorders: app.group_workorders.toJSON(),
            _t:_t, 
            labels: this.model.labels || [],
            declaration_ok: app.declaration_ok || app.workorder.produce.length,
            consumptions: app.workorder.consumptions,
            produce: app.workorder.produce,
        }));
        this.timetrackingView = new app.TimetrackingView({
            model: this.model.timetracking
        });
        this.firstResourceView = new app.WOResourceView({
            model: this.model.firstResource
        });
        this.rawMaterialsView = new app.RawMaterialsView({
            collection: this.model.rawMaterial
        });
        this.unassignedView = new app.UnassignedLabelsView();
        this.$('#timetracking').append(this.timetrackingView.$el);
        this.$('#firstresource').append(this.firstResourceView.$el);
        this.$('#rawmaterial').append(this.rawMaterialsView.$el);
        this.$('#unassigned').append(this.unassignedView.$el);
    },
    initialize: function() {
        $('body').append(this.$el);
        this.model.on("change", this.render, this);
        if (this.model.get('id')) {
            this.render();
            this.listenTo(this.model.rawMaterial, 'update change_product', function() {
                this.unassignedView.render();
            });
        }
    },
    onButtonClick: function(e) {
        var WO = new Model('mrp.workorder');
        var self = this;
        WO.call('button_' + e.target.id + '_timetracking', [this.model.get('id')]).done(function(r) {
            if (r) {
                self.model.loadTimetracking();
                self.model.set({
                    'state_timetracking': e.target.id
                });
            }
        }
        );
    },
    onTraceabilityClick: function(e) {
        app.router.loadView(new app.TraceabilityView({
            collection: new app.LabelConsumedCollection(),
        }));
        app.router.navigate('traceability-' + app.workorder.get('id'));
    },
    onDeclarationClick: function(e) {
        var args = [this.model.get('id')];
        new Model('wo.declaration.main').call('create_and_produce', args, {context: {active_model: 'mrp.workorder'}}).done(function(r) {
            new Model('wo.declaration.produce').query().filter([['id', '=', r]]).first().done(function(s) {
                app.declaration = new app.Declaration(s);
                app.declaration_main_id = s.declaration_id[0];
                app.router.loadView(new app.DeclarationView({
                    model: app.declaration
                }));
            }
            ).fail(function(r){alert(r.data.message);});
        }
        ).fail(function(r){alert(r.data.message);});
    },
    onExitClick: function(e){
        var WO = new Model('mrp.workorder');
        var self = this;
        WO.call('button_stop_timetracking', [app.group_workorders.pluck('id')]).done(function(r) {
            if (r) {
                self.model.loadTimetracking().then(function(){
                    self.model.set({
                        'state_timetracking': 'stop',
                    });
                    app.router.loadView(new app.ExitView());
                });
            }
        }
        );
    },
    onConsoClick: function(e) {
        app.router.loadView(new app.ConsoView({model: app.workorder}));
        app.router.navigate('conso-' + app.workorder.get('id'));
    },
    onNoteClick: function(e) {
        this.note_view = new app.NoteView();
        app.router.view.$el.append(this.note_view.$el);
        $('#note_popup').modal();
        $('#note_popup').one('hidden.bs.modal', function(ev) {
            $('#note_popup').remove();
            delete this.note_view;
        });
    },
    onAddResourceClick: function(e) {
        this.add_resource_view = new app.AddResourceView();
        app.router.view.$el.append(this.add_resource_view.$el);
        $('#add_resource_popup').modal();
        $('#add_resource_popup input').focus();
        $('#add_resource_popup').one('hidden.bs.modal', function(ev) {
            $('#add_resource_popup').remove();
            delete this.add_resource_view;
        });
    },
    toggleAdditionalResource: function(e) {
        var res_id = $(e.target).data('resId');
        var self = this;
        new Model('mrp.wo.additional.resource').call(
            'write', [
                res_id,
                {end_date:time.datetime_to_str(new Date())}
            ]).then(function(res){
            self.$el.find('#resources-list .btn[data-res-id=' + res_id + ']').remove();
            var resources = app.workorder.get('additional_resources');
            var index = _.find(resources, function(el){return el.id == res_id;});
            resources.splice(index, 1);
        });
    }
});

app.AddResourceView = Backbone.View.extend({
    tagName: 'div',
    events: {
        'click #add_resource_cancel': 'cancel',
        'click #add_resource_ok': 'validate',
        'keyup input[name=resource]': 'completeResource',
        'click #complete li': 'selectComplete',
    },
    template: _.template($('#t_add_resource').html()),
    initialize: function(args) {
        this.render();
    },
    render: function() {
        this.$el.html(this.template({_t:_t}));
    },
    cancel: function() {
        $('#add_resource_popup').modal('hide');
    },
    validate: function() {
        var self = this;
        var data = {
            resource_id: this.resource_id,
            wo_id: app.workorder.id,
        };
        new Model('mrp.wo.additional.resource').call(
            'create',
            [data]).then(function(res){
            var resource_ids = app.workorder.get('additional_resource_ids').concat(res);
            app.workorder.set({additional_resource_ids: resource_ids}, {silent:true});
            app.workorder.loadAdditionalResources(resource_ids, {silent: false});
            self.cancel();
        }).fail(function(res){
            alert(res.data.message);
        });
    },
    completeResource: function(e) {
        this.$('#complete').show();
        var val = e.target.value;
        var Resource = new Model('mrp.resource');
        var self = this;
        Resource.query(['name',]).filter([
            ['name', 'ilike', val],
            ['type', '=', 'human'],
            ['id', '!=', app.workorder.get('first_resource_id')[0]],
        ]).limit(10).order_by('-name').all().done(function(r) {
            var html = _.reduce(r, function(html, e) {
                return html + '<li resource_id="' + e.id + '">' + e.name + '</li>';
            }, '');
            self.$('#complete').html(html);
        });
    },
    selectComplete: function(e) {
        var target = $(e.target);
        var resource_id = parseInt(target.attr('resource_id'));
        this.resource_id = resource_id;
        this.$('input[name=resource]').val(target.text());
        this.$('#complete').hide();
    },
});

app.NoteView = Backbone.View.extend({
    tagName: 'div',
    events: {
        'click #note_cancel': 'cancel',
        'click #note_ok': 'validate',
    },
    template: _.template($('#t_note').html()),
    initialize: function(args) {
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults({note:app.workorder.get('declaration_note') || ""}, {_t:_t})));
    },
    cancel: function() {
        $('#note_popup').modal('hide');
    },
    validate: function() {
        var self = this;
        var deferreds = app.group_workorders.map(function(wo) {
            return wo.save({declaration_note: self.$('textarea').val()}, {patch: true, silent:true});
        });
        $.when.apply($, deferreds).then(function(){
            self.cancel();
        });
    }
});

app.ConsoView = Backbone.View.extend({
    tagName: 'div',
    className: 'form form-conso',
    template: _.template($('#t_conso').html()),
    events: {
        "click #validate_conso": "validateConso",
        "click #cancel_conso": "cancel",
        "change input[name=\"qty_declaration\"]": "changeQty",
        "click #conso_add_another_label": "addAnotherLabel",
        "click #conso_add_another_product": "addAnotherProduct",
    },
    initialize: function() {
        $('body').append(this.$el);
        this.model.on("change", this.render, this);
        if (this.model.id) {
            this.render();
            this.changeQty();
        }
    },
    render: function() {
        var consumed = _.reduce(app.workorder.consumptions, function(r,n){return r+n.quantity;}, 0);
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t, consumed: consumed })));
        this.consoRMsView = new app.ConsoRMsView({collection: this.model.rawMaterial});
        this.$('#conso_rawmaterial').append(this.consoRMsView.$el);
    },
    validateConso: function(ev) {
        var vals = this.model.rawMaterial.toJSON();
        var wiz_decl_obj = new Model('wo.declaration.consumption');

        var wo_id = app.workorder.id;
        var quantity = parseFloat(this.$('input[name="qty_declaration"]').val());
        var line_ids = this.consoRMsView.getWizardLines();
        var wiz = wiz_decl_obj.call(
            'create',
            [{
                'wo_id': wo_id,
                'quantity': quantity,
                'is_produce': false,
                'line_ids': line_ids,
                'date': time.datetime_to_str(new Date()),
            }]);
        wiz.then(function(res_id){
            return wiz_decl_obj.call('action_validate', [res_id]);
        }).then(function(res) {
            if (app.group_workorders.length > 1) {
                app.router.navigate('main-g' + app.workorder_group_id);
            }
            else {
                app.router.navigate('main-' + app.workorder.id);
            } 
            window.location.reload();
        }, function(err){
            alert(err.data.message);
            if (app.group_workorders.length > 1) {
                app.router.main('g' + app.workorder_group_id);
            }
            else {
                app.router.main(app.workorder.id);
            } 
        });
    },
    changeQty: function() {
        var val = parseFloat(this.$('input[name="qty_declaration"]').val());
        var initialQty = parseFloat(this.$('input[name="qty_declaration"]').attr('value'));
        if (!_.isFinite(val)) {
            val = initialQty;
            this.$('input[name="qty_declaration"]').val(val);
        }
        var ratio = val / initialQty;
        _.each(this.$('#conso_rawmaterial li:not(:has(.track_label)) input'), function(el){
            el.value = parseFloat(el.dataset.max) * ratio;
        });
        _.each(this.$('#conso_rawmaterial li:has(.track_label)'), function(e){
            var remaining;
            var rm_id = parseInt(e.dataset.rm);
            var rm = app.workorder.rawMaterial.get(rm_id);
            if (_.isUndefined(remaining)){
                remaining = (rm.get('uom_qty') - rm.get('consumed_qty')) * ratio;
            }
            _.each($(e).find('input'), function(el){
                var to_remove = Math.min(remaining, parseFloat(el.dataset.max));
                el.value = parseFloat(to_remove.toFixed(4));
                remaining = remaining - to_remove;
            });
        });
    },
    cancel: function(ev) {
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        } 
    },
    addAnotherLabel: function(ev) {
        this.add_label_view = new app.AddConsoLabelView();
        $('body').append(this.add_label_view.$el);
        $('.add_conso_label').modal();
        $('.add_conso_label input[name=label]').focus();
        $('.add_conso_label').one('hidden.bs.modal', function(ev) {
            $('.add_conso_label').remove();
            delete this.add_label_view;
        });
    },
    addAnotherProduct: function(ev) {
        this.add_product_view = new app.AddConsoProductView();
        $('body').append(this.add_product_view.$el);
        $('.add_conso_product').modal();
        $('.add_conso_product input[name=product]').focus();
        $('.add_conso_product').one('hidden.bs.modal', function(ev) {
            $('.add_conso_product').remove();
            delete this.add_product_view;
        });
    },
});


app.AddConsoLabelView = Backbone.View.extend({
    tagName: 'div',
    className: 'add_conso_label modal',
    id: "add_label_conso",
    events: {
        'click #cancel': 'cancel',
        'click #ok': 'validate',
        'click .button_plus': 'buttonPlus',
        'click .button_minus': 'buttonMinus',
        'change input[name=qty]': 'onChangeQty',
        'keyup input[name=label]': 'completeLabel',
        'click #complete li': 'selectComplete',
    },
    template: _.template($('#t_add_conso_label').html()),
    initialize: function(args) {
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults({}, {_t:_t})));
    },
    cancel: function() {
        $('.add_conso_label').modal('hide');
        $('.add_conso_label').remove();
    },
    validate: function() {
        var label_id = this.label_id;
        var qty = parseFloat(this.$('input[name="qty"]').val());
        var WO = new Model('mrp.workorder');
        if (_.isUndefined(label_id) || _.isNaN(qty)) {
        	alert(_t('Missing label or quantity'));
        	return false;
        }
        WO.call('add_another_label', [app.workorder.id, label_id, qty]).done(function(){
            window.location.reload();
        }).fail(function(res){
            alert(res.data.message);
        });
        this.cancel();
    },
    buttonPlus: function(ev){
        var old_val = parseFloat(ev.target.previousElementSibling.value) || 0;
        var new_val = old_val + 1;
        ev.target.previousElementSibling.value = new_val;
    },
    buttonMinus: function(ev){
        var old_val = parseFloat(ev.target.nextElementSibling.value) || 0;
        var new_val = Math.max(old_val - 1, 0);
        ev.target.nextElementSibling.value = new_val;
    },
    onChangeQty: function(ev) {
        var old_val = parseFloat(ev.target.value) || 0;
        var new_val = Math.max(old_val, 0);
        ev.target.value = new_val;
    },
    completeLabel: function(e) {
        this.$('#complete').show();
        var val = e.target.value;
        var Label = new Model('stock.label');
        var self = this;
        Label.query(['name', 'uom_qty']).filter([['name', 'ilike', val]]).limit(10).order_by('-name').all().done(function(r) {
            var html = _.reduce(r, function(html, e) {
                return html + '<li label_id="' + e.id + '" quantity="' + e.uom_qty + '">' + e.name + '</li>';
            }, '');
            self.$('#complete').html(html);
        }
        );
    },
    selectComplete: function(e) {
        var target = $(e.target);
        var label_id = parseInt(target.attr('label_id'));
        this.label_id = label_id;
        this.$('input[name=label]').val(target.text());
        this.$('input[name=qty]').val(target.attr('quantity'));
        this.$('#complete').hide();
    },
});


app.AddConsoProductView = Backbone.View.extend({
    tagName: 'div',
    className: 'add_conso_product modal',
    id: "add_label_product",
    events: {
        'click #cancel': 'cancel',
        'click #ok': 'validate',
        'click .button_plus': 'buttonPlus',
        'click .button_minus': 'buttonMinus',
        'change input[name=qty]': 'onChangeQty',
        'keyup input[name=product]': 'completeProduct',
        'click #complete li': 'selectComplete',
    },
    template: _.template($('#t_add_conso_product').html()),
    initialize: function(args) {
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults({}, {_t:_t})));
    },
    cancel: function() {
        $('.add_conso_product').modal('hide');
        $('.add_conso_product').remove();
    },
    validate: function() {
        //var product_id = this.$('input[name="product"]').val();
        var product_id = this.product_id;
        var qty = parseFloat(this.$('input[name="qty"]').val());
        if (_.isUndefined(product_id) || _.isNaN(qty) || qty === 0) {
        	alert(_t('Missing label or quantity'));
        	return false;
        }

        // création d'un wizard create.rm, write du produit/quantité, action_validate
        var product_model = new Model('product.product');
        product_model.query(['uom_id']).filter([['id', '=', product_id]]).first().done(function(product){
            if (product) {
                var create_rm = new Model('create.rm');
                create_rm.call('create', [{
                    product_id: product_id,
                    quantity: qty,
                    uom_id: product.uom_id[0],
                }], {context: {active_id: app.workorder.id}}).done(function(res){
                    create_rm.call('action_validate', [res]).done(function(){
                        window.location.reload();
                    }).fail(function(res){
                        alert(res.data.message);
                    });
                }).fail(function(res){
                    alert(res.data.message);
                });
            } else {
                alert(_t('Unknown product'));
            }
        }).fail(function(res){
            alert(res.data.message);
        });

        this.cancel();
    },
    buttonPlus: function(ev){
        var old_val = parseFloat(ev.target.previousElementSibling.value) || 0;
        var new_val = old_val + 1;
        ev.target.previousElementSibling.value = new_val;
    },
    buttonMinus: function(ev){
        var old_val = parseFloat(ev.target.nextElementSibling.value) || 0;
        var new_val = Math.max(old_val - 1, 0);
        ev.target.nextElementSibling.value = new_val;
    },
    onChangeQty: function(ev) {
        var old_val = parseFloat(ev.target.value) || 0;
        var new_val = Math.max(old_val, 0);
        ev.target.value = new_val;
    },
    completeProduct: function(e) {
        this.$('#complete').show();
        var val = e.target.value;
        var Product = new Model('product.product');
        var self = this;
        Product.query(['name']).filter([['name', 'ilike', val]]).limit(10).order_by('-name').all().done(function(r) {
            var html = _.reduce(r, function(html, e) {
                return html + '<li product_id="' + e.id + '">' + e.name + '</li>';
            }, '');
            self.$('#complete').html(html);
        }
        );
    },
    selectComplete: function(e) {
        var target = $(e.target);
        var product_id = parseInt(target.attr('product_id'));
        this.product_id = product_id;
        this.$('input[name=product]').val(target.text());
        this.$('#complete').hide();
    },
});

app.ConsoRMsView = Backbone.View.extend({
    tagName: 'ul',
    childViews: [],
    initialize: function() {
        this.collection.on("add", this.addOne, this);
        if (this.collection.length > 0) {
            this.collection.forEach(this.addOne, this);
        }
    },
    addOne: function(rm) {
        if ((rm.get('uom_qty') - rm.get('consumed_qty')) > 0) {
            var rmView = new app.ConsoRMView({
                model: rm
            });
            this.childViews.push(rmView);
            this.$el.append(rmView.$el);
        }
    },
    remove: function() {
        _.each(this.childViews, function(x) {
            x.remove();
        });
        Backbone.View.prototype.remove.call(this);
    },
    getWizardLines: function() {
        var ret = _.compact(_.invoke(this.childViews, 'getWizardLine'));
        return ret;
    },
});

app.ConsoLabelView = app.LabelConsumedView.extend({
    className: 'wrapper-col',
    template: _.template($('#t_conso_label').html()),
    events: {
        'click .button_plus': 'onPlusClick',
        'click .button_minus': 'onMinusClick',
        'blur input': 'onBlurInput',
    },
    onBlurInput: function(ev) {
        var input = $(ev.target);
        var val = input.val();
        var max = input.data('max');
        if (val > max) {
            input.val(max);
        } else if (val < 0) {
            input.val(0);
        }
    },
    getLabelLines: function() {
        var self = this;
        var ret = _.compact(app.workorder.labels.map(function(label) {
            if (label.get('product_id')[0] == self.model.get('product_id')[0]) {
                var label_id = label.get('label_id')[0];
                var quantity = parseFloat(self.$('[data-label="'+label_id+'"] input').val());
                if (quantity) {
                    return [0, 0, {
                        quantity: quantity,
                        quantity_init_inv: label.get('quantity_label'),
                        label_id: label_id,
                        sec_uom_qty: label.get('sec_uom_qty'),
                        is_variable_double_unit: label.get('is_variable_double_unit'),
                    }];
                } else {
                    return;
                }
            }
        }));
        return ret;
    },
});

app.ConsoRMView = Backbone.View.extend({
    tagName: 'li',
    //className: 'wrapper-col',
    attributes: function() {
        return {
            class: 'wrapper-col',
            'data-rm': this.model.id,
        };
    },
    template: _.template($('#t_conso_rm').html()),
    events: {
        'click .button_plus': 'onPlusClick',
        'click .button_minus': 'onMinusClick',
        'click .track_label.rm button': 'onAddLabelClick',
        'click .remove-rm': 'onRemoveRMClick',
        'blur input': 'onBlurInput',
    },
    initialize: function() {
        this.render();
    },
    render: function() {
        var track_label = this.model.get('track_label_product');
        this.$el.html(this.template(_.defaults(this.model.toJSON(), {_t:_t})));
        if (track_label) {
            this.consoLabelView = new app.ConsoLabelView({
                model: this.model
            });
            this.$el.append(this.consoLabelView.$el);
        }
    },
    onPlusClick: function(ev){
        var input = $(ev.target).next();
        input.val(parseInt(input.val()) + 1);
        input.blur();
    },
    onMinusClick: function(ev){
        var input = $(ev.target).prev();
        input.val(parseInt(input.val()) - 1);
        input.blur();
    },
    onBlurInput: function(ev) {
        var input = $(ev.target);
        var val = input.val();
        if (val < 0) {
            input.val(0);
        }
    },
    getWizardLine: function() {
        var product_id = this.model.get('product_id')[0];
        var move_id = this.model.id;
        var quantity = 0;//parseFloat(this.$('input').val());
        this.$('input').each(function(i, el){
            quantity += parseFloat(el.value);
        });
        if (!quantity) {
            return;
        }
        var ratio = this.model.get('uom_qty') / this.model.get('sec_uom_qty');
        var sec_uom_qty = quantity / ratio;

        var ret = [0, 0, {
            product_id: product_id,
            move_id: move_id,
            quantity: quantity,
            sec_uom_qty: sec_uom_qty,
            is_variable_double_unit: this.model.get('is_variable_double_unit'),
            track_label: this.model.get('track_label_product'),
        }];
        
        if (this.model.get('track_label_product')) {
            ret[2].label_consumption_ids = [[0, 0, {
                line_ids: this.consoLabelView.getLabelLines(),
                is_variable_double_unit: this.model.get('is_variable_double_unit'),
            }]];
            ret[2].track_label_product = true;
        }

        return ret;
    },
    onAddLabelClick: function() {
        // ouvrir popup;
        this.add_label_view = new app.AddLabelView({product_id: this.model.get('product_id')[0]});
        $('body').append(this.add_label_view.$el);
        $('#add_label_conso').modal();
        $('#add_label_conso input').focus();
        $('#add_label_conso').one('hidden.bs.modal', function(ev) {
            $('#add_label_conso').remove();
            delete this.add_label_view;
        });
    },
    onRemoveRMClick: function(ev) {
        this.model.destroy({
            success: function(model, response){
                window.location.reload();
            },
            error: function(model, response) {
                alert(response.data.message);
            },
        });
    },
});


app.AddLabelView = Backbone.View.extend({
    tagName: 'ul',
    events: {
        'keypress input': 'onLabelKeypress',
        'click #add_label_cancel': 'cancel',
        'click #add_label_ok': 'validate',
    },
    template: _.template($('#t_add_label_conso').html()),
    initialize: function(args) {
        this.product_id = args.product_id;
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults({}, {_t:_t})));
    },
    onLabelKeypress: function(e) {
        if (e.which === ENTER_KEY) {
            var Label = new Model('stock.label');
            var self = this;
            Label.query().filter([['name', '=', this.$(e.target).val()], ['product_id', '=', self.product_id]]).first().done(function(r) {
                if (r){
                    $(e.target).attr('data-label-id', r.id);
                    $(e.target).attr('data-label-quantity', r.quantity);
                    var li = $('<li><input /></li>');
                    self.$el.find('ul').append(li);
                    li.find('input').focus();
                } else {
                    alert(_t('Label not found'));
                }
            }
            );
        }
    },
    cancel: function() {
        $('#add_label_conso').modal('hide');
        $('#add_label_conso').remove();
        delete this.add_label_view;
    },
    validate: function() {
        var consumption_obj = new Model('mrp.label.consumption');
        var promises = _.compact(_.map(this.$('input'), function(input) {
            if (input.dataset.labelId) {
                return consumption_obj.call('create', [{
                    wo_id: app.workorder.id,
                    label_id: input.dataset.labelId,
                    quantity: input.dataset.labelQuantity,
                    use_consumption: app.label_consumption_grouping_flag,
                }]);
            } else {
                return undefined;
            }
        }));
        if (promises.length) {
            $.when.apply($, promises).then(function(){
                window.location.reload();
            }).fail(function(error){
                alert(error.data.message);
            });
            $('#add_label_conso').modal('hide');
            $('#add_label_conso').remove();
            delete this.add_label_view;
        }
    }
});

app.ExitView = Backbone.View.extend({
    tagName: 'div',
    className: 'form',
    template: _.template($('#t_exit').html()),
    events: {
        'click #validate': 'onValidateClick',
        'click #cancel': 'onCancelClick',
        'change #time_ok': 'onTimeOkChange',
    },
    initialize: function() {
        $('body').append(this.$el);
        this.render();
    },
    render: function() {
        this.$el.html(this.template(_.defaults({
            declaration_ok: app.declaration_ok || app.workorder.produce.length,
            preparation_time:app.workorder.timetracking.get('prep_time'),
            production_time:app.workorder.timetracking.get('prod_time'),
            cleaning_time:app.workorder.timetracking.get('cleaning_time'),
        }, {_t:_t})));
    },
    onValidateClick: function(e){
        var finishOT = false;
        if (this.$('#wind_up_exit').is(':checked')){
            finishOT = true;
        }
        if (this.$('#time_ok').is(':checked')){
            app.workorder.save({correct_time:true}, {patch: true}).done(function(){
                if (finishOT) {
                    var WO = new Model('mrp.workorder');
                    WO.call('wkf_done', [_.pluck(app.group_workorders.models, 'id')] , {}).then(function() {
                        app.router.navigate('');
                        window.location.reload();
                    }); 
                } 
                else {
                    app.router.navigate('');
                    window.location.reload();
                }   
            });
        } else {
            var splitted = this.$('#decl_time').val().split(':');
            if (splitted.length != 2) {
                alert(_t('Invalid time format'));
                return;
            }
            var hours = parseInt(splitted[0]);
            var minutes = parseInt(splitted[1]);
            var decl_time = hours + minutes/60;
            app.workorder.save({correct_time:false, declared_time_tablet: decl_time}, {patch: true}).done(function(){
                if (finishOT) {
                    var WO = new Model('mrp.workorder');
                    WO.call('wkf_done', [_.pluck(app.group_workorders.models, 'id')] , {}).then(function() {
                        app.router.navigate('');
                        window.location.reload();
                    }); 
                } 
                else {
                    app.router.navigate('');
                    window.location.reload();
                }   
            });
        }
    },
    onCancelClick: function(e){
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        } 
    },
    onTimeOkChange: function(ev) {
        if (!ev.target.checked) {
            this.$('#decl_time,label[for=decl_time]').show();
        } else {
            this.$('#decl_time,label[for=decl_time]').hide();
        }
    },
});

app.DeclarationView = Backbone.View.extend({
    tagName: 'div',
    className: 'form',
    template: _.template($('#t_declaration').html()),
    initialize: function() {
        $('body').append(this.$el);
        this.render();
    },
    events: {
        'click #cancel': 'cancel',
        'click #validate': 'saveDeclaration',
        'click #generate_labels': 'generateLabels',
        'click #delete_labels': 'deleteLabels',
        'input #quantity': 'copyQty',
    },
    render: function() {
        var is_subproduct = (this.model.get('product_id')[0] != app.workorder.get('final_product_id')[0]);
        this.$el.html(this.template(_.defaults(
            this.model.toJSON(),
            {_t:_t, is_subproduct:is_subproduct})));
    },
    cancel: function(e) {
        if (app.group_workorders.length > 1) {
            app.router.main('g' + app.workorder_group_id);
        }
        else {
             app.router.main(app.workorder.id);
        } 
    },
    saveDeclaration: function(e) {
        var self = this;
        var qty_ok = parseFloat(self.$('#qty_ok').val());
        var qty_hs = parseFloat(self.$('#qty_hs').val());
        var qty_quarantine = parseFloat(self.$('#qty_quarantine').val());
        var quantity = parseFloat(self.$('#quantity').val());
        if (quantity != qty_ok + qty_hs + qty_quarantine) {
            alert(_t('Quantity != quantity ok + quantity hs + quantity quarantine'));
            return;
        }
        var deferreds = [];
        if (self.model.labels) {
            self.model.labels.each(function(el){
                if (el.hasChanged()){
                    deferreds.push(el.save(el.changed));
                }
            });
        }
        var saveLabelQty = $.when.apply($, deferreds);
        saveLabelQty.done(function(){
            self.model.save({
                quantity: quantity,
                qty_ok: qty_ok,
                qty_hs: qty_hs,
                qty_quarantine: qty_quarantine,
                wind_up: self.$('#wind_up').is(':checked'),
                is_print_label: self.$('#is_print_label').is(':checked'),
                theorical_consumption: self.$('#consume').is(':checked'),
            }, {
                patch: true,
                success: _.bind(self.model.action_validate, self.model),
            });
        }).fail(function(r){
            alert(r.data.message);
        });
    },
    generateLabels: function(e) {
        var self = this;
        self.model.save({
                quantity: parseFloat(this.$('#quantity').val()),
                qty_ok: parseFloat(this.$('#qty_ok').val()),
                qty_hs: parseFloat(this.$('#qty_hs').val()),
                wind_up: this.$('#wind_up').is(':checked'),
                is_print_label: this.$('#is_print_label').is(':checked'),
                qty_label: parseFloat(this.$('#qty_label').val()),
                nb_label: parseFloat(this.$('#nb_label').val()),
            }, {
                patch: true,
                success: function(r) {
                    new Model('wo.declaration.produce').call('generate_label', [self.model.get('id')]).done(function(r) {
                        new Model('assign.label.wo.produce')
                        .query()
                        .filter([
                            ['consumption_line_id', '=', self.model.id],
                        ])
                        .all()
                        .done(function(r) {
                            self.model.labels = new app.ProduceLabelCollection(r);
                            self.labelsView = new app.ProduceLabelCollectionView({collection:self.model.labels});
                            self.$('#section_labels').append(self.labelsView.$el);
                            self.$('#generate_labels').hide();
                            self.$('#delete_labels').show();
                        }
                        );
                }
                ).fail(function(r){alert(r.data.message);});
            }
        });
    },
    deleteLabels: function(e){
        this.$('#generate_labels').show();
        this.$('#delete_labels').hide();
        var self = this;
        new Model('wo.declaration.produce').call('delete_label', [this.model.get('id')]).done(function(r) {
            self.model.labels.reset();
        });
    },
    copyQty: function(e){
        this.$('#qty_ok').val(e.target.value);
    },
});

app.ProduceLabelCollectionView = Backbone.View.extend({
    tagName: 'ul',
    childViews: [],
    initialize: function() {
        this.collection.on("add", this.addOne, this);
        this.collection.on("reset", this.reset, this);
        if (this.collection.length > 0) {
            this.collection.forEach(this.addOne, this);
        }
    },
    addOne: function(label) {
        var labelView = new app.ProduceLabelView({
            model: label
        });
        this.childViews.push(labelView);
        this.$el.append(labelView.$el);
    },
    remove: function() {
        _.each(this.childViews, function(x) {
            x.remove();
        });
        Backbone.View.prototype.remove.call(this);
    },
    reset: function(collection, options){
        _.each(this.childViews, function(x) {
            x.remove();
        });
        this.childViews = [];
        this.remove();
    }
});


app.ProduceLabelView = Backbone.View.extend({
    tagName: 'li',
    template: _.template($('#t_producelabel').html()),
    events: {
        'keyup input':'onKeyUp',
        'click input[type=checkbox]':'onKeyUp',
    },
    initialize: function() {
        this.model.on("change", this.render, this);
        this.render();
    },
    render: function() {
        var datas = _.extend(this.model.toJSON(), {index:this.model.collection.indexOf(this.model) + 1});
        this.$el.html(this.template(_.defaults(datas, {_t:_t})));
    },
    onKeyUp: function(e){
        this.model.set({
            quantity:this.$('input.quantity').val(),
            for_quarantine:this.$('input.for_quarantine').is(':checked')
        });
    },
});

/*  =======
 *  Routers
 *  =======
 */
app.Router = Backbone.Router.extend({
    routes: {
        '': 'home',
        'main-:id': 'main',
        'traceability-:id': 'traceability',
        'conso-:id': 'conso',
        'declarationlist-:id': 'declarationList',
    },
    home: function() {
        this.loadView(new app.HomeView());
    },
    main: function(id) {
        var StockConfigSettings = new Model('stock.config.settings');
        var self = this;
        StockConfigSettings.query(['label_consumption_grouping_flag']).first().done( function (data) {
            app.label_consumption_grouping_flag = data.label_consumption_grouping_flag;
        });


        if ( _.isNaN(parseInt(id)) ) {
            var group_id = parseInt(id.slice(1));
            app.workorder_group_id = group_id;
            var self = this;
            var WO = new Model('mrp.workorder');

            return WO.query([
                'id',
                'display_name',
                'first_resource_id',
                'final_product_id',
                'quantity',
                'state_timetracking',
                'name',
                'workorder_produce_ids',
                'declare_tablet_product',
                'declare_tablet_cons',
                'rm_draft_ids',
                'workorder_consumption_ids',
                'advancement',
                'declaration_note',
                'additional_resource_ids',
                'allow_operator_add',
                'planned_start_date',
                ]).filter([
                    ['group_wo_id', '=', group_id],
                    ['state', 'not in', ['draft', 'waiting', 'done', 'cancel']],
                ]).all().done(function(data){
                    if (data.length === 0) {
                        alert(_t('Unknown or invalid Workorder group'));
                    }
                    else{
                        _.each(data, function(wo){             
                            var workorder_model = app.group_workorders.add(wo);
                            workorder_model.loadFirstResource();
                            workorder_model.loadRawMaterials();
                            workorder_model.loadTimetracking();
                            workorder_model.loadLabels();
                        });
                        app.workorder = app.group_workorders.first();
                        $.when(
                            app.workorder.loadConsumptions(app.workorder.get('workorder_consumption_ids')),
                            app.workorder.loadAdditionalResources(app.workorder.get('additional_resource_ids')),
                            app.workorder.loadProductions(app.workorder.get('workorder_produce_ids'))              
                        ).then(function(){
                            app.router.loadView(new app.MainView({
                                model: app.workorder
                            }));
                            app.router.navigate('main-g' + group_id);
                        });
                    }
            });
        }
        else {
            app.workorder.fetch({
                id: id
                }).then(function() {
                app.group_workorders.add([app.workorder]);
            });
            this.loadView(new app.MainView({
                model: app.workorder
            }));
            app.router.navigate('main-' + id);
        }
    },
    
    loadView: function(view) {
        if (this.view) {
            this.view.remove();
        }
        this.view = view;
    },
    traceability: function(id) {
        app.workorder.fetch({
            id: id
        });
        this.loadView(new app.TraceabilityView({
            collection: new app.LabelConsumedCollection()
        }));
    },
    conso: function(id) {
        app.workorder.fetch({
            id: id
        });
        this.loadView(new app.ConsoView({model: app.workorder}));
    },
    declarationList: function(id) {
        app.workorder = new app.Workorder();
        app.workorder.fetch({
            id: id
        });
        app.workorder.once('sync', function() {
            app.subproducts = new app.SubproductCollection();
            app.subproducts.fetch({
                wo_id: parseInt(id),
            });
            app.subproductsView = new app.DeclarationListView({
                collection: app.subproducts,
            });
            app.router.loadView(app.subproductsView);
        });
    },

});

/*  =====
 *  Utils
 *  =====
 */
app.format_time = function(time) {
    if (typeof time == 'undefined') {
        return '00:00';
    }
    var hours = Math.floor(time);
    if (hours < 10) {
        hours = '0' + hours;
    }
    var minutes = Math.round((time - Math.floor(time)) * 60);
    if (minutes < 10) {
        minutes = '0' + minutes;
    }
    return hours + ":" + minutes;
};

app.get_equivalent_rm = function (rm, wo) {
    return wo.rawMaterial.find(function(other_rm){
        return other_rm.get('product_id')[0] == rm.get('product_id')[0];
    });
};

app.get_equivalent_label = function (label, wo) {
    return wo.labels.find(function(other_label){
        return other_label.get('label_id')[0] == label.get('label_id')[0];
    });
};

app.router = new app.Router();
_.bindAll(Backbone.history, ['start']);
session.session_reload().then(function(){
    _t.database.load_translations(session, ['web', 'declaration'], session.user_context.lang).then(Backbone.history.start);
});

});