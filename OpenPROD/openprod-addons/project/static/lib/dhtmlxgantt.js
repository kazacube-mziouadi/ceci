/*
@license

dhtmlxGantt v.4.0.0 dhtmlx.com
This software can be used only as part of dhtmlx.com site.
You are not allowed to use it on any other site

(c) Dinamenta, UAB.
*/
window.Gantt = {
    _seed: 0
}, Gantt.plugin = function(t) {
    this._ganttPlugin.push(t), t(window.gantt)
}, Gantt._ganttPlugin = [], Gantt.getGanttInstance = function() {
    var t = {
        version: "4.0.0"
    };
    t = {
            version: "4.0.0"
        }, t.event = function(t, e, i) {
            t.addEventListener ? t.addEventListener(e, i, !1) : t.attachEvent && t.attachEvent("on" + e, i)
        }, t.eventRemove = function(t, e, i) {
            t.removeEventListener ? t.removeEventListener(e, i, !1) : t.detachEvent && t.detachEvent("on" + e, i)
        }, t._eventable = function(t) {
            t._silent_mode = !1, t._silentStart = function() {
                this._silent_mode = !0;
            }, t._silentEnd = function() {
                this._silent_mode = !1
            }, t.attachEvent = function(t, e, i) {
                return t = "ev_" + t.toLowerCase(), this[t] || (this[t] = new this._eventCatcher(i || this)), t + ":" + this[t].addEvent(e)
            }, t.callEvent = function(t, e) {
                return this._silent_mode ? !0 : (t = "ev_" + t.toLowerCase(), this[t] ? this[t].apply(this, e) : !0)
            }, t.checkEvent = function(t) {
                return !!this["ev_" + t.toLowerCase()]
            }, t._eventCatcher = function(t) {
                var e = [],
                    i = function() {
                        for (var i = !0, n = 0; n < e.length; n++)
                            if (e[n]) {
                                var a = e[n].apply(t, arguments);
                                i = i && a
                            }
                        return i
                    };
                return i.addEvent = function(t) {
                    return "function" == typeof t ? e.push(t) - 1 : !1
                }, i.removeEvent = function(t) {
                    e[t] = null
                }, i
            }, t.detachEvent = function(t) {
                if (t) {
                    var e = t.split(":");
                    this[e[0]].removeEvent(e[1])
                }
            }, t.detachAllEvents = function() {
                for (var t in this) 0 === t.indexOf("ev_") && delete this[t]
            }, t = null
        }, t.copy = function(e) {
            var i, n, a;
            if (e && "object" == typeof e) {
                for (a = {}, n = [Array, Date, Number, String, Boolean], i = 0; i < n.length; i++) e instanceof n[i] && (a = i ? new n[i](e) : new n[i]);
                for (i in e) Object.prototype.hasOwnProperty.apply(e, [i]) && (a[i] = t.copy(e[i]))
            }
            return a || e
        }, t.mixin = function(t, e, i) {
            for (var n in e)(!t[n] || i) && (t[n] = e[n]);
            return t
        }, t.defined = function(t) {
            return "undefined" != typeof t
        }, t.uid = function() {
            return this._seed || (this._seed = (new Date).valueOf()), this._seed++, this._seed
        }, t.bind = function(t, e) {
            return t.bind ? t.bind(e) : function() {
                return t.apply(e, arguments)
            }
        }, t._get_position = function(t) {
            var e = 0,
                i = 0;
            if (t.getBoundingClientRect) {
                var n = t.getBoundingClientRect(),
                    a = document.body,
                    s = document.documentElement,
                    r = window.pageYOffset || s.scrollTop || a.scrollTop,
                    o = window.pageXOffset || s.scrollLeft || a.scrollLeft,
                    _ = s.clientTop || a.clientTop || 0,
                    d = s.clientLeft || a.clientLeft || 0;
                return e = n.top + r - _, i = n.left + o - d, {
                    y: Math.round(e),
                    x: Math.round(i),
                    width: t.offsetWidth,
                    height: t.offsetHeight
                }
            }
            for (; t;) e += parseInt(t.offsetTop, 10), i += parseInt(t.offsetLeft, 10), t = t.offsetParent;
            return {
                y: e,
                x: i,
                width: t.offsetWidth,
                height: t.offsetHeight
            }
        }, t._detectScrollSize = function() {
            var t = document.createElement("div");
            t.style.cssText = "visibility:hidden;position:absolute;left:-1000px;width:100px;padding:0px;margin:0px;height:110px;min-height:100px;overflow-y:scroll;", document.body.appendChild(t);
            var e = t.offsetWidth - t.clientWidth;
            return document.body.removeChild(t), e
        }, window.dhtmlx && (dhtmlx.attaches || (dhtmlx.attaches = {}), dhtmlx.attaches.attachGantt = function(t, e, i) {
            var n = document.createElement("DIV");
            i = i || window.gantt, n.id = "gantt_" + i.uid(), n.style.width = "100%", n.style.height = "100%", n.cmp = "grid", document.body.appendChild(n), this.attachObject(n.id);
            var a = this.vs[this.av];
            a.grid = i, i.init(n.id, t, e), n.firstChild.style.border = "none", a.gridId = n.id, a.gridObj = n;
            var s = "_viewRestore";
            return this.vs[this[s]()].grid
        }), "undefined" != typeof window.dhtmlXCellObject && (dhtmlXCellObject.prototype.attachGantt = function(t, e, i) {
            i = i || window.gantt;
            var n = document.createElement("DIV");
            n.id = "gantt_" + i.uid(), n.style.width = "100%", n.style.height = "100%", n.cmp = "grid", document.body.appendChild(n), this.attachObject(n.id), i.init(n.id, t, e), n.firstChild.style.border = "none";
            return n = null, this.callEvent("_onContentAttach", []), this.dataObj
        }), t._eventable(t), t._click = {}, t._dbl_click = {}, t._context_menu = {}, t._on_click = function(e) {
            e = e || window.event;
            var i = e.target || e.srcElement,
                n = t.locate(e),
                a = !0;
            if (null !== n ? a = !t.checkEvent("onTaskClick") || t.callEvent("onTaskClick", [n, e]) : t.callEvent("onEmptyClick", [e]),
                a) {
                var s = t._find_ev_handler(e, i, t._click, n);
                if (!s) return;
                n && t.getTask(n) && t.config.select_task && t.selectTask(n)
            }
        }, t._on_contextmenu = function(e) {
            e = e || window.event;
            var i = e.target || e.srcElement,
                n = t.locate(i),
                a = t.locate(i, t.config.link_attribute),
                s = !t.checkEvent("onContextMenu") || t.callEvent("onContextMenu", [n, a, e]);
            return s || (e.preventDefault ? e.preventDefault() : e.returnValue = !1), s
        }, t._find_ev_handler = function(e, i, n, a) {
            for (var s = !0; i;) {
                var r = t._getClassName(i);
                if (r) {
                    r = r.split(" ");
                    for (var o = 0; o < r.length; o++)
                        if (r[o] && n[r[o]]) {
                            var _ = n[r[o]].call(t, e, a, i);
                            s = s && !("undefined" != typeof _ && _ !== !0)
                        }
                }
                i = i.parentNode
            }
            return s
        }, t._on_dblclick = function(e) {
            e = e || window.event;
            var i = e.target || e.srcElement,
                n = t.locate(e),
                a = !t.checkEvent("onTaskDblClick") || t.callEvent("onTaskDblClick", [n, e]);
            if (a) {
                var s = t._find_ev_handler(e, i, t._dbl_click, n);
                if (!s) return;
                null !== n && t.getTask(n) && a && t.config.details_on_dblclick && t.showLightbox(n)
            }
        }, t._on_mousemove = function(e) {
            if (t.checkEvent("onMouseMove")) {
                var i = t.locate(e);
                t._last_move_event = e, t.callEvent("onMouseMove", [i, e]);
            }
        }, t._DnD = function(e, i) {
            i && (this._settings = i), t._eventable(this), t.event(e, "mousedown", t.bind(function(t) {
                i.original_target = {
                    target: t.target || t.srcElement
                }, this.dragStart(e, t)
            }, this))
        }, t._DnD.prototype = {
            dragStart: function(e, i) {
                this.config = {
                    obj: e,
                    marker: null,
                    started: !1,
                    pos: this.getPosition(i),
                    sensitivity: 4
                }, this._settings && t.mixin(this.config, this._settings, !0);
                var n = t.bind(function(t) {
                        return this.dragMove(e, t)
                    }, this),
                    a = (t.bind(function(t) {
                        return this.dragScroll(e, t)
                    }, this), t.bind(function(e) {
                        return t.defined(this.config.updates_per_second) && !t._checkTimeout(this, this.config.updates_per_second) ? !0 : n(e);
                    }, this)),
                    s = t.bind(function(i) {
                        return t.eventRemove(document.body, "mousemove", a), t.eventRemove(document.body, "mouseup", s), this.dragEnd(e)
                    }, this);
                t.event(document.body, "mousemove", a), t.event(document.body, "mouseup", s), document.body.className += " gantt_noselect"
            },
            dragMove: function(t, e) {
                if (!this.config.marker && !this.config.started) {
                    var i = this.getPosition(e),
                        n = i.x - this.config.pos.x,
                        a = i.y - this.config.pos.y,
                        s = Math.sqrt(Math.pow(Math.abs(n), 2) + Math.pow(Math.abs(a), 2));
                    if (s > this.config.sensitivity) {
                        if (this.config.started = !0,
                            this.config.ignore = !1, this.callEvent("onBeforeDragStart", [t, this.config.original_target]) === !1) return this.config.ignore = !0, !0;
                        var r = this.config.marker = document.createElement("div");
                        r.className = "gantt_drag_marker", r.innerHTML = "Dragging object", document.body.appendChild(r), this.callEvent("onAfterDragStart", [t, this.config.original_target])
                    } else this.config.ignore = !0
                }
                this.config.ignore || (e.pos = this.getPosition(e), this.config.marker.style.left = e.pos.x + "px", this.config.marker.style.top = e.pos.y + "px", this.callEvent("onDragMove", [t, e]));
            },
            dragEnd: function(t) {
                this.config.marker && (this.config.marker.parentNode.removeChild(this.config.marker), this.config.marker = null, this.callEvent("onDragEnd", [])), document.body.className = document.body.className.replace(" gantt_noselect", "")
            },
            getPosition: function(t) {
                var e = 0,
                    i = 0;
                return t = t || window.event, t.pageX || t.pageY ? (e = t.pageX, i = t.pageY) : (t.clientX || t.clientY) && (e = t.clientX + document.body.scrollLeft + document.documentElement.scrollLeft, i = t.clientY + document.body.scrollTop + document.documentElement.scrollTop), {
                    x: e,
                    y: i
                }
            }
        }, t._init_grid = function() {
            this._click.gantt_close = this.bind(function(t, e, i) {
                return this.close(e), !1
            }, this), this._click.gantt_open = this.bind(function(t, e, i) {
                return this.open(e), !1
            }, this), this._click.gantt_row = this.bind(function(t, e, i) {
                if (null !== e) {
                    var n = this.getTask(e);
                    this.config.scroll_on_click && this.showDate(n.start_date), this.callEvent("onTaskRowClick", [e, i])
                }
            }, this), this._click.gantt_grid_head_cell = this.bind(function(t, e, i) {
                var n = i.getAttribute("column_id");
                if (this.callEvent("onGridHeaderClick", [n, t])) {
                    if ("add" == n) return void this._click.gantt_add(t, this.config.root_id);
                    if (this.config.sort) {
                        for (var a, s = n, r = 0; this.config.columns.length; r++)
                            if (this.config.columns[r].name == n) {
                                a = this.config.columns[r];
                                break
                            }
                        if (a && void 0 !== a.sort && a.sort !== !0 && (s = a.sort, !s)) return;
                        var o = this._sort && this._sort.direction && this._sort.name == n ? this._sort.direction : "desc";
                        o = "desc" == o ? "asc" : "desc", this._sort = {
                            name: n,
                            direction: o
                        }, this.sort(s, "desc" == o)
                    }
                }
            }, this), !this.config.sort && this.config.order_branch && this._init_dnd(), this._click.gantt_add = this.bind(function(t, e, i) {
                if (!this.config.readonly) {
                    var n = {};
                    return this.createTask(n, e ? e : this.config.root_id), !1
                }
            }, this), this._init_resize && this._init_resize()
        }, t._render_grid = function() {
            this._is_grid_visible() && (this._calc_grid_width(), this._render_grid_header())
        }, t._calc_grid_width = function() {
            for (var t = this.getGridColumns(), e = 0, i = [], n = [], a = 0; a < t.length; a++) {
                var s = parseInt(t[a].width, 10);
                window.isNaN(s) && (s = 50, i.push(a)), n[a] = s, e += s
            }
            if (this.config.autofit || i.length) {
                var r = this._get_grid_width() - e;
                r / (i.length > 0 ? i.length : n.length > 0 ? n.length : 1);
                if (i.length > 0)
                    for (var o = r / (i.length ? i.length : 1), a = 0; a < i.length; a++) {
                        var _ = i[a];
                        n[_] += o
                    } else
                        for (var o = r / (n.length ? n.length : 1), a = 0; a < n.length; a++) n[a] += o;
                for (var a = 0; a < n.length; a++) t[a].width = n[a]
            } else this.config.grid_width = e
        }, t._render_grid_header = function() {
            for (var t = this.getGridColumns(), e = [], i = 0, n = this.locale.labels, a = this.config.scale_height - 2, s = 0; s < t.length; s++) {
                var r = s == t.length - 1,
                    o = t[s],
                    _ = 1 * o.width;
                r && this._get_grid_width() > i + _ && (o.width = _ = this._get_grid_width() - i), i += _;
                var d = this._sort && o.name == this._sort.name ? "<div class='gantt_sort gantt_" + this._sort.direction + "'></div>" : "",
                    l = ["gantt_grid_head_cell", "gantt_grid_head_" + o.name, r ? "gantt_last_cell" : "", this.templates.grid_header_class(o.name, o)].join(" "),
                    h = "width:" + (_ - (r ? 1 : 0)) + "px;",
                    c = o.label || n["column_" + o.name];
                c = c || "";
                var u = "<div class='" + l + "' style='" + h + "' column_id='" + o.name + "'>" + c + d + "</div>";
                e.push(u)
            }
            this.$grid_scale.style.height = this.config.scale_height - 1 + "px", this.$grid_scale.style.lineHeight = a + "px", this.$grid_scale.style.width = i - 1 + "px", this.$grid_scale.innerHTML = e.join("")
        }, t._render_grid_item = function(e) {
            if (!t._is_grid_visible()) return null;
            for (var i = this.getGridColumns(), n = [], a = 0; a < i.length; a++) {
                var s, r, o = a == i.length - 1,
                    _ = i[a];
                "add" == _.name ? r = "<div class='gantt_add'></div>" : (r = _.template ? _.template(e) : e[_.name],
                    r instanceof Date && (r = this.templates.date_grid(r, e)), r = "<div class='gantt_tree_content'>" + r + "</div>");
                var d = "gantt_cell" + (o ? " gantt_last_cell" : ""),
                    l = "";
                if (_.tree) {
                    for (var h = 0; h < e.$level; h++) l += this.templates.grid_indent(e);
                    var c = this._has_children(e.id);
                    c ? (l += this.templates.grid_open(e), l += this.templates.grid_folder(e)) : (l += this.templates.grid_blank(e), l += this.templates.grid_file(e))
                }
                var u = "width:" + (_.width - (o ? 1 : 0)) + "px;";
                this.defined(_.align) && (u += "text-align:" + _.align + ";"), s = "<div class='" + d + "' style='" + u + "'>" + l + r + "</div>",
                    n.push(s)
            }
            var d = e.$index % 2 === 0 ? "" : " odd";
            if (d += e.$transparent ? " gantt_transparent" : "", d += e.$dataprocessor_class ? " " + e.$dataprocessor_class : "", this.templates.grid_row_class) {
                var g = this.templates.grid_row_class.call(this, e.start_date, e.end_date, e);
                g && (d += " " + g)
            }
            this.getState().selected_task == e.id && (d += " gantt_selected");
            var f = document.createElement("div");
            return f.className = "gantt_row" + d, f.style.height = this.config.row_height + "px", f.style.lineHeight = t.config.row_height + "px", f.setAttribute(this.config.task_attribute, e.id),
                f.innerHTML = n.join(""), f
        }, t.open = function(e) {
            t._set_item_state(e, !0), this.callEvent("onTaskOpened", [e])
        }, t.close = function(e) {
            t._set_item_state(e, !1), this.callEvent("onTaskClosed", [e])
        }, t._set_item_state = function(e, i) {
            e && this._pull[e] && (this._pull[e].$open = i, t._refresh_on_toggle_element(e))
        }, t._refresh_on_toggle_element = function(t) {
            this.refreshData()
        }, t._is_grid_visible = function() {
            return this.config.grid_width && this.config.show_grid
        }, t._get_grid_width = function() {
            return this._is_grid_visible() ? this._is_chart_visible() ? this.config.grid_width : this._x : 0;
        }, t.moveTask = function(e, i, n) {
            var a = arguments[3];
            if (a) {
                if (a === e) return;
                n = this.getParent(a), i = this.getTaskIndex(a)
            }
            if (e != n) {
                n = n || this.config.root_id;
                var s = this.getTask(e),
                    r = this.getParent(s.id),
                    o = (this.getChildren(this.getParent(s.id)), this.getChildren(n));
                if (-1 == i && (i = o.length + 1), r == n) {
                    var _ = this.getTaskIndex(e);
                    if (_ == i) return
                }
                if (this.callEvent("onBeforeTaskMove", [e, n, i]) !== !1) {
                    this._replace_branch_child(r, e), o = this.getChildren(n);
                    var d = o[i];
                    d ? o = o.slice(0, i).concat([e]).concat(o.slice(i)) : o.push(e),
                        this.setParent(s, n), this._branches[n] = o, s.$level = this.calculateTaskLevel(s), 1 * i > 0 ? a ? s.$drop_target = (this.getTaskIndex(e) > this.getTaskIndex(a) ? "next:" : "") + a : s.$drop_target = "next:" + t.getPrevSibling(e) : o[1 * i + 1] ? s.$drop_target = o[1 * i + 1] : s.$drop_target = n, this.callEvent("onAfterTaskMove", [e, n, i]) && this.refreshData()
                }
            }
        }, t._init_dnd = function() {
            var e = new t._DnD(this.$grid_data, {
                updates_per_second: 60
            });
            this.defined(this.config.dnd_sensitivity) && (e.config.sensitivity = this.config.dnd_sensitivity), e.attachEvent("onBeforeDragStart", this.bind(function(i, n) {
                var a = this._locateHTML(n);
                if (!a) return !1;
                this.hideQuickInfo && this._hideQuickInfo();
                var s = this.locate(n),
                    r = t.getTask(s);
                return t._is_readonly(r) ? !1 : (e.config.initial_open_state = r.$open, this.callEvent("onRowDragStart", [s, n.target || n.srcElement, n]) ? void 0 : !1)
            }, this)), e.attachEvent("onAfterDragStart", this.bind(function(t, i) {
                var n = this._locateHTML(i);
                e.config.marker.innerHTML = n.outerHTML, e.config.id = this.locate(i);
                var a = this.getTask(e.config.id);
                e.config.index = this.getTaskIndex(e.config.id), e.config.parent = a.parent,
                    a.$open = !1, a.$transparent = !0, this.refreshData()
            }, this)), e.lastTaskOfLevel = function(e) {
                for (var i = t._order, n = t._pull, a = null, s = 0, r = i.length; r > s; s++) n[i[s]].$level == e && (a = n[i[s]]);
                return a ? a.id : null
            }, e._getGridPos = this.bind(function(t) {
                var e = this._get_position(this.$grid_data),
                    i = e.x,
                    n = t.pos.y - 10;
                return n < e.y && (n = e.y), n > e.y + this.$grid_data.offsetHeight - this.config.row_height && (n = e.y + this.$grid_data.offsetHeight - this.config.row_height), e.x = i, e.y = n, e
            }, this), e.attachEvent("onDragMove", this.bind(function(i, n) {
                function a(e, i) {
                    return e.$level == i.$level || t.config.order_branch_free
                }
                var s = e.config,
                    r = e._getGridPos(n);
                s.marker.style.left = r.x + 10 + "px", s.marker.style.top = r.y + "px", r = e._getGridPos(n);
                var o = (r.x, r.y),
                    _ = document.documentElement.scrollTop || document.body.scrollTop,
                    d = document.documentElement.scrollLeft || document.body.scrollLeft,
                    l = document.elementFromPoint(r.x - d + 1, o - _),
                    h = this.locate(l),
                    c = this.getTask(e.config.id);
                if (this.isTaskExists(h) || (h = e.lastTaskOfLevel(t.config.order_branch_free ? c.$level : 0), h == e.config.id && (h = null)),
                    this.isTaskExists(h)) {
                    var u = t._get_position(l),
                        g = this.getTask(h);
                    if (u.y + l.offsetHeight / 2 < o) {
                        var f = this.getGlobalTaskIndex(g.id),
                            p = this._pull[this._order[f + 1]];
                        if (p) {
                            if (p.id == c.id) return;
                            g = p
                        } else if (p = this._pull[this._order[f]], a(p, c) && p.id != c.id) return void this.moveTask(c.id, -1, this.getParent(p.id))
                    }
                    for (var f = this.getGlobalTaskIndex(g.id), v = this._pull[this._order[f - 1]], m = 1;
                        (!v || v.id == g.id) && f - m >= 0;) v = this._pull[this._order[f - m]], m++;
                    if (c.id == g.id) return;
                    a(g, c) && c.id != g.id ? this.moveTask(c.id, 0, 0, g.id) : g.$level != c.$level - 1 || t.getChildren(g.id).length ? v && a(v, c) && c.id != v.id && this.moveTask(c.id, -1, this.getParent(v.id)) : this.moveTask(c.id, 0, g.id);
                }
                return !0
            }, this)), e.attachEvent("onDragEnd", this.bind(function() {
                var t = this.getTask(e.config.id);
                this.callEvent("onBeforeRowDragEnd", [e.config.id, e.config.parent, e.config.index]) === !1 ? (this.moveTask(e.config.id, e.config.index, e.config.parent), t.$drop_target = null) : this.callEvent("onRowDragEnd", [e.config.id, t.$drop_target]), t.$transparent = !1, t.$open = e.config.initial_open_state, this.refreshData()
            }, this))
        }, t.getGridColumns = function() {
            return this.config.columns
        }, t._has_children = function(t) {
            return this.getChildren(t).length > 0;
        }, t._render_grid_header_resize = function() {
            for (var t = this.getGridColumns(), e = 0, i = this.config.scale_height, n = (this._get_position(this.$grid_scale), 0); n < t.length; n++) {
                var a = (n == t.length - 1, t[n]);
                if (e += a.width, a.resize) {
                    var s = document.createElement("div");
                    s.className = "gantt_grid_column_resize_wrap", s.style.top = "0px", s.style.height = i + "px", s.innerHTML = "<div class='gantt_grid_column_resize'></div>", s.setAttribute(this.config.grid_resizer_column_attribute, n), this.$grid_scale.appendChild(s), s.style.left = Math.max(0, e - 1 - s.offsetWidth / 2) + "px";
                }
            }
            if (this.config.grid_resize) {
                var r = document.createElement("div");
                r.className = "gantt_grid_resize_wrap", r.style.top = "0px", r.style.height = this.$grid.offsetHeight + "px", r.innerHTML = "<div class='gantt_grid_resize'></div>", r.setAttribute(this.config.grid_resizer_attribute, !0), this.$grid_scale.appendChild(r), r.style.left = Math.max(0, this.config.grid_width - 1 - r.offsetWidth / 2) + "px"
            }
        }, t._init_resize = function() {
            var e = new t._DnD(this.$grid_scale, {
                updates_per_second: 60
            });
            this.defined(this.config.dnd_sensitivity) && (e.config.sensitivity = this.config.dnd_sensitivity),
                e.attachEvent("onBeforeDragStart", this.bind(function(e, i) {
                    var n = this._locateHTML(i, this.config.grid_resizer_column_attribute);
                    if (!n) return !1;
                    var a = this.locate(i, this.config.grid_resizer_column_attribute),
                        s = this.getGridColumns()[a];
                    return t.callEvent("onColumnResizeStart", [a, s]) === !1 ? !1 : void 0
                }, this)), e.attachEvent("onAfterDragStart", this.bind(function(t, i) {
                    var n = this.locate(i, this.config.grid_resizer_column_attribute);
                    e.config.marker.innerHTML = "", e.config.marker.className += " gantt_grid_resize_area",
                        e.config.marker.style.height = this.$grid.offsetHeight + "px", e.config.marker.style.top = "0px", e.config.drag_index = n
                }, this)), e.attachEvent("onDragMove", this.bind(function(i, n) {
                    var a = e.config,
                        s = this.getGridColumns(),
                        r = this._get_position(this.$grid_scale),
                        o = parseInt(a.marker.style.left, 10),
                        _ = this.config.min_grid_column_width,
                        d = this.$grid_data.offsetWidth - this.config.min_grid_column_width * (s.length - a.drag_index - 2),
                        l = 0,
                        h = 0;
                    o -= r.x - 1;
                    for (var c = 0; c < a.drag_index; c++) _ += s[c].width, l += s[c].width;
                    return _ > o && (o = _),
                        this.config.keep_grid_width && o > d && (o = d), h = o - l, a.marker.style.top = r.y + "px", a.marker.style.left = r.x - 1 + l + "px", a.marker.style.width = h + "px", a.left = o - 1, t.callEvent("onColumnResize", [a.drag_index, s[a.drag_index], h - 1]), !0
                }, this)), e.attachEvent("onDragEnd", this.bind(function(i, n) {
                    for (var a = this.getGridColumns(), s = 0, r = parseInt(e.config.drag_index, 10), o = a[r], _ = 0; r > _; _++) s += a[_].width;
                    var d = o.min_width && e.config.left - s < o.min_width ? o.min_width : e.config.left - s;
                    if (t.callEvent("onColumnResizeEnd", [r, o, d]) !== !1 && o.width != d) {
                        if (o.width = d, this.config.keep_grid_width)
                            for (var _ = r + 1, l = a.length; l > _; _++) "add" == a[_].name ? a[_].width = 1 * a[_].width || 44 : a[_].width = null;
                        else {
                            for (var _ = r, l = a.length; l > _; _++) s += a[_].width;
                            this.config.grid_width = s
                        }
                        this.render()
                    }
                }, this));
            var i = new t._DnD(this.$grid, {
                updates_per_second: 60
            });
            this.defined(this.config.dnd_sensitivity) && (i.config.sensitivity = this.config.dnd_sensitivity), i.attachEvent("onBeforeDragStart", this.bind(function(e, i) {
                var n = this._locateHTML(i, this.config.grid_resizer_attribute);
                return n ? t.callEvent("onGridResizeStart", [t.config.grid_width]) === !1 ? !1 : void 0 : !1;
            }, this)), i.attachEvent("onAfterDragStart", this.bind(function(t, e) {
                i.config.marker.innerHTML = "", i.config.marker.className += " gantt_grid_resize_area", i.config.marker.style.height = this.$grid.offsetHeight + "px", i.config.marker.style.top = "0px"
            }, this)), i.attachEvent("onDragMove", this.bind(function(e, n) {
                for (var a = i.config, s = this.config.columns, r = this._get_position(this.$grid), o = parseInt(a.marker.style.left, 10), _ = 0, d = 0; d < s.length; d++) s[d].hide || (_ += s[d].min_width ? s[d].min_width : this.config.min_grid_column_width);
                return o -= r.x - 1, _ > o && (o = _), a.marker.style.top = r.y + "px", a.marker.style.left = r.x - 1 + "px", a.marker.style.width = o + "px", a.left = o - 1, t.callEvent("onGridResize", [this.config.grid_width, o - 1]), !0
            }, this)), i.attachEvent("onDragEnd", this.bind(function(e, n) {
                for (var a = this.config.columns, s = 0, r = i.config.left, o = 0, _ = a.length; _ > o; o++) a[o].hide || (s += a[o].width);
                for (var d, l = a.length, h = r - s, o = 0; l > o; o++)
                    if (!a[o].hide) {
                        var c = Math.floor(h * (a[o].width / s));
                        s -= a[o].width, d = a[o].width + c, (a[o].min_width && d >= a[o].min_width || !a[o].min_width || d > a[o].width) && (h -= c,
                            a[o].width = d)
                    }
                for (var u = h > 0 ? 1 : -1; h > 0 && 1 === u || 0 > h && -1 === u;) {
                    var g = h;
                    for (o = 0; l > o; o++) {
                        var f = a[o].width + u;
                        if ((a[o].min_width && f >= a[o].min_width || !a[o].min_width || d > a[o].width) && (h -= u, a[o].width = f, 0 === h)) break
                    }
                    if (g == h) break
                }
                t.callEvent("onGridResizeEnd", [this.config.grid_width, r]) !== !1 && (this.config.grid_width = r, this.render())
            }, this))
        }, t.attachEvent("onGanttRender", function() {
            t._render_grid_header_resize()
        }),
        function() {
            var e = t._has_children;
            t._has_children = function(t) {
                return e.apply(this, arguments) ? !0 : this.isTaskExists(t) ? this.getTask(t).$has_child : !1;
            }
        }(), t._need_dynamic_loading = function(e) {
            if (t.config.branch_loading && t._load_url) {
                var i = t.getUserData(e, "was_rendered");
                if (!i && t._has_children(e)) return !0
            }
            return !1
        }, t._refresh_on_toggle_element = function(e) {
            t._need_dynamic_loading(e) || this.refreshData()
        }, t.attachEvent("onTaskOpened", function(e) {
            if (t.config.branch_loading && t._load_url && t._need_dynamic_loading(e)) {
                var i = t._load_url;
                i = i.replace(/(\?|&)?parent_id=.+&?/, "");
                var n = i.indexOf("?") >= 0 ? "&" : "?",
                    a = 0;
                this._cached_scroll_pos && this._cached_scroll_pos.y && (a = Math.max(this._cached_scroll_pos.y, 0)),
                    t.load(i + n + "parent_id=" + encodeURIComponent(e), this._load_type, function() {
                        a && t.scrollTo(null, a)
                    }), t.setUserData(e, "was_rendered", !0)
            }
        }), t.getGridColumns = function() {
            for (var e = t.config.columns, i = [], n = 0; n < e.length; n++) e[n].hide || i.push(e[n]);
            return i
        }, t.getGridColumn = function(e) {
            for (var i = t.config.columns, n = 0; n < i.length; n++)
                if (i[n].name == e) return i[n];
            return null
        }, t._scale_helpers = {
            getSum: function(t, e, i) {
                void 0 === i && (i = t.length - 1), void 0 === e && (e = 0);
                for (var n = 0, a = e; i >= a; a++) n += t[a];
                return n
            },
            setSumWidth: function(t, e, i, n) {
                var a = e.width;
                void 0 === n && (n = a.length - 1), void 0 === i && (i = 0);
                var s = n - i + 1;
                if (!(i > a.length - 1 || 0 >= s || n > a.length - 1)) {
                    var r = this.getSum(a, i, n),
                        o = t - r;
                    this.adjustSize(o, a, i, n), this.adjustSize(-o, a, n + 1), e.full_width = this.getSum(a)
                }
            },
            splitSize: function(t, e) {
                for (var i = [], n = 0; e > n; n++) i[n] = 0;
                return this.adjustSize(t, i), i
            },
            adjustSize: function(t, e, i, n) {
                i || (i = 0), void 0 === n && (n = e.length - 1);
                for (var a = n - i + 1, s = this.getSum(e, i, n), r = 0, o = i; n >= o; o++) {
                    var _ = Math.floor(t * (s ? e[o] / s : 1 / a));
                    s -= e[o], t -= _, a--, e[o] += _, r += _
                }
                e[e.length - 1] += t;
            },
            sortScales: function(e) {
                function i(e, i) {
                    var n = new Date(1970, 0, 1);
                    return t.date.add(n, i, e) - n
                }
                e.sort(function(t, e) {
                    return i(t.unit, t.step) < i(e.unit, e.step) ? 1 : i(t.unit, t.step) > i(e.unit, e.step) ? -1 : 0
                })
            },
            primaryScale: function() {
                return t._init_template("date_scale"), {
                    unit: t.config.scale_unit,
                    step: t.config.step,
                    template: t.templates.date_scale,
                    date: t.config.date_scale,
                    css: t.templates.scale_cell_class
                }
            },
            prepareConfigs: function(t, e, i, n) {
                for (var a = this.splitSize(n, t.length), s = i, r = [], o = t.length - 1; o >= 0; o--) {
                    var _ = o == t.length - 1,
                        d = this.initScaleConfig(t[o]);
                    _ && this.processIgnores(d), this.initColSizes(d, e, s, a[o]), this.limitVisibleRange(d), _ && (s = d.full_width), r.unshift(d)
                }
                for (var o = 0; o < r.length - 1; o++) this.alineScaleColumns(r[r.length - 1], r[o]);
                for (var o = 0; o < r.length; o++) this.setPosSettings(r[o]);
                return r
            },
            setPosSettings: function(t) {
                for (var e = 0, i = t.trace_x.length; i > e; e++) t.left.push((t.width[e - 1] || 0) + (t.left[e - 1] || 0))
            },
            _ignore_time_config: function(t) {
                return this.config.skip_off_time ? !this.isWorkTime(t) : !1
            },
            processIgnores: function(t) {
                t.ignore_x = {}, t.display_count = t.count;
            },
            initColSizes: function(t, e, i, n) {
                var a = i;
                t.height = n;
                var s = void 0 === t.display_count ? t.count : t.display_count;
                s || (s = 1), t.col_width = Math.floor(a / s), e && t.col_width < e && (t.col_width = e, a = t.col_width * s), t.width = [];
                for (var r = t.ignore_x || {}, o = 0; o < t.trace_x.length; o++) r[t.trace_x[o].valueOf()] || t.display_count == t.count ? t.width[o] = 0 : t.width[o] = 1;
                this.adjustSize(a - this.getSum(t.width), t.width), t.full_width = this.getSum(t.width)
            },
            initScaleConfig: function(e) {
                var i = t.mixin({
                    count: 0,
                    col_width: 0,
                    full_width: 0,
                    height: 0,
                    width: [],
                    left: [],
                    trace_x: []
                }, e);
                return this.eachColumn(e.unit, e.step, function(t) {
                    i.count++, i.trace_x.push(new Date(t))
                }), i
            },
            iterateScales: function(t, e, i, n, a) {
                for (var s = e.trace_x, r = t.trace_x, o = i || 0, _ = n || r.length - 1, d = 0, l = 1; l < s.length; l++)
                    for (var h = o; _ >= h; h++) + r[h] != +s[l] || (a && a.apply(this, [d, l, o, h]), o = h, d = l)
            },
            alineScaleColumns: function(t, e, i, n) {
                this.iterateScales(t, e, i, n, function(i, n, a, s) {
                    var r = this.getSum(t.width, a, s - 1),
                        o = this.getSum(e.width, i, n - 1);
                    o != r && this.setSumWidth(r, e, i, n - 1)
                })
            },
            eachColumn: function(e, i, n) {
                var a = new Date(t._min_date),
                    s = new Date(t._max_date);
                t.date[e + "_start"] && (a = t.date[e + "_start"](a));
                var r = new Date(a);
                for (+r >= +s && (s = t.date.add(r, i, e)); + s > +r;) {
                    n.call(this, new Date(r));
                    var o = r.getTimezoneOffset();
                    r = t.date.add(r, i, e), r = t._correct_dst_change(r, o, i, e), t.date[e + "_start"] && (r = t.date[e + "_start"](r))
                }
            },
            limitVisibleRange: function(e) {
                var i = e.trace_x,
                    n = 0,
                    a = e.width.length - 1,
                    s = 0;
                if (+i[0] < +t._min_date && n != a) {
                    var r = Math.floor(e.width[0] * ((i[1] - t._min_date) / (i[1] - i[0])));
                    s += e.width[0] - r, e.width[0] = r,
                        i[0] = new Date(t._min_date)
                }
                var o = i.length - 1,
                    _ = i[o],
                    d = t.date.add(_, e.step, e.unit);
                if (+d > +t._max_date && o > 0) {
                    var r = e.width[o] - Math.floor(e.width[o] * ((d - t._max_date) / (d - _)));
                    s += e.width[o] - r, e.width[o] = r
                }
                if (s) {
                    for (var l = this.getSum(e.width), h = 0, c = 0; c < e.width.length; c++) {
                        var u = Math.floor(s * (e.width[c] / l));
                        e.width[c] += u, h += u
                    }
                    this.adjustSize(s - h, e.width)
                }
            }
        }, t._scale_helpers.processIgnores = function(e) {
            var i = e.count;
            if (e.ignore_x = {}, t.ignore_time || t.config.skip_off_time) {
                var n = t.ignore_time || function() {
                    return !1;
                };
                i = 0;
                for (var a = 0; a < e.trace_x.length; a++) n.call(t, e.trace_x[a]) || this._ignore_time_config.call(t, e.trace_x[a]) ? (e.ignore_x[e.trace_x[a].valueOf()] = !0, e.ignored_colls = !0) : i++
            }
            e.display_count = i
        }, t._tasks_dnd = {
            drag: null,
            _events: {
                before_start: {},
                before_finish: {},
                after_finish: {}
            },
            _handlers: {},
            init: function() {
                this.clear_drag_state();
                var e = t.config.drag_mode;
                this.set_actions();
                var i = {
                    before_start: "onBeforeTaskDrag",
                    before_finish: "onBeforeTaskChanged",
                    after_finish: "onAfterTaskDrag"
                };
                for (var n in this._events)
                    for (var a in e) this._events[n][a] = i[n];
                this._handlers[e.move] = this._move, this._handlers[e.resize] = this._resize, this._handlers[e.progress] = this._resize_progress
            },
            set_actions: function() {
                var e = t.$task_data;
                t.event(e, "mousemove", t.bind(function(t) {
                    this.on_mouse_move(t || event)
                }, this)), t.event(e, "mousedown", t.bind(function(t) {
                    this.on_mouse_down(t || event)
                }, this)), t.event(e, "mouseup", t.bind(function(t) {
                    this.on_mouse_up(t || event)
                }, this))
            },
            clear_drag_state: function() {
                this.drag = {
                    id: null,
                    mode: null,
                    pos: null,
                    start_x: null,
                    start_y: null,
                    obj: null,
                    left: null
                }
            },
            _resize: function(e, i, n) {
                var a = t.config,
                    s = this._drag_task_coords(e, n);
                n.left ? (e.start_date = t.dateFromPos(s.start + i), e.start_date || (e.start_date = new Date(t.getState().min_date))) : (e.end_date = t.dateFromPos(s.end + i), e.end_date || (e.end_date = new Date(t.getState().max_date))), e.end_date - e.start_date < a.min_duration && (n.left ? e.start_date = t.calculateEndDate(e.end_date, -1) : e.end_date = t.calculateEndDate(e.start_date, 1)), t._init_task_timing(e)
            },
            _resize_progress: function(t, e, i) {
                var n = this._drag_task_coords(t, i),
                    a = Math.max(0, i.pos.x - n.start);
                t.progress = Math.min(1, a / (n.end - n.start))
            },
            _move: function(e, i, n) {
                var a = this._drag_task_coords(e, n),
                    s = t.dateFromPos(a.start + i),
                    r = t.dateFromPos(a.end + i);
                s ? r ? (e.start_date = s, e.end_date = r) : (e.end_date = new Date(t.getState().max_date), e.start_date = t.dateFromPos(t.posFromDate(e.end_date) - (a.end - a.start))) : (e.start_date = new Date(t.getState().min_date), e.end_date = t.dateFromPos(t.posFromDate(e.start_date) + (a.end - a.start)))
            },
            _drag_task_coords: function(e, i) {
                var n = i.obj_s_x = i.obj_s_x || t.posFromDate(e.start_date),
                    a = i.obj_e_x = i.obj_e_x || t.posFromDate(e.end_date);
                return {
                    start: n,
                    end: a
                }
            },
            on_mouse_move: function(e) {
                this.drag.start_drag && this._start_dnd(e);
                var i = this.drag;
                if (i.mode) {
                    if (!t._checkTimeout(this, 40)) return;
                    this._update_on_move(e)
                }
            },
            _update_on_move: function(e) {
                var i = this.drag;
                if (i.mode) {
                    var n = t._get_mouse_pos(e);
                    if (i.pos && i.pos.x == n.x) return;
                    i.pos = n;
                    var a = t.dateFromPos(n.x);
                    if (!a || isNaN(a.getTime())) return;
                    var s = n.x - i.start_x,
                        r = t.getTask(i.id);
                    if (this._handlers[i.mode]) {
                        var o = t.mixin({}, r),
                            _ = t.mixin({}, r);
                        this._handlers[i.mode].apply(this, [_, s, i]), t.mixin(r, _, !0),
                            t.callEvent("onTaskDrag", [r.id, i.mode, _, o, e]), t.mixin(r, _, !0), t._update_parents(i.id), t.refreshTask(i.id)
                    }
                }
            },
            on_mouse_down: function(e, i) {
                if (2 != e.button) {
                    var n = t.locate(e),
                        a = null;
                    if (t.isTaskExists(n) && (a = t.getTask(n)), !t._is_readonly(a) && !this.drag.mode) {
                        this.clear_drag_state(), i = i || e.target || e.srcElement;
                        var s = t._getClassName(i);
                        if (!s || !this._get_drag_mode(s)) return i.parentNode ? this.on_mouse_down(e, i.parentNode) : void 0;
                        var r = this._get_drag_mode(s);
                        if (r)
                            if (r.mode && r.mode != t.config.drag_mode.ignore && t.config["drag_" + r.mode]) {
                                if (n = t.locate(i), a = t.copy(t.getTask(n) || {}), t._is_readonly(a)) return this.clear_drag_state(), !1;
                                if (t._is_flex_task(a) && r.mode != t.config.drag_mode.progress) return void this.clear_drag_state();
                                r.id = n;
                                var o = t._get_mouse_pos(e);
                                r.start_x = o.x, r.start_y = o.y, r.obj = a, this.drag.start_drag = r
                            } else this.clear_drag_state();
                        else if (t.checkEvent("onMouseDown") && t.callEvent("onMouseDown", [s.split(" ")[0]]) && i.parentNode) return this.on_mouse_down(e, i.parentNode)
                    }
                }
            },
            _fix_dnd_scale_time: function(e, i) {
                function n(e) {
                    t.isWorkTime(e.start_date) || (e.start_date = t.calculateEndDate(e.start_date, -1, t.config.duration_unit))
                }

                function a(e) {
                    t.isWorkTime(new Date(e.end_date - 1)) || (e.end_date = t.calculateEndDate(e.end_date, 1, t.config.duration_unit))
                }
                var s = t._tasks.unit,
                    r = t._tasks.step;
                t.config.round_dnd_dates || (s = "minute", r = t.config.time_step), i.mode == t.config.drag_mode.resize ? i.left ? (e.start_date = t.roundDate({
                    date: e.start_date,
                    unit: s,
                    step: r
                }), n(e)) : (e.end_date = t.roundDate({
                    date: e.end_date,
                    unit: s,
                    step: r
                }), a(e)) : i.mode == t.config.drag_mode.move && (e.start_date = t.roundDate({
                    date: e.start_date,
                    unit: s,
                    step: r
                }), n(e), e.end_date = t.calculateEndDate(e.start_date, e.duration, t.config.duration_unit))
            },
            _fix_working_times: function(e, i) {
                var i = i || {
                    mode: t.config.drag_mode.move
                };
                t.config.work_time && t.config.correct_work_time && (i.mode == t.config.drag_mode.resize ? i.left ? e.start_date = t.getClosestWorkTime({
                    date: e.start_date,
                    dir: "future"
                }) : e.end_date = t.getClosestWorkTime({
                    date: e.end_date,
                    dir: "past"
                }) : i.mode == t.config.drag_mode.move && t.correctTaskWorkTime(e))
            },
            on_mouse_up: function(e) {
                var i = this.drag;
                if (i.mode && i.id) {
                    var n = t.getTask(i.id);
                    if (t.config.work_time && t.config.correct_work_time && this._fix_working_times(n, i), this._fix_dnd_scale_time(n, i), t._init_task_timing(n), this._fireEvent("before_finish", i.mode, [i.id, i.mode, t.copy(i.obj), e])) {
                        var a = i.id;
                        t._init_task_timing(n), this.clear_drag_state(), t.updateTask(n.id), this._fireEvent("after_finish", i.mode, [a, i.mode, e])
                    } else i.obj._dhx_changed = !1, t.mixin(n, i.obj, !0), t.updateTask(n.id)
                }
                this.clear_drag_state()
            },
            _get_drag_mode: function(e) {
                var i = t.config.drag_mode,
                    n = (e || "").split(" "),
                    a = n[0],
                    s = {
                        mode: null,
                        left: null
                    };
                switch (a) {
                    case "gantt_task_line":
                    case "gantt_task_content":
                        s.mode = i.move;
                        break;
                    case "gantt_task_drag":
                        s.mode = i.resize, n[1] && -1 !== n[1].indexOf("left", n[1].length - "left".length) ? s.left = !0 : s.left = !1;
                        break;
                    case "gantt_task_progress_drag":
                        s.mode = i.progress;
                        break;
                    case "gantt_link_control":
                    case "gantt_link_point":
                        s.mode = i.ignore;
                        break;
                    default:
                        s = null
                }
                return s
            },
            _start_dnd: function(e) {
                var i = this.drag = this.drag.start_drag;
                delete i.start_drag;
                var n = t.config,
                    a = i.id;
                n["drag_" + i.mode] && t.callEvent("onBeforeDrag", [a, i.mode, e]) && this._fireEvent("before_start", i.mode, [a, i.mode, e]) ? (delete i.start_drag,
                    t.callEvent("onTaskDragStart", [])) : this.clear_drag_state()
            },
            _fireEvent: function(e, i, n) {
                t.assert(this._events[e], "Invalid stage:{" + e + "}");
                var a = this._events[e][i];
                return t.assert(a, "Unknown after drop mode:{" + i + "}"), t.assert(n, "Invalid event arguments"), t.checkEvent(a) ? t.callEvent(a, n) : !0
            }
        }, t.roundTaskDates = function(e) {
            var i = t._tasks_dnd.drag;
            i || (i = {
                mode: t.config.drag_mode.move
            }), t._tasks_dnd._fix_dnd_scale_time(e, i)
        }, t._render_link = function(e) {
            for (var i = this.getLink(e), n = t._get_link_renderers(), a = 0; a < n.length; a++) n[a].render_item(i);
        }, t._get_link_type = function(e, i) {
            var n = null;
            return e && i ? n = t.config.links.start_to_start : !e && i ? n = t.config.links.finish_to_start : e || i ? e && !i && (n = t.config.links.start_to_finish) : n = t.config.links.finish_to_finish, n
        }, t.isLinkAllowed = function(t, e, i, n) {
            var a = null;
            if (a = "object" == typeof t ? t : {
                    source: t,
                    target: e,
                    type: this._get_link_type(i, n)
                }, !a) return !1;
            if (!(a.source && a.target && a.type)) return !1;
            if (a.source == a.target) return !1;
            var s = !0;
            return this.checkEvent("onLinkValidation") && (s = this.callEvent("onLinkValidation", [a])),
                s
        }, t._render_link_element = function(e) {
            var i = this._path_builder.get_points(e),
                n = t._drawer,
                a = n.get_lines(i),
                s = document.createElement("div"),
                r = "gantt_task_link";
            e.color && (r += " gantt_link_inline_color");
            var o = this.templates.link_class ? this.templates.link_class(e) : "";
            o && (r += " " + o), this.config.highlight_critical_path && this.isCriticalLink && this.isCriticalLink(e) && (r += " gantt_critical_link"), s.className = r, s.setAttribute(t.config.link_attribute, e.id);
            for (var _ = 0; _ < a.length; _++) {
                _ == a.length - 1 && (a[_].size -= t.config.link_arrow_size);
                var d = n.render_line(a[_], a[_ + 1]);
                e.color && (d.firstChild.style.backgroundColor = e.color), s.appendChild(d)
            }
            var l = a[a.length - 1].direction,
                h = t._render_link_arrow(i[i.length - 1], l);
            return e.color && (h.style.borderColor = e.color), s.appendChild(h), s
        }, t._render_link_arrow = function(e, i) {
            var n = document.createElement("div"),
                a = t._drawer,
                s = e.y,
                r = e.x,
                o = t.config.link_arrow_size,
                _ = t.config.row_height,
                d = "gantt_link_arrow gantt_link_arrow_" + i;
            switch (i) {
                case a.dirs.right:
                    s -= (o - _) / 2, r -= o;
                    break;
                case a.dirs.left:
                    s -= (o - _) / 2;
                    break;
                case a.dirs.up:
                    r -= o;
                    break;
                case a.dirs.down:
                    s += 2 * o, r -= o
            }
            return n.style.cssText = ["top:" + s + "px", "left:" + r + "px"].join(";"), n.className = d, n
        }, t._drawer = {
            current_pos: null,
            dirs: {
                left: "left",
                right: "right",
                up: "up",
                down: "down"
            },
            path: [],
            clear: function() {
                this.current_pos = null, this.path = []
            },
            point: function(e) {
                this.current_pos = t.copy(e)
            },
            get_lines: function(t) {
                this.clear(), this.point(t[0]);
                for (var e = 1; e < t.length; e++) this.line_to(t[e]);
                return this.get_path()
            },
            line_to: function(e) {
                var i = t.copy(e),
                    n = this.current_pos,
                    a = this._get_line(n, i);
                this.path.push(a), this.current_pos = i
            },
            get_path: function() {
                return this.path
            },
            get_wrapper_sizes: function(e) {
                var i, n = t.config.link_wrapper_width,
                    a = (t.config.link_line_width, e.y + (t.config.row_height - n) / 2);
                switch (e.direction) {
                    case this.dirs.left:
                        i = {
                            top: a,
                            height: n,
                            lineHeight: n,
                            left: e.x - e.size - n / 2,
                            width: e.size + n
                        };
                        break;
                    case this.dirs.right:
                        i = {
                            top: a,
                            lineHeight: n,
                            height: n,
                            left: e.x - n / 2,
                            width: e.size + n
                        };
                        break;
                    case this.dirs.up:
                        i = {
                            top: a - e.size,
                            lineHeight: e.size + n,
                            height: e.size + n,
                            left: e.x - n / 2,
                            width: n
                        };
                        break;
                    case this.dirs.down:
                        i = {
                            top: a,
                            lineHeight: e.size + n,
                            height: e.size + n,
                            left: e.x - n / 2,
                            width: n
                        }
                }
                return i
            },
            get_line_sizes: function(e) {
                var i, n = t.config.link_line_width,
                    a = t.config.link_wrapper_width,
                    s = e.size + n;
                switch (e.direction) {
                    case this.dirs.left:
                    case this.dirs.right:
                        i = {
                            height: n,
                            width: s,
                            marginTop: (a - n) / 2,
                            marginLeft: (a - n) / 2
                        };
                        break;
                    case this.dirs.up:
                    case this.dirs.down:
                        i = {
                            height: s,
                            width: n,
                            marginTop: (a - n) / 2,
                            marginLeft: (a - n) / 2
                        }
                }
                return i
            },
            render_line: function(t) {
                var e = this.get_wrapper_sizes(t),
                    i = document.createElement("div");
                i.style.cssText = ["top:" + e.top + "px", "left:" + e.left + "px", "height:" + e.height + "px", "width:" + e.width + "px"].join(";"),
                    i.className = "gantt_line_wrapper";
                var n = this.get_line_sizes(t),
                    a = document.createElement("div");
                return a.style.cssText = ["height:" + n.height + "px", "width:" + n.width + "px", "margin-top:" + n.marginTop + "px", "margin-left:" + n.marginLeft + "px"].join(";"), a.className = "gantt_link_line_" + t.direction, i.appendChild(a), i
            },
            _get_line: function(t, e) {
                var i = this.get_direction(t, e),
                    n = {
                        x: t.x,
                        y: t.y,
                        direction: this.get_direction(t, e)
                    };
                return i == this.dirs.left || i == this.dirs.right ? n.size = Math.abs(t.x - e.x) : n.size = Math.abs(t.y - e.y),
                    n
            },
            get_direction: function(t, e) {
                var i = 0;
                return i = e.x < t.x ? this.dirs.left : e.x > t.x ? this.dirs.right : e.y > t.y ? this.dirs.down : this.dirs.up
            }
        }, t._y_from_ind = function(e) {
            return e * t.config.row_height
        }, t._path_builder = {
            path: [],
            clear: function() {
                this.path = []
            },
            current: function() {
                return this.path[this.path.length - 1]
            },
            point: function(e) {
                return e ? (this.path.push(t.copy(e)), e) : this.current()
            },
            point_to: function(e, i, n) {
                n = n ? {
                    x: n.x,
                    y: n.y
                } : t.copy(this.point());
                var a = t._drawer.dirs;
                switch (e) {
                    case a.left:
                        n.x -= i;
                        break;
                    case a.right:
                        n.x += i;
                        break;
                    case a.up:
                        n.y -= i;
                        break;
                    case a.down:
                        n.y += i
                }
                return this.point(n)
            },
            get_points: function(e) {
                var i = this.get_endpoint(e),
                    n = t.config,
                    a = i.e_y - i.y,
                    s = i.e_x - i.x,
                    r = t._drawer.dirs;
                this.clear(), this.point({
                    x: i.x,
                    y: i.y
                });
                var o = 2 * n.link_arrow_size,
                    _ = i.e_x > i.x;
                if (e.type == t.config.links.start_to_start) this.point_to(r.left, o), _ ? (this.point_to(r.down, a), this.point_to(r.right, s)) : (this.point_to(r.right, s), this.point_to(r.down, a)), this.point_to(r.right, o);
                else if (e.type == t.config.links.finish_to_start)
                    if (_ = i.e_x > i.x + 2 * o,
                        this.point_to(r.right, o), _) s -= o, this.point_to(r.down, a), this.point_to(r.right, s);
                    else {
                        s -= 2 * o;
                        var d = a > 0 ? 1 : -1;
                        this.point_to(r.down, d * (n.row_height / 2)), this.point_to(r.right, s), this.point_to(r.down, d * (Math.abs(a) - n.row_height / 2)), this.point_to(r.right, o)
                    } else if (e.type == t.config.links.finish_to_finish) this.point_to(r.right, o), _ ? (this.point_to(r.right, s), this.point_to(r.down, a)) : (this.point_to(r.down, a), this.point_to(r.right, s)), this.point_to(r.left, o);
                else if (e.type == t.config.links.start_to_finish)
                    if (_ = i.e_x > i.x - 2 * o,
                        this.point_to(r.left, o), _) {
                        s += 2 * o;
                        var d = a > 0 ? 1 : -1;
                        this.point_to(r.down, d * (n.row_height / 2)), this.point_to(r.right, s), this.point_to(r.down, d * (Math.abs(a) - n.row_height / 2)), this.point_to(r.left, o)
                    } else s += o, this.point_to(r.down, a), this.point_to(r.right, s);
                return this.path
            },
            get_endpoint: function(e) {
                var i = t.config.links,
                    n = !1,
                    a = !1;
                e.type == i.start_to_start ? n = a = !0 : e.type == i.finish_to_finish ? n = a = !1 : e.type == i.finish_to_start ? (n = !1, a = !0) : e.type == i.start_to_finish ? (n = !0, a = !1) : t.assert(!1, "Invalid link type");
                var s = t._get_task_visible_pos(t._pull[e.source], n),
                    r = t._get_task_visible_pos(t._pull[e.target], a);
                return {
                    x: s.x,
                    e_x: r.x,
                    y: s.y,
                    e_y: r.y
                }
            }
        }, t._init_links_dnd = function() {
            function e(e, i, n) {
                var a = t._get_task_pos(e, !!i);
                return a.y += t._get_task_height() / 2, n = n || 0, a.x += (i ? -1 : 1) * n, a
            }

            function i(e) {
                var i = a(),
                    n = ["gantt_link_tooltip"];
                i.from && i.to && (t.isLinkAllowed(i.from, i.to, i.from_start, i.to_start) ? n.push("gantt_allowed_link") : n.push("gantt_invalid_link"));
                var s = t.templates.drag_link_class(i.from, i.from_start, i.to, i.to_start);
                s && n.push(s);
                var r = "<div class='" + s + "'>" + t.templates.drag_link(i.from, i.from_start, i.to, i.to_start) + "</div>";
                e.innerHTML = r
            }

            function n(t, e) {
                t.style.left = e.x + 5 + "px", t.style.top = e.y + 5 + "px"
            }

            function a() {
                return {
                    from: t._link_source_task,
                    to: t._link_target_task,
                    from_start: t._link_source_task_start,
                    to_start: t._link_target_task_start
                }
            }

            function s() {
                t._link_source_task = t._link_source_task_start = t._link_target_task = null, t._link_target_task_start = !0
            }

            function r(e, i, n, s) {
                var r = d(),
                    l = a(),
                    h = ["gantt_link_direction"];
                t.templates.link_direction_class && h.push(t.templates.link_direction_class(l.from, l.from_start, l.to, l.to_start));
                var c = Math.sqrt(Math.pow(n - e, 2) + Math.pow(s - i, 2));
                if (c = Math.max(0, c - 3)) {
                    r.className = h.join(" ");
                    var u = (s - i) / (n - e),
                        g = Math.atan(u);
                    2 == _(e, n, i, s) ? g += Math.PI : 3 == _(e, n, i, s) && (g -= Math.PI);
                    var f = Math.sin(g),
                        p = Math.cos(g),
                        v = Math.round(i),
                        m = Math.round(e),
                        k = ["-webkit-transform: rotate(" + g + "rad)", "-moz-transform: rotate(" + g + "rad)", "-ms-transform: rotate(" + g + "rad)", "-o-transform: rotate(" + g + "rad)", "transform: rotate(" + g + "rad)", "width:" + Math.round(c) + "px"];
                    if (-1 != window.navigator.userAgent.indexOf("MSIE 8.0")) {
                        k.push('-ms-filter: "' + o(f, p) + '"');
                        var b = Math.abs(Math.round(e - n)),
                            y = Math.abs(Math.round(s - i));
                        switch (_(e, n, i, s)) {
                            case 1:
                                v -= y;
                                break;
                            case 2:
                                m -= b, v -= y;
                                break;
                            case 3:
                                m -= b
                        }
                    }
                    k.push("top:" + v + "px"), k.push("left:" + m + "px"), r.style.cssText = k.join(";")
                }
            }

            function o(t, e) {
                return "progid:DXImageTransform.Microsoft.Matrix(M11 = " + e + ",M12 = -" + t + ",M21 = " + t + ",M22 = " + e + ",SizingMethod = 'auto expand')"
            }

            function _(t, e, i, n) {
                return e >= t ? i >= n ? 1 : 4 : i >= n ? 2 : 3
            }

            function d() {
                return h._direction || (h._direction = document.createElement("div"),
                    t.$task_links.appendChild(h._direction)), h._direction
            }

            function l() {
                h._direction && (h._direction.parentNode && h._direction.parentNode.removeChild(h._direction), h._direction = null)
            }
            var h = new t._DnD(this.$task_bars, {
                    sensitivity: 0,
                    updates_per_second: 60
                }),
                c = "task_left",
                u = "task_right",
                g = "gantt_link_point",
                f = "gantt_link_control";
            h.attachEvent("onBeforeDragStart", t.bind(function(i, n) {
                var a = n.target || n.srcElement;
                if (s(), t.getState().drag_id) return !1;
                if (t._locate_css(a, g)) {
                    t._locate_css(a, c) && (t._link_source_task_start = !0);
                    var r = t._link_source_task = this.locate(n),
                        o = t.getTask(r);
                    if (t._is_readonly(o)) return s(), !1;
                    var _ = 0;
                    return t._get_safe_type(o.type) == t.config.types.milestone && (_ = (t._get_visible_milestone_width() - t._get_milestone_width()) / 2), this._dir_start = e(o, !!t._link_source_task_start, _), !0
                }
                return !1
            }, this)), h.attachEvent("onAfterDragStart", t.bind(function(t, e) {
                i(h.config.marker)
            }, this)), h.attachEvent("onDragMove", t.bind(function(a, s) {
                var o = h.config,
                    _ = h.getPosition(s);
                n(o.marker, _);
                var d = t._is_link_drop_area(s),
                    l = t._link_target_task,
                    c = t._link_landing,
                    g = t._link_target_task_start,
                    p = t.locate(s),
                    v = !0;
                if (d && (v = !t._locate_css(s, u), d = !!p), t._link_target_task = p, t._link_landing = d, t._link_target_task_start = v, d) {
                    var m = t.getTask(p),
                        k = t._locate_css(s, f),
                        b = 0;
                    k && (b = Math.floor(k.offsetWidth / 2)), this._dir_end = e(m, !!t._link_target_task_start, b)
                } else this._dir_end = t._get_mouse_pos(s);
                var y = !(c == d && l == p && g == v);
                return y && (l && t.refreshTask(l, !1), p && t.refreshTask(p, !1)), y && i(o.marker), r(this._dir_start.x, this._dir_start.y, this._dir_end.x, this._dir_end.y), !0
            }, this)), h.attachEvent("onDragEnd", t.bind(function() {
                var e = a();
                if (e.from && e.to && e.from != e.to) {
                    var i = t._get_link_type(e.from_start, e.to_start),
                        n = {
                            source: e.from,
                            target: e.to,
                            type: i
                        };
                    n.type && t.isLinkAllowed(n) && t.addLink(n)
                }
                s(), e.from && t.refreshTask(e.from, !1), e.to && t.refreshTask(e.to, !1), l()
            }, this)), t._is_link_drop_area = function(e) {
                return !!t._locate_css(e, f)
            }
        }, t._get_link_state = function() {
            return {
                link_landing_area: this._link_landing,
                link_target_id: this._link_target_task,
                link_target_start: this._link_target_task_start,
                link_source_id: this._link_source_task,
                link_source_start: this._link_source_task_start
            }
        }, t._task_renderer = function(e, i, n, a) {
            return this._task_area_pulls || (this._task_area_pulls = {}), this._task_area_renderers || (this._task_area_renderers = {}), this._task_area_renderers[e] ? this._task_area_renderers[e] : (i || this.assert(!1, "Invalid renderer call"), n && n.setAttribute(this.config.layer_attribute, !0), this._task_area_renderers[e] = {
                render_item: function(e, s) {
                    if (s = s || n, a && !a(e)) return void this.remove_item(e.id);
                    var r = i.call(t, e);
                    this.append(e, r, s)
                },
                clear: function(i) {
                    this.rendered = t._task_area_pulls[e] = {},
                        this.clear_container(i)
                },
                clear_container: function(t) {
                    t = t || n, t && (t.innerHTML = "")
                },
                render_items: function(t, e) {
                    e = e || n;
                    var i = document.createDocumentFragment();
                    this.clear(e);
                    for (var a = 0, s = t.length; s > a; a++) this.render_item(t[a], i);
                    e.appendChild(i)
                },
                append: function(t, e, i) {
                    e && (this.rendered[t.id] && this.rendered[t.id].parentNode ? this.replace_item(t.id, e) : i.appendChild(e), this.rendered[t.id] = e)
                },
                replace_item: function(t, e) {
                    var i = this.rendered[t];
                    i && i.parentNode && i.parentNode.replaceChild(e, i), this.rendered[t] = e;
                },
                remove_item: function(t) {
                    this.hide(t), delete this.rendered[t]
                },
                hide: function(t) {
                    var e = this.rendered[t];
                    e && e.parentNode && e.parentNode.removeChild(e)
                },
                restore: function(t) {
                    var e = this.rendered[t.id];
                    e ? e.parentNode || this.append(t, e, n) : this.render_item(t, n)
                },
                change_id: function(t, e) {
                    this.rendered[e] = this.rendered[t], delete this.rendered[t]
                },
                rendered: this._task_area_pulls[e],
                node: n,
                unload: function() {
                    this.clear(), delete t._task_area_renderers[e], delete t._task_area_pulls[e]
                }
            }, this._task_area_renderers[e]);
        }, t._clear_renderers = function() {
            for (var t in this._task_area_renderers) this._task_renderer(t).unload()
        }, t._is_layer = function(t) {
            return t && t.hasAttribute && t.hasAttribute(this.config.layer_attribute)
        }, t._init_tasks = function() {
            function e(t, e, i, n) {
                for (var a = 0; a < t.length; a++) t[a].change_id(e, i), t[a].render_item(n)
            }
            this._tasks = {
                col_width: this.config.columnWidth,
                width: [],
                full_width: 0,
                trace_x: [],
                rendered: {}
            }, this._click.gantt_task_link = this.bind(function(e, i) {
                var n = this.locate(e, t.config.link_attribute);
                n && this.callEvent("onLinkClick", [n, e]);
            }, this), this._click.gantt_scale_cell = this.bind(function(e, i) {
                var n = t._get_mouse_pos(e),
                    a = t.dateFromPos(n.x),
                    s = Math.floor(t._day_index_by_date(a)),
                    r = t._tasks.trace_x[s];
                t.callEvent("onScaleClick", [e, r])
            }, this), this._dbl_click.gantt_task_link = this.bind(function(e, i, n) {
                var i = this.locate(e, t.config.link_attribute);
                this._delete_link_handler(i, e)
            }, this), this._dbl_click.gantt_link_point = this.bind(function(e, i, n) {
                var i = this.locate(e),
                    a = this.getTask(i),
                    s = null;
                return n.parentNode && t._getClassName(n.parentNode) && (s = t._getClassName(n.parentNode).indexOf("_left") > -1 ? a.$target[0] : a.$source[0]),
                    s && this._delete_link_handler(s, e), !1
            }, this), this._tasks_dnd.init(), this._init_links_dnd(), this._link_layers.clear();
            var i = this.addLinkLayer({
                renderer: this._render_link_element,
                container: this.$task_links,
                filter: t._create_filter([t._filter_link, t._is_chart_visible].concat(this._get_link_filters()))
            });
            this._linkRenderer = this._link_layers.getRenderer(i), this._task_layers.clear();
            var n = this.addTaskLayer({
                renderer: this._render_task_element,
                container: this.$task_bars,
                filter: t._create_filter([t._filter_task, t._is_chart_visible].concat(this._get_task_filters()))
            });
            this._taskRenderer = this._task_layers.getRenderer(n), this.addTaskLayer({
                renderer: this._render_grid_item,
                container: this.$grid_data,
                filter: t._create_filter([t._filter_task, t._is_grid_visible].concat(this._get_task_filters()))
            }), this.addTaskLayer({
                renderer: this._render_bg_line,
                container: this.$task_bg,
                filter: t._create_filter([t._filter_task, t._is_chart_visible, t._is_std_background].concat(this._get_task_filters()))
            }), this._onTaskIdChange && this.detachEvent(this._onTaskIdChange), this._onTaskIdChange = this.attachEvent("onTaskIdChange", function(t, i) {
                var n = this._get_task_renderers();
                e(n, t, i, this.getTask(i))
            }), this._onLinkIdChange && this.detachEvent(this._onLinkIdChange), this._onLinkIdChange = this.attachEvent("onLinkIdChange", function(t, i) {
                var n = this._get_link_renderers();
                e(n, t, i, this.getLink(i))
            })
        }, t._get_task_filters = function() {
            return []
        }, t._get_link_filters = function() {
            return []
        }, t._is_chart_visible = function() {
            return !!this.config.show_chart
        }, t._filter_task = function(t, e) {
            var i = null,
                n = null;
            return this.config.start_date && this.config.end_date && (i = this.config.start_date.valueOf(),
                n = this.config.end_date.valueOf(), +e.start_date > n || +e.end_date < +i) ? !1 : !0
        }, t._filter_link = function(e, i) {
            return this.config.show_links ? !t.isTaskVisible(i.source) || !t.isTaskVisible(i.target) || t._isAllowedUnscheduledTask(t.getTask(i.source)) || t._isAllowedUnscheduledTask(t.getTask(i.target)) ? !1 : this.callEvent("onBeforeLinkDisplay", [e, i]) : !1
        }, t._is_std_background = function() {
            return !this.config.static_background
        }, t._delete_link_handler = function(e, i) {
            if (e && this.callEvent("onLinkDblClick", [e, i])) {
                var n = t.getLink(e);
                if (t._is_readonly(n)) return;
                var a = "",
                    s = t.locale.labels.link + " " + this.templates.link_description(this.getLink(e)) + " " + t.locale.labels.confirm_link_deleting;
                window.setTimeout(function() {
                    t._dhtmlx_confirm(s, a, function() {
                        t.deleteLink(e)
                    })
                }, t.config.touch ? 300 : 1)
            }
        }, t.getTaskNode = function(t) {
            return this._taskRenderer.rendered[t]
        }, t.getLinkNode = function(t) {
            return this._linkRenderer.rendered[t]
        }, t._get_tasks_data = function() {
            for (var t = [], e = this._get_data_range(), i = 0; i < e.length; i++) {
                var n = this._pull[e[i]];
                n.$index = i,
                    this.resetProjectDates(n), t.push(n)
            }
            return t
        }, t._get_data_range = function() {
            return this._order
        }, t._get_links_data = function() {
            return this._links.slice()
        }, t._render_data = function() {
            if (this.callEvent("onBeforeDataRender", []), this._is_render_active()) {
                this._order_synced ? this._order_synced = !1 : this._sync_order(), this._update_layout_sizes(), this._scroll_resize();
                for (var e = this._get_tasks_data(), i = this._get_task_renderers(), n = 0; n < i.length; n++) i[n].render_items(e);
                var a = t._get_links_data();
                i = this._get_link_renderers();
                for (var n = 0; n < i.length; n++) i[n].render_items(a);
                this.callEvent("onDataRender", [])
            }
        }, t._update_layout_sizes = function() {
            var e = this._tasks;
            e.bar_height = this._get_task_height(), this.$task_data.style.height = Math.max(this.$task.offsetHeight - this.config.scale_height, 0) + "px", t.config.smart_rendering ? this.$task_bg.style.height = t.config.row_height * this.getVisibleTaskCount() + "px" : this.$task_bg.style.height = "", this.$task_bg.style.backgroundImage = "";
            for (var i = this.$task_data.childNodes, n = 0, a = i.length; a > n; n++) {
                var s = i[n];
                this._is_layer(s) && s.style && (s.style.width = e.full_width + "px")
            }
            if (this._is_grid_visible()) {
                for (var r = this.getGridColumns(), o = 0, n = 0; n < r.length; n++) o += r[n].width;
                this.$grid_data.style.width = Math.max(o - 1, 0) + "px"
            }
        }, t._scale_range_unit = function() {
            var t = this.config.scale_unit;
            if (this.config.scale_offset_minimal) {
                var e = this._get_scales();
                t = e[e.length - 1].unit
            }
            return t
        }, t._init_tasks_range = function() {
            var t = this._scale_range_unit();
            if (this.config.start_date && this.config.end_date) {
                this._min_date = this.date[t + "_start"](new Date(this.config.start_date));
                var e = new Date(this.config.end_date),
                    i = this.date[t + "_start"](new Date(e));
                return e = +e != +i ? this.date.add(i, 1, t) : i, void(this._max_date = e)
            }
            this._get_tasks_data();
            var n = this.getSubtaskDates();
            this._min_date = n.start_date, this._max_date = n.end_date, this._max_date && this._max_date || (this._min_date = new Date, this._max_date = new Date(this._min_date)), this._min_date = this.date[t + "_start"](this._min_date), this._min_date = this.calculateEndDate(this.date[t + "_start"](this._min_date), -1, t), this._max_date = this.date[t + "_start"](this._max_date),
                this._max_date = this.calculateEndDate(this._max_date, 2, t)
        }, t._prepare_scale_html = function(e) {
            var i = [],
                n = null,
                a = null,
                s = null;
            (e.template || e.date) && (a = e.template || this.date.date_to_str(e.date)), s = e.css || function() {}, !e.css && this.config.inherit_scale_class && (s = t.templates.scale_cell_class);
            for (var r = 0; r < e.count; r++) {
                n = new Date(e.trace_x[r]);
                var o = a.call(this, n),
                    _ = e.width[r],
                    d = "",
                    l = "",
                    h = "";
                if (_) {
                    d = "width:" + _ + "px;", h = "gantt_scale_cell" + (r == e.count - 1 ? " gantt_last_cell" : ""), l = s.call(this, n), l && (h += " " + l);
                    var c = "<div class='" + h + "' style='" + d + "'>" + o + "</div>";
                    i.push(c)
                }
            }
            return i.join("")
        }, t._get_scales = function() {
            var t = this._scale_helpers,
                e = [t.primaryScale()].concat(this.config.subscales);
            return t.sortScales(e), e
        }, t._render_tasks_scales = function() {
            this._init_tasks_range(), this._scroll_resize(), this._set_sizes();
            var t = "",
                e = 0,
                i = 0,
                n = 0;
            if (this._is_chart_visible()) {
                var a = this._scale_helpers,
                    s = this._get_scales();
                n = this.config.scale_height - 1;
                for (var r = this._get_resize_options(), o = r.x ? Math.max(this.config.autosize_min_width, 0) : this.$task.offsetWidth, _ = a.prepareConfigs(s, this.config.min_column_width, o, n), d = this._tasks = _[_.length - 1], l = [], h = this.templates.scale_row_class, c = 0; c < _.length; c++) {
                    var u = "gantt_scale_line",
                        g = h(_[c]);
                    g && (u += " " + g), l.push('<div class="' + u + '" style="height:' + _[c].height + "px;line-height:" + _[c].height + 'px">' + this._prepare_scale_html(_[c]) + "</div>")
                }
                t = l.join(""), e = d.full_width + this.$scroll_ver.offsetWidth + "px", i = d.full_width + "px", n += "px"
            }
            this._is_chart_visible() ? this.$task.style.display = "" : this.$task.style.display = "none", this.$task_scale.style.height = n, this.$task_data.style.width = this.$task_scale.style.width = e, this.$task_scale.innerHTML = t
        }, t._render_bg_line = function(e) {
            var i = t._tasks,
                n = i.count,
                a = document.createElement("div");
            if (t.config.show_task_cells)
                for (var s = 0; n > s; s++) {
                    var r = i.width[s],
                        o = "";
                    if (r > 0) {
                        var _ = document.createElement("div");
                        _.style.width = r + "px", o = "gantt_task_cell" + (s == n - 1 ? " gantt_last_cell" : ""), l = this.templates.task_cell_class(e, i.trace_x[s]), l && (o += " " + l), _.className = o, a.appendChild(_)
                    }
                }
            var d = e.$index % 2 !== 0,
                l = t.templates.task_row_class(e.start_date, e.end_date, e),
                h = "gantt_task_row" + (d ? " odd" : "") + (l ? " " + l : "");
            return this.getState().selected_task == e.id && (h += " gantt_selected"),
                a.className = h, t.config.smart_rendering && (a.style.position = "absolute", a.style.top = this.getTaskTop(e.id) + "px", a.style.width = "100%"), a.style.height = t.config.row_height + "px", a.setAttribute(this.config.task_attribute, e.id), a
        }, t._adjust_scales = function() {
            if (this.config.fit_tasks) {
                var t = +this._min_date,
                    e = +this._max_date;
                if (this._init_tasks_range(), +this._min_date != t || +this._max_date != e) return this.render(), this.callEvent("onScaleAdjusted", []), !0
            }
            return !1
        }, t.refreshTask = function(e, i) {
            if (this._is_render_active()) {
                var n = this._get_task_renderers(),
                    a = this.getTask(e);
                if (a && this.isTaskVisible(e)) {
                    for (var s = 0; s < n.length; s++) n[s].render_item(a);
                    if (void 0 !== i && !i) return;
                    for (var s = 0; s < a.$source.length; s++) t.refreshLink(a.$source[s]);
                    for (var s = 0; s < a.$target.length; s++) t.refreshLink(a.$target[s])
                }
            }
        }, t.refreshLink = function(t) {
            if (this._is_render_active())
                if (this.isLinkExists(t)) this._render_link(t);
                else
                    for (var e = this._get_link_renderers(), i = 0; i < e.length; i++) e[i].remove_item(t)
        }, t._combine_item_class = function(e, i, n) {
            var a = [e];
            i && a.push(i);
            var s = t.getState(),
                r = this.getTask(n);
            this._get_safe_type(r.type) == this.config.types.milestone && a.push("gantt_milestone"), this._get_safe_type(r.type) == this.config.types.project && a.push("gantt_project"), this._is_flex_task(r) && a.push("gantt_dependent_task"), this.config.select_task && n == s.selected_task && a.push("gantt_selected"), n == s.drag_id && (a.push("gantt_drag_" + s.drag_mode), s.touch_drag && a.push("gantt_touch_" + s.drag_mode));
            var o = t._get_link_state();
            if (o.link_source_id == n && a.push("gantt_link_source"),
                o.link_target_id == n && a.push("gantt_link_target"), this.config.highlight_critical_path && this.isCriticalTask && this.isCriticalTask(r) && a.push("gantt_critical_task"), o.link_landing_area && o.link_target_id && o.link_source_id && o.link_target_id != o.link_source_id) {
                var _ = o.link_source_id,
                    d = o.link_source_start,
                    l = o.link_target_start,
                    h = t.isLinkAllowed(_, n, d, l),
                    c = "";
                c = h ? l ? "link_start_allow" : "link_finish_allow" : l ? "link_start_deny" : "link_finish_deny", a.push(c)
            }
            return a.join(" ")
        }, t._render_pair = function(e, i, n, a) {
            var s = t.getState(); + n.end_date <= +s.max_date && e.appendChild(a(i + " task_right")), +n.start_date >= +s.min_date && e.appendChild(a(i + " task_left"))
        }, t._get_task_height = function() {
            var t = this.config.task_height;
            return "full" == t && (t = this.config.row_height - 5), t = Math.min(t, this.config.row_height), Math.max(t, 0)
        }, t._get_milestone_width = function() {
            return this._get_task_height()
        }, t._get_visible_milestone_width = function() {
            var e = t._get_task_height();
            return Math.sqrt(2 * e * e)
        }, t.getTaskPosition = function(e, i, n) {
            var a = this.posFromDate(i || e.start_date),
                s = this.posFromDate(n || e.end_date);
            s = Math.max(a, s);
            var r = this.getTaskTop(e.id),
                o = t._get_task_height();
            return {
                left: a,
                top: r,
                height: o,
                width: Math.max(s - a, 0)
            }
        }, t._get_task_width = function(t, e, i) {
            return Math.round(this._get_task_pos(t, !1).x - this._get_task_pos(t, !0).x)
        }, t._is_readonly = function(t) {
            return t && t[this.config.editable_property] ? !1 : t && t[this.config.readonly_property] || this.config.readonly
        }, t._task_default_render = function(e) {
            if (!this._isAllowedUnscheduledTask(e)) {
                var i = this._get_task_pos(e),
                    n = this.config,
                    a = this._get_task_height(),
                    s = Math.floor((this.config.row_height - a) / 2);
                this._get_safe_type(e.type) == n.types.milestone && n.link_line_width > 1 && (s += 1);
                var r = document.createElement("div"),
                    o = t._get_task_width(e),
                    _ = this._get_safe_type(e.type);
                r.setAttribute(this.config.task_attribute, e.id), n.show_progress && _ != this.config.types.milestone && this._render_task_progress(e, r, o);
                var d = t._render_task_content(e, o);
                e.textColor && (d.style.color = e.textColor), r.appendChild(d);
                var l = this._combine_item_class("gantt_task_line", this.templates.task_class(e.start_date, e.end_date, e), e.id);
                (e.color || e.progressColor || e.textColor) && (l += " gantt_task_inline_color"),
                r.className = l;
                var h = ["left:" + i.x + "px", "top:" + (s + i.y) + "px", "height:" + a + "px", "line-height:" + a + "px", "width:" + o + "px"];
                e.color && h.push("background-color:" + e.color), e.textColor && h.push("color:" + e.textColor), r.style.cssText = h.join(";");
                var c = this._render_leftside_content(e);
                return c && r.appendChild(c), c = this._render_rightside_content(e), c && r.appendChild(c), this._is_readonly(e) || (n.drag_resize && !this._is_flex_task(e) && _ != this.config.types.milestone && t._render_pair(r, "gantt_task_drag", e, function(t) {
                    var e = document.createElement("div");
                    return e.className = t, e
                }), n.drag_links && this.config.show_links && t._render_pair(r, "gantt_link_control", e, function(t) {
                    var e = document.createElement("div");
                    e.className = t, e.style.cssText = ["height:" + a + "px", "line-height:" + a + "px"].join(";");
                    var i = document.createElement("div");
                    return i.className = "gantt_link_point", e.appendChild(i), e
                })), r
            }
        }, t._render_task_element = function(t) {
            var e = this.config.type_renderers,
                i = e[this._get_safe_type(t.type)],
                n = this._task_default_render;
            return i || (i = n), i.call(this, t, this.bind(n, this));
        }, t._render_side_content = function(t, e, i) {
            if (!e) return null;
            var n = e(t.start_date, t.end_date, t);
            if (!n) return null;
            var a = document.createElement("div");
            return a.className = "gantt_side_content " + i, a.innerHTML = n, a
        }, t._render_leftside_content = function(e) {
            var i = "gantt_left " + t._get_link_crossing_css(!0, e);
            return t._render_side_content(e, this.templates.leftside_text, i)
        }, t._render_rightside_content = function(e) {
            var i = "gantt_right " + t._get_link_crossing_css(!1, e);
            return t._render_side_content(e, this.templates.rightside_text, i);
        }, t._get_conditions = function(e) {
            return e ? {
                $source: [t.config.links.start_to_start],
                $target: [t.config.links.start_to_start, t.config.links.finish_to_start]
            } : {
                $source: [t.config.links.finish_to_start, t.config.links.finish_to_finish],
                $target: [t.config.links.finish_to_finish]
            }
        }, t._get_link_crossing_css = function(e, i) {
            var n = t._get_conditions(e);
            for (var a in n)
                for (var s = i[a], r = 0; r < s.length; r++)
                    for (var o = t.getLink(s[r]), _ = 0; _ < n[a].length; _++)
                        if (o.type == n[a][_]) return "gantt_link_crossing";
            return ""
        }, t._render_task_content = function(t, e) {
            var i = document.createElement("div");
            return this._get_safe_type(t.type) != this.config.types.milestone && (i.innerHTML = this.templates.task_text(t.start_date, t.end_date, t)), i.className = "gantt_task_content", i
        }, t._render_task_progress = function(e, i, n) {
            var a = 1 * e.progress || 0;
            n = Math.max(n - 2, 0);
            var s = document.createElement("div"),
                r = Math.round(n * a);
            if (r = Math.min(n, r), e.progressColor && (s.style.backgroundColor = e.progressColor, s.style.opacity = 1), s.style.width = r + "px", s.className = "gantt_task_progress", s.innerHTML = this.templates.progress_text(e.start_date, e.end_date, e),
                i.appendChild(s), this.config.drag_progress && !t._is_readonly(e)) {
                var o = document.createElement("div");
                o.style.left = r + "px", o.className = "gantt_task_progress_drag", s.appendChild(o), i.appendChild(o)
            }
        }, t._get_line = function(t) {
            var e = {
                second: 1,
                minute: 60,
                hour: 3600,
                day: 86400,
                week: 604800,
                month: 2592e3,
                year: 31536e3
            };
            return e[t] || 0
        }, t.dateFromPos = function(e) {
            var i = this._tasks;
            if (0 > e || e > i.full_width || !i.full_width) return null;
            var n = this._findBinary(this._tasks.left, e),
                a = this._tasks.left[n],
                s = i.width[n] || i.col_width,
                r = 0;
            s && (r = (e - a) / s);
            var o = 0;
            r && (o = t._get_coll_duration(i, i.trace_x[n]));
            var _ = new Date(i.trace_x[n].valueOf() + Math.round(r * o));
            return _
        }, t.posFromDate = function(e) {
            var i = t._day_index_by_date(e);
            this.assert(i >= 0, "Invalid day index");
            var n = Math.floor(i),
                a = i % 1,
                s = t._tasks.left[Math.min(n, t._tasks.width.length - 1)];
            return n == t._tasks.width.length && (s += t._tasks.width[t._tasks.width.length - 1]), a && (s += n < t._tasks.width.length ? t._tasks.width[n] * (a % 1) : 1), s
        }, t._day_index_by_date = function(e) {
            var i = new Date(e).valueOf(),
                n = t._tasks.trace_x,
                a = t._tasks.ignore_x;
            if (i <= this._min_date) return 0;
            if (i >= this._max_date) return n.length;
            for (var s = t._findBinary(n, i), r = +t._tasks.trace_x[s]; a[r];) r = t._tasks.trace_x[++s];
            return r ? s + (e - n[s]) / t._get_coll_duration(t._tasks, n[s]) : 0
        }, t._findBinary = function(t, e) {
            for (var i, n, a, s = 0, r = t.length - 1; r >= s;)
                if (i = Math.floor((s + r) / 2), n = +t[i], a = +t[i - 1], e > n) s = i + 1;
                else {
                    if (!(n > e)) return i;
                    if (!isNaN(a) && e > a) return i - 1;
                    r = i - 1
                }
            return t.length - 1
        }, t._get_coll_duration = function(e, i) {
            return t.date.add(i, e.step, e.unit) - i
        }, t._get_x_pos = function(e, i) {
            i = i !== !1;
            t.posFromDate(i ? e.start_date : e.end_date)
        }, t.getTaskTop = function(t) {
            return this._y_from_ind(this.getGlobalTaskIndex(t))
        }, t._get_task_coord = function(t, e, i) {
            e = e !== !1, i = i || 0;
            var n = this._get_safe_type(t.type) == this.config.types.milestone,
                a = null;
            a = e || n ? t.start_date || this._default_task_date(t) : t.end_date || this.calculateEndDate(this._default_task_date(t));
            var s = this.posFromDate(a),
                r = this.getTaskTop(t.id);
            return n && (e ? s -= i : s += i), {
                x: s,
                y: r
            }
        }, t._get_task_pos = function(e, i) {
            i = i !== !1;
            var n = t._get_milestone_width() / 2;
            return this._get_task_coord(e, i, n)
        }, t._get_task_visible_pos = function(e, i) {
            i = i !== !1;
            var n = t._get_visible_milestone_width() / 2;
            return this._get_task_coord(e, i, n)
        }, t._correct_shift = function(e, i) {
            return e -= 6e4 * (new Date(t._min_date).getTimezoneOffset() - new Date(e).getTimezoneOffset()) * (i ? -1 : 1)
        }, t._get_mouse_pos = function(e) {
            if (e.pageX || e.pageY) var i = {
                x: e.pageX,
                y: e.pageY
            };
            var n = t.env.isIE ? document.documentElement : document.body,
                i = {
                    x: e.clientX + n.scrollLeft - n.clientLeft,
                    y: e.clientY + n.scrollTop - n.clientTop
                },
                a = t._get_position(t.$task_data);
            return i.x = i.x - a.x + t.$task_data.scrollLeft, i.y = i.y - a.y + t.$task_data.scrollTop, i
        }, t._is_layer = function(t) {
            return t && t.hasAttribute && t.hasAttribute(this.config.layer_attribute)
        }, t.attachEvent("onDataRender", function() {
            t._render_bg_canvas()
        }), t._render_bg_canvas = function() {
            function e() {
                for (var e = t._tasks.width, i = {}, n = 0; n < e.length; n++) 1 * e[n] && (i[e[n]] = !0);
                return i
            }

            function i(e, i) {
                var n = t.config.row_height,
                    a = document.createElement("canvas");
                a.height = n, a.width = e;
                var s = a.getContext("2d");
                s.beginPath();
                var r = i.bottomBorderWidth;
                s.moveTo(0, n), s.lineTo(e, n), s.lineWidth = r, s.strokeStyle = i.bottomBorderColor || "#ebebeb", s.stroke(), s.beginPath();
                var o = i.rightBorderWidth;
                return s.moveTo(e, n), s.lineTo(e, 0), s.lineWidth = o, s.strokeStyle = i.rightBorderColor || "#ebebeb", s.stroke(), a.toDataURL()
            }

            function n(t) {
                var n = {},
                    a = e();
                for (var s in a) n[s] = i(1 * s, t);
                return n
            }

            function a(e) {
                for (var i, n, a = [], s = 0, r = t._tasks.width.filter(function(t) {
                        return !!t
                    }), o = 0; o < r.length; o++) {
                    var _ = r[o];
                    if (_ != n && void 0 !== n || o == r.length - 1) {
                        i = document.createElement("div"),
                            i.style.height = t.config.row_height * t._order.length + "px", i.style.cssFloat = "left", i.style.whiteSpace = "no-wrap", i.style.backgroundImage = "url(" + e[n || _] + ")";
                        var d = s;
                        o == r.length - 1 && (d = _ + d - 1), i.style.width = d + "px", s = 0, a.push(i)
                    }
                    _ && (s += _, n = _)
                }
                return a
            }

            function s() {
                var e = document.createElement("div");
                e.className = "gantt_task_cell";
                var i = document.createElement("div");
                i.className = "gantt_task_row", i.appendChild(e), t.$task_bg.appendChild(i);
                var n = getComputedStyle(i),
                    a = getComputedStyle(e),
                    s = {
                        bottomBorderWidth: n.getPropertyValue("border-bottom-width").replace("px", ""),
                        rightBorderWidth: a.getPropertyValue("border-right-width").replace("px", ""),
                        bottomBorderColor: n.getPropertyValue("border-bottom-color"),
                        rightBorderColor: a.getPropertyValue("border-right-color")
                    };
                return t.$task_bg.removeChild(i), s
            }
            if (t.config.static_background) {
                var r = document.createElement("canvas");
                if (r.getContext) {
                    t.$task_bg.innerHTML = "";
                    var o = s(),
                        _ = n(o),
                        d = a(_);
                    d.forEach(function(e) {
                        t.$task_bg.appendChild(e)
                    })
                }
            }
        }, t.attachEvent("onGanttReady", function() {
            t._task_layers.add(), t._link_layers.add()
        }),
        t._layers = {
            prepareConfig: function(e) {
                "function" == typeof e && (e = {
                    renderer: e
                });
                e.id = t.uid();
                return e.container || (e.container = document.createElement("div")), e
            },
            create: function(e, i) {
                return {
                    tempCollection: [],
                    renderers: {},
                    container: e,
                    getRenderers: function() {
                        var t = [];
                        for (var e in this.renderers) t.push(this.renderers[e]);
                        return t
                    },
                    getRenderer: function(t) {
                        return this.renderers[t]
                    },
                    add: function(e) {
                        if (e && this.tempCollection.push(e), this.container())
                            for (var n = this.container(), a = this.tempCollection, s = 0; s < a.length; s++) {
                                var e = a[s],
                                    r = e.container,
                                    o = e.id,
                                    _ = e.topmost;
                                if (!r.parentNode)
                                    if (_) n.appendChild(r);
                                    else {
                                        var d = i ? i() : n.firstChild;
                                        d ? n.insertBefore(r, d) : n.appendChild(r)
                                    }
                                this.renderers[o] = t._task_renderer(o, e.renderer, r, e.filter), this.tempCollection.splice(s, 1), s--
                            }
                    },
                    remove: function(t) {
                        this.renderers[t].unload(), delete this.renderers[t]
                    },
                    clear: function() {
                        for (var t in this.renderers) this.renderers[t].unload();
                        this.renderers = {}
                    }
                }
            }
        }, t._create_filter = function(e) {
            return e instanceof Array || (e = Array.prototype.slice.call(arguments, 0)),
                function(i) {
                    for (var n = !0, a = 0, s = e.length; s > a; a++) {
                        var r = e[a];
                        r && (n = n && r.apply(t, [i.id, i]) !== !1)
                    }
                    return n
                }
        }, t._add_generic_layer = function(e, i) {
            return function(n) {
                return void 0 === n.filter && (n.filter = t._create_filter(i)), n = t._layers.prepareConfig(n), e.add(n), n.id
            }
        }, t._task_layers = t._layers.create(function() {
            return t.$task_data
        }, function() {
            return t.$task_links
        }), t._link_layers = t._layers.create(function() {
            return t.$task_data
        }), t.addTaskLayer = t._add_generic_layer(t._task_layers, [t._filter_task, t._is_chart_visible].concat(t._get_task_filters())),
        t.removeTaskLayer = function(e) {
            t._task_layers.remove(e)
        }, t.addLinkLayer = t._add_generic_layer(t._link_layers, [t._filter_link, t._is_chart_visible].concat(t._get_link_filters())), t.removeLinkLayer = function(e) {
            t._link_layers.remove(e)
        }, t._get_task_renderers = function() {
            return this._task_layers.getRenderers()
        }, t._get_link_renderers = function() {
            return this._link_layers.getRenderers()
        }, t._pull = {}, t._branches = {}, t._order = [], t._lpull = {}, t._links = [], t._order_full = [], t.load = function(e, i, n) {
            this._load_url = e, this.assert(arguments.length, "Invalid load arguments"),
                this.callEvent("onLoadStart", []);
            var a = "json",
                s = null;
            arguments.length >= 3 ? (a = i, s = n) : "string" == typeof arguments[1] ? a = arguments[1] : "function" == typeof arguments[1] && (s = arguments[1]), this._load_type = a, this.ajax.get(e, t.bind(function(t) {
                this.on_load(t, a), this.callEvent("onLoadEnd", []), "function" == typeof s && s.call(this)
            }, this))
        }, t.parse = function(t, e) {
            this.on_load({
                xmlDoc: {
                    responseText: t
                }
            }, e)
        }, t.serialize = function(t) {
            return t = t || "json", this[t].serialize()
        }, t.on_load = function(t, e) {
            this.callEvent("onBeforeParse", []),
                e || (e = "json"), this.assert(this[e], "Invalid data type:'" + e + "'");
            var i = t.xmlDoc.responseText,
                n = this[e].parse(i, t);
            this._process_loading(n)
        }, t._load_task = function(t) {
            return this._init_task(t), this.callEvent("onTaskLoading", [t]) ? (this._pull[t.id] = t, !0) : !1
        }, t._build_pull = function(t) {
            for (var e = null, i = [], n = 0, a = t.length; a > n; n++) e = t[n], this._load_task(e) && i.push(e);
            return i
        }, t._build_hierarchy = function(t) {
            for (var e = null, i = 0, n = t.length; n > i; i++) e = t[i], this.setParent(e, this.getParent(e) || this.config.root_id);
            for (var i = 0, n = t.length; n > i; i++) e = t[i], this._add_branch(e), e.$level = this.calculateTaskLevel(e)
        }, t._process_loading = function(t) {
            t.collections && this._load_collections(t.collections);
            var e = this._build_pull(t.data);
            if (this._build_hierarchy(e), this._sync_order(), this._order_synced = !0, this._init_links(t.links || (t.collections ? t.collections.links : [])), this.callEvent("onParse", []), this.render(), this.config.initial_scroll) {
                var i = this._order[0] || this.config.root_id;
                i && this.showTask(i)
            }
        }, t._init_links = function(t) {
            if (t)
                for (var e = 0; e < t.length; e++)
                    if (t[e]) {
                        var i = this._init_link(t[e]);
                        this._lpull[i.id] = i
                    }
            this._sync_links()
        }, t._load_collections = function(t) {
            var e = !1;
            for (var i in t)
                if (t.hasOwnProperty(i)) {
                    e = !0;
                    var n = t[i],
                        a = this.serverList[i];
                    if (!a) continue;
                    a.splice(0, a.length);
                    for (var s = 0; s < n.length; s++) {
                        var r = n[s],
                            o = this.copy(r);
                        o.key = o.value;
                        for (var _ in r)
                            if (r.hasOwnProperty(_)) {
                                if ("value" == _ || "label" == _) continue;
                                o[_] = r[_]
                            }
                        a.push(o)
                    }
                }
            e && this.callEvent("onOptionsLoad", [])
        }, t._sync_order = function(t) {
            this._order = [],
                this._order_full = [], this._order_search = {}, this._sync_order_item({
                    parent: this.config.root_id,
                    $open: !0,
                    $ignore: !0,
                    id: this.config.root_id
                }), t || (this._scroll_resize(), this._set_sizes())
        }, t.attachEvent("onBeforeTaskDisplay", function(t, e) {
            return !e.$ignore
        }), t._sync_order_item = function(t, e) {
            t.id && (this._order_full.push(t.id), !e && this._filter_task(t.id, t) && this.callEvent("onBeforeTaskDisplay", [t.id, t]) && (this._order.push(t.id), this._order_search[t.id] = this._order.length - 1));
            var i = this.getChildren(t.id);
            if (i)
                for (var n = 0; n < i.length; n++) this._sync_order_item(this._pull[i[n]], e || !t.$open);
        }, t.getTaskCount = function() {
            return this._order_full.length
        }, t.getLinkCount = function() {
            return this._links.length
        }, t.getVisibleTaskCount = function() {
            return this._order.length
        }, t.getTaskIndex = function(t) {
            for (var e = this.getChildren(this.getParent(t)), i = 0; i < e.length; i++)
                if (e[i] == t) return i;
            return -1
        }, t.getGlobalTaskIndex = function(t) {
            this.assert(t, "Invalid argument");
            var e = this._order_search[t];
            return void 0 !== e ? e : -1
        }, t._get_visible_order = t.getGlobalTaskIndex, t.eachTask = function(t, e, i) {
            e = e || this.config.root_id,
                i = i || this;
            var n = this.getChildren(e);
            if (n)
                for (var a = 0; a < n.length; a++) {
                    var s = this._pull[n[a]];
                    t.call(i, s), this.hasChild(s.id) && this.eachTask(t, s.id, i)
                }
        }, t.json = {
            parse: function(e) {
                return t.assert(e, "Invalid data"), "string" == typeof e && (window.JSON ? e = JSON.parse(e) : t.assert(!1, "JSON is not supported")), e.dhx_security && (t.security_key = e.dhx_security), e
            },
            _copyLink: function(t) {
                var e = {};
                for (var i in t) e[i] = t[i];
                return e
            },
            _copyObject: function(e) {
                var i = {};
                for (var n in e) "$" != n.charAt(0) && (i[n] = e[n], i[n] instanceof Date && (i[n] = t.templates.xml_format(i[n])));
                return i
            },
            serialize: function() {
                var e = [],
                    i = [];
                return t.eachTask(function(i) {
                    t.resetProjectDates(i), e.push(this._copyObject(i))
                }, t.config.root_id, this), i = t._links.slice(), {
                    data: e,
                    links: i
                }
            }
        }, t.xml = {
            _xmlNodeToJSON: function(t, e) {
                for (var i = {}, n = 0; n < t.attributes.length; n++) i[t.attributes[n].name] = t.attributes[n].value;
                if (!e) {
                    for (var n = 0; n < t.childNodes.length; n++) {
                        var a = t.childNodes[n];
                        1 == a.nodeType && (i[a.tagName] = a.firstChild ? a.firstChild.nodeValue : "")
                    }
                    i.text || (i.text = t.firstChild ? t.firstChild.nodeValue : "");
                }
                return i
            },
            _getCollections: function(e) {
                for (var i = {}, n = t.ajax.xpath("//coll_options", e), a = 0; a < n.length; a++)
                    for (var s = n[a].getAttribute("for"), r = i[s] = [], o = t.ajax.xpath(".//item", n[a]), _ = 0; _ < o.length; _++) {
                        for (var d = o[_], l = d.attributes, h = {
                                key: o[_].getAttribute("value"),
                                label: o[_].getAttribute("label")
                            }, c = 0; c < l.length; c++) {
                            var u = l[c];
                            "value" != u.nodeName && "label" != u.nodeName && (h[u.nodeName] = u.nodeValue)
                        }
                        r.push(h)
                    }
                return i
            },
            _getXML: function(e, i, n) {
                n = n || "data", i.getXMLTopNode || (i = t.ajax.parse(i));
                var a = t.ajax.xmltop(n, i.xmlDoc);
                if (a.tagName != n) throw "Invalid XML data";
                var s = a.getAttribute("dhx_security");
                return s && (t.security_key = s), a
            },
            parse: function(e, i) {
                i = this._getXML(e, i);
                for (var n = {}, a = n.data = [], s = t.ajax.xpath("//task", i), r = 0; r < s.length; r++) a[r] = this._xmlNodeToJSON(s[r]);
                return n.collections = this._getCollections(i), n
            },
            _copyLink: function(t) {
                return "<item id='" + t.id + "' source='" + t.source + "' target='" + t.target + "' type='" + t.type + "' />"
            },
            _copyObject: function(t) {
                return "<task id='" + t.id + "' parent='" + (t.parent || "") + "' start_date='" + t.start_date + "' duration='" + t.duration + "' open='" + !!t.open + "' progress='" + t.progress + "' end_date='" + t.end_date + "'><![CDATA[" + t.text + "]]></task>";
            },
            serialize: function() {
                for (var e = [], i = [], n = t.json.serialize(), a = 0, s = n.data.length; s > a; a++) e.push(this._copyObject(n.data[a]));
                for (var a = 0, s = n.links.length; s > a; a++) i.push(this._copyLink(n.links[a]));
                return "<data>" + e.join("") + "<coll_options for='links'>" + i.join("") + "</coll_options></data>"
            }
        }, t.oldxml = {
            parse: function(e, i) {
                i = t.xml._getXML(e, i, "projects");
                for (var n = {
                        collections: {
                            links: []
                        }
                    }, a = n.data = [], s = t.ajax.xpath("//task", i), r = 0; r < s.length; r++) {
                    a[r] = t.xml._xmlNodeToJSON(s[r]);
                    var o = s[r].parentNode;
                    "project" == o.tagName ? a[r].parent = "project-" + o.getAttribute("id") : a[r].parent = o.parentNode.getAttribute("id");
                }
                s = t.ajax.xpath("//project", i);
                for (var r = 0; r < s.length; r++) {
                    var _ = t.xml._xmlNodeToJSON(s[r], !0);
                    _.id = "project-" + _.id, a.push(_)
                }
                for (var r = 0; r < a.length; r++) {
                    var _ = a[r];
                    _.start_date = _.startdate || _.est, _.end_date = _.enddate, _.text = _.name, _.duration = _.duration / 8, _.open = 1, _.duration || _.end_date || (_.duration = 1), _.predecessortasks && n.collections.links.push({
                        target: _.id,
                        source: _.predecessortasks,
                        type: t.config.links.finish_to_start
                    })
                }
                return n
            },
            serialize: function() {
                t.message("Serialization to 'old XML' is not implemented");
            }
        }, t.serverList = function(t, e) {
            return e ? this.serverList[t] = e.slice(0) : this.serverList[t] || (this.serverList[t] = []), this.serverList[t]
        }, t._working_time_helper = {
            units: ["year", "month", "week", "day", "hour", "minute"],
            hours: [8, 17],
            dates: {
                0: !1,
                6: !1
            },
            _working_units_cache: {
                _cache: {},
                get: function(t, e) {
                    var i = -1,
                        n = this._cache;
                    if (n && n[t]) {
                        var a = n[t],
                            s = e.getTime();
                        void 0 !== a[s] && (i = a[s])
                    }
                    return i
                },
                put: function(t, e, i) {
                    if (!t || !e) return !1;
                    var n = this._cache,
                        a = e.getTime();
                    return i = !!i, n ? (n[t] || (n[t] = {}), n[t][a] = i, !0) : !1;
                },
                clear: function() {
                    this._cache = {}
                }
            },
            _get_unit_order: function(e) {
                for (var i = 0, n = this.units.length; n > i; i++)
                    if (this.units[i] == e) return i;
                t.assert(!1, "Incorrect duration unit")
            },
            _timestamp: function(e) {
                var i = null;
                return e.day || 0 === e.day ? i = e.day : e.date && (i = t.date.date_part(new Date(e.date)).valueOf()), i
            },
            set_time: function(t) {
                var e = void 0 !== t.hours ? t.hours : !0,
                    i = this._timestamp(t);
                null !== i ? this.dates[i] = e : this.hours = e, this._working_units_cache.clear()
            },
            unset_time: function(t) {
                if (t) {
                    var e = this._timestamp(t);
                    null !== e && delete this.dates[e]
                } else this.hours = [];
                this._working_units_cache.clear()
            },
            is_working_unit: function(e, i, n) {
                if (!t.config.work_time) return !0;
                var a = this._working_units_cache.get(i, e);
                return -1 == a && (a = this._check_is_working_unit(e, i, n), this._working_units_cache.put(i, e, a)), a
            },
            _check_is_working_unit: function(t, e, i) {
                return void 0 === i && (i = this._get_unit_order(e)), void 0 === i ? !1 : i && !this.is_working_unit(t, this.units[i - 1], i - 1) ? !1 : this["is_work_" + e] ? this["is_work_" + e](t) : !0
            },
            is_work_day: function(t) {
                var e = this.get_working_hours(t);
                return e instanceof Array ? e.length > 0 : !1
            },
            is_work_hour: function(t) {
                for (var e = this.get_working_hours(t), i = t.getHours(), n = 0; n < e.length; n += 2) {
                    if (void 0 === e[n + 1]) return e[n] == i;
                    if (i >= e[n] && i < e[n + 1]) return !0
                }
                return !1
            },
            get_working_hours: function(t) {
                var e = this._timestamp({
                        date: t
                    }),
                    i = !0;
                return void 0 !== this.dates[e] ? i = this.dates[e] : void 0 !== this.dates[t.getDay()] && (i = this.dates[t.getDay()]), i === !0 ? this.hours : i ? i : []
            },
            intern_dates_pull: {},
            next_date: function(e, i, n) {
                var a = +e,
                    s = i + "_" + n,
                    r = this.intern_dates_pull[s];
                return r || (r = this.intern_dates_pull[s] = {}), r[a] || (r[a] = t.date.add(e, n, i)), r[a]
            },
            get_work_units_between: function(t, e, i, n) {
                if (!i) return !1;
                for (var a = new Date(t), s = new Date(e), n = n || 1, r = 0; a.valueOf() < s.valueOf();) this.is_working_unit(a, i) && r++, a = this.next_date(a, i, n);
                return r
            },
            is_work_units_between: function(t, e, i, n) {
                if (!i) return !1;
                for (var a = new Date(t), s = new Date(e), n = n || 1; a.valueOf() < s.valueOf();) {
                    if (this.is_working_unit(a, i)) return !0;
                    a = this.next_date(a, i, n)
                }
                return !1
            },
            add_worktime: function(e, i, n, a) {
                if (!n) return !1;
                var s = new Date(e),
                    r = 0,
                    a = a || 1,
                    i = 1 * i;
                if (t.config.work_time) {
                    for (; i > r;) {
                        var o = this.next_date(s, n, a);
                        this.is_working_unit(a > 0 ? new Date(o.valueOf() - 1) : new Date(o.valueOf() + 1), n) && r++, s = o
                    }
                    return s
                }
                return t.date.add(s, a * i, n)
            },
            get_closest_worktime: function(e) {
                if (this.is_working_unit(e.date, e.unit)) return e.date;
                var i = e.unit,
                    n = t.date[i + "_start"](e.date),
                    a = new Date(n),
                    s = new Date(n),
                    r = !0,
                    o = 3e3,
                    _ = 0,
                    d = "any" == e.dir || !e.dir,
                    l = 1;
                for ("past" == e.dir && (l = -1); !this.is_working_unit(n, i);) {
                    d && (n = r ? a : s, l = -1 * l);
                    var h = n.getTimezoneOffset();
                    if (n = t.date.add(n, l, i), n = t._correct_dst_change(n, h, l, i), t.date[i + "_start"] && (n = t.date[i + "_start"](n)), d && (r ? a = n : s = n), r = !r, _++, _ > o) return t.assert(!1, "Invalid working time check"), !1
                }
                return (n == s || "past" == e.dir) && (n = t.date.add(n, 1, i)), n
            }
        }, t.getTask = function(e) {
            t.assert(e, "Invalid argument for gantt.getTask");
            var i = this._pull[e];
            return t.assert(i, "Task not found id=" + e), i
        }, t.getTaskByTime = function(t, e) {
            var i = this._pull,
                n = [];
            if (t || e) {
                t = +t || -(1 / 0), e = +e || 1 / 0;
                for (var a in i) {
                    var s = i[a]; + s.start_date < e && +s.end_date > t && n.push(s);
                }
            } else
                for (var a in i) n.push(i[a]);
            return n
        }, t.isTaskExists = function(e) {
            return t.defined(this._pull[e])
        }, t.isUnscheduledTask = function(t) {
            return !!t.unscheduled || !t.start_date
        }, t._isAllowedUnscheduledTask = function(e) {
            return e.unscheduled && t.config.show_unscheduled
        }, t.isTaskVisible = function(e) {
            if (!this._pull[e]) return !1;
            var i = this._pull[e];
            return (+i.start_date < +this._max_date && +i.end_date > +this._min_date || t._isAllowedUnscheduledTask(i)) && void 0 !== this._order_search[e] ? !0 : !1
        }, t.updateTask = function(e, i) {
            return t.defined(i) || (i = this.getTask(e)), this.callEvent("onBeforeTaskUpdate", [e, i]) === !1 ? !1 : (this._pull[i.id] = i, this._is_parent_sync(i) || this._resync_parent(i), this._isAllowedUnscheduledTask(i) && (this._init_task(i), this._sync_links()), this._update_parents(i.id), this.refreshTask(i.id), this.callEvent("onAfterTaskUpdate", [e, i]), this._sync_order(), void this._adjust_scales())
        }, t._add_branch = function(t, e) {
            var i = this.getParent(t);
            this.hasChild(i) || (this._branches[i] = []);
            for (var n = this.getChildren(i), a = !1, s = 0, r = n.length; r > s; s++)
                if (n[s] == t.id) {
                    a = !0;
                    break
                }
            a || (1 * e == e ? n.splice(e, 0, t.id) : n.push(t.id)), this._sync_parent(t)
        }, t._move_branch = function(t, e, i) {
            this.setParent(t, i), this._sync_parent(t), this._replace_branch_child(e, t.id), this.isTaskExists(i) || i == this.config.root_id ? this._add_branch(t) : delete this._branches[t.id], t.$level = this.calculateTaskLevel(t), this._sync_order()
        }, t._resync_parent = function(t) {
            this._move_branch(t, t.$rendered_parent, this.getParent(t))
        }, t._sync_parent = function(t) {
            t.$rendered_parent = this.getParent(t)
        }, t._is_parent_sync = function(t) {
            return t.$rendered_parent == this.getParent(t)
        }, t._replace_branch_child = function(t, e, i) {
            var n = this.getChildren(t);
            if (n) {
                for (var a = [], s = 0; s < n.length; s++) n[s] != e ? a.push(n[s]) : i && a.push(i);
                this._branches[t] = a
            }
            this._sync_order()
        }, t.addTask = function(e, i, n) {
            return t.defined(i) || (i = this.getParent(e) || 0), this.isTaskExists(i) || (i = 0), this.setParent(e, i), e = this._init_task(e), this.callEvent("onBeforeTaskAdd", [e.id, e]) === !1 ? !1 : (this._pull[e.id] = e, this._add_branch(e, n), this.callEvent("onAfterTaskAdd", [e.id, e]), this.refreshData(),
                this._adjust_scales(), e.id)
        }, t._default_task_date = function(e, i) {
            var n = i && i != this.config.root_id ? this.getTask(i) : !1,
                a = "";
            if (n) a = n.start_date;
            else {
                var s = this._order[0];
                a = s ? this.getTask(s).start_date ? this.getTask(s).start_date : this.getTask(s).end_date ? this.calculateEndDate(this.getTask(s).end_date, -this.config.duration_step) : "" : this.config.start_date || this.getState().min_date
            }
            return t.assert(a, "Invalid dates"), new Date(a)
        }, t._set_default_task_timing = function(e) {
            e.start_date = e.start_date || t._default_task_date(e, this.getParent(e)),
                e.duration = e.duration || this.config.duration_step, e.end_date = e.end_date || this.calculateEndDate(e.start_date, e.duration)
        }, t.createTask = function(e, i, n) {
            if (e = e || {}, e.id = t.uid(), e.start_date || (e.start_date = t._default_task_date(e, i)), void 0 === e.text && (e.text = t.locale.labels.new_task), void 0 === e.duration && (e.duration = 1), i) {
                this.setParent(e, i);
                var a = this.getTask(i);
                a.$open = !0
            }
            return this.callEvent("onTaskCreated", [e]) ? (this.config.details_on_create ? (e.$new = !0, this._pull[e.id] = this._init_task(e), this._add_branch(e, n),
                e.$level = this.calculateTaskLevel(e), this.selectTask(e.id), this.refreshData(), this.showLightbox(e.id)) : this.addTask(e, i, n) && (this.showTask(e.id), this.selectTask(e.id)), e.id) : null
        }, t.deleteTask = function(t) {
            return this._deleteTask(t)
        }, t._getChildLinks = function(t) {
            var e = this.getTask(t);
            if (!e) return [];
            for (var i = e.$source.concat(e.$target), n = this.getChildren(e.id), a = 0; a < n.length; a++) i = i.concat(this._getChildLinks(n[a]));
            for (var s = {}, a = 0; a < i.length; a++) s[i[a]] = !0;
            i = [];
            for (var a in s) i.push(a);
            return i
        },
        t._getTaskTree = function(t) {
            var e = this.getTask(t);
            if (!e) return [];
            for (var i = [], n = this.getChildren(e.id), a = 0; a < n.length; a++) i.push(n[a]), i = i.concat(this._getTaskTree(n[a]));
            return i
        }, t._deleteRelatedLinks = function(t, e) {
            var i = this._dp && !e,
                n = "",
                a = i ? "off" != this._dp.updateMode : !1;
            i && (n = this._dp.updateMode, this._dp.setUpdateMode("off"));
            for (var s = 0; s < t.length; s++) i && (this._dp.setGanttMode("links"), this._dp.setUpdated(t[s], !0, "deleted")), this._deleteLink(t[s], !0);
            i && (this._dp.setUpdateMode(n), a && this._dp.sendAllData());
        }, t._deleteRelatedTasks = function(t, e) {
            var i = this._dp && !e,
                n = "";
            i && (n = this._dp.updateMode, this._dp.setGanttMode("tasks"), this._dp.setUpdateMode("off"));
            for (var a = this._getTaskTree(t), s = 0; s < a.length; s++) {
                var r = a[s];
                this._unset_task(r), i && this._dp.setUpdated(r, !0, "deleted")
            }
            i && this._dp.setUpdateMode(n)
        }, t._unset_task = function(t) {
            var e = this.getTask(t);
            this._update_flags(t, null), delete this._pull[t], this._move_branch(e, this.getParent(e), null)
        }, t._deleteTask = function(e, i) {
            var n = this.getTask(e);
            if (!i && this.callEvent("onBeforeTaskDelete", [e, n]) === !1) return !1;
            var a = t._getChildLinks(e);
            return this._deleteRelatedTasks(e, i), this._deleteRelatedLinks(a, i), this._unset_task(e), i || (this.callEvent("onAfterTaskDelete", [e, n]), this.refreshData()), !0
        }, t.clearAll = function() {
            this._clear_data(), this.callEvent("onClear", []), this.refreshData()
        }, t._clear_data = function() {
            this._pull = {}, this._branches = {}, this._order = [], this._order_full = [], this._lpull = {}, this._links = [], this._update_flags(), this.userdata = {}
        }, t._update_flags = function(t, e) {
            void 0 === t ? (this._lightbox_id = this._selected_task = null,
                this._tasks_dnd.drag && (this._tasks_dnd.drag.id = null)) : (this._lightbox_id == t && (this._lightbox_id = e), this._selected_task == t && (this._selected_task = e), this._tasks_dnd.drag && this._tasks_dnd.drag.id == t && (this._tasks_dnd.drag.id = e))
        }, t.changeTaskId = function(t, e) {
            var i = this._pull[e] = this._pull[t];
            this._pull[e].id = e, delete this._pull[t], this._update_flags(t, e), this._replace_branch_child(this.getParent(i), t, e);
            for (var n in this._pull) {
                var a = this._pull[n];
                this.getParent(a) == t && (this.setParent(a, e), this._resync_parent(a));
            }
            for (var s = this._get_task_links(i), r = 0; r < s.length; r++) {
                var o = this.getLink(s[r]);
                o.source == t && (o.source = e), o.target == t && (o.target = e)
            }
            this.callEvent("onTaskIdChange", [t, e])
        }, t._get_task_links = function(t) {
            var e = [];
            return t.$source && (e = e.concat(t.$source)), t.$target && (e = e.concat(t.$target)), e
        }, t._get_duration_unit = function() {
            return 1e3 * t._get_line(this.config.duration_unit) || this.config.duration_unit
        }, t._get_safe_type = function(t) {
            return "task"
        }, t._get_type_name = function(t) {
            for (var e in this.config.types)
                if (this.config.types[e] == t) return e;
            return "task"
        }, t.getWorkHours = function(t) {
            return this._working_time_helper.get_working_hours(t)
        }, t.setWorkTime = function(t) {
            this._working_time_helper.set_time(t)
        }, t.isWorkTime = function(t, e) {
            var i = this._working_time_helper;
            return i.is_working_unit(t, e || this.config.duration_unit)
        }, t.correctTaskWorkTime = function(e) {
            t.config.work_time && t.config.correct_work_time && (t.isWorkTime(e.start_date) ? t.isWorkTime(new Date(+e.end_date - 1)) || (e.end_date = t.calculateEndDate(e.start_date, e.duration)) : (e.start_date = t.getClosestWorkTime({
                date: e.start_date,
                dir: "future"
            }), e.end_date = t.calculateEndDate(e.start_date, e.duration)))
        }, t.getClosestWorkTime = function(t) {
            var e = this._working_time_helper;
            return t instanceof Date && (t = {
                date: t
            }), t.dir = t.dir || "any", t.unit = t.unit || this.config.duration_unit, e.get_closest_worktime(t)
        }, t.calculateDuration = function(t, e) {
            var i = this._working_time_helper;
            return i.get_work_units_between(t, e, this.config.duration_unit, this.config.duration_step)
        }, t._hasDuration = function(t, e) {
            var i = this._working_time_helper;
            return i.is_work_units_between(t, e, this.config.duration_unit, this.config.duration_step);
        }, t.calculateEndDate = function(t, e, i) {
            var n = this._working_time_helper,
                a = e >= 0 ? 1 : -1;
            return n.add_worktime(t, Math.abs(e), i || this.config.duration_unit, a * this.config.duration_step)
        }, t._init_task = function(e) {
            return t.defined(e.id) || (e.id = t.uid()), e.start_date && (e.start_date = t.date.parseDate(e.start_date, "xml_date")), e.end_date && (e.end_date = t.date.parseDate(e.end_date, "xml_date")), e.start_date ? !e.end_date && e.duration && (e.end_date = this.calculateEndDate(e.start_date, e.duration)) : e.end_date && void 0 !== e.duration && (e.start_date = this.calculateEndDate(e.end_date, -e.duration)),
                this._isAllowedUnscheduledTask(e) && this._set_default_task_timing(e), t._init_task_timing(e), e.start_date && e.end_date && t.correctTaskWorkTime(e), e.$source = [], e.$target = [], void 0 === e.parent && this.setParent(e, this.config.root_id), t.defined(e.$open) || (e.$open = t.defined(e.open) ? e.open : this.config.open_tree_initially), e.$level = this.calculateTaskLevel(e), e
        }, t._init_task_timing = function(t) {
            var e = this._get_safe_type(t.type);
            void 0 === t.$rendered_type ? t.$rendered_type = e : t.$rendered_type != e && (delete t.$no_end,
                delete t.$no_start, t.$rendered_type = e), void 0 !== t.$no_end && void 0 !== t.$no_start || e == this.config.types.milestone || (e == this.config.types.project ? (t.$no_end = t.$no_start = !0, this._set_default_task_timing(t)) : (t.$no_end = !(t.end_date || t.duration), t.$no_start = !t.start_date, this._isAllowedUnscheduledTask(t) && (t.$no_end = t.$no_start = !1))), e == this.config.types.milestone && (t.end_date = t.start_date), t.start_date && t.end_date && (t.duration = this.calculateDuration(t.start_date, t.end_date)), t.duration = t.duration || 0
        },
        t._is_flex_task = function(t) {
            return !(!t.$no_end && !t.$no_start)
        }, t.resetProjectDates = function(t) {
            if (t.$no_end || t.$no_start) {
                var e = this.getSubtaskDates(t.id);
                this._assign_project_dates(t, e.start_date, e.end_date)
            }
        }, t.getSubtaskDates = function(e) {
            var i = null,
                n = null,
                a = void 0 !== e ? e : t.config.root_id;
            return this.eachTask(function(e) {
                this._get_safe_type(e.type) == t.config.types.project || this.isUnscheduledTask(e) || (e.start_date && !e.$no_start && (!i || i > e.start_date.valueOf()) && (i = e.start_date.valueOf()), e.end_date && !e.$no_end && (!n || n < e.end_date.valueOf()) && (n = e.end_date.valueOf()));
            }, a), {
                start_date: i ? new Date(i) : null,
                end_date: n ? new Date(n) : null
            }
        }, t._assign_project_dates = function(t, e, i) {
            t.$no_start && (e && e != 1 / 0 ? t.start_date = new Date(e) : t.start_date = this._default_task_date(t, this.getParent(t))), t.$no_end && (i && i != -(1 / 0) ? t.end_date = new Date(i) : t.end_date = this.calculateEndDate(t.start_date, this.config.duration_step)), (t.$no_start || t.$no_end) && this._init_task_timing(t)
        }, t._update_parents = function(e, i) {
            if (e) {
                var n = this.getTask(e),
                    a = this.getParent(n),
                    s = !0;
                if (n.$no_start || n.$no_end) {
                    var r = n.start_date.valueOf(),
                        o = n.end_date.valueOf();
                    t.resetProjectDates(n), r == n.start_date.valueOf() && o == n.end_date.valueOf() && (s = !1), s && !i && this.refreshTask(n.id, !0)
                }
                s && a && this.isTaskExists(a) && this._update_parents(a, i)
            }
        }, t.isChildOf = function(t, e) {
            if (!this.isTaskExists(t)) return !1;
            if (e === this.config.root_id) return this.isTaskExists(t);
            for (var i = this.getTask(t), n = this.getParent(t); i && this.isTaskExists(n);) {
                if (i = this.getTask(n), i && i.id == e) return !0;
                n = this.getParent(i)
            }
            return !1
        }, t.roundDate = function(e) {
            e instanceof Date && (e = {
                date: e,
                unit: t._tasks.unit,
                step: t._tasks.step
            });
            var i, n, a, s = e.date,
                r = e.step,
                o = e.unit;
            if (o == t._tasks.unit && r == t._tasks.step && +s >= +t._min_date && +s <= +t._max_date) a = Math.floor(t._day_index_by_date(s)), t._tasks.trace_x[a] || (a -= 1), n = new Date(t._tasks.trace_x[a]), i = new Date(n), i = t._tasks.trace_x[a + 1] ? new Date(t._tasks.trace_x[a + 1]) : t.date.add(n, r, o);
            else {
                for (a = Math.floor(t._day_index_by_date(s)), i = t.date[o + "_start"](new Date(this._min_date)), t._tasks.trace_x[a] && (i = t.date[o + "_start"](t._tasks.trace_x[a])); + s > +i;) {
                    i = t.date[o + "_start"](t.date.add(i, r, o));
                    var _ = i.getTimezoneOffset();
                    i = t.date.add(i, r, o), i = t._correct_dst_change(i, _, i, o), t.date[o + "_start"] && (i = t.date[o + "_start"](i))
                }
                n = t.date.add(i, -1 * r, o)
            }
            return e.dir && "future" == e.dir ? i : e.dir && "past" == e.dir ? n : Math.abs(s - n) < Math.abs(i - s) ? n : i
        }, t.attachEvent("onBeforeTaskUpdate", function(e, i) {
            return t._init_task_timing(i), !0
        }), t.attachEvent("onBeforeTaskAdd", function(e, i) {
            return t._init_task_timing(i), !0
        }), t.calculateTaskLevel = function(t) {
            for (var e = 0; this.getParent(t) && this.isTaskExists(this.getParent(t));) t = this.getTask(this.getParent(t)),
                e++;
            return e
        }, t.sort = function(t, e, i, n) {
            var a = !n;
            this.isTaskExists(i) || (i = this.config.root_id), t || (t = "order");
            var s = "string" == typeof t ? function(e, i) {
                if (e[t] == i[t]) return 0;
                var n = e[t] > i[t];
                return n ? 1 : -1
            } : t;
            if (e) {
                var r = s;
                s = function(t, e) {
                    return r(e, t)
                }
            }
            var o = this.getChildren(i);
            if (o) {
                for (var _ = [], d = o.length - 1; d >= 0; d--) _[d] = this._pull[o[d]];
                _.sort(s);
                for (var d = 0; d < _.length; d++) o[d] = _[d].id, this.sort(t, e, o[d], !0)
            }
            a && this.render()
        }, t.getNext = function(t) {
            for (var e = 0; e < this._order.length - 1; e++)
                if (this._order[e] == t) return this._order[e + 1];
            return null
        }, t.getPrev = function(t) {
            for (var e = 1; e < this._order.length; e++)
                if (this._order[e] == t) return this._order[e - 1];
            return null
        }, t._get_parent_id = function(t) {
            var e = this.config.root_id;
            return t && (e = t.parent), e
        }, t.getParent = function(e) {
            var i = null;
            return i = e.id ? e : t.getTask(e), this._get_parent_id(i)
        }, t.setParent = function(t, e) {
            t.parent = e
        }, t.getSiblings = function(t) {
            if (!this.isTaskExists(t)) return [];
            var e = this.getParent(t);
            return this.getChildren(e)
        }, t.getNextSibling = function(t) {
            for (var e = this.getSiblings(t), i = 0, n = e.length; n > i; i++)
                if (e[i] == t) return e[i + 1] || null;
            return null
        }, t.getPrevSibling = function(t) {
            for (var e = this.getSiblings(t), i = 0, n = e.length; n > i; i++)
                if (e[i] == t) return e[i - 1] || null;
            return null
        }, t._dp_init = function(e) {
            e.setTransactionMode("POST", !0), e.serverProcessor += (-1 != e.serverProcessor.indexOf("?") ? "&" : "?") + "editing=true", e._serverProcessor = e.serverProcessor, e.styles = {
                    updated: "gantt_updated",
                    order: "gantt_updated",
                    inserted: "gantt_inserted",
                    deleted: "gantt_deleted",
                    invalid: "gantt_invalid",
                    error: "gantt_error",
                    clear: ""
                }, e._methods = ["_row_style", "setCellTextStyle", "_change_id", "_delete_task"],
                e.setGanttMode = function(t) {
                    var i = e.modes || {};
                    e._ganttMode && (i[e._ganttMode] = {
                        _in_progress: e._in_progress,
                        _invalid: e._invalid,
                        updatedRows: e.updatedRows
                    });
                    var n = i[t];
                    n || (n = i[t] = {
                        _in_progress: {},
                        _invalid: {},
                        updatedRows: []
                    }), e._in_progress = n._in_progress, e._invalid = n._invalid, e.updatedRows = n.updatedRows, e.modes = i, e._ganttMode = t
                }, this._sendTaskOrder = function(t, i) {
                    i.$drop_target && (e.setGanttMode("tasks"), this.getTask(t).target = i.$drop_target, e.setUpdated(t, !0, "order"), delete this.getTask(t).$drop_target);
                }, this.attachEvent("onAfterTaskAdd", function(t, i) {
                    e.setGanttMode("tasks"), e.setUpdated(t, !0, "inserted")
                }), this.attachEvent("onAfterTaskUpdate", function(i, n) {
                    e.setGanttMode("tasks"), e.setUpdated(i, !0), t._sendTaskOrder(i, n)
                }), this.attachEvent("onAfterTaskDelete", function(t, i) {
                    e.setGanttMode("tasks"), e.setUpdated(t, !0, "deleted"), "off" == e.updateMode || e._tSend || e.sendAllData()
                }), this.attachEvent("onAfterLinkUpdate", function(t, i) {
                    e.setGanttMode("links"), e.setUpdated(t, !0)
                }), this.attachEvent("onAfterLinkAdd", function(t, i) {
                    e.setGanttMode("links"), e.setUpdated(t, !0, "inserted")
                }), this.attachEvent("onAfterLinkDelete", function(t, i) {
                    e.setGanttMode("links"), e.setUpdated(t, !0, "deleted")
                }), this.attachEvent("onRowDragEnd", function(e, i) {
                    t._sendTaskOrder(e, t.getTask(e))
                });
            var i = null,
                n = null;
            this.attachEvent("onTaskIdChange", function(a, s) {
                if (e._waitMode) {
                    var r = t.getChildren(s);
                    if (r.length) {
                        i = i || {};
                        for (var o = 0; o < r.length; o++) {
                            var _ = this.getTask(r[o]);
                            i[_.id] = _
                        }
                    }
                    var d = this.getTask(s),
                        l = this._get_task_links(d);
                    if (l.length) {
                        n = n || {};
                        for (var o = 0; o < l.length; o++) {
                            var h = this.getLink(l[o]);
                            n[h.id] = h
                        }
                    }
                }
            }), e.attachEvent("onAfterUpdateFinish", function() {
                (i || n) && (t.batchUpdate(function() {
                    for (var e in i) t.updateTask(i[e].id);
                    for (var e in n) t.updateLink(n[e].id);
                    i = null, n = null
                }), i ? t._dp.setGanttMode("tasks") : t._dp.setGanttMode("links"))
            }), e.attachEvent("onBeforeDataSending", function() {
                var e = this._serverProcessor;
                if ("REST" == this._tMode) {
                    var i = this._ganttMode.substr(0, this._ganttMode.length - 1);
                    e = e.substring(0, e.indexOf("?") > -1 ? e.indexOf("?") : e.length),
                        this.serverProcessor = e + ("/" == e.slice(-1) ? "" : "/") + i
                } else this.serverProcessor = e + t._urlSeparator(e) + "gantt_mode=" + this._ganttMode;
                return !0
            }), this._init_dp_live_update_hooks(e);
            var a = e.afterUpdate;
            e.afterUpdate = function() {
                var t;
                t = 3 == arguments.length ? arguments[1] : arguments[4];
                var i = e._ganttMode,
                    n = t.filePath;
                i = "REST" != this._tMode ? -1 != n.indexOf("gantt_mode=links") ? "links" : "tasks" : n.indexOf("/link") > n.indexOf("/task") ? "links" : "tasks", e.setGanttMode(i);
                var s = a.apply(e, arguments);
                return e.setGanttMode(i),
                    s
            }, e._getRowData = t.bind(function(i, n) {
                var a;
                a = "tasks" == e._ganttMode ? this.isTaskExists(i) ? this.getTask(i) : {
                    id: i
                } : this.isLinkExists(i) ? this.getLink(i) : {
                    id: i
                }, a = t.copy(a);
                var s = {};
                for (var r in a)
                    if ("$" != r.substr(0, 1)) {
                        var o = a[r];
                        o instanceof Date ? s[r] = this.templates.xml_format(o) : null === o ? s[r] = "" : s[r] = o
                    }
                return a.$no_start && (a.start_date = "", a.duration = ""), a.$no_end && (a.end_date = "", a.duration = ""), s[e.action_param] = this.getUserData(i, e.action_param), s
            }, this), this._change_id = t.bind(function(t, i) {
                "tasks" != e._ganttMode ? this.changeLinkId(t, i) : this.changeTaskId(t, i);
            }, this), this._row_style = function(i, n) {
                if ("tasks" == e._ganttMode && t.isTaskExists(i)) {
                    var a = t.getTask(i);
                    a.$dataprocessor_class = n, t.refreshTask(i)
                }
            }, this._delete_task = function(t, e) {}, this._dp = e
        }, t.getUserData = function(t, e) {
            return this.userdata || (this.userdata = {}), this.userdata[t] && this.userdata[t][e] ? this.userdata[t][e] : ""
        }, t.setUserData = function(t, e, i) {
            this.userdata || (this.userdata = {}), this.userdata[t] || (this.userdata[t] = {}), this.userdata[t][e] = i
        }, t._init_link = function(e) {
            return t.defined(e.id) || (e.id = t.uid()),
                e
        }, t._sync_links = function() {
            for (var t = null, e = 0, i = this._order_full.length; i > e; e++) t = this._pull[this._order_full[e]], t.$source = [], t.$target = [];
            this._links = [];
            for (var n in this._lpull) {
                var a = this._lpull[n];
                this._links.push(a), this._pull[a.source] && this._pull[a.source].$source.push(n), this._pull[a.target] && this._pull[a.target].$target.push(n)
            }
        }, t.getLink = function(e) {
            return t.assert(this._lpull[e], "Link doesn't exist"), this._lpull[e]
        }, t.getLinks = function() {
            var e = [];
            for (var i in t._lpull) e.push(t._lpull[i]);
            return e
        }, t.isLinkExists = function(e) {
            return t.defined(this._lpull[e])
        }, t.addLink = function(t) {
            return t = this._init_link(t), this.callEvent("onBeforeLinkAdd", [t.id, t]) === !1 ? !1 : (this._lpull[t.id] = t, this._sync_links(), this._render_link(t.id), this.callEvent("onAfterLinkAdd", [t.id, t]), t.id)
        }, t.updateLink = function(e, i) {
            return t.defined(i) || (i = this.getLink(e)), this.callEvent("onBeforeLinkUpdate", [e, i]) === !1 ? !1 : (this._lpull[e] = i, this._sync_links(), this._render_link(e), this.callEvent("onAfterLinkUpdate", [e, i]), !0)
        }, t.deleteLink = function(t) {
            return this._deleteLink(t)
        }, t._deleteLink = function(t, e) {
            var i = this.getLink(t);
            return e || this.callEvent("onBeforeLinkDelete", [t, i]) !== !1 ? (delete this._lpull[t], this._sync_links(), this.refreshLink(t), e || this.callEvent("onAfterLinkDelete", [t, i]), !0) : !1
        }, t.changeLinkId = function(t, e) {
            this._lpull[t] && (this._lpull[e] = this._lpull[t], this._lpull[e].id = e, delete this._lpull[t], this._sync_links(), this.callEvent("onLinkIdChange", [t, e]))
        }, t.getChildren = function(e) {
            return t.defined(this._branches[e]) ? this._branches[e] : [];
        }, t.hasChild = function(e) {
            return t.defined(this._branches[e]) && this._branches[e].length
        }, t.refreshData = function() {
            this._render_data()
        }, t._isTask = function(e) {
            return !(e.type && e.type == t.config.types.project || e.$no_start || e.$no_end)
        }, t._isProject = function(t) {
            return !this._isTask(t)
        }, t._configure = function(t, e, i) {
            for (var n in e)("undefined" == typeof t[n] || i) && (t[n] = e[n])
        }, t._init_skin = function() {
            t._get_skin(!1), t._init_skin = function() {}
        }, t._get_skin = function(e) {
            if (!t.skin || e)
                for (var i = document.getElementsByTagName("link"), n = 0; n < i.length; n++) {
                    var a = i[n].href.match("dhtmlxgantt_([a-z]+).css");
                    if (a) {
                        t.skin = a[1];
                        break
                    }
                }
            t.skin || (t.skin = "terrace");
            var s = t.skins[t.skin];
            this._configure(t.config, s.config, e);
            var r = t.getGridColumns();
            r[1] && "undefined" == typeof r[1].width && (r[1].width = s._second_column_width), r[2] && "undefined" == typeof r[2].width && (r[2].width = s._third_column_width), s._lightbox_template && (t._lightbox_template = s._lightbox_template), t.resetLightbox()
        }, t.resetSkin = function() {
            this.skin = "", this._get_skin(!0)
        }, t.skins = {}, t._lightbox_methods = {},
        t._lightbox_template = "<div class='gantt_cal_ltitle'><span class='gantt_mark'>&nbsp;</span><span class='gantt_time'></span><span class='gantt_title'></span></div><div class='gantt_cal_larea'></div>", t.showLightbox = function(e) {
            if (e && !t._is_readonly(this.getTask(e)) && this.callEvent("onBeforeLightbox", [e])) {
                var i = this.getTask(e),
                    n = this.getLightbox(this._get_safe_type(i.type));
                this._center_lightbox(n), this.showCover(), this._fill_lightbox(e, n), this.callEvent("onLightbox", [e])
            }
        }, t._get_timepicker_step = function() {
            if (this.config.round_dnd_dates) {
                var e = t._tasks,
                    i = this._get_line(e.unit) * e.step / 60;
                return (i >= 1440 || !this._is_chart_visible()) && (i = this.config.time_step), i
            }
            return this.config.time_step
        }, t.getLabel = function(t, e) {
            for (var i = this._get_typed_lightbox_config(), n = 0; n < i.length; n++)
                if (i[n].map_to == t)
                    for (var a = i[n].options, s = 0; s < a.length; s++)
                        if (a[s].key == e) return a[s].label;
            return ""
        }, t.updateCollection = function(e, i) {
            i = i.slice(0);
            var n = t.serverList(e);
            return n ? (n.splice(0, n.length), n.push.apply(n, i || []), void t.resetLightbox()) : !1;
        }, t.getLightboxType = function() {
            return this._get_safe_type(this._lightbox_type)
        }, t.getLightbox = function(e) {
            if (void 0 === e && (e = this.getLightboxType()), !this._lightbox || this.getLightboxType() != this._get_safe_type(e)) {
                this._lightbox_type = this._get_safe_type(e);
                var i = document.createElement("DIV");
                i.className = "gantt_cal_light";
                var n = this._is_lightbox_timepicker();
                (t.config.wide_form || n) && (i.className += " gantt_cal_light_wide"), n && (t.config.wide_form = !0, i.className += " gantt_cal_light_full"), i.style.visibility = "hidden";
                for (var a = this._lightbox_template, s = this.config.buttons_left, r = 0; r < s.length; r++) {
                    var o = this.config._migrate_buttons[s[r]] ? this.config._migrate_buttons[s[r]] : s[r];
                    a += "<div class='gantt_btn_set gantt_left_btn_set " + o + "_set'><div dhx_button='1' class='" + o + "'></div><div>" + this.locale.labels[o] + "</div></div>"
                }
                s = this.config.buttons_right;
                for (var r = 0; r < s.length; r++) {
                    var o = this.config._migrate_buttons[s[r]] ? this.config._migrate_buttons[s[r]] : s[r];
                    a += "<div class='gantt_btn_set gantt_right_btn_set " + o + "_set' style='float:right;'><div dhx_button='1' class='" + o + "'></div><div>" + this.locale.labels[o] + "</div></div>";
                }
                a += "</div>", i.innerHTML = a, t.config.drag_lightbox && (i.firstChild.onmousedown = t._ready_to_dnd, i.firstChild.onselectstart = function() {
                    return !1
                }, i.firstChild.style.cursor = "pointer", t._init_dnd_events()), document.body.insertBefore(i, document.body.firstChild), this._lightbox = i;
                var _ = this._get_typed_lightbox_config(e);
                a = this._render_sections(_);
                for (var d = i.getElementsByTagName("div"), r = 0; r < d.length; r++) {
                    var l = d[r];
                    if ("gantt_cal_larea" == l.className) {
                        l.innerHTML = a;
                        break
                    }
                }
                this.resizeLightbox(), this._init_lightbox_events(this),
                    i.style.display = "none", i.style.visibility = "visible"
            }
            return this._lightbox
        }, t._render_sections = function(t) {
            for (var e = "", i = 0; i < t.length; i++) {
                var n = this.form_blocks[t[i].type];
                if (n) {
                    t[i].id = "area_" + this.uid();
                    var a = t[i].hidden ? " style='display:none'" : "",
                        s = "";
                    t[i].button && (s = "<div class='gantt_custom_button' index='" + i + "'><div class='gantt_custom_button_" + t[i].button + "'></div><div>" + this.locale.labels["button_" + t[i].button] + "</div></div>"), this.config.wide_form && (e += "<div class='gantt_wrap_section' " + a + ">"),
                        e += "<div id='" + t[i].id + "' class='gantt_cal_lsection'>" + s + this.locale.labels["section_" + t[i].name] + "</div>" + n.render.call(this, t[i]), e += "</div>"
                }
            }
            return e
        }, t.resizeLightbox = function() {
            var t = this._lightbox;
            if (t) {
                var e = t.childNodes[1];
                e.style.height = "0px", e.style.height = e.scrollHeight + "px", t.style.height = e.scrollHeight + this.config.lightbox_additional_height + "px", e.style.height = e.scrollHeight + "px"
            }
        }, t._center_lightbox = function(t) {
            if (t) {
                t.style.display = "block";
                var e = window.pageYOffset || document.body.scrollTop || document.documentElement.scrollTop,
                    i = window.pageXOffset || document.body.scrollLeft || document.documentElement.scrollLeft,
                    n = window.innerHeight || document.documentElement.clientHeight;
                e ? t.style.top = Math.round(e + Math.max((n - t.offsetHeight) / 2, 0)) + "px" : t.style.top = Math.round(Math.max((n - t.offsetHeight) / 2, 0) + 9) + "px", document.documentElement.scrollWidth > document.body.offsetWidth ? t.style.left = Math.round(i + (document.body.offsetWidth - t.offsetWidth) / 2) + "px" : t.style.left = Math.round((document.body.offsetWidth - t.offsetWidth) / 2) + "px"
            }
        }, t.showCover = function() {
            if (!this._cover) {
                this._cover = document.createElement("DIV"), this._cover.className = "gantt_cal_cover";
                var t = void 0 !== document.height ? document.height : document.body.offsetHeight,
                    e = document.documentElement ? document.documentElement.scrollHeight : 0;
                this._cover.style.height = Math.max(t, e) + "px", document.body.appendChild(this._cover)
            }
        }, t._init_lightbox_events = function() {
            t.lightbox_events = {}, t.lightbox_events.gantt_save_btn = function(e) {
                t._save_lightbox()
            }, t.lightbox_events.gantt_delete_btn = function(e) {
                t.callEvent("onLightboxDelete", [t._lightbox_id]) && (t.isTaskExists(t._lightbox_id) ? t.$click.buttons["delete"](t._lightbox_id) : t.hideLightbox())
            }, t.lightbox_events.gantt_cancel_btn = function(e) {
                t._cancel_lightbox()
            }, t.lightbox_events["default"] = function(e, i) {
                if (i.getAttribute("dhx_button")) t.callEvent("onLightboxButton", [i.className, i, e]);
                else {
                    var n, a, s, r = t._getClassName(i); - 1 != r.indexOf("gantt_custom_button") && (-1 != r.indexOf("gantt_custom_button_") ? (n = i.parentNode.getAttribute("index"), s = i.parentNode.parentNode) : (n = i.getAttribute("index"), s = i.parentNode, i = i.firstChild));
                    var o = t._get_typed_lightbox_config();
                    n && (a = t.form_blocks[o[n].type], a.button_click(n, i, s, s.nextSibling))
                }
            }, this.event(t.getLightbox(), "click", function(e) {
                e = e || window.event;
                var i = e.target ? e.target : e.srcElement,
                    n = t._getClassName(i);
                if (n || (i = i.previousSibling, n = t._getClassName(i)), i && n && 0 === n.indexOf("gantt_btn_set") && (i = i.firstChild, n = t._getClassName(i)), i && n) {
                    var a = t.defined(t.lightbox_events[i.className]) ? t.lightbox_events[i.className] : t.lightbox_events["default"];
                    return a(e, i)
                }
                return !1
            }), t.getLightbox().onkeydown = function(e) {
                switch ((e || event).keyCode) {
                    case t.keys.edit_save:
                        if ((e || event).shiftKey) return;
                        t._save_lightbox();
                        break;
                    case t.keys.edit_cancel:
                        t._cancel_lightbox()
                }
            }
        }, t._cancel_lightbox = function() {
            var e = this.getLightboxValues();
            this.callEvent("onLightboxCancel", [this._lightbox_id, e.$new]), t.isTaskExists(e.id) && e.$new && this._deleteTask(e.id, !0), this.refreshData(), this.hideLightbox()
        }, t._save_lightbox = function() {
            var t = this.getLightboxValues();
            this.callEvent("onLightboxSave", [this._lightbox_id, t, !!t.$new]) && (t.$new ? (delete t.$new, this._replace_branch_child(this.getParent(t.id), t.id), this.addTask(t)) : this.isTaskExists(t.id) && (this.mixin(this.getTask(t.id), t, !0), this.updateTask(t.id)), this.refreshData(), this.hideLightbox())
        },
        t._resolve_default_mapping = function(t) {
            var e = t.map_to,
                i = {
                    time: !0,
                    time_optional: !0,
                    duration: !0,
                    duration_optional: !0
                };
            return i[t.type] && ("auto" == t.map_to ? e = {
                start_date: "start_date",
                end_date: "end_date",
                duration: "duration"
            } : "string" == typeof t.map_to && (e = {
                start_date: t.map_to
            })), e
        }, t.getLightboxValues = function() {
            var e = {};
            t.isTaskExists(this._lightbox_id) && (e = this.mixin({}, this.getTask(this._lightbox_id)));
            for (var i = this._get_typed_lightbox_config(), n = 0; n < i.length; n++) {
                var a = document.getElementById(i[n].id);
                a = a ? a.nextSibling : a;
                var s = this.form_blocks[i[n].type];
                if (s) {
                    var r = s.get_value.call(this, a, e, i[n]),
                        o = t._resolve_default_mapping(i[n]);
                    if ("string" == typeof o && "auto" != o) e[o] = r;
                    else if ("object" == typeof o)
                        for (var _ in o) o[_] && (e[o[_]] = r[_])
                }
            }
            return e
        }, t.hideLightbox = function() {
            var t = this.getLightbox();
            t && (t.style.display = "none"), this._lightbox_id = null, this.hideCover(), this.callEvent("onAfterLightbox", [])
        }, t.hideCover = function() {
            this._cover && this._cover.parentNode.removeChild(this._cover), this._cover = null;
        }, t.resetLightbox = function() {
            t._lightbox && !t._custom_lightbox && t._lightbox.parentNode.removeChild(t._lightbox), t._lightbox = null
        }, t._set_lightbox_values = function(e, i) {
            var n = e,
                a = i.getElementsByTagName("span");
            t.templates.lightbox_header ? (a[1].innerHTML = "", a[2].innerHTML = t.templates.lightbox_header(n.start_date, n.end_date, n)) : (a[1].innerHTML = this.templates.task_time(n.start_date, n.end_date, n), a[2].innerHTML = (this.templates.task_text(n.start_date, n.end_date, n) || "").substr(0, 70));
            for (var s = this._get_typed_lightbox_config(this.getLightboxType()), r = 0; r < s.length; r++) {
                var o = s[r];
                if (this.form_blocks[o.type]) {
                    var _ = document.getElementById(o.id).nextSibling,
                        d = this.form_blocks[o.type],
                        l = t._resolve_default_mapping(s[r]),
                        h = this.defined(n[l]) ? n[l] : o.default_value;
                    d.set_value.call(t, _, h, n, o), o.focus && d.focus.call(t, _)
                }
            }
            e.id && (t._lightbox_id = e.id)
        }, t._fill_lightbox = function(t, e) {
            var i = this.getTask(t);
            this._set_lightbox_values(i, e)
        }, t.getLightboxSection = function(e) {
            var i = this._get_typed_lightbox_config(),
                n = 0;
            for (n; n < i.length && i[n].name != e; n++);
            var a = i[n];
            if (!a) return null;
            this._lightbox || this.getLightbox();
            var s = document.getElementById(a.id),
                r = s.nextSibling,
                o = {
                    section: a,
                    header: s,
                    node: r,
                    getValue: function(e) {
                        return t.form_blocks[a.type].get_value.call(t, r, e || {}, a)
                    },
                    setValue: function(e, i) {
                        return t.form_blocks[a.type].set_value.call(t, r, e, i || {}, a)
                    }
                },
                _ = this._lightbox_methods["get_" + a.type + "_control"];
            return _ ? _(o) : o
        }, t._lightbox_methods.get_template_control = function(t) {
            return t.control = t.node, t
        }, t._lightbox_methods.get_select_control = function(t) {
            return t.control = t.node.getElementsByTagName("select")[0],
                t
        }, t._lightbox_methods.get_textarea_control = function(t) {
            return t.control = t.node.getElementsByTagName("textarea")[0], t
        }, t._lightbox_methods.get_time_control = function(t) {
            return t.control = t.node.getElementsByTagName("select"), t
        }, t._init_dnd_events = function() {
            this.event(document.body, "mousemove", t._move_while_dnd), this.event(document.body, "mouseup", t._finish_dnd), t._init_dnd_events = function() {}
        }, t._move_while_dnd = function(e) {
            if (t._dnd_start_lb) {
                document.gantt_unselectable || (document.body.className += " gantt_unselectable",
                    document.gantt_unselectable = !0);
                var i = t.getLightbox(),
                    n = e && e.target ? [e.pageX, e.pageY] : [event.clientX, event.clientY];
                i.style.top = t._lb_start[1] + n[1] - t._dnd_start_lb[1] + "px", i.style.left = t._lb_start[0] + n[0] - t._dnd_start_lb[0] + "px"
            }
        }, t._ready_to_dnd = function(e) {
            var i = t.getLightbox();
            t._lb_start = [parseInt(i.style.left, 10), parseInt(i.style.top, 10)], t._dnd_start_lb = e && e.target ? [e.pageX, e.pageY] : [event.clientX, event.clientY]
        }, t._finish_dnd = function() {
            t._lb_start && (t._lb_start = t._dnd_start_lb = !1, document.body.className = document.body.className.replace(" gantt_unselectable", ""),
                document.gantt_unselectable = !1)
        }, t._focus = function(e, i) {
            if (e && e.focus)
                if (t.config.touch);
                else try {
                    i && e.select && e.select(), e.focus()
                } catch (n) {}
        }, t.form_blocks = {
            getTimePicker: function(e, i) {
                var n = e.time_format;
                if (!n) {
                    var n = ["%d", "%m", "%Y"];
                    t._get_line(t._tasks.unit) < t._get_line("day") && n.push("%H:%i")
                }
                e._time_format_order = {
                    size: 0
                };
                var a = this.config,
                    s = this.date.date_part(new Date(t._min_date.valueOf())),
                    r = 1440,
                    o = 0;
                t.config.limit_time_select && (r = 60 * a.last_hour + 1, o = 60 * a.first_hour, s.setHours(a.first_hour));
                for (var _ = "", d = 0; d < n.length; d++) {
                    var l = n[d];
                    d > 0 && (_ += " ");
                    var h = "";
                    switch (l) {
                        case "%Y":
                            e._time_format_order[2] = d, e._time_format_order.size++;
                            var c, u, g, f;
                            e.year_range && (isNaN(e.year_range) ? e.year_range.push && (g = e.year_range[0], f = e.year_range[1]) : c = e.year_range), c = c || 10, u = u || Math.floor(c / 2), g = g || s.getFullYear() - u, f = f || g + c;
                            for (var p = g; f > p; p++) h += "<option value='" + p + "'>" + p + "</option>";
                            break;
                        case "%m":
                            e._time_format_order[1] = d, e._time_format_order.size++;
                            for (var p = 0; 12 > p; p++) h += "<option value='" + p + "'>" + this.locale.date.month_full[p] + "</option>";
                            break;
                        case "%d":
                            e._time_format_order[0] = d, e._time_format_order.size++;
                            for (var p = 1; 32 > p; p++) h += "<option value='" + p + "'>" + p + "</option>";
                            break;
                        case "%H:%i":
                            e._time_format_order[3] = d, e._time_format_order.size++;
                            var p = o,
                                v = s.getDate();
                            for (e._time_values = []; r > p;) {
                                var m = this.templates.time_picker(s);
                                h += "<option value='" + p + "'>" + m + "</option>", e._time_values.push(p), s.setTime(s.valueOf() + 60 * this._get_timepicker_step() * 1e3);
                                var k = s.getDate() != v ? 1 : 0;
                                p = 24 * k * 60 + 60 * s.getHours() + s.getMinutes()
                            }
                    }
                    if (h) {
                        var b = e.readonly ? "disabled='disabled'" : "",
                            y = i ? " style='display:none'" : "";
                        _ += "<select " + b + y + ">" + h + "</select>"
                    }
                }
                return _
            },
            _fill_lightbox_select: function(e, i, n, a, s) {
                if (e[i + a[0]].value = n.getDate(), e[i + a[1]].value = n.getMonth(), e[i + a[2]].value = n.getFullYear(), t.defined(a[3])) {
                    var r = 60 * n.getHours() + n.getMinutes();
                    r = Math.round(r / t._get_timepicker_step()) * t._get_timepicker_step();
                    var o = e[i + a[3]];
                    o.value = r, o.setAttribute("data-value", r)
                }
            },
            template: {
                render: function(t) {
                    var e = (t.height || "30") + "px";
                    return "<div class='gantt_cal_ltext gantt_cal_template' style='height:" + e + ";'></div>";
                },
                set_value: function(t, e, i, n) {
                    t.innerHTML = e || ""
                },
                get_value: function(t, e, i) {
                    return t.innerHTML || ""
                },
                focus: function(t) {}
            },
            textarea: {
                render: function(t) {
                    var e = (t.height || "130") + "px";
                    return "<div class='gantt_cal_ltext' style='height:" + e + ";'><textarea></textarea></div>"
                },
                set_value: function(t, e, i) {
                    t.firstChild.value = e || ""
                },
                get_value: function(t, e) {
                    return t.firstChild.value
                },
                focus: function(e) {
                    var i = e.firstChild;
                    t._focus(i, !0)
                }
            },
            select: {
                render: function(t) {
                    for (var e = (t.height || "23") + "px", i = "<div class='gantt_cal_ltext' style='height:" + e + ";'><select style='width:100%;'>", n = 0; n < t.options.length; n++) i += "<option value='" + t.options[n].key + "'>" + t.options[n].label + "</option>";
                    return i += "</select></div>"
                },
                set_value: function(t, e, i, n) {
                    var a = t.firstChild;
                    !a._dhx_onchange && n.onchange && (a.onchange = n.onchange, a._dhx_onchange = !0), "undefined" == typeof e && (e = (a.options[0] || {}).value), a.value = e || ""
                },
                get_value: function(t, e) {
                    return t.firstChild.value
                },
                focus: function(e) {
                    var i = e.firstChild;
                    t._focus(i, !0)
                }
            },
            time: {
                render: function(t) {
                    var e = this.form_blocks.getTimePicker.call(this, t),
                        i = ["<div style='height:" + (t.height || 30) + "px;padding-top:0px;font-size:inherit;text-align:center;' class='gantt_section_time'>"];
                    return i.push(e), t.single_date ? (e = this.form_blocks.getTimePicker.call(this, t, !0), i.push("<span></span>")) : i.push("<span style='font-weight:normal; font-size:10pt;'> &nbsp;&ndash;&nbsp; </span>"), i.push(e), i.push("</div>"), i.join("")
                },
                set_value: function(e, i, n, a) {
                    var s = a,
                        r = e.getElementsByTagName("select"),
                        o = a._time_format_order;
                    a._time_format_size;
                    if (s.auto_end_date)
                        for (var _ = function() {
                                h = new Date(r[o[2]].value, r[o[1]].value, r[o[0]].value, 0, 0), c = t.calculateEndDate(h, 1), this.form_blocks._fill_lightbox_select(r, o.size, c, o, s);
                            }, d = 0; 4 > d; d++) r[d].onchange = _;
                    var l = t._resolve_default_mapping(a);
                    "string" == typeof l && (l = {
                        start_date: l
                    });
                    var h = n[l.start_date] || new Date,
                        c = n[l.end_date] || t.calculateEndDate(h, 1);
                    this.form_blocks._fill_lightbox_select(r, 0, h, o, s), this.form_blocks._fill_lightbox_select(r, o.size, c, o, s)
                },
                get_value: function(e, i, n) {
                    var a = e.getElementsByTagName("select"),
                        s = n._time_format_order,
                        r = 0,
                        o = 0;
                    if (t.defined(s[3])) {
                        var _ = parseInt(a[s[3]].value, 10);
                        r = Math.floor(_ / 60), o = _ % 60
                    }
                    var d = new Date(a[s[2]].value, a[s[1]].value, a[s[0]].value, r, o);
                    if (r = o = 0, t.defined(s[3])) {
                        var _ = parseInt(a[s.size + s[3]].value, 10);
                        r = Math.floor(_ / 60), o = _ % 60
                    }
                    var l = new Date(a[s[2] + s.size].value, a[s[1] + s.size].value, a[s[0] + s.size].value, r, o);
                    d >= l && (l = t.date.add(d, t._get_timepicker_step(), "minute"));
                    var h = t._resolve_default_mapping(n),
                        c = {
                            start_date: new Date(d),
                            end_date: new Date(l)
                        };
                    return "string" == typeof h ? c.start_date : c
                },
                focus: function(e) {
                    t._focus(e.getElementsByTagName("select")[0])
                }
            },
            duration: {
                render: function(t) {
                    var e = this.form_blocks.getTimePicker.call(this, t);
                    e = "<div class='gantt_time_selects'>" + e + "</div>";
                    var i = this.locale.labels[this.config.duration_unit + "s"],
                        n = t.single_date ? ' style="display:none"' : "",
                        a = t.readonly ? " disabled='disabled'" : "",
                        s = "<div class='gantt_duration' " + n + "><input type='button' class='gantt_duration_dec' value='-'" + a + "><input type='text' value='5' class='gantt_duration_value'" + a + "><input type='button' class='gantt_duration_inc' value='+'" + a + "> " + i + " <span></span></div>",
                        r = "<div style='height:" + (t.height || 30) + "px;padding-top:0px;font-size:inherit;' class='gantt_section_time'>" + e + " " + s + "</div>";
                    return r
                },
                set_value: function(e, i, n, a) {
                    function s() {
                        var i = t.form_blocks.duration._get_start_date.call(t, e, a),
                            n = t.form_blocks.duration._get_duration.call(t, e, a),
                            s = t.calculateEndDate(i, n);
                        c.innerHTML = t.templates.task_date(s)
                    }

                    function r(t) {
                        var e = l.value;
                        e = parseInt(e, 10), window.isNaN(e) && (e = 0), e += t, 1 > e && (e = 1), l.value = e, s()
                    }
                    var o = a,
                        _ = e.getElementsByTagName("select"),
                        d = e.getElementsByTagName("input"),
                        l = d[1],
                        h = [d[0], d[2]],
                        c = e.getElementsByTagName("span")[0],
                        u = a._time_format_order;
                    h[0].onclick = t.bind(function() {
                        r(-1 * this.config.duration_step)
                    }, this), h[1].onclick = t.bind(function() {
                        r(1 * this.config.duration_step)
                    }, this), _[0].onchange = s, _[1].onchange = s, _[2].onchange = s, _[3] && (_[3].onchange = s), l.onkeydown = t.bind(function(t) {
                        t = t || window.event;
                        var e = t.charCode || t.keyCode || t.which;
                        return 40 == e ? (r(-1 * this.config.duration_step), !1) : 38 == e ? (r(1 * this.config.duration_step), !1) : void window.setTimeout(function(t) {
                            s()
                        }, 1)
                    }, this), l.onchange = t.bind(function(t) {
                        s()
                    }, this);
                    var g = t._resolve_default_mapping(a);
                    "string" == typeof g && (g = {
                        start_date: g
                    });
                    var f = n[g.start_date] || new Date,
                        p = n[g.end_date] || t.calculateEndDate(f, 1),
                        v = Math.round(n[g.duration]) || t.calculateDuration(f, p);
                    t.form_blocks._fill_lightbox_select(_, 0, f, u, o), l.value = v, s()
                },
                _get_start_date: function(e, i) {
                    var n = e.getElementsByTagName("select"),
                        a = i._time_format_order,
                        s = 0,
                        r = 0;
                    if (t.defined(a[3])) {
                        var o = n[a[3]],
                            _ = parseInt(o.value, 10);
                        isNaN(_) && o.hasAttribute("data-value") && (_ = parseInt(o.getAttribute("data-value"), 10)), s = Math.floor(_ / 60), r = _ % 60
                    }
                    return new Date(n[a[2]].value, n[a[1]].value, n[a[0]].value, s, r);
                },
                _get_duration: function(t, e) {
                    var i = t.getElementsByTagName("input")[1];
                    return i = parseInt(i.value, 10), (!i || window.isNaN(i)) && (i = 1), 0 > i && (i *= -1), i
                },
                get_value: function(e, i, n) {
                    var a = t.form_blocks.duration._get_start_date(e, n),
                        s = t.form_blocks.duration._get_duration(e, n),
                        r = t.calculateEndDate(a, s),
                        o = t._resolve_default_mapping(n),
                        _ = {
                            start_date: new Date(a),
                            end_date: new Date(r),
                            duration: s
                        };
                    return "string" == typeof o ? _.start_date : _
                },
                focus: function(e) {
                    t._focus(e.getElementsByTagName("select")[0])
                }
            },
            parent: {
                _filter: function(e, i, n) {
                    var a = i.filter || function() {
                        return !0
                    };
                    e = e.slice(0);
                    for (var s = 0; s < e.length; s++) {
                        var r = e[s];
                        (r.id == n || t.isChildOf(r.id, n) || a(r.id, r) === !1) && (e.splice(s, 1), s--)
                    }
                    return e
                },
                _display: function(e, i) {
                    var n = [],
                        a = [];
                    i && (n = t.getTaskByTime(), e.allow_root && n.unshift({
                        id: t.config.root_id,
                        text: e.root_label || ""
                    }), n = this._filter(n, e, i), e.sort && n.sort(e.sort));
                    for (var s = e.template || t.templates.task_text, r = 0; r < n.length; r++) {
                        var o = s.apply(t, [n[r].start_date, n[r].end_date, n[r]]);
                        void 0 === o && (o = ""), a.push({
                            key: n[r].id,
                            label: o
                        })
                    }
                    return e.options = a, e.map_to = e.map_to || "parent", t.form_blocks.select.render.apply(this, arguments)
                },
                render: function(e) {
                    return t.form_blocks.parent._display(e, !1)
                },
                set_value: function(e, i, n, a) {
                    var s = document.createElement("div");
                    s.innerHTML = t.form_blocks.parent._display(a, n.id);
                    var r = s.removeChild(s.firstChild);
                    return e.onselect = null, e.parentNode.replaceChild(r, e), t.form_blocks.select.set_value.apply(t, [r, i, n, a])
                },
                get_value: function() {
                    return t.form_blocks.select.get_value.apply(t, arguments)
                },
                focus: function() {
                    return t.form_blocks.select.focus.apply(t, arguments)
                }
            }
        }, t._is_lightbox_timepicker = function() {
            for (var t = this._get_typed_lightbox_config(), e = 0; e < t.length; e++)
                if ("time" == t[e].name && "time" == t[e].type) return !0;
            return !1
        }, t._dhtmlx_confirm = function(e, i, n, a) {
            if (!e) return n();
            var s = {
                text: e
            };
            i && (s.title = i), a && (s.ok = a), n && (s.callback = function(t) {
                t && n()
            }), t.confirm(s)
        }, t._get_typed_lightbox_config = function(e) {
            void 0 === e && (e = this.getLightboxType());
            var i = this._get_type_name(e);
            return t.config.lightbox[i + "_sections"] ? t.config.lightbox[i + "_sections"] : t.config.lightbox.sections;
        }, t._silent_redraw_lightbox = function(t) {
            var e = this.getLightboxType();
            if (this.getState().lightbox) {
                var i = this.getState().lightbox,
                    n = this.getLightboxValues(),
                    a = this.copy(this.getTask(i));
                this.resetLightbox();
                var s = this.mixin(a, n, !0),
                    r = this.getLightbox(t ? t : void 0);
                this._center_lightbox(this.getLightbox()), this._set_lightbox_values(s, r)
            } else this.resetLightbox(), this.getLightbox(t ? t : void 0);
            this.callEvent("onLightboxChange", [e, this.getLightboxType()])
        }, t._extend_to_optional = function(e) {
            var i = e,
                n = {
                    render: i.render,
                    focus: i.focus,
                    set_value: function(e, a, s, r) {
                        var o = t._resolve_default_mapping(r);
                        if (!s[o.start_date] || "start_date" == o.start_date && this._isAllowedUnscheduledTask(s)) {
                            n.disable(e, r);
                            var _ = {};
                            for (var d in o) _[o[d]] = s[d];
                            return i.set_value.call(t, e, a, _, r)
                        }
                        return n.enable(e, r), i.set_value.call(t, e, a, s, r)
                    },
                    get_value: function(e, n, a) {
                        return a.disabled ? {
                            start_date: null
                        } : i.get_value.call(t, e, n, a)
                    },
                    update_block: function(e, i) {
                        if (t.callEvent("onSectionToggle", [t._lightbox_id, i]), e.style.display = i.disabled ? "none" : "block",
                            i.button) {
                            var n = e.previousSibling.firstChild.firstChild,
                                a = t.locale.labels,
                                s = i.disabled ? a[i.name + "_enable_button"] : a[i.name + "_disable_button"];
                            n.nextSibling.innerHTML = s
                        }
                        t.resizeLightbox()
                    },
                    disable: function(t, e) {
                        e.disabled = !0, n.update_block(t, e)
                    },
                    enable: function(t, e) {
                        e.disabled = !1, n.update_block(t, e)
                    },
                    button_click: function(e, i, a, s) {
                        if (t.callEvent("onSectionButton", [t._lightbox_id, a]) !== !1) {
                            var r = t._get_typed_lightbox_config()[e];
                            r.disabled ? n.enable(s, r) : n.disable(s, r)
                        }
                    }
                };
            return n
        }, t.form_blocks.duration_optional = t._extend_to_optional(t.form_blocks.duration),
        t.form_blocks.time_optional = t._extend_to_optional(t.form_blocks.time), t.dataProcessor = function(e) {
            return this.serverProcessor = e, this.action_param = "!nativeeditor_status", this.object = null, this.updatedRows = [], this.autoUpdate = !0, this.updateMode = "cell", this._tMode = "GET", this._headers = null, this._payload = null, this.post_delim = "_", this._waitMode = 0, this._in_progress = {}, this._invalid = {}, this.mandatoryFields = [], this.messages = [], this.styles = {
                updated: "font-weight:bold;",
                inserted: "font-weight:bold;",
                deleted: "text-decoration : line-through;",
                invalid: "background-color:FFE0E0;",
                invalid_cell: "border-bottom:2px solid red;",
                error: "color:red;",
                clear: "font-weight:normal;text-decoration:none;"
            }, this.enableUTFencoding(!0), t._eventable(this), this
        }, t.dataProcessor.prototype = {
            setTransactionMode: function(t, e) {
                "object" == typeof t ? (this._tMode = t.mode || this._tMode, this._headers = this._headers || t.headers, this._payload = this._payload || t.payload) : (this._tMode = t, this._tSend = e), "REST" == this._tMode && (this._tSend = !1, this._endnm = !0)
            },
            escape: function(t) {
                return this._utf ? encodeURIComponent(t) : escape(t);
            },
            enableUTFencoding: function(t) {
                this._utf = !!t
            },
            setDataColumns: function(t) {
                this._columns = "string" == typeof t ? t.split(",") : t
            },
            getSyncState: function() {
                return !this.updatedRows.length
            },
            enableDataNames: function(t) {
                this._endnm = !!t
            },
            enablePartialDataSend: function(t) {
                this._changed = !!t
            },
            setUpdateMode: function(t, e) {
                this.autoUpdate = "cell" == t, this.updateMode = t, this.dnd = e
            },
            ignore: function(t, e) {
                this._silent_mode = !0, t.call(e || window), this._silent_mode = !1
            },
            setUpdated: function(t, e, i) {
                if (!this._silent_mode) {
                    var n = this.findRow(t);
                    i = i || "updated";
                    var a = this.obj.getUserData(t, this.action_param);
                    a && "updated" == i && (i = a), e ? (this.set_invalid(t, !1), this.updatedRows[n] = t, this.obj.setUserData(t, this.action_param, i), this._in_progress[t] && (this._in_progress[t] = "wait")) : this.is_invalid(t) || (this.updatedRows.splice(n, 1), this.obj.setUserData(t, this.action_param, "")), e || this._clearUpdateFlag(t), this.markRow(t, e, i), e && this.autoUpdate && this.sendData(t)
                }
            },
            _clearUpdateFlag: function(t) {},
            markRow: function(t, e, i) {
                var n = "",
                    a = this.is_invalid(t);
                if (a && (n = this.styles[a],
                        e = !0), this.callEvent("onRowMark", [t, e, i, a]) && (n = this.styles[e ? i : "clear"] + n, this.obj[this._methods[0]](t, n), a && a.details)) {
                    n += this.styles[a + "_cell"];
                    for (var s = 0; s < a.details.length; s++) a.details[s] && this.obj[this._methods[1]](t, s, n)
                }
            },
            getState: function(t) {
                return this.obj.getUserData(t, this.action_param)
            },
            is_invalid: function(t) {
                return this._invalid[t]
            },
            set_invalid: function(t, e, i) {
                i && (e = {
                    value: e,
                    details: i,
                    toString: function() {
                        return this.value.toString()
                    }
                }), this._invalid[t] = e
            },
            checkBeforeUpdate: function(t) {
                return !0
            },
            sendData: function(t) {
                return !this._waitMode || "tree" != this.obj.mytype && !this.obj._h2 ? (this.obj.editStop && this.obj.editStop(), "undefined" == typeof t || this._tSend ? this.sendAllData() : this._in_progress[t] ? !1 : (this.messages = [], !this.checkBeforeUpdate(t) && this.callEvent("onValidationError", [t, this.messages]) ? !1 : void this._beforeSendData(this._getRowData(t), t))) : void 0
            },
            _beforeSendData: function(t, e) {
                return this.callEvent("onBeforeUpdate", [e, this.getState(e), t]) ? void this._sendData(t, e) : !1
            },
            serialize: function(e, i) {
                if ("string" == typeof e) return e;
                if ("undefined" != typeof i) return this.serialize_one(e, "");
                var n = [],
                    a = [];
                for (var s in e) e.hasOwnProperty(s) && (n.push(this.serialize_one(e[s], s + this.post_delim)), a.push(s));
                return n.push("ids=" + this.escape(a.join(","))), t.security_key && n.push("dhx_security=" + t.security_key), n.join("&")
            },
            serialize_one: function(t, e) {
                if ("string" == typeof t) return t;
                var i = [];
                for (var n in t)
                    if (t.hasOwnProperty(n)) {
                        if (("id" == n || n == this.action_param) && "REST" == this._tMode) continue;
                        i.push(this.escape((e || "") + n) + "=" + this.escape(t[n]));
                    }
                return i.join("&")
            },
            _sendData: function(e, i) {
                if (e) {
                    if (!this.callEvent("onBeforeDataSending", i ? [i, this.getState(i), e] : [null, null, e])) return !1;
                    i && (this._in_progress[i] = (new Date).valueOf());
                    var n = this,
                        a = function(t) {
                            var a = [];
                            if (i) a.push(i);
                            else if (e)
                                for (var s in e) a.push(s);
                            return n.afterUpdate(n, t, a)
                        },
                        s = this.serverProcessor + (this._user ? t._urlSeparator(this.serverProcessor) + ["dhx_user=" + this._user, "dhx_version=" + this.obj.getUserData(0, "version")].join("&") : "");
                    if ("GET" == this._tMode) t.ajax.get(s + (-1 != s.indexOf("?") ? "&" : "?") + this.serialize(e, i), a);
                    else if ("POST" == this._tMode) t.ajax.post(s, this.serialize(e, i), a);
                    else if ("REST" == this._tMode) {
                        var r = this.getState(i),
                            o = s.replace(/(\&|\?)editing\=true/, ""),
                            _ = "",
                            d = "post";
                        if ("inserted" == r ? _ = this.serialize(e, i) : "deleted" == r ? (d = "DELETE", o = o + ("/" == o.slice(-1) ? "" : "/") + i) : (d = "PUT", _ = this.serialize(e, i), o = o + ("/" == o.slice(-1) ? "" : "/") + i), this._payload)
                            for (var l in this._payload) o = o + this._urlSeparator(o) + this.escape(l) + "=" + this.escape(this._payload[l]);
                        t.ajax.query({
                            url: o,
                            method: d,
                            headers: this._headers,
                            data: _,
                            callback: a
                        })
                    }
                    this._waitMode++
                }
            },
            sendAllData: function() {
                if (this.updatedRows.length) {
                    this.messages = [];
                    for (var t = !0, e = 0; e < this.updatedRows.length; e++) t &= this.checkBeforeUpdate(this.updatedRows[e]);
                    if (!t && !this.callEvent("onValidationError", ["", this.messages])) return !1;
                    if (this._tSend) this._sendData(this._getAllData());
                    else
                        for (var e = 0; e < this.updatedRows.length; e++)
                            if (!this._in_progress[this.updatedRows[e]]) {
                                if (this.is_invalid(this.updatedRows[e])) continue;
                                if (this._beforeSendData(this._getRowData(this.updatedRows[e]), this.updatedRows[e]), this._waitMode && ("tree" == this.obj.mytype || this.obj._h2)) return;
                            }
                }
            },
            _getAllData: function(t) {
                for (var e = {}, i = !1, n = 0; n < this.updatedRows.length; n++) {
                    var a = this.updatedRows[n];
                    this._in_progress[a] || this.is_invalid(a) || this.callEvent("onBeforeUpdate", [a, this.getState(a), this._getRowData(a)]) && (e[a] = this._getRowData(a, a + this.post_delim), i = !0, this._in_progress[a] = (new Date).valueOf())
                }
                return i ? e : null
            },
            setVerificator: function(t, e) {
                this.mandatoryFields[t] = e || function(t) {
                    return "" !== t
                }
            },
            clearVerificator: function(t) {
                this.mandatoryFields[t] = !1
            },
            findRow: function(t) {
                var e = 0;
                for (e = 0; e < this.updatedRows.length && t != this.updatedRows[e]; e++);
                return e
            },
            defineAction: function(t, e) {
                this._uActions || (this._uActions = []), this._uActions[t] = e
            },
            afterUpdateCallback: function(t, e, i, n) {
                var a = t,
                    s = "error" != i && "invalid" != i;
                if (s || this.set_invalid(t, i), this._uActions && this._uActions[i] && !this._uActions[i](n)) return delete this._in_progress[a];
                "wait" != this._in_progress[a] && this.setUpdated(t, !1);
                var r = t;
                switch (i) {
                    case "inserted":
                    case "insert":
                        e != t && (this.obj[this._methods[2]](t, e), t = e);
                        break;
                    case "delete":
                    case "deleted":
                        return this.obj.setUserData(t, this.action_param, "true_deleted"),
                            this.obj[this._methods[3]](t), delete this._in_progress[a], this.callEvent("onAfterUpdate", [t, i, e, n])
                }
                "wait" != this._in_progress[a] ? (s && this.obj.setUserData(t, this.action_param, ""), delete this._in_progress[a]) : (delete this._in_progress[a], this.setUpdated(e, !0, this.obj.getUserData(t, this.action_param))), this.callEvent("onAfterUpdate", [r, i, e, n])
            },
            afterUpdate: function(e, i, n) {
                if (window.JSON) try {
                    var a = JSON.parse(i.xmlDoc.responseText),
                        s = a.action || this.getState(n) || "updated",
                        r = a.sid || n[0],
                        o = a.tid || n[0];
                    return e.afterUpdateCallback(r, o, s, a),
                        void e.finalizeUpdate()
                } catch (_) {}
                var d = t.ajax.xmltop("data", i.xmlDoc);
                if (!d) return this.cleanUpdate(n);
                var l = t.ajax.xpath("//data/action", d);
                if (!l.length) return this.cleanUpdate(n);
                for (var h = 0; h < l.length; h++) {
                    var c = l[h],
                        s = c.getAttribute("type"),
                        r = c.getAttribute("sid"),
                        o = c.getAttribute("tid");
                    e.afterUpdateCallback(r, o, s, c)
                }
                e.finalizeUpdate()
            },
            cleanUpdate: function(t) {
                if (t)
                    for (var e = 0; e < t.length; e++) delete this._in_progress[t[e]]
            },
            finalizeUpdate: function() {
                this._waitMode && this._waitMode--, ("tree" == this.obj.mytype || this.obj._h2) && this.updatedRows.length && this.sendData(),
                    this.callEvent("onAfterUpdateFinish", []), this.updatedRows.length || this.callEvent("onFullSync", [])
            },
            init: function(t) {
                this.obj = t, this.obj._dp_init && this.obj._dp_init(this)
            },
            setOnAfterUpdate: function(t) {
                this.attachEvent("onAfterUpdate", t)
            },
            enableDebug: function(t) {},
            setOnBeforeUpdateHandler: function(t) {
                this.attachEvent("onBeforeDataSending", t)
            },
            setAutoUpdate: function(t, e) {
                t = t || 2e3, this._user = e || (new Date).valueOf(), this._need_update = !1, this._update_busy = !1, this.attachEvent("onAfterUpdate", function(t, e, i, n) {
                    this.afterAutoUpdate(t, e, i, n)
                }), this.attachEvent("onFullSync", function() {
                    this.fullSync()
                });
                var i = this;
                window.setInterval(function() {
                    i.loadUpdate()
                }, t)
            },
            afterAutoUpdate: function(t, e, i, n) {
                return "collision" == e ? (this._need_update = !0, !1) : !0
            },
            fullSync: function() {
                return this._need_update && (this._need_update = !1, this.loadUpdate()), !0
            },
            getUpdates: function(e, i) {
                return this._update_busy ? !1 : (this._update_busy = !0, void t.ajax.get(e, i))
            },
            _v: function(t) {
                return t.firstChild ? t.firstChild.nodeValue : ""
            },
            _a: function(t) {
                for (var e = [], i = 0; i < t.length; i++) e[i] = this._v(t[i]);
                return e
            },
            loadUpdate: function() {
                var e = this,
                    i = this.obj.getUserData(0, "version"),
                    n = this.serverProcessor + t._urlSeparator(this.serverProcessor) + ["dhx_user=" + this._user, "dhx_version=" + i].join("&");
                n = n.replace("editing=true&", ""), this.getUpdates(n, function(i) {
                    var n = t.ajax.xpath("//userdata", i);
                    e.obj.setUserData(0, "version", e._v(n[0]));
                    var a = t.ajax.xpath("//update", i);
                    if (a.length) {
                        e._silent_mode = !0;
                        for (var s = 0; s < a.length; s++) {
                            var r = a[s].getAttribute("status"),
                                o = a[s].getAttribute("id"),
                                _ = a[s].getAttribute("parent");
                            switch (r) {
                                case "inserted":
                                    e.callEvent("insertCallback", [a[s], o, _]);
                                    break;
                                case "updated":
                                    e.callEvent("updateCallback", [a[s], o, _]);
                                    break;
                                case "deleted":
                                    e.callEvent("deleteCallback", [a[s], o, _])
                            }
                        }
                        e._silent_mode = !1
                    }
                    e._update_busy = !1, e = null
                })
            }
        }, t._init_dp_live_update_hooks = function(e) {
            e.attachEvent("insertCallback", t._insert_callback), e.attachEvent("updateCallback", t._update_callback), e.attachEvent("deleteCallback", t._delete_callback)
        }, t._update_callback = function(e, i) {
            var n = e.data || t.xml._xmlNodeToJSON(e.firstChild);
            if (t.isTaskExists(i)) {
                var a = t.getTask(i);
                for (var s in n) {
                    var r = n[s];
                    switch (s) {
                        case "id":
                            continue;
                        case "start_date":
                        case "end_date":
                            r = t.templates.xml_date(r);
                            break;
                        case "duration":
                            a.end_date = t.calculateEndDate(a.start_date, r)
                    }
                    a[s] = r
                }
                t.updateTask(i), t.refreshData()
            }
        }, t._insert_callback = function(e, i, n, a) {
            var s = e.data || t.xml._xmlNodeToJSON(e.firstChild),
                r = {
                    add: t.addTask,
                    isExist: t.isTaskExists
                };
            "links" == a && (r.add = t.addLink, r.isExist = t.isLinkExists), r.isExist.call(t, i) || (s.id = i, r.add.call(t, s))
        }, t._delete_callback = function(e, i, n, a) {
            var s = {
                "delete": t.deleteTask,
                isExist: t.isTaskExists
            };
            "links" == a && (s["delete"] = t.deleteLink, s.isExist = t.isLinkExists), s.isExist.call(t, i) && s["delete"].call(t, i)
        }, t._get_safe_type = function(e) {
            for (var i in this.config.types)
                if (this.config.types[i] == e) return e;
            return t.config.types.task
        }, t.form_blocks.typeselect = {
            render: function(e) {
                var i = t.config.types,
                    n = t.locale.labels,
                    a = [],
                    s = e.filter || function() {
                        return !0
                    };
                for (var r in i) !s(r, i[r]) == !1 && a.push({
                    key: i[r],
                    label: n["type_" + r]
                });
                e.options = a;
                var o = e.onchange;
                return e.onchange = function() {
                    t.getState().lightbox;
                    t.changeLightboxType(this.value), "function" == typeof o && o.apply(this, arguments)
                }, t.form_blocks.select.render.apply(t, arguments)
            },
            set_value: function() {
                return t.form_blocks.select.set_value.apply(t, arguments)
            },
            get_value: function() {
                return t.form_blocks.select.get_value.apply(t, arguments)
            },
            focus: function() {
                return t.form_blocks.select.focus.apply(this, arguments)
            }
        },
        function() {
            function e() {
                return t._cached_functions.update_if_changed(t), t._cached_functions.active || t._cached_functions.activate(), !0
            }
            t._cached_functions = {
                cache: {},
                mode: !1,
                critical_path_mode: !1,
                wrap_methods: function(t, e) {
                    if (e._prefetch_originals)
                        for (var i in e._prefetch_originals) e[i] = e._prefetch_originals[i];
                    e._prefetch_originals = {};
                    for (var i = 0; i < t.length; i++) this.prefetch(t[i], e)
                },
                prefetch: function(t, e) {
                    var i = e[t];
                    if (i) {
                        var n = this;
                        e._prefetch_originals[t] = i, e[t] = function() {
                            if (n.active) {
                                var e = n.get_arguments_hash(Array.prototype.slice.call(arguments));
                                n.cache[t] || (n.cache[t] = {});
                                var a = n.cache[t];
                                if (n.has_cached_value(a, e)) return n.get_cached_value(a, e);
                                var s = i.apply(this, arguments);
                                return n.cache_value(a, e, s), s
                            }
                            return i.apply(this, arguments)
                        }
                    }
                    return i
                },
                cache_value: function(t, e, i) {
                    this.is_date(i) && (i = new Date(i)), t[e] = i
                },
                has_cached_value: function(t, e) {
                    return t.hasOwnProperty(e)
                },
                get_cached_value: function(t, e) {
                    var i = t[e];
                    return this.is_date(i) && (i = new Date(i)), i
                },
                is_date: function(t) {
                    return t && t.getUTCDate
                },
                get_arguments_hash: function(t) {
                    for (var e = [], i = 0; i < t.length; i++) e.push(this.stringify_argument(t[i]));
                    return "(" + e.join(";") + ")"
                },
                stringify_argument: function(t) {
                    var e = "";
                    return e = t.id ? t.id : this.is_date(t) ? t.valueOf() : t, e + ""
                },
                activate: function() {
                    this.clear(), this.active = !0
                },
                deactivate: function() {
                    this.clear(), this.active = !1
                },
                clear: function() {
                    this.cache = {}
                },
                setup: function(t) {
                    var e = [],
                        i = ["isCriticalTask", "isCriticalLink", "_isProjectEnd", "_getProjectEnd"];
                    "auto" == this.mode ? t.config.highlight_critical_path && (e = i) : this.mode === !0 && (e = i), this.wrap_methods(e, t)
                },
                update_if_changed: function(t) {
                    var e = this.critical_path_mode != t.config.highlight_critical_path || this.mode !== t.config.optimize_render;
                    e && (this.critical_path_mode = t.config.highlight_critical_path, this.mode = t.config.optimize_render, this.setup(t))
                }
            }, t.attachEvent("onBeforeGanttRender", e), t.attachEvent("onBeforeDataRender", e), t.attachEvent("onBeforeParse", e), t.attachEvent("onDataRender", function() {
                t._cached_functions.deactivate()
            }), t.attachEvent("onBeforeGanttReady", function() {
                return t._cached_functions.update_if_changed(t), !0
            })
        }(), t.assert = function(e, i) {
            e || t.config.show_errors && t.callEvent("onError", [i]) !== !1 && t.message({
                type: "error",
                text: i,
                expire: -1
            })
        }, t.init = function(e, i, n) {
            this.callEvent("onBeforeGanttReady", []), i && n && (this.config.start_date = this._min_date = new Date(i), this.config.end_date = this._max_date = new Date(n)), this._init_skin(), this.date.init(), this.config.scroll_size || (this.config.scroll_size = this._detectScrollSize()), t.event(window, "resize", this._on_resize), this.init = function(t) {
                this.$container && this.$container.parentNode && (this.$container.parentNode.removeChild(this.$container), this.$container = null), this._reinit(t);
            }, this._reinit(e)
        }, t._reinit = function(e) {
            this._init_html_area(e), this._set_sizes(), this._clear_renderers(), this.resetLightbox(), this._update_flags(), this._init_touch_events(), this._init_templates(), this._init_grid(), this._init_tasks(), this._set_scroll_events(), t.event(this.$container, "click", this._on_click), t.event(this.$container, "dblclick", this._on_dblclick), t.event(this.$container, "mousemove", this._on_mousemove), t.event(this.$container, "contextmenu", this._on_contextmenu), this.callEvent("onGanttReady", []),
                this.render()
        }, t._init_html_area = function(e) {
            "string" == typeof e ? this._obj = document.getElementById(e) : this._obj = e, window.gantt !== t && (this._obj.gantt = t), this.assert(this._obj, "Invalid html container: " + e);
            var i = "<div class='gantt_container'><div class='gantt_grid'></div><div class='gantt_task'></div>";
            i += "<div class='gantt_ver_scroll'><div></div></div><div class='gantt_hor_scroll'><div></div></div></div>", this._obj.innerHTML = i, this.$container = this._obj.firstChild;
            var n = this.$container.childNodes;
            this.$grid = n[0],
                this.$task = n[1], this.$scroll_ver = n[2], this.$scroll_hor = n[3], this.$grid.innerHTML = "<div class='gantt_grid_scale'></div><div class='gantt_grid_data'></div>", this.$grid_scale = this.$grid.childNodes[0], this.$grid_data = this.$grid.childNodes[1], this.$task.innerHTML = "<div class='gantt_task_scale'></div><div class='gantt_data_area'><div class='gantt_task_bg'></div><div class='gantt_links_area'></div><div class='gantt_bars_area'></div></div>", this.$task_scale = this.$task.childNodes[0], this.$task_data = this.$task.childNodes[1],
                this.$task_bg = this.$task_data.childNodes[0], this.$task_links = this.$task_data.childNodes[1], this.$task_bars = this.$task_data.childNodes[2]
        }, t.$click = {
            buttons: {
                edit: function(e) {
                    t.showLightbox(e)
                },
                "delete": function(e) {
                    var i = t.locale.labels.confirm_deleting,
                        n = t.locale.labels.confirm_deleting_title;
                    t._dhtmlx_confirm(i, n, function() {
                        if (!t.isTaskExists(e)) return void t.hideLightbox();
                        var i = t.getTask(e);
                        i.$new ? (t._deleteTask(e, !0), t.refreshData()) : t.deleteTask(e), t.hideLightbox()
                    })
                }
            }
        }, t._calculate_content_height = function() {
            var t = this.config.scale_height,
                e = this._order.length * this.config.row_height,
                i = this._scroll_hor ? this.config.scroll_size + 1 : 0;
            return this._is_grid_visible() || this._is_chart_visible() ? t + e + 2 + i : 0
        }, t._calculate_content_width = function() {
            var t = this._get_grid_width(),
                e = this._tasks ? this._tasks.full_width : 0;
            this._scroll_ver ? this.config.scroll_size + 1 : 0;
            return this._is_chart_visible() || (e = 0), this._is_grid_visible() || (t = 0), t + e + 1
        }, t._get_resize_options = function() {
            var t = {
                x: !1,
                y: !1
            };
            return "xy" == this.config.autosize ? t.x = t.y = !0 : "y" == this.config.autosize || this.config.autosize === !0 ? t.y = !0 : "x" == this.config.autosize && (t.x = !0),
                t
        }, t._clean_el_size = function(t) {
            return 1 * (t || "").toString().replace("px", "") || 0
        }, t._get_box_styles = function() {
            var t = null;
            t = window.getComputedStyle ? window.getComputedStyle(this._obj, null) : {
                width: this._obj.clientWidth,
                height: this._obj.clientHeight
            };
            var e = ["width", "height", "paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "borderLeftWidth", "borderRightWidth", "borderTopWidth", "borderBottomWidth"],
                i = {
                    boxSizing: "border-box" == t.boxSizing
                };
            t.MozBoxSizing && (i.boxSizing = "border-box" == t.MozBoxSizing);
            for (var n = 0; n < e.length; n++) i[e[n]] = t[e[n]] ? this._clean_el_size(t[e[n]]) : 0;
            var a = {
                horPaddings: i.paddingLeft + i.paddingRight + i.borderLeftWidth + i.borderRightWidth,
                vertPaddings: i.paddingTop + i.paddingBottom + i.borderTopWidth + i.borderBottomWidth,
                borderBox: i.boxSizing,
                innerWidth: i.width,
                innerHeight: i.height,
                outerWidth: i.width,
                outerHeight: i.height
            };
            return a.borderBox ? (a.innerWidth -= a.horPaddings, a.innerHeight -= a.vertPaddings) : (a.outerWidth += a.horPaddings, a.outerHeight += a.vertPaddings), a
        }, t._do_autosize = function() {
            var t = this._get_resize_options(),
                e = this._get_box_styles();
            if (t.y) {
                var i = this._calculate_content_height();
                e.borderBox && (i += e.vertPaddings), this._obj.style.height = i + "px"
            }
            if (t.x) {
                var n = this._calculate_content_width();
                e.borderBox && (n += e.horPaddings), this._obj.style.width = n + "px"
            }
        }, t._set_sizes = function() {
            this._do_autosize();
            var t = this._get_box_styles();
            if (this._y = t.innerHeight, !(this._y < 20)) {
                this.$grid.style.height = this.$task.style.height = Math.max(this._y - this.$scroll_hor.offsetHeight - 2, 0) + "px";
                var e = Math.max(this._y - (this.config.scale_height || 0) - this.$scroll_hor.offsetHeight - 2, 0);
                this.$grid_data.style.height = this.$task_data.style.height = e + "px";
                var i = Math.max(this._get_grid_width() - 1, 0);
                this.$grid.style.width = i + "px", this.$grid.style.display = 0 === i ? "none" : "", t = this._get_box_styles(), this._x = t.innerWidth, this._x < 20 || (this.$grid_data.style.width = Math.max(this._get_grid_width() - 1, 0) + "px", this.$task.style.width = Math.max(this._x - this._get_grid_width() - 2, 0) + "px")
            }
        }, t.getScrollState = function() {
            return this.$task && this.$task_data ? {
                x: this.$task.scrollLeft,
                y: this.$task_data.scrollTop
            } : null;
        }, t._save_scroll_state = function(t, e) {
            var i = {};
            this._cached_scroll_pos = this._cached_scroll_pos || {}, void 0 !== t && (i.x = Math.max(t, 0)), void 0 !== e && (i.y = Math.max(e, 0)), this.mixin(this._cached_scroll_pos, i, !0)
        }, t._restore_scroll_state = function() {
            var t = {
                x: 0,
                y: 0
            };
            return this._cached_scroll_pos && (t.x = this._cached_scroll_pos.x || t.x, t.y = this._cached_scroll_pos.y || t.y), t
        }, t.scrollTo = function(e, i) {
            var n = this._restore_scroll_state();
            1 * e == e && (this.$task.scrollLeft = e, this._save_scroll_state(e, void 0)), 1 * i == i && (this.$task_data.scrollTop = i,
                this.$grid_data.scrollTop = i, t.config.smart_rendering && this.$grid_data.scrollTop != i && (this.$grid_data.scrollTop = i % t.config.row_height), this._save_scroll_state(void 0, this.$task_data.scrollTop));
            var a = t._restore_scroll_state();
            this.callEvent("onGanttScroll", [n.x, n.y, a.x, a.y])
        }, t.showDate = function(t) {
            var e = this.posFromDate(t),
                i = Math.max(e - this.config.task_scroll_offset, 0);
            this.scrollTo(i)
        }, t.showTask = function(t) {
            var e = this.getTaskNode(t);
            if (e) {
                var i = Math.max(e.offsetLeft - this.config.task_scroll_offset, 0),
                    n = e.offsetTop - (this.$task_data.offsetHeight - this.config.row_height) / 2;
                this.scrollTo(i, n)
            }
        }, t._on_resize = t.setSizes = function() {
            t._set_sizes(), t._scroll_resize()
        }, t.render = function() {
            if (this._is_render_active()) {
                this.callEvent("onBeforeGanttRender", []);
                var e = this.copy(this._restore_scroll_state()),
                    i = null;
                if (e && (i = t.dateFromPos(e.x + this.config.task_scroll_offset)), this._render_grid(), this._render_tasks_scales(), this._scroll_resize(), this._on_resize(), this._render_data(), this.config.preserve_scroll && e) {
                    var n = t._restore_scroll_state(),
                        a = t.dateFromPos(n.x);
                    (+i != +a || n.y != e.y) && (i && this.showDate(i),
                        t.scrollTo(void 0, e.y))
                }
                this.callEvent("onGanttRender", [])
            }
        }, t._set_scroll_events = function() {
            function e(e) {
                var n = t._get_resize_options();
                t._wheel_time = new Date;
                var a = i ? -20 * e.deltaX : 2 * e.wheelDeltaX,
                    s = i ? -40 * e.deltaY : e.wheelDelta;
                if (a && Math.abs(a) > Math.abs(s)) {
                    if (n.x) return !0;
                    if (!t.$scroll_hor || !t.$scroll_hor.offsetWidth) return !0;
                    var r = a / -40,
                        o = t.$task.scrollLeft,
                        _ = o + 30 * r;
                    if (t.scrollTo(_, null), t.$scroll_hor.scrollLeft = _, o == t.$task.scrollLeft) return !0
                } else {
                    if (n.y) return !0;
                    if (!t.$scroll_ver || !t.$scroll_ver.offsetHeight) return !0;
                    var r = s / -40;
                    "undefined" == typeof s && (r = e.detail);
                    var d = t.$scroll_ver.scrollTop,
                        l = t.$scroll_ver.scrollTop + 30 * r;
                    if (!t.config.prevent_default_scroll && t._cached_scroll_pos && (t._cached_scroll_pos.y == l || t._cached_scroll_pos.y <= 0 && 0 >= l)) return !0;
                    if (t.scrollTo(null, l), t.$scroll_ver.scrollTop = l, d == t.$scroll_ver.scrollTop) return !0
                }
                return e.preventDefault && e.preventDefault(), e.cancelBubble = !0, !1
            }
            this.event(this.$scroll_hor, "scroll", function() {
                if (new Date - (t._wheel_time || 0) < 100) return !0;
                if (!t._touch_scroll_active) {
                    var e = t.$scroll_hor.scrollLeft;
                    t.scrollTo(e)
                }
            }), this.event(this.$scroll_ver, "scroll", function() {
                if (!t._touch_scroll_active) {
                    var e = t.$scroll_ver.scrollTop;
                    t.$grid_data.scrollTop = e, t.scrollTo(null, e)
                }
            }), this.event(this.$task, "scroll", function() {
                var e = t.$task.scrollLeft,
                    i = t.$scroll_hor.scrollLeft;
                i != e && (t.$scroll_hor.scrollLeft = e)
            }), this.event(this.$task_data, "scroll", function() {
                var e = t.$task_data.scrollTop,
                    i = t.$scroll_ver.scrollTop;
                i != e && (t.$scroll_ver.scrollTop = e)
            });
            var i = t.env.isFF;
            i ? this.event(t.$container, "wheel", e) : this.event(t.$container, "mousewheel", e);
        }, t._scroll_resize = function() {
            if (!(this._x < 20 || this._y < 20)) {
                var t = this._scroll_sizes();
                t.x ? (this.$scroll_hor.style.display = "block", this.$scroll_hor.style.height = t.scroll_size + "px", this.$scroll_hor.style.width = t.x + "px", this.$scroll_hor.firstChild.style.width = t.x_inner + "px") : (this.$scroll_hor.style.display = "none", this.$scroll_hor.style.height = this.$scroll_hor.style.width = "0px"), t.y ? (this.$scroll_ver.style.display = "block", this.$scroll_ver.style.width = t.scroll_size + "px", this.$scroll_ver.style.height = t.y + "px",
                    this.$scroll_ver.style.top = this.config.scale_height + "px", this.$scroll_ver.firstChild.style.height = t.y_inner + "px") : (this.$scroll_ver.style.display = "none", this.$scroll_ver.style.width = this.$scroll_ver.style.height = "0px")
            }
        }, t._scroll_sizes = function() {
            var t = this._get_grid_width(),
                e = Math.max(this._x - t, 0),
                i = Math.max(this._y - this.config.scale_height, 0),
                n = this.config.scroll_size + 1,
                a = Math.max(this.$task_data.offsetWidth - n, 0),
                s = this.config.row_height * this._order.length,
                r = this._get_resize_options(),
                o = this._scroll_hor = r.x ? !1 : a > e,
                _ = this._scroll_ver = r.y ? !1 : s > i,
                d = {
                    x: !1,
                    y: !1,
                    scroll_size: n,
                    x_inner: a + t + n + 2,
                    y_inner: this.config.scale_height + s
                };
            return o && (d.x = Math.max(this._x - (_ ? n : 2), 0)), _ && (d.y = Math.max(this._y - (o ? n : 0) - this.config.scale_height, 0)), d
        }, t._getClassName = function(e) {
            if (!e) return "";
            var i = e.className || "";
            return i.baseVal && (i = i.baseVal), i.indexOf || (i = ""), t._trim(i)
        }, t.locate = function(e) {
            var i = t._get_target_node(e),
                n = t._getClassName(i);
            if ((n || "").indexOf("gantt_task_cell") >= 0) return null;
            for (var a = arguments[1] || this.config.task_attribute; i;) {
                if (i.getAttribute) {
                    var s = i.getAttribute(a);
                    if (s) return s
                }
                i = i.parentNode
            }
            return null
        }, t._get_target_node = function(t) {
            var e;
            return t.tagName ? e = t : (t = t || window.event, e = t.target || t.srcElement), e
        }, t._trim = function(t) {
            var e = String.prototype.trim || function() {
                return this.replace(/^\s+|\s+$/g, "")
            };
            return e.apply(t)
        }, t._locate_css = function(e, i, n) {
            void 0 === n && (n = !0);
            for (var a = t._get_target_node(e), s = ""; a;) {
                if (s = t._getClassName(a)) {
                    var r = s.indexOf(i);
                    if (r >= 0) {
                        if (!n) return a;
                        var o = 0 === r || !t._trim(s.charAt(r - 1)),
                            _ = r + i.length >= s.length || !t._trim(s.charAt(r + i.length));
                        if (o && _) return a
                    }
                }
                a = a.parentNode
            }
            return null
        }, t._locateHTML = function(e, i) {
            var n = t._get_target_node(e);
            for (i = i || this.config.task_attribute; n;) {
                if (n.getAttribute) {
                    var a = n.getAttribute(i);
                    if (a) return n
                }
                n = n.parentNode
            }
            return null
        }, t.getTaskRowNode = function(t) {
            for (var e = this.$grid_data.childNodes, i = this.config.task_attribute, n = 0; n < e.length; n++)
                if (e[n].getAttribute) {
                    var a = e[n].getAttribute(i);
                    if (a == t) return e[n]
                }
            return null
        }, t.getState = function() {
            return {
                drag_id: this._tasks_dnd.drag.id,
                drag_mode: this._tasks_dnd.drag.mode,
                drag_from_start: this._tasks_dnd.drag.left,
                selected_task: this._selected_task,
                min_date: new Date(this._min_date),
                max_date: new Date(this._max_date),
                lightbox: this._lightbox_id,
                touch_drag: this._touch_drag
            }
        }, t._checkTimeout = function(t, e) {
            if (!e) return !0;
            var i = 1e3 / e;
            return 1 > i ? !0 : t._on_timeout ? !1 : (setTimeout(function() {
                delete t._on_timeout
            }, i), t._on_timeout = !0, !0)
        }, t.selectTask = function(t) {
            if (!this.config.select_task) return !1;
            if (t) {
                if (this._selected_task == t) return this._selected_task;
                if (!this.callEvent("onBeforeTaskSelected", [t])) return !1;
                this.unselectTask(), this._selected_task = t, this.refreshTask(t), this.callEvent("onTaskSelected", [t])
            }
            return this._selected_task
        }, t.unselectTask = function(t) {
            var t = t || this._selected_task;
            t && (this._selected_task = null, this.refreshTask(t), this.callEvent("onTaskUnselected", [t]))
        }, t.getSelectedId = function() {
            return this.defined(this._selected_task) ? this._selected_task : null
        }, t.changeLightboxType = function(e) {
            return this.getLightboxType() == e ? !0 : void t._silent_redraw_lightbox(e)
        }, t._is_render_active = function() {
            return !this._skip_render
        }, t._correct_dst_change = function(e, i, n, a) {
            var s = t._get_line(a) * n;
            if (s > 3600 && 86400 > s) {
                var r = e.getTimezoneOffset() - i;
                r && (e = t.date.add(e, r, "minute"))
            }
            return e
        }, t.batchUpdate = function(t, e) {
            var i, n = this._dp && "off" != this._dp.updateMode;
            n && (i = this._dp.updateMode, this._dp.setUpdateMode("off"));
            var a = this._sync_order;
            this._sync_order = function() {};
            var s = this._sync_links;
            this._sync_links = function() {};
            var r = this._adjust_scales;
            this._adjust_scales = function() {};
            var o = {},
                _ = this.resetProjectDates;
            this.resetProjectDates = function(t) {
                o[t.id] = t
            }, this._skip_render = !0, this.callEvent("onBeforeBatchUpdate", []);
            try {
                t()
            } catch (d) {}
            this.callEvent("onAfterBatchUpdate", []), this._sync_order = a, this._sync_order(), this._sync_links = s, this._sync_links(), this.resetProjectDates = _;
            for (var l in o) this.resetProjectDates(o[l]);
            this._adjust_scales = r, this._adjust_scales(), this._skip_render = !1, e || this.render(), n && (this._dp.setUpdateMode(i), this._dp.setGanttMode("tasks"), this._dp.sendData(), this._dp.setGanttMode("links"),
                this._dp.sendData())
        }, t.env = {
            isIE: navigator.userAgent.indexOf("MSIE") >= 0 || navigator.userAgent.indexOf("Trident") >= 0,
            isIE6: !window.XMLHttpRequest && navigator.userAgent.indexOf("MSIE") >= 0,
            isIE7: navigator.userAgent.indexOf("MSIE 7.0") >= 0 && navigator.userAgent.indexOf("Trident") < 0,
            isIE8: navigator.userAgent.indexOf("MSIE 8.0") >= 0 && navigator.userAgent.indexOf("Trident") >= 0,
            isOpera: navigator.userAgent.indexOf("Opera") >= 0,
            isChrome: navigator.userAgent.indexOf("Chrome") >= 0,
            isKHTML: navigator.userAgent.indexOf("Safari") >= 0 || navigator.userAgent.indexOf("Konqueror") >= 0,
            isFF: navigator.userAgent.indexOf("Firefox") >= 0,
            isIPad: navigator.userAgent.search(/iPad/gi) >= 0,
            isEdge: -1 != navigator.userAgent.indexOf("Edge")
        }, t.ajax = {
            cache: !0,
            method: "get",
            parse: function(e) {
                if ("string" != typeof e) return e;
                var i;
                return e = e.replace(/^[\s]+/, ""), window.DOMParser && !t.env.isIE ? i = (new window.DOMParser).parseFromString(e, "text/xml") : window.ActiveXObject !== window.undefined && (i = new window.ActiveXObject("Microsoft.XMLDOM"), i.async = "false", i.loadXML(e)), i
            },
            xmltop: function(e, i, n) {
                if ("undefined" == typeof i.status || i.status < 400) {
                    var a = i.responseXML ? i.responseXML || i : t.ajax.parse(i.responseText || i);
                    if (a && null !== a.documentElement && !a.getElementsByTagName("parsererror").length) return a.getElementsByTagName(e)[0]
                }
                return -1 !== n && t.callEvent("onLoadXMLError", ["Incorrect XML", arguments[1], n]), document.createElement("DIV")
            },
            xpath: function(e, i) {
                if (i.nodeName || (i = i.responseXML || i), t.env.isIE) return i.selectNodes(e) || [];
                for (var n, a = [], s = (i.ownerDocument || i).evaluate(e, i, null, XPathResult.ANY_TYPE, null);;) {
                    if (n = s.iterateNext(), !n) break;
                    a.push(n)
                }
                return a
            },
            query: function(e) {
                t.ajax._call(e.method || "GET", e.url, e.data || "", e.async || !0, e.callback, null, e.headers)
            },
            get: function(t, e) {
                this._call("GET", t, null, !0, e)
            },
            getSync: function(t) {
                return this._call("GET", t, null, !1)
            },
            put: function(t, e, i) {
                this._call("PUT", t, e, !0, i)
            },
            del: function(t, e, i) {
                this._call("DELETE", t, e, !0, i)
            },
            post: function(t, e, i) {
                1 == arguments.length ? e = "" : 2 != arguments.length || "function" != typeof e && "function" != typeof window[e] ? e = String(e) : (i = e, e = ""), this._call("POST", t, e, !0, i)
            },
            postSync: function(t, e) {
                return e = null === e ? "" : String(e), this._call("POST", t, e, !1)
            },
            getLong: function(t, e) {
                this._call("GET", t, null, !0, e, {
                    url: t
                })
            },
            postLong: function(t, e, i) {
                2 == arguments.length && (i = e, e = ""), this._call("POST", t, e, !0, i, {
                    url: t,
                    postData: e
                })
            },
            _call: function(e, i, n, a, s, r, o) {
                var _ = window.XMLHttpRequest && !t.env.isIE ? new XMLHttpRequest : new ActiveXObject("Microsoft.XMLHTTP"),
                    d = null !== navigator.userAgent.match(/AppleWebKit/) && null !== navigator.userAgent.match(/Qt/) && null !== navigator.userAgent.match(/Safari/);
                if (a && (_.onreadystatechange = function() {
                        if (4 == _.readyState || d && 3 == _.readyState) {
                            if ((200 != _.status || "" === _.responseText) && !t.callEvent("onAjaxError", [_])) return;
                            window.setTimeout(function() {
                                "function" == typeof s && s.apply(window, [{
                                    xmlDoc: _,
                                    filePath: i
                                }]), r && ("undefined" != typeof r.postData ? t.ajax.postLong(r.url, r.postData, s) : t.ajax.getLong(r.url, s)), s = null, _ = null
                            }, 1)
                        }
                    }), "GET" != e || this.cache || (i += (i.indexOf("?") >= 0 ? "&" : "?") + "dhxr" + (new Date).getTime() + "=1"), _.open(e, i, a), o)
                    for (var l in o) _.setRequestHeader(l, o[l]);
                else "POST" == e.toUpperCase() || "PUT" == e || "DELETE" == e ? _.setRequestHeader("Content-Type", "application/x-www-form-urlencoded") : "GET" == e && (n = null);
                return _.setRequestHeader("X-Requested-With", "XMLHttpRequest"), _.send(n), a ? void 0 : {
                    xmlDoc: _,
                    filePath: i
                }
            }
        }, t._urlSeparator = function(t) {
            return -1 != t.indexOf("?") ? "&" : "?"
        },
        function() {
            function e(t, e) {
                var i = t.callback;
                n(!1), t.box.parentNode.removeChild(t.box), u = t.box = null, i && i(e)
            }

            function i(i) {
                if (u) {
                    i = i || event;
                    var n = i.which || event.keyCode;
                    return t.message.keyboard && ((13 == n || 32 == n) && e(u, !0), 27 == n && e(u, !1)), i.preventDefault && i.preventDefault(), !(i.cancelBubble = !0)
                }
            }

            function n(t) {
                n.cover || (n.cover = document.createElement("DIV"),
                    n.cover.onkeydown = i, n.cover.className = "dhx_modal_cover", document.body.appendChild(n.cover));
                document.body.scrollHeight;
                n.cover.style.display = t ? "inline-block" : "none"
            }

            function a(t, e) {
                var i = "gantt_" + t.toLowerCase().replace(/ /g, "_") + "_button dhtmlx_" + t.toLowerCase().replace(/ /g, "_") + "_button";
                return "<div class='gantt_popup_button dhtmlx_popup_button " + i + "' result='" + e + "' ><div>" + t + "</div></div>"
            }

            function s(t) {
                g.area || (g.area = document.createElement("DIV"), g.area.className = "gantt_message_area dhtmlx_message_area",
                    g.area.style[g.position] = "5px", document.body.appendChild(g.area)), g.hide(t.id);
                var e = document.createElement("DIV");
                return e.innerHTML = "<div>" + t.text + "</div>", e.className = "gantt-info dhtmlx-info gantt-" + t.type + " dhtmlx-" + t.type, e.onclick = function() {
                    g.hide(t.id), t = null
                }, "bottom" == g.position && g.area.firstChild ? g.area.insertBefore(e, g.area.firstChild) : g.area.appendChild(e), t.expire > 0 && (g.timers[t.id] = window.setTimeout(function() {
                    g.hide(t.id)
                }, t.expire)), g.pull[t.id] = e, e = null, t.id
            }

            function r(t, i, n) {
                var s = document.createElement("DIV");
                s.className = " gantt_modal_box dhtmlx_modal_box gantt-" + t.type + " dhtmlx-" + t.type, s.setAttribute("dhxbox", 1);
                var r = "";
                if (t.width && (s.style.width = t.width), t.height && (s.style.height = t.height), t.title && (r += '<div class="gantt_popup_title dhtmlx_popup_title">' + t.title + "</div>"), r += '<div class="gantt_popup_text dhtmlx_popup_text"><span>' + (t.content ? "" : t.text) + '</span></div><div  class="gantt_popup_controls dhtmlx_popup_controls">', i && (r += a(t.ok || "OK", !0)), n && (r += a(t.cancel || "Cancel", !1)), t.buttons)
                    for (var o = 0; o < t.buttons.length; o++) r += a(t.buttons[o], o);
                if (r += "</div>", s.innerHTML = r, t.content) {
                    var _ = t.content;
                    "string" == typeof _ && (_ = document.getElementById(_)), "none" == _.style.display && (_.style.display = ""), s.childNodes[t.title ? 1 : 0].appendChild(_)
                }
                return s.onclick = function(i) {
                    i = i || event;
                    var n = i.target || i.srcElement;
                    if (n.className || (n = n.parentNode), "gantt_popup_button" == n.className.split(" ")[0]) {
                        var a = n.getAttribute("result");
                        a = "true" == a || ("false" == a ? !1 : a), e(t, a)
                    }
                }, t.box = s, (i || n) && (u = t), s
            }

            function o(e, a, s) {
                var o = e.tagName ? e : r(e, a, s);
                e.hidden || n(!0),
                    document.body.appendChild(o);
                var _ = Math.abs(Math.floor(((window.innerWidth || document.documentElement.offsetWidth) - o.offsetWidth) / 2)),
                    d = Math.abs(Math.floor(((window.innerHeight || document.documentElement.offsetHeight) - o.offsetHeight) / 2));
                return "top" == e.position ? o.style.top = "-3px" : o.style.top = d + "px", o.style.left = _ + "px", o.onkeydown = i, o.focus(), e.hidden && t.modalbox.hide(o), o
            }

            function _(t) {
                return o(t, !0, !1)
            }

            function d(t) {
                return o(t, !0, !0)
            }

            function l(t) {
                return o(t)
            }

            function h(t, e, i) {
                return "object" != typeof t && ("function" == typeof e && (i = e,
                    e = ""), t = {
                    text: t,
                    type: e,
                    callback: i
                }), t
            }

            function c(t, e, i, n) {
                return "object" != typeof t && (t = {
                    text: t,
                    type: e,
                    expire: i,
                    id: n
                }), t.id = t.id || g.uid(), t.expire = t.expire || g.expire, t
            }
            var u = null;
            document.attachEvent ? document.attachEvent("onkeydown", i) : document.addEventListener("keydown", i, !0), t.alert = function() {
                var t = h.apply(this, arguments);
                return t.type = t.type || "confirm", _(t)
            }, t.confirm = function() {
                var t = h.apply(this, arguments);
                return t.type = t.type || "alert", d(t)
            }, t.modalbox = function() {
                var t = h.apply(this, arguments);
                return t.type = t.type || "alert", l(t)
            }, t.modalbox.hide = function(t) {
                for (; t && t.getAttribute && !t.getAttribute("dhxbox");) t = t.parentNode;
                t && (t.parentNode.removeChild(t), n(!1))
            };
            var g = t.message = function(t, e, i, n) {
                t = c.apply(this, arguments), t.type = t.type || "info";
                var a = t.type.split("-")[0];
                switch (a) {
                    case "alert":
                        return _(t);
                    case "confirm":
                        return d(t);
                    case "modalbox":
                        return l(t);
                    default:
                        return s(t)
                }
            };
            g.seed = (new Date).valueOf(), g.uid = function() {
                    return g.seed++
                }, g.expire = 4e3, g.keyboard = !0, g.position = "top", g.pull = {},
                g.timers = {}, g.hideAll = function() {
                    for (var t in g.pull) g.hide(t)
                }, g.hide = function(t) {
                    var e = g.pull[t];
                    e && e.parentNode && (window.setTimeout(function() {
                        e.parentNode.removeChild(e), e = null
                    }, 2e3), e.className += " hidden", g.timers[t] && window.clearTimeout(g.timers[t]), delete g.pull[t])
                }
        }(), t.date = {
            init: function() {
                for (var e = t.locale.date.month_short, i = t.locale.date.month_short_hash = {}, n = 0; n < e.length; n++) i[e[n]] = n;
                for (var e = t.locale.date.month_full, i = t.locale.date.month_full_hash = {}, n = 0; n < e.length; n++) i[e[n]] = n;
            },
            date_part: function(t) {
                var e = new Date(t);
                return t.setHours(0), this.hour_start(t), t.getHours() && (t.getDate() < e.getDate() || t.getMonth() < e.getMonth() || t.getFullYear() < e.getFullYear()) && t.setTime(t.getTime() + 36e5 * (24 - t.getHours())), t
            },
            time_part: function(t) {
                return (t.valueOf() / 1e3 - 60 * t.getTimezoneOffset()) % 86400
            },
            week_start: function(e) {
                var i = e.getDay();
                return t.config.start_on_monday && (0 === i ? i = 6 : i--), this.date_part(this.add(e, -1 * i, "day"))
            },
            month_start: function(t) {
                return t.setDate(1), this.date_part(t)
            },
            year_start: function(t) {
                return t.setMonth(0), this.month_start(t)
            },
            day_start: function(t) {
                return this.date_part(t)
            },
            hour_start: function(t) {
                return t.getMinutes() && t.setMinutes(0), this.minute_start(t), t
            },
            minute_start: function(t) {
                return t.getSeconds() && t.setSeconds(0), t.getMilliseconds() && t.setMilliseconds(0), t
            },
            _add_days: function(t, e) {
                var i = new Date(t.valueOf());
                return i.setDate(i.getDate() + e), e >= 0 && !t.getHours() && i.getHours() && (i.getDate() <= t.getDate() || i.getMonth() < t.getMonth() || i.getFullYear() < t.getFullYear()) && i.setTime(i.getTime() + 36e5 * (24 - i.getHours())),
                    i
            },
            add: function(e, i, n) {
                var a = new Date(e.valueOf());
                switch (n) {
                    case "day":
                        a = t.date._add_days(a, i);
                        break;
                    case "week":
                        a = t.date._add_days(a, 7 * i);
                        break;
                    case "month":
                        a.setMonth(a.getMonth() + i);
                        break;
                    case "year":
                        a.setYear(a.getFullYear() + i);
                        break;
                    case "hour":
                        a.setTime(a.getTime() + 60 * i * 60 * 1e3);
                        break;
                    case "minute":
                        a.setTime(a.getTime() + 60 * i * 1e3);
                        break;
                    default:
                        return t.date["add_" + n](e, i, n)
                }
                return a
            },
            to_fixed: function(t) {
                return 10 > t ? "0" + t : t
            },
            copy: function(t) {
                return new Date(t.valueOf())
            },
            date_to_str: function(t, e) {
                return t = t.replace(/%[a-zA-Z]/g, function(t) {
                    switch (t) {
                        case "%d":
                            return '"+gantt.date.to_fixed(date.getDate())+"';
                        case "%m":
                            return '"+gantt.date.to_fixed((date.getMonth()+1))+"';
                        case "%j":
                            return '"+date.getDate()+"';
                        case "%n":
                            return '"+(date.getMonth()+1)+"';
                        case "%y":
                            return '"+gantt.date.to_fixed(date.getFullYear()%100)+"';
                        case "%Y":
                            return '"+date.getFullYear()+"';
                        case "%D":
                            return '"+gantt.locale.date.day_short[date.getDay()]+"';
                        case "%l":
                            return '"+gantt.locale.date.day_full[date.getDay()]+"';
                        case "%M":
                            return '"+gantt.locale.date.month_short[date.getMonth()]+"';
                        case "%F":
                            return '"+gantt.locale.date.month_full[date.getMonth()]+"';
                        case "%h":
                            return '"+gantt.date.to_fixed((date.getHours()+11)%12+1)+"';
                        case "%g":
                            return '"+((date.getHours()+11)%12+1)+"';
                        case "%G":
                            return '"+date.getHours()+"';
                        case "%H":
                            return '"+gantt.date.to_fixed(date.getHours())+"';
                        case "%i":
                            return '"+gantt.date.to_fixed(date.getMinutes())+"';
                        case "%a":
                            return '"+(date.getHours()>11?"pm":"am")+"';
                        case "%A":
                            return '"+(date.getHours()>11?"PM":"AM")+"';
                        case "%s":
                            return '"+gantt.date.to_fixed(date.getSeconds())+"';
                        case "%W":
                            return '"+gantt.date.to_fixed(gantt.date.getISOWeek(date))+"';
                        default:
                            return t
                    }
                }), e && (t = t.replace(/date\.get/g, "date.getUTC")), new Function("date", 'return "' + t + '";')
            },
            str_to_date: function(t, e) {
                for (var i = "var temp=date.match(/[a-zA-Z]+|[0-9]+/g);", n = t.match(/%[a-zA-Z]/g), a = 0; a < n.length; a++) switch (n[a]) {
                    case "%j":
                    case "%d":
                        i += "set[2]=temp[" + a + "]||1;";
                        break;
                    case "%n":
                    case "%m":
                        i += "set[1]=(temp[" + a + "]||1)-1;";
                        break;
                    case "%y":
                        i += "set[0]=temp[" + a + "]*1+(temp[" + a + "]>50?1900:2000);";
                        break;
                    case "%g":
                    case "%G":
                    case "%h":
                    case "%H":
                        i += "set[3]=temp[" + a + "]||0;";
                        break;
                    case "%i":
                        i += "set[4]=temp[" + a + "]||0;";
                        break;
                    case "%Y":
                        i += "set[0]=temp[" + a + "]||0;";
                        break;
                    case "%a":
                    case "%A":
                        i += "set[3]=set[3]%12+((temp[" + a + "]||'').toLowerCase()=='am'?0:12);";
                        break;
                    case "%s":
                        i += "set[5]=temp[" + a + "]||0;";
                        break;
                    case "%M":
                        i += "set[1]=gantt.locale.date.month_short_hash[temp[" + a + "]]||0;";
                        break;
                    case "%F":
                        i += "set[1]=gantt.locale.date.month_full_hash[temp[" + a + "]]||0;"
                }
                var s = "set[0],set[1],set[2],set[3],set[4],set[5]";
                return e && (s = " Date.UTC(" + s + ")"),
                    new Function("date", "var set=[0,0,1,0,0,0]; " + i + " return new Date(" + s + ");")
            },
            getISOWeek: function(t) {
                if (!t) return !1;
                var e = t.getDay();
                0 === e && (e = 7);
                var i = new Date(t.valueOf());
                i.setDate(t.getDate() + (4 - e));
                var n = i.getFullYear(),
                    a = Math.round((i.getTime() - new Date(n, 0, 1).getTime()) / 864e5),
                    s = 1 + Math.floor(a / 7);
                return s
            },
            getUTCISOWeek: function(t) {
                return this.getISOWeek(t)
            },
            convert_to_utc: function(t) {
                return new Date(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate(), t.getUTCHours(), t.getUTCMinutes(), t.getUTCSeconds());
            },
            parseDate: function(e, i) {
                return "string" == typeof e && (t.defined(i) && (i = "string" == typeof i ? t.defined(t.templates[i]) ? t.templates[i] : t.date.str_to_date(i) : t.templates.xml_date), e = e ? i(e) : null), e
            }
        }, t.date.quarter_start = function(e) {
            t.date.month_start(e);
            var i, n = e.getMonth();
            return i = n >= 9 ? 9 : n >= 6 ? 6 : n >= 3 ? 3 : 0, e.setMonth(i), e
        }, t.date.add_quarter = function(e, i) {
            return t.date.add(e, 3 * i, "month")
        }, t.config || (t.config = {}), t.config || (t.config = {}), t.templates || (t.templates = {}),
        function() {
            t.mixin(t.config, {
                links: {
                    finish_to_start: "0",
                    start_to_start: "1",
                    finish_to_finish: "2",
                    start_to_finish: "3"
                },
                types: {
                    task: "task",
                    project: "project",
                    milestone: "milestone"
                },
                duration_unit: "day",
                work_time: !1,
                correct_work_time: !1,
                skip_off_time: !1,
                autosize: !1,
                autosize_min_width: 0,
                show_links: !0,
                show_task_cells: !0,
                static_background: !1,
                branch_loading: !1,
                show_loading: !1,
                show_chart: !0,
                show_grid: !0,
                min_duration: 36e5,
                xml_date: "%d-%m-%Y %H:%i",
                api_date: "%d-%m-%Y %H:%i",
                start_on_monday: !0,
                server_utc: !1,
                show_progress: !0,
                fit_tasks: !1,
                select_task: !0,
                scroll_on_click: !0,
                preserve_scroll: !0,
                readonly: !1,
                date_grid: "%Y-%m-%d",
                drag_links: !0,
                drag_progress: !0,
                drag_resize: !0,
                drag_move: !0,
                drag_mode: {
                    resize: "resize",
                    progress: "progress",
                    move: "move",
                    ignore: "ignore"
                },
                round_dnd_dates: !0,
                link_wrapper_width: 20,
                root_id: 0,
                autofit: !1,
                columns: [{
                    name: "text",
                    tree: !0,
                    width: "*",
                    resize: !0
                }, {
                    name: "start_date",
                    align: "center",
                    resize: !0
                }, {
                    name: "duration",
                    align: "center"
                }, {
                    name: "add",
                    width: "44"
                }],
                step: 1,
                scale_unit: "day",
                scale_offset_minimal: !0,
                subscales: [],
                inherit_scale_class: !1,
                time_step: 60,
                duration_step: 1,
                date_scale: "%d %M",
                task_date: "%d %F %Y",
                time_picker: "%H:%i",
                task_attribute: "task_id",
                link_attribute: "link_id",
                layer_attribute: "data-layer",
                buttons_left: ["gantt_save_btn", "gantt_cancel_btn"],
                _migrate_buttons: {
                    dhx_save_btn: "gantt_save_btn",
                    dhx_cancel_btn: "gantt_cancel_btn",
                    dhx_delete_btn: "gantt_delete_btn"
                },
                buttons_right: ["gantt_delete_btn"],
                lightbox: {
                    sections: [{
                        name: "description",
                        height: 70,
                        map_to: "text",
                        type: "textarea",
                        focus: !0
                    }, {
                        name: "time",
                        type: "duration",
                        map_to: "auto"
                    }],
                    project_sections: [{
                        name: "description",
                        height: 70,
                        map_to: "text",
                        type: "textarea",
                        focus: !0
                    }, {
                        name: "type",
                        type: "typeselect",
                        map_to: "type"
                    }, {
                        name: "time",
                        type: "duration",
                        readonly: !0,
                        map_to: "auto"
                    }],
                    milestone_sections: [{
                        name: "description",
                        height: 70,
                        map_to: "text",
                        type: "textarea",
                        focus: !0
                    }, {
                        name: "type",
                        type: "typeselect",
                        map_to: "type"
                    }, {
                        name: "time",
                        type: "duration",
                        single_date: !0,
                        map_to: "auto"
                    }]
                },
                drag_lightbox: !0,
                sort: !1,
                details_on_create: !0,
                details_on_dblclick: !0,
                initial_scroll: !0,
                task_scroll_offset: 100,
                order_branch: !1,
                order_branch_free: !1,
                task_height: "full",
                min_column_width: 70,
                min_grid_column_width: 70,
                grid_resizer_column_attribute: "column_index",
                grid_resizer_attribute: "grid_resizer",
                keep_grid_width: !1,
                grid_resize: !1,
                show_unscheduled: !0,
                readonly_property: "readonly",
                editable_property: "editable",
                type_renderers: {},
                open_tree_initially: !1,
                optimize_render: !0,
                prevent_default_scroll: !1,
                show_errors: !0
            }), t.keys = {
                edit_save: 13,
                edit_cancel: 27
            }, t._init_template = function(t, e, i) {
                var n = this._reg_templates || {};
                i = i || t, this.config[t] && n[i] != this.config[t] && (e && this.templates[i] || (this.templates[i] = this.date.date_to_str(this.config[t]),
                    n[i] = this.config[t])), this._reg_templates = n
            }, t._init_templates = function() {
                var e = t.locale.labels;
                e.gantt_save_btn = e.icon_save, e.gantt_cancel_btn = e.icon_cancel, e.gantt_delete_btn = e.icon_delete;
                var i = this.date.date_to_str,
                    n = this.config;
                t._init_template("date_scale", !0), t._init_template("date_grid", !0, "grid_date_format"), t._init_template("task_date", !0), t.mixin(this.templates, {
                    xml_date: this.date.str_to_date(n.xml_date, n.server_utc),
                    xml_format: i(n.xml_date, n.server_utc),
                    api_date: this.date.str_to_date(n.api_date),
                    progress_text: function(t, e, i) {
                        return ""
                    },
                    grid_header_class: function(t, e) {
                        return ""
                    },
                    task_text: function(t, e, i) {
                        return i.text
                    },
                    task_class: function(t, e, i) {
                        return ""
                    },
                    grid_row_class: function(t, e, i) {
                        return ""
                    },
                    task_row_class: function(t, e, i) {
                        return ""
                    },
                    task_cell_class: function(t, e) {
                        return ""
                    },
                    scale_cell_class: function(t) {
                        return ""
                    },
                    scale_row_class: function(t) {
                        return ""
                    },
                    grid_indent: function(t) {
                        return "<div class='gantt_tree_indent'></div>"
                    },
                    grid_folder: function(t) {
                        return "<div class='gantt_tree_icon gantt_folder_" + (t.$open ? "open" : "closed") + "'></div>";
                    },
                    grid_file: function(t) {
                        return "<div class='gantt_tree_icon gantt_file'></div>"
                    },
                    grid_open: function(t) {
                        return "<div class='gantt_tree_icon gantt_" + (t.$open ? "close" : "open") + "'></div>"
                    },
                    grid_blank: function(t) {
                        return "<div class='gantt_tree_icon gantt_blank'></div>"
                    },
                    date_grid: function(e, i) {
                        return i && t.isUnscheduledTask(i) && t.config.show_unscheduled ? t.templates.task_unscheduled_time(i) : t.templates.grid_date_format(e)
                    },
                    task_time: function(e, i, n) {
                        return t.isUnscheduledTask(n) && t.config.show_unscheduled ? t.templates.task_unscheduled_time(n) : t.templates.task_date(e) + " - " + t.templates.task_date(i);
                    },
                    task_unscheduled_time: function(t) {
                        return ""
                    },
                    time_picker: i(n.time_picker),
                    link_class: function(t) {
                        return ""
                    },
                    link_description: function(e) {
                        var i = t.getTask(e.source),
                            n = t.getTask(e.target);
                        return "<b>" + i.text + "</b> &ndash;  <b>" + n.text + "</b>"
                    },
                    drag_link: function(e, i, n, a) {
                        e = t.getTask(e);
                        var s = t.locale.labels,
                            r = "<b>" + e.text + "</b> " + (i ? s.link_start : s.link_end) + "<br/>";
                        return n && (n = t.getTask(n), r += "<b> " + n.text + "</b> " + (a ? s.link_start : s.link_end) + "<br/>"), r
                    },
                    drag_link_class: function(e, i, n, a) {
                        var s = "";
                        if (e && n) {
                            var r = t.isLinkAllowed(e, n, i, a);
                            s = " " + (r ? "gantt_link_allow" : "gantt_link_deny")
                        }
                        return "gantt_link_tooltip" + s
                    }
                }), this.callEvent("onTemplatesReady", [])
            }
        }(), window.jQuery && ! function(t) {
            var e = [];
            t.fn.dhx_gantt = function(i) {
                if (i = i || {}, "string" != typeof i) {
                    var n = [];
                    return this.each(function() {
                        if (this && this.getAttribute)
                            if (this.gantt) n.push("object" == typeof this.gantt ? this.gantt : window.gantt);
                            else {
                                var t = window.gantt.$container ? Gantt.getGanttInstance() : window.gantt;
                                for (var e in i) "data" != e && (t.config[e] = i[e]);
                                t.init(this), i.data && t.parse(i.data), n.push(t)
                            }
                    }), 1 === n.length ? n[0] : n
                }
                return e[i] ? e[i].apply(this, []) : void t.error("Method " + i + " does not exist on jQuery.dhx_gantt")
            }
        }(jQuery), t.locale = {
            date: {
                month_full: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
                month_short: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                day_full: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                day_short: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            },
            labels: {
                new_task: "New task",
                icon_save: "Save",
                icon_cancel: "Cancel",
                icon_details: "Details",
                icon_edit: "Edit",
                icon_delete: "Delete",
                confirm_closing: "",
                confirm_deleting: "Task will be deleted permanently, are you sure?",
                section_description: "Description",
                section_time: "Time period",
                section_type: "Type",
                column_text: "Task name",
                column_start_date: "Start time",
                column_duration: "Duration",
                column_add: "",
                link: "Link",
                confirm_link_deleting: "will be deleted",
                link_start: " (start)",
                link_end: " (end)",
                type_task: "Task",
                type_project: "Project",
                type_milestone: "Milestone",
                minutes: "Minutes",
                hours: "Hours",
                days: "Days",
                weeks: "Week",
                months: "Months",
                years: "Years"
            }
        }, t.skins.skyblue = {
            config: {
                grid_width: 350,
                row_height: 27,
                scale_height: 27,
                link_line_width: 1,
                link_arrow_size: 8,
                lightbox_additional_height: 75
            },
            _second_column_width: 95,
            _third_column_width: 80
        }, t.skins.meadow = {
            config: {
                grid_width: 350,
                row_height: 27,
                scale_height: 30,
                link_line_width: 2,
                link_arrow_size: 6,
                lightbox_additional_height: 72
            },
            _second_column_width: 95,
            _third_column_width: 80
        }, t.skins.terrace = {
            config: {
                grid_width: 360,
                row_height: 35,
                scale_height: 35,
                link_line_width: 2,
                link_arrow_size: 6,
                lightbox_additional_height: 75
            },
            _second_column_width: 90,
            _third_column_width: 70
        }, t.skins.broadway = {
            config: {
                grid_width: 360,
                row_height: 35,
                scale_height: 35,
                link_line_width: 1,
                link_arrow_size: 7,
                lightbox_additional_height: 86
            },
            _second_column_width: 90,
            _third_column_width: 80,
            _lightbox_template: "<div class='gantt_cal_ltitle'><span class='gantt_mark'>&nbsp;</span><span class='gantt_time'></span><span class='gantt_title'></span><div class='gantt_cancel_btn'></div></div><div class='gantt_cal_larea'></div>",
            _config_buttons_left: {},
            _config_buttons_right: {
                gantt_delete_btn: "icon_delete",
                gantt_save_btn: "icon_save"
            }
        }, t.config.touch_drag = 500, t.config.touch = !0, t.config.touch_feedback = !0, t._touch_feedback = function() {
            t.config.touch_feedback && navigator.vibrate && navigator.vibrate(1)
        }, t._init_touch_events = function() {
            "force" != this.config.touch && (this.config.touch = this.config.touch && (-1 != navigator.userAgent.indexOf("Mobile") || -1 != navigator.userAgent.indexOf("iPad") || -1 != navigator.userAgent.indexOf("Android") || -1 != navigator.userAgent.indexOf("Touch"))),
                this.config.touch && (window.navigator.msPointerEnabled ? this._touch_events(["MSPointerMove", "MSPointerDown", "MSPointerUp"], function(t) {
                    return t.pointerType == t.MSPOINTER_TYPE_MOUSE ? null : t
                }, function(t) {
                    return !t || t.pointerType == t.MSPOINTER_TYPE_MOUSE
                }) : this._touch_events(["touchmove", "touchstart", "touchend"], function(t) {
                    return t.touches && t.touches.length > 1 ? null : t.touches[0] ? {
                        target: t.target,
                        pageX: t.touches[0].pageX,
                        pageY: t.touches[0].pageY,
                        clientX: t.touches[0].clientX,
                        clientY: t.touches[0].clientY
                    } : t
                }, function() {
                    return !1
                }))
        }, t._touch_events = function(e, i, n) {
            function a(t) {
                return t && t.preventDefault && t.preventDefault(), (t || event).cancelBubble = !0, !1
            }

            function s(e) {
                var i = t._task_area_pulls,
                    n = t.getTask(e);
                if (n && t.isTaskVisible(e))
                    for (var a in i)
                        if (n = i[a][e], n && n.getAttribute("task_id") && n.getAttribute("task_id") == e) {
                            var s = n.cloneNode(!0);
                            return c = n, i[a][e] = s, n.style.display = "none", s.className += " gantt_drag_move ", n.parentNode.appendChild(s), s
                        }
            }
            var r, o = 0,
                _ = !1,
                d = !1,
                l = null,
                h = null,
                c = null;
            this._gantt_touch_event_ready || (this._gantt_touch_event_ready = 1,
                t.event(t.$container, e[0], function(e) {
                    if (!n(e) && _) {
                        h && clearTimeout(h);
                        var s = i(e);
                        if (t._tasks_dnd.drag.id || t._tasks_dnd.drag.start_drag) return t._tasks_dnd.on_mouse_move(s), e.preventDefault && e.preventDefault(), e.cancelBubble = !0, !1;
                        if (s && l) {
                            var c = l.pageX - s.pageX,
                                u = l.pageY - s.pageY;
                            if (!d && (Math.abs(c) > 5 || Math.abs(u) > 5) && (t._touch_scroll_active = d = !0, o = 0, r = t.getScrollState()), d) {
                                t.scrollTo(r.x + c, r.y + u);
                                var g = t.getScrollState();
                                if (r.x != g.x && u > 2 * c || r.y != g.y && c > 2 * u) return a(e)
                            }
                        }
                        return a(e)
                    }
                })), t.event(this.$container, "contextmenu", function(t) {
                return _ ? a(t) : void 0
            }), t.event(this.$container, e[1], function(e) {
                if (!n(e)) {
                    if (e.touches && e.touches.length > 1) return void(_ = !1);
                    if (_ = !0, l = i(e), l && o) {
                        var r = new Date;
                        500 > r - o ? (t._on_dblclick(l), a(e)) : o = r
                    } else o = new Date;
                    h = setTimeout(function() {
                        var e = t.locate(l);
                        !e || t._locate_css(l, "gantt_link_control") || t._locate_css(l, "gantt_grid_data") || (t._tasks_dnd.on_mouse_down(l), t._tasks_dnd.drag && t._tasks_dnd.drag.start_drag && (s(e), t._tasks_dnd._start_dnd(l), t._touch_drag = !0, t.refreshTask(e), t._touch_feedback())),
                            h = null
                    }, t.config.touch_drag)
                }
            }), t.event(this.$container, e[2], function(e) {
                if (!n(e)) {
                    h && clearTimeout(h), t._touch_drag = !1, _ = !1;
                    var a = i(e);
                    t._tasks_dnd.on_mouse_up(a), c && (t.refreshTask(t.locate(c)), c.parentNode && (c.parentNode.removeChild(c), t._touch_feedback())), t._touch_scroll_active = _ = d = !1, c = null
                }
            })
        },
        function() {
            function e(e, i) {
                var n = t.env.isIE ? "" : "%c",
                    a = [n, '"', e, '"', n, " has been deprecated in dhtmlxGantt v4.0 and will stop working in v5.0. Use ", n, '"', i, '"', n, " instead. \nSee more details at http://docs.dhtmlx.com/gantt/migrating.html "].join(""),
                    s = window.console.warn || window.console.log,
                    r = [a];
                t.env.isIE || (r = r.concat(["font-weight:bold", "font-weight:normal", "font-weight:bold", "font-weight:normal"])), s.apply(window.console, r)
            }

            function i(i) {
                return function() {
                    return e("dhtmlx." + i, "gantt." + i), t[i].apply(t, arguments)
                }
            }
            window.dhtmlx || (window.dhtmlx = {});
            for (var n = ["message", "alert", "confirm", "modalbox", "uid", "copy", "mixin", "defined", "bind", "assert"], a = 0; a < n.length; a++) window.dhtmlx[n[a]] || (dhtmlx[n[a]] = i(n[a]));
            window.dataProcessor || (window.dataProcessor = function(i) {
                return e("new dataProcessor(url)", "new gantt.dataProcessor(url)"),
                    new t.dataProcessor(i)
            })
        }();
    for (var e = 0; e < Gantt._ganttPlugin.length; e++) Gantt._ganttPlugin[e](t);
    return t._internal_id = Gantt._seed++, Gantt.$syncFactory && Gantt.$syncFactory(t), t
}, window.gantt = Gantt.getGanttInstance(), dhtmlx && (dhtmlx.attaches = dhtmlx.attaches || [], dhtmlx.attaches.attachGantt = function(t, e, i) {
    var n = document.createElement("DIV");
    return n.id = "dhxSchedObj_" + this._genStr(12), n.style.cssText = "width:100%; height:100%;", document.body.appendChild(n), this.attachObject(n.id, !1, !0), i = i || (window.gantt.$container ? Gantt.getGanttInstance() : window.gantt),
        this.vs[this.av].sched = i, this.vs[this.av].schedId = n.id, i.destructor = function() {}, i.init(n.id, t, e), this.vs[this._viewRestore()].sched
});