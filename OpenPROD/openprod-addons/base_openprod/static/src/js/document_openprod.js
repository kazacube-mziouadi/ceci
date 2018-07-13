"use strict"
odoo.define('document.openprod', function(require) {
    var core = require('web.core');
    var View = require('web.View');
    var Model = require('web.Model');
    var time = require('web.time');
    var formats = require('web.formats');
    var _t = core._t;
    //
    var DirectoryView = View.extend({
        display_name: 'Directories',
        multi: false,
        searchable: false,
        multi_record: true,
        icon: 'folder-o',
        view_type: 'directory',
        view_loading: function(fvg) {
            this.do_push_state({});
            return this.load_directories();
        },
        load_directories: function() {
            var self = this;
            var myMenu = new dhtmlXMenuObject();
            myMenu.setIconsPath("/base_openprod/static/lib/imgs/");
            myMenu.renderAsContextMenu();
            myMenu.attachEvent("onClick", function(menuId, type) {
                return self.onButtonClick(menuId, type);
            });
            var myTreeGrid = this.grid = new dhtmlXGridObject(this.$el[0]);
            myTreeGrid.setImagePath("/base_openprod/static/lib/imgs/");
            myTreeGrid.setHeader(_t("Name") + "," + _t("Type") + "," + _t("Version") + "," + _t("Status") + "," + _t("User") + "," + _t("Modif") + "," + _t("Document") + "," + _t("File"));
            myTreeGrid.setColTypes("tree,ro,ro,ro,ro,ro,link,link");
            myTreeGrid.setColSorting("str,str,str,str,str,str,na,na");
            myTreeGrid.setInitWidths("*,*,100,*");
            myTreeGrid.setStyle("background-color:#f0eeee;color:black; font-weight:bold;font-family:\"Lucida Grande\", Helvetica, Verdana, Arial, sans-serif", "","", "");
            myTreeGrid.enableAutoWidth(true);
            myTreeGrid.enableAutoHeight(true);
            myTreeGrid.enableContextMenu(myMenu);
            myTreeGrid.enableDragAndDrop(true);
            myTreeGrid.init();
            myMenu.addNewChild(myMenu.topId, null, 'new_dir', 'New Dir');
            myMenu.addNewChild(myMenu.topId, null, 'delete', 'Delete');
            this.menu = myMenu;
            this.grid = myTreeGrid;
            this.grid.attachEvent("onBeforeContextMenu", function(id, ind, obj) {
                self.menu_target = id;
                if (id.indexOf('dir_') == 0) {
                    self.menu.setItemEnabled('new_dir');
                    if (self.grid.hasChildren(id)) {
                        self.menu.setItemDisabled('delete');
                    } else {
                        self.menu.setItemEnabled('delete');
                    }
                } else {
                    self.menu.setItemDisabled('new_dir');
                }
                return true;
            });
            this.grid.attachEvent('onEditCell', function(stage, row_id, cell_id, new_value, old_value) {
                if (stage == 0) {
                    if (cell_id != 0) {
                        return false;
                    }
                    return true;
                } else if (stage == 1) {
                    //
                } else if (stage == 2) {
                    var model = (row_id.indexOf('dir_') == 0) ? 'document.directory' : 'document.openprod';
                    var dir_obj = new Model(model);
                    var dir_id = parseInt(row_id.slice(4));
                    dir_obj.call('write', [dir_id, {
                        name: new_value,
                    }]).then(null, function(){
                        self.grid.setItemText(row_id, old_value)
                    });
                    return true;
                }
            });
            this.grid.attachEvent("onDrag", function(source_id,target_id){
                var source_parent_id = self.grid.getParentId(source_id);
                var model = (source_id.indexOf('dir_') == 0) ? 'document.directory' : 'document.openprod';
                var dir_obj = new Model(model);
                var elem_id = parseInt(source_id.slice(4));
                var new_parent_id = (target_id != undefined && parseInt(target_id.slice(4))) || 0;
                var vals = {};
                if (source_id.indexOf('dir_') == 0) {
                    vals['parent_id'] = new_parent_id;
                } else {
                    vals['directory_id'] = new_parent_id;
                }
                dir_obj.call('write', [elem_id, vals]).then(null, function(res) {
                    self.grid.moveRowTo(source_id, source_parent_id, 'move', 'child');
                });
                return true;
            });
            this.grid.attachEvent("onDragIn", function(source_id,target_id){
                if (target_id == undefined) {
                    return true;
                }
                if (target_id.indexOf('dir_') == 0) {
                    return true;
                } else {
                    return false;
                }
            });
        },
        onButtonClick: function(menuitemId, type) {
            var dir_obj = new Model('document.directory');
            var parent_id = parseInt(this.menu_target.slice(4));
            var self = this;
            if (menuitemId == 'new_dir') {
                var def = dir_obj.call('create', [{
                    parent_id: parent_id,
                    name: 'New Dir',
                }]).then(function(res) {
                    dir_obj.query().filter([['id', '=', res]]).first().then(function(row) {
                        self.grid.addRow('dir_' + res, row.name, null, 'dir_'+row.parent_id[0], 'folder.gif');
                    });
                });
            } else if (menuitemId == 'delete') {
                if (this.menu_target.indexOf('dir_') == 0) {
                    var def = dir_obj.call('unlink', [parent_id]).then(function(res) {
                        self.grid.deleteRow(self.menu_target);
                    });
                } else {
                    (new Model('document.openprod')).call('unlink', [parent_id]).then(function(res) {
                        self.grid.deleteRow(self.menu_target);
                    });
                }
                
            }
        },
        do_show: function() {
            var self = this;
            var directories = new Model('document.directory').query().all();
            var documents = new Model('document.openprod')
                                     .query(['name', 'version', 'state', 'write_date', 'directory_id', 'fname'])
                                     .filter([['directory_id', '!=', false], ['state', '!=', 'obsolete']])
                                     .all();
            $.when(directories, documents).then(function(directories, documents) {
                var res = directories.concat(documents);
                var rows = self.unflatten(res);
                self.grid.clearAll();
                self.grid.parse({
                    rows: rows
                }, 'json');
                return true;
            });
            return this._super();
        },
        unflatten: function(array, parent) {
            var self = this;
            var tree = [];
            parent = typeof parent !== 'undefined' ? parent : {
                id: 0
            };
            if ('directory_id'in parent) {
                return [];
            }
            var children = _.filter(array, function(child) {
                if ('parent_id'in child)
                    return (child.parent_id[0] || 0) == parent.id;
                else
                    return (child.directory_id[0] || 0) == parent.id;
            });
            return _.map(children, function(child) {
                var directory = !('directory_id'in child);
                var val = directory ? {
                    "value": child.name,
                    "image": "folder.gif"
                } : child.name;
                var document = directory ? null : "Document^#id=" + child.id + "&view_type=form&model=document.openprod^_self";
                var link = directory ? null : child.fname + '^/web/content/document.openprod/' + child.id + '/attachment/' + child.fname +'^_blank';
                return {
                    id: (directory ? 'dir_' : 'doc_') + child.id,
                    rows: self.unflatten(array, child),
                    data: [
                        val,
                        child.type_id && child.type_id[1],
                        child.version,
                        _t(child.state),
                        child.user_id && child.user_id[1],
                        formats.format_value(child.write_date, {type:'datetime'}),
                        document,
                        link,
                    ],
                }
            })
        },
    });
    core.view_registry.add('directory', DirectoryView);
});
