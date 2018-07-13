(function() {
    $.fn.gridEditor.RTEs.trumbowyg = {
        init: function(settings, contentAreas) {
            if (!jQuery().trumbowyg) {
                console.error('Trumbowyg not available! Make sure you loaded the Trumbowyg js file.');
            }
            $.trumbowyg.svgPath = '/web_editor/static/lib/trumbowyg/dist/ui/icons.svg';
            var self = this;
            contentAreas.each(function initialize() {
                var contentArea = $(this);
                if (!(contentArea.hasClass('active') || !!contentArea.find('.active').length)) {
                    contentArea.addClass('active');
                    var configuration = $.extend((settings.trumbowyg && settings.trumbowyg.config ? settings.trumbowyg.config : {}), {
                        btns: [
                               ['openprod'],
                               ['formatting'],
                               ['strong', 'em', 'underline'],
                               ['fontsize'],
                               ['superscript', 'subscript'],
                               ['link'],
                               'btnGrp-justify',
                               'btnGrp-lists',
                               ['upload'],
                               ['table'],
                               'foreColor',
                               'backColor',
                               ['removeformat'],
                              ],
                        plugins: {
                            upload: {
                                serverPath: '/web_editor/attachment/add',
                                data: [{
                                    name: 'csrf_token',
                                    value: settings.trumbowyg.csrf_token,
                                }, {
                                    name: 'func',
                                    value: 'trumbop',
                                }, ],
                                success: function(res) {
                                    // TODO différencier image/document => créer élément
                                    var res_object = JSON.parse(res.match('{.*}')[0]);
                                    if (['jpg', 'jpeg', 'gif', 'png'].indexOf(res_object.name.split('.').pop()) > -1) {
                                        var url = '/web/image/' + res_object.id;
                                        var range = document.getSelection().getRangeAt(0);
                                        var imgId = parent._.uniqueId('img_');
                                        var node = '<img src="' + url + '" id="' + imgId + '" />';
                                        contentArea.trumbowyg('execCmd', {
                                            cmd: 'insertHTML',
                                            param: node,
                                        });
                                        $('#'+imgId).on('load', function() {
                                            $(this).css({height:this.naturalHeight, width:this.naturalWidth}).resizable({
                                                aspectRatio:true, 
                                            });
                                        });
                                    } else {
                                        var range = document.getSelection().getRangeAt(0);
                                        var path = '/web/content?model=ir.attachment&field=datas&id=' + res_object.id + '&download=true&filename_field=datas_fname';
                                        var $node = $('<a href="' + path + '">' + res_object.name + '</a>');
                                        range.deleteContents();
                                        range.insertNode($node[0]);
                                        contentArea.trumbowyg('closeModal');
                                        contentArea.trumbowyg('execCmd', {cmd: 'syncCode'});
                                    }
                                    setTimeout(function() {
                                    	contentArea.trumbowyg('closeModal');
                                    }, 250);
                                },
                                fileFieldName: 'upload',
                            },
                            table: {
                                styler: 'table table-striped table-bordered',
                            }
                        },
                        resetCss: false,
                        lang: session.user_context.lang.substr(0,2),
                    });
                    contentArea.trumbowyg(configuration);
                    contentArea.one('tbwinit', function(){
                        contentArea.focus();
                        contentArea.find('img').each(function() {
                            $(this).resizable({
                                aspectRatio:true, 
                            });
                        });
                    });
                    contentArea.on('tbwblur', function(ev, modal){
                        if (!modal && !contentArea.parent().has(document.activeElement).length) {
                            contentArea.find('.ui-resizable').resizable('destroy');
                            contentArea.trumbowyg('execCmd', {cmd: 'syncCode'});
                            setTimeout(function(){
                                contentArea.trumbowyg('destroy');
                                contentArea.removeClass('active').removeAttr('id').removeAttr('style').removeAttr('spellcheck');
                            }, 250);
                        }
                    });
                    contentArea.on('click', initialize)
                }
            });
        },
        deinit: function(settings, contentAreas) {
            contentAreas.filter('.active').each(function() {
                var contentArea = $(this);
                contentArea.trumbowyg('destroy');
                contentArea.removeClass('active').removeAttr('id').removeAttr('style').removeAttr('spellcheck');
            });
        },
        initialContent: '&nbsp;',
    };
})();
