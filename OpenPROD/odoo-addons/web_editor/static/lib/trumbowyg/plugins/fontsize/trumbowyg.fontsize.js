(function ($) {
    'use strict';

    $.extend(true, $.trumbowyg, {
        langs: {
            // jshint camelcase:false
            en: {
                fontsize: 'Font size',
                fontsizes: {
                    'x-small': 'Extra Small',
                    'small': 'Small',
                    'medium': 'Regular',
                    'large': 'Large',
                    'x-large': 'Extra Large'
                }
            },
            nl: {
                fontsize: 'Lettergrootte',
                fontsizes: {
                    'x-small': 'Extra Klein',
                    'small': 'Klein',
                    'medium': 'Normaal',
                    'large': 'Groot',
                    'x-large': 'Extra Groot'
                }
            }
        }
    });
    // jshint camelcase:true

    // Add dropdown with font sizes
    $.extend(true, $.trumbowyg, {
        plugins: {
            fontsize: {
                init: function (trumbowyg) {
                    trumbowyg.addBtnDef('fontsize', {
                        dropdown: buildDropdown(trumbowyg)
                    });
                }
            }
        }
    });
    function buildDropdown(trumbowyg) {
        var dropdown = [];
        var sizes = {'x-small': '0.5em', 'small':'0.75em', 'medium':'1em', 'large':'2em', 'x-large':'4em'};

        $.each(sizes, function(size, value) {
            trumbowyg.addBtnDef('fontsize_' + size, {
                text: '<span style="font-size: ' + size + ';">' + trumbowyg.lang.fontsizes[size] + '</span>',
                hasIcon: false,
                fn: function(){
                    trumbowyg.expandRange();
                    //trumbowyg.execCmd('fontSize', index+1, true);
                    var range = document.getSelection().getRangeAt(0);
                    var contentParent = range.startContainer.parentElement;
                    var contents;
                    if (range.startContainer.parentElement.classList.contains('fontsize')) {
                        range.startContainer.parentElement.style.fontSize = value;
                    } else if (range.startContainer.classList && range.startContainer.classList.contains('fontsize')) {
                        range.startContainer.style.fontSize = value;
                    } else {
                        var span = $('<span class="fontsize" style="font-size:' + value + '"></span>')[0];
                        contents = range.cloneContents();
                        span.appendChild(contents);
                        range.deleteContents();
                        range.insertNode(span);
                    }
                    trumbowyg.syncCode();
                }
            });
            dropdown.push('fontsize_' + size);
        });

        return dropdown;
    }
})(jQuery);
