(function ($) {
    'use strict';

    // Add dropdown with font sizes
    $.extend(true, $.trumbowyg, {
        plugins: {
            openprod: {
                init: function (trumbowyg) {
                    trumbowyg.addBtnDef('openprod', {
                        dropdown: buildDropdown(trumbowyg),
                        text: 'Openprod',
                    });
                }
            }
        }
    });
    function buildDropdown(trumbowyg) {
        trumbowyg.addBtnDef('menu', {
            text: _t('Menu'),
            hasIcon: false,
            fn: function(){
                var content = $('<div>');
                $('<h1>' + _t('Select a menu') + '</h1>').appendTo(content);
                var input = $('<input>');
                new Model('ir.ui.menu')
                    .query()
                    .filter([['parent_id', '!=', false], ['action', '!=', false]])
                    .all()
                    .done(function(res){
                        input.autocomplete({
                            source : $.map(res, function(el){
                                return {label: el.name, value: el};
                            }),
                            select: function(ev, ui) {
                                $(ev.target).data('menu_id', ui.item.value.id);
                                $(ev.target).data('action', parseInt(ui.item.value.action.split(',').pop()));
                                $(ev.target).val(ui.item.label);
                                ev.preventDefault();
                            },
                        });
                    });
                input.appendTo(content);
                trumbowyg.openModal(
                    // title
                        _t('Insert Menu'),
                    // content
                    content
                ).on('tbwconfirm', function(ev){
                    var menu_id = $(ev.target).find('input').data('menu_id');
                    var action = $(ev.target).find('input').data('action');
                    var $menu_link = $('<a href="/web#menu_id=' + menu_id + '&action=' + action + '">' + $(ev.target).find('input').val() + '</a>')
                    trumbowyg.range.deleteContents();
                    trumbowyg.range.insertNode($menu_link[0]);
                    trumbowyg.closeModal();
                    trumbowyg.syncCode();
                    return true;
                }).on('tbwcancel', function(){
                    trumbowyg.closeModal();
                    return true;
                });
            },
        });
        trumbowyg.addBtnDef('page', {
            text: _t('Page'),
            hasIcon: false,
            fn: function(){
                var content = $('<div>');
                $('<h1>' + _t('Select a page') + '</h1>').appendTo(content);
                var input = $('<input>');
                new Model('web.page')
                    .query()
                    .all()
                    .done(function(res){
                        input.autocomplete({
                            source : $.map(res, function(el){
                                return {label: el.name, value: el};
                            }),
                            select: function(ev, ui) {
                                $(ev.target).data('path', ui.item.value.path);
                                $(ev.target).val(ui.item.label);
                                ev.preventDefault();
                            },
                        });
                    });
                input.appendTo(content);
                trumbowyg.openModal(
                    // title
                    _t('Insert Page'),
                    // content
                    content
                ).on('tbwconfirm', function(ev){
                    var path = $(ev.target).find('input').data('path');
                    if (!path) {
                        return false;
                    }
                    var $menu_link = $('<a href="' + path + '">' + $(ev.target).find('input').val() + '</a>');
                    trumbowyg.range.deleteContents();
                    trumbowyg.range.insertNode($menu_link[0]);
                    trumbowyg.closeModal();
                    trumbowyg.syncCode();
                    return true;
                }).on('tbwcancel', function(){
                    trumbowyg.closeModal();
                    return true;
                });
            },
        });
        trumbowyg.addBtnDef('newpage', {
            text: _t('New Page'),
            hasIcon: false,
            fn: function(){
                trumbowyg.openModalInsert(
                        _t('New Page'),
                    {
                        name: {
                            type: 'text',
                            required: true
                        },
                    },
                    function(v) {
                        new Model('web.page').call('create', [{name: v.name}], {context: {prev_page_id: page_id}})
                        .then(function(page_id){
                            return new Model('web.page').query().filter([['id', '=', page_id]]).first();
                        }).then(function(res) {
                            var $menu_link = $('<a href="' + res.path + '">' + v.name + '</a>')
                            trumbowyg.range.deleteContents();
                            trumbowyg.range.insertNode($menu_link[0]);
                            trumbowyg.closeModal();
                            trumbowyg.syncCode();
                        });
                    return true;
                    }
                );
            },
        });
        /*trumbowyg.addBtnDef('diagram', {
            text: 'Diagram',
            hasIcon: false,
            fn: function(){
                var content = $('<div>');
                var editor = new mxEditor();
                trumbowyg.openModal(
                    'Diagram',
                    content
                ).on('tbwconfirm', function(ev){
                    debugger;
                });
            },
        });*/
        trumbowyg.addBtnDef('insertAttachment', {
            text: _t('Attachment'),
            hasIcon: false,
            fn: function(){
                var content = $('<div>');
                $('<h1>' + _t('Select an attachment') + '</h1>').appendTo(content);
                var input = $('<input>');
                new Model('ir.attachment')
                    .query(['id', 'name', 'datas_fname'])
                    //.filter([['state', '=', 'validated']])
                    .all()
                    .done(function(res){
                        input.autocomplete({
                            source : $.map(res, function(el){
                                return {label: el.name, value: el};
                            }),
                            select: function(ev, ui) {
                                $(ev.target).data('doc_id', ui.item.value.id);
                                $(ev.target).data('fname', ui.item.value.datas_fname);
                                $(ev.target).val(ui.item.label);
                                ev.preventDefault();
                            },
                        });
                    });
                input.appendTo(content);
                trumbowyg.openModal(
                    // title
                    _t('Insert Attachment'),
                    // content
                    content
                ).on('tbwconfirm', function(ev){
                    var document_id = $(ev.target).find('input').data('doc_id');
                    if (document_id == undefined) {
                        return false;
                    }
                    var fname = $(ev.target).find('input').data('fname');
                    var path = '/web/content?model=ir.attachment&field=datas&id=' + document_id + '&download=true&filename_field=datas_fname';
                    if (['jpg', 'jpeg', 'gif', 'png'].indexOf(fname.split('.').pop()) > -1) {
                        var $node = $('<img src="' + path + '" />');
                        $node.on('load', function(){
                            $(this).css({height:this.naturalHeight, width:this.naturalWidth}).resizable({
                                aspectRatio:true, 
                            });
                        });
                    } else {
                        var $node = $('<a href="' + path + '">' + $(ev.target).find('input').val() + '</a>');
                    }
                    trumbowyg.range.deleteContents();
                    trumbowyg.range.insertNode($node[0]);
                    trumbowyg.closeModal();
                    trumbowyg.syncCode();
                    return true;
                }).on('tbwcancel', function(){
                    trumbowyg.closeModal();
                    return true;
                });
            },
        });
        trumbowyg.addBtnDef('insertDocument', {
            text: _t('Document'),
            hasIcon: false,
            fn: function(){
                var content = $('<div>');
                $('<h1>' + _t('Select a document') + '</h1>').appendTo(content);
                var input = $('<input>');
                new Model('document.openprod')
                    .query()
                    .all()
                    .done(function(res){
                        input.autocomplete({
                            source : $.map(res, function(el){
                                return {label: el.name, value: el};
                            }),
                            select: function(ev, ui) {
                                $(ev.target).data('doc_id', ui.item.value.id);
                                $(ev.target).val(ui.item.label);
                                ev.preventDefault();
                            },
                        });
                    });
                input.appendTo(content);
                trumbowyg.openModal(
                    // title
                    _t('Insert Document'),
                    // content
                    content
                ).on('tbwconfirm', function(ev){
                    var doc_id = $(ev.target).find('input').data('doc_id');
                    var path = '/web#id=' + doc_id + '&view_type=form&model=document.openprod';
                    var $menu_link = $('<a href="' + path + '">' + $(ev.target).find('input').val() + '</a>');
                    trumbowyg.range.deleteContents();
                    trumbowyg.range.insertNode($menu_link[0]);
                    trumbowyg.closeModal();
                    trumbowyg.syncCode();
                    return true;
                }).on('tbwcancel', function(){
                    trumbowyg.closeModal();
                    return true;
                });
            },
        });
        return ['menu', 'page', 'newpage', 'insertAttachment', 'insertDocument'];
    }
})(jQuery);
