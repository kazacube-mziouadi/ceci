/*
@license
dhtmlxScheduler v.4.3.1 

This software is covered by DHTMLX Evaluation License. Contact sales@dhtmlx.com to get Commercial or Enterprise license. Usage without proper license is prohibited.

(c) Dinamenta, UAB.
*/
Scheduler.plugin(function(e) {
    e.config.limit_start = null, e.config.limit_end = null, e.config.limit_view = !1, e.config.check_limits = !0, e.config.mark_now = !0, e.config.display_marked_timespans = !0, e._temp_limit_scope = function() {
        function t(t, a, i, n, r) {
            var s = e,
                d = [],
                o = {
                    _props: "map_to",
                    matrix: "y_property"
                };
            for (var _ in o) {
                var l = o[_];
                if (s[_])
                    for (var h in s[_]) {
                        var c = s[_][h],
                            u = c[l];
                        t[u] && (d = s._add_timespan_zones(d, e._get_blocked_zones(a[h], t[u], i, n, r)))
                    }
            }
            return d = s._add_timespan_zones(d, e._get_blocked_zones(a, "global", i, n, r));

        }
        var a = null,
            i = "dhx_time_block",
            n = "default",
            r = function(e, t, a) {
                return t instanceof Date && a instanceof Date ? (e.start_date = t, e.end_date = a) : (e.days = t, e.zones = a), e
            },
            s = function(e, t, a) {
                var n = "object" == typeof e ? e : {
                    days: e
                };
                return n.type = i, n.css = "", t && (a && (n.sections = a), n = r(n, e, t)), n
            };
        e.blockTime = function(t, a, i) {
            var n = s(t, a, i);
            return e.addMarkedTimespan(n)
        }, e.unblockTime = function(t, a, i) {
            a = a || "fullday";
            var n = s(t, a, i);
            return e.deleteMarkedTimespan(n)
        }, e.attachEvent("onBeforeViewChange", function(t, a, i, n) {
            function r(t, a) {
                var i = e.config.limit_start,
                    n = e.config.limit_end,
                    r = e.date.add(t, 1, a);
                return t.valueOf() > n.valueOf() || r <= i.valueOf()
            }
            return e.config.limit_view && (n = n || a, i = i || t, r(n, i) && a.valueOf() != n.valueOf()) ? (setTimeout(function() {
                var t = r(a, i) ? e.config.limit_start : a;
                e.setCurrentView(r(t, i) ? null : t, i)
            }, 1), !1) : !0
        }), e.checkInMarkedTimespan = function(a, i, r) {
            i = i || n;
            for (var s = !0, d = new Date(a.start_date.valueOf()), o = e.date.add(d, 1, "day"), _ = e._marked_timespans; d < a.end_date; d = e.date.date_part(o), o = e.date.add(d, 1, "day")) {
                var l = +e.date.date_part(new Date(d)),
                    h = d.getDay(),
                    c = t(a, _, h, l, i);

                if (c)
                    for (var u = 0; u < c.length; u += 2) {
                        var v = e._get_zone_minutes(d),
                            f = a.end_date > o || a.end_date.getDate() != d.getDate() ? 1440 : e._get_zone_minutes(a.end_date),
                            g = c[u],
                            m = c[u + 1];
                        if (f > g && m > v && (s = "function" == typeof r ? r(a, v, f, g, m) : !1, !s)) break
                    }
            }
            return !s
        };
        var d = e.checkLimitViolation = function(t) {
            if (!t) return !0;
            if (!e.config.check_limits) return !0;
            var a = e,
                n = a.config,
                r = [];
            if (t.rec_type)
                for (var s = e.getRecDates(t), d = 0; d < s.length; d++) {
                    var o = e._copy_event(t);
                    e._lame_copy(o, s[d]), r.push(o)
                } else r = [t];
            for (var _ = !0, l = 0; l < r.length; l++) {
                var h = !0,
                    o = r[l];
                o._timed = e.isOneDayEvent(o), h = n.limit_start && n.limit_end ? o.start_date.valueOf() >= n.limit_start.valueOf() && o.end_date.valueOf() <= n.limit_end.valueOf() : !0, h && (h = !e.checkInMarkedTimespan(o, i, function(e, t, i, n, r) {
                    var s = !0;
                    return r >= t && t >= n && ((1440 == r || r > i) && (s = !1), e._timed && a._drag_id && "new-size" == a._drag_mode ? (e.start_date.setHours(0), e.start_date.setMinutes(r)) : s = !1), (i >= n && r > i || n > t && i > r) && (e._timed && a._drag_id && "new-size" == a._drag_mode ? (e.end_date.setHours(0), e.end_date.setMinutes(n)) : s = !1),
                        s
                })), h || (h = a.checkEvent("onLimitViolation") ? a.callEvent("onLimitViolation", [o.id, o]) : h), _ = _ && h
            }
            return _ || (a._drag_id = null, a._drag_mode = null), _
        };
        e._get_blocked_zones = function(e, t, a, i, n) {
                var r = [];
                if (e && e[t])
                    for (var s = e[t], d = this._get_relevant_blocked_zones(a, i, s, n), o = 0; o < d.length; o++) r = this._add_timespan_zones(r, d[o].zones);
                return r
            }, e._get_relevant_blocked_zones = function(e, t, a, i) {
                var n = a[t] && a[t][i] ? a[t][i] : a[e] && a[e][i] ? a[e][i] : [];
                return n
            }, e.attachEvent("onMouseDown", function(e) {
                return !(e == i)
            }),
            e.attachEvent("onBeforeDrag", function(t) {
                return t ? d(e.getEvent(t)) : !0
            }), e.attachEvent("onClick", function(t, a) {
                return d(e.getEvent(t))
            }), e.attachEvent("onBeforeLightbox", function(t) {
                var i = e.getEvent(t);
                return a = [i.start_date, i.end_date], d(i)
            }), e.attachEvent("onEventSave", function(t, a, i) {
                if (!a.start_date || !a.end_date) {
                    var n = e.getEvent(t);
                    a.start_date = new Date(n.start_date), a.end_date = new Date(n.end_date)
                }
                if (a.rec_type) {
                    var r = e._lame_clone(a);
                    return e._roll_back_dates(r), d(r)
                }
                return d(a)
            }), e.attachEvent("onEventAdded", function(t) {
                if (!t) return !0;
                var a = e.getEvent(t);
                return !d(a) && e.config.limit_start && e.config.limit_end && (a.start_date < e.config.limit_start && (a.start_date = new Date(e.config.limit_start)), a.start_date.valueOf() >= e.config.limit_end.valueOf() && (a.start_date = this.date.add(e.config.limit_end, -1, "day")), a.end_date < e.config.limit_start && (a.end_date = new Date(e.config.limit_start)), a.end_date.valueOf() >= e.config.limit_end.valueOf() && (a.end_date = this.date.add(e.config.limit_end, -1, "day")), a.start_date.valueOf() >= a.end_date.valueOf() && (a.end_date = this.date.add(a.start_date, this.config.event_duration || this.config.time_step, "minute")),
                    a._timed = this.isOneDayEvent(a)), !0
            }), e.attachEvent("onEventChanged", function(t) {
                if (!t) return !0;
                var i = e.getEvent(t);
                if (!d(i)) {
                    if (!a) return !1;
                    i.start_date = a[0], i.end_date = a[1], i._timed = this.isOneDayEvent(i)
                }
                return !0
            }), e.attachEvent("onBeforeEventChanged", function(e, t, a) {
                return d(e)
            }), e.attachEvent("onBeforeEventCreated", function(t) {
                var a = e.getActionData(t).date,
                    i = {
                        _timed: !0,
                        start_date: a,
                        end_date: e.date.add(a, e.config.time_step, "minute")
                    };
                return d(i)
            }), e.attachEvent("onViewChange", function() {
                e._mark_now();

            }), e.attachEvent("onSchedulerResize", function() {
                return window.setTimeout(function() {
                    e._mark_now()
                }, 1), !0
            }), e.attachEvent("onTemplatesReady", function() {
                e._mark_now_timer = window.setInterval(function() {
                    e._is_initialized() && e._mark_now()
                }, 6e4)
            }), e._mark_now = function(t) {
                var a = "dhx_now_time";
                this._els[a] || (this._els[a] = []);
                var i = e._currentDate(),
                    n = this.config;
                if (e._remove_mark_now(), !t && n.mark_now && i < this._max_date && i > this._min_date && i.getHours() >= n.first_hour && i.getHours() < n.last_hour) {
                    var r = this.locate_holder_day(i);

                    this._els[a] = e._append_mark_now(r, i)
                }
            }, e._append_mark_now = function(t, a) {
                var i = "dhx_now_time",
                    n = e._get_zone_minutes(a),
                    r = {
                        zones: [n, n + 1],
                        css: i,
                        type: i
                    };
                if (!this._table_view) {
                    if (this._props && this._props[this._mode]) {
                        for (var s = this._props[this._mode], d = s.size || s.options.length, o = t * d, _ = (t + 1) * d, l = (this._els.dhx_cal_data[0].childNodes, []), h = o; _ > h; h++) {
                            var c = h;
                            r.days = c;
                            var u = e._render_marked_timespan(r, null, c)[0];
                            l.push(u)
                        }
                        return l
                    }
                    return r.days = t, e._render_marked_timespan(r, null, t)
                }
                return "month" == this._mode ? (r.days = +e.date.date_part(a),
                    e._render_marked_timespan(r, null, null)) : void 0
            }, e._remove_mark_now = function() {
                for (var e = "dhx_now_time", t = this._els[e], a = 0; a < t.length; a++) {
                    var i = t[a],
                        n = i.parentNode;
                    n && n.removeChild(i)
                }
                this._els[e] = []
            }, e._marked_timespans = {
                global: {}
            }, e._get_zone_minutes = function(e) {
                return 60 * e.getHours() + e.getMinutes()
            }, e._prepare_timespan_options = function(t) {
                var a = [],
                    i = [];
                if ("fullweek" == t.days && (t.days = [0, 1, 2, 3, 4, 5, 6]), t.days instanceof Array) {
                    for (var r = t.days.slice(), s = 0; s < r.length; s++) {
                        var d = e._lame_clone(t);
                        d.days = r[s],
                            a.push.apply(a, e._prepare_timespan_options(d))
                    }
                    return a
                }
                if (!t || !(t.start_date && t.end_date && t.end_date > t.start_date || void 0 !== t.days && t.zones)) return a;
                var o = 0,
                    _ = 1440;
                "fullday" == t.zones && (t.zones = [o, _]), t.zones && t.invert_zones && (t.zones = e.invertZones(t.zones)), t.id = e.uid(), t.css = t.css || "", t.type = t.type || n;
                var l = t.sections;
                if (l) {
                    for (var h in l)
                        if (l.hasOwnProperty(h)) {
                            var c = l[h];
                            c instanceof Array || (c = [c]);
                            for (var s = 0; s < c.length; s++) {
                                var u = e._lame_copy({}, t);
                                u.sections = {}, u.sections[h] = c[s], i.push(u);

                            }
                        }
                } else i.push(t);
                for (var v = 0; v < i.length; v++) {
                    var f = i[v],
                        g = f.start_date,
                        m = f.end_date;
                    if (g && m)
                        for (var p = e.date.date_part(new Date(g)), x = e.date.add(p, 1, "day"); m > p;) {
                            var u = e._lame_copy({}, f);
                            delete u.start_date, delete u.end_date, u.days = p.valueOf();
                            var y = g > p ? e._get_zone_minutes(g) : o,
                                b = m > x || m.getDate() != p.getDate() ? _ : e._get_zone_minutes(m);
                            u.zones = [y, b], a.push(u), p = x, x = e.date.add(x, 1, "day")
                        } else f.days instanceof Date && (f.days = e.date.date_part(f.days).valueOf()), f.zones = t.zones.slice(), a.push(f)
                }
                return a;

            }, e._get_dates_by_index = function(t, a, i) {
                var n = [];
                a = e.date.date_part(new Date(a || e._min_date)), i = new Date(i || e._max_date);
                for (var r = a.getDay(), s = t - r >= 0 ? t - r : 7 - a.getDay() + t, d = e.date.add(a, s, "day"); i > d; d = e.date.add(d, 1, "week")) n.push(d);
                return n
            }, e._get_css_classes_by_config = function(e) {
                var t = [];
                return e.type == i && (t.push(i), e.css && t.push(i + "_reset")), t.push("dhx_marked_timespan", e.css), t.join(" ")
            }, e._get_block_by_config = function(e) {
                var t = document.createElement("DIV");
                return e.html && ("string" == typeof e.html ? t.innerHTML = e.html : t.appendChild(e.html)),
                    t
            }, e._render_marked_timespan = function(t, a, i) {
                var n = [],
                    r = e.config,
                    s = this._min_date,
                    d = this._max_date,
                    o = !1;
                if (!r.display_marked_timespans) return n;
                if (!i && 0 !== i) {
                    if (t.days < 7) i = t.days;
                    else {
                        var _ = new Date(t.days);
                        if (o = +_, !(+d > +_ && +_ >= +s)) return n;
                        i = _.getDay()
                    }
                    var l = s.getDay();
                    l > i ? i = 7 - (l - i) : i -= l
                }
                var h = t.zones,
                    c = e._get_css_classes_by_config(t);
                if (e._table_view && "month" == e._mode) {
                    var u = [],
                        v = [];
                    if (a) u.push(a), v.push(i);
                    else {
                        v = o ? [o] : e._get_dates_by_index(i);
                        for (var f = 0; f < v.length; f++) u.push(this._scales[v[f]]);

                    }
                    for (var f = 0; f < u.length; f++) {
                        a = u[f], i = v[f];
                        var g = Math.floor((this._correct_shift(i, 1) - s.valueOf()) / (864e5 * this._cols.length)),
                            m = this.locate_holder_day(i, !1) % this._cols.length;
                        if (!this._ignores[m]) {
                            var p = e._get_block_by_config(t),
                                x = Math.max(a.offsetHeight - 1, 0),
                                y = Math.max(a.offsetWidth - 1, 0),
                                b = this._colsS[m],
                                w = this._colsS.heights[g] + (this._colsS.height ? this.xy.month_scale_height + 2 : 2) - 1;
                            p.className = c, p.style.top = w + "px", p.style.lineHeight = p.style.height = x + "px";
                            for (var E = 0; E < h.length; E += 2) {
                                var D = h[f],
                                    k = h[f + 1];

                                if (D >= k) return [];
                                var M = p.cloneNode(!0);
                                M.style.left = b + Math.round(D / 1440 * y) + "px", M.style.width = Math.round((k - D) / 1440 * y) + "px", a.appendChild(M), n.push(M)
                            }
                        }
                    }
                } else {
                    var N = i;
                    if (this._ignores[this.locate_holder_day(i, !1)]) return n;
                    if (this._props && this._props[this._mode] && t.sections && t.sections[this._mode]) {
                        var O = this._props[this._mode];
                        N = O.order[t.sections[this._mode]];
                        var L = O.order[t.sections[this._mode]];
                        if (O.days > 1) {
                            var S = O.size || O.options.length;
                            N = N * S + L
                        } else N = L, O.size && N > O.position + O.size && (N = 0)
                    }
                    a = a ? a : e.locate_holder(N);

                    for (var f = 0; f < h.length; f += 2) {
                        var D = Math.max(h[f], 60 * r.first_hour),
                            k = Math.min(h[f + 1], 60 * r.last_hour);
                        if (D >= k) {
                            if (f + 2 < h.length) continue;
                            return []
                        }
                        var M = e._get_block_by_config(t);
                        M.className = c;
                        var C = 24 * this.config.hour_size_px + 1,
                            T = 36e5;
                        M.style.top = Math.round((60 * D * 1e3 - this.config.first_hour * T) * this.config.hour_size_px / T) % C + "px", M.style.lineHeight = M.style.height = Math.max(Math.round(60 * (k - D) * 1e3 * this.config.hour_size_px / T) % C, 1) + "px", a.appendChild(M), n.push(M)
                    }
                }
                return n
            }, e.markTimespan = function(t) {
                var a = [],
                    i = !1;

                this._els.dhx_cal_data || (e.get_elements(), i = !0);
                var n = this._els.dhx_cal_data[0],
                    r = e._marked_timespans_ids,
                    s = e._marked_timespans_types,
                    d = e._marked_timespans;
                e.deleteMarkedTimespan(), e.addMarkedTimespan(t);
                for (var o = new Date(e._min_date), _ = 0, l = n.childNodes.length; l > _; _++) {
                    var h = n.childNodes[_];
                    h.firstChild && (h.firstChild.className || "").indexOf("dhx_scale_hour") > -1 || (a.push.apply(a, e._on_scale_add_marker(h, o)), o = e.date.add(o, 1, "day"))
                }
                return i && (e._els = []), e._marked_timespans_ids = r, e._marked_timespans_types = s,
                    e._marked_timespans = d, a
            }, e.unmarkTimespan = function(e) {
                if (e)
                    for (var t = 0; t < e.length; t++) {
                        var a = e[t];
                        a.parentNode && a.parentNode.removeChild(a)
                    }
            }, e._marked_timespans_ids = {}, e.addMarkedTimespan = function(t) {
                var a = e._prepare_timespan_options(t),
                    i = "global";
                if (a.length) {
                    var n = a[0].id,
                        r = e._marked_timespans,
                        s = e._marked_timespans_ids;
                    s[n] || (s[n] = []);
                    for (var d = 0; d < a.length; d++) {
                        var o = a[d],
                            _ = o.days,
                            l = (o.zones, o.css, o.sections),
                            h = o.type;
                        if (o.id = n, l) {
                            for (var c in l)
                                if (l.hasOwnProperty(c)) {
                                    r[c] || (r[c] = {});
                                    var u = l[c],
                                        v = r[c];

                                    v[u] || (v[u] = {}), v[u][_] || (v[u][_] = {}), v[u][_][h] || (v[u][_][h] = [], e._marked_timespans_types || (e._marked_timespans_types = {}), e._marked_timespans_types[h] || (e._marked_timespans_types[h] = !0));
                                    var f = v[u][_][h];
                                    o._array = f, f.push(o), s[n].push(o)
                                }
                        } else {
                            r[i][_] || (r[i][_] = {}), r[i][_][h] || (r[i][_][h] = []), e._marked_timespans_types || (e._marked_timespans_types = {}), e._marked_timespans_types[h] || (e._marked_timespans_types[h] = !0);
                            var f = r[i][_][h];
                            o._array = f, f.push(o), s[n].push(o)
                        }
                    }
                    return n
                }
            }, e._add_timespan_zones = function(e, t) {
                var a = e.slice();
                if (t = t.slice(), !a.length) return t;
                for (var i = 0; i < a.length; i += 2)
                    for (var n = a[i], r = a[i + 1], s = i + 2 == a.length, d = 0; d < t.length; d += 2) {
                        var o = t[d],
                            _ = t[d + 1];
                        if (_ > r && r >= o || n > o && _ >= n) a[i] = Math.min(n, o), a[i + 1] = Math.max(r, _), i -= 2;
                        else {
                            if (!s) continue;
                            var l = n > o ? 0 : 2;
                            a.splice(i + l, 0, o, _)
                        }
                        t.splice(d--, 2);
                        break
                    }
                return a
            }, e._subtract_timespan_zones = function(e, t) {
                for (var a = e.slice(), i = 0; i < a.length; i += 2)
                    for (var n = a[i], r = a[i + 1], s = 0; s < t.length; s += 2) {
                        var d = t[s],
                            o = t[s + 1];
                        if (o > n && r > d) {
                            var _ = !1;
                            n >= d && o >= r && a.splice(i, 2),
                                d > n && (a.splice(i, 2, n, d), _ = !0), r > o && a.splice(_ ? i + 2 : i, _ ? 0 : 2, o, r), i -= 2;
                            break
                        }
                    }
                return a
            }, e.invertZones = function(t) {
                return e._subtract_timespan_zones([0, 1440], t.slice())
            }, e._delete_marked_timespan_by_id = function(t) {
                var a = e._marked_timespans_ids[t];
                if (a)
                    for (var i = 0; i < a.length; i++)
                        for (var n = a[i], r = n._array, s = 0; s < r.length; s++)
                            if (r[s] == n) {
                                r.splice(s, 1);
                                break
                            }
            }, e._delete_marked_timespan_by_config = function(t) {
                var a = e._marked_timespans,
                    i = t.sections,
                    r = t.days,
                    s = t.type || n,
                    d = [];
                if (i) {
                    for (var o in i)
                        if (i.hasOwnProperty(o) && a[o]) {
                            var _ = i[o];
                            a[o][_] && a[o][_][r] && a[o][_][r][s] && (d = a[o][_][r][s])
                        }
                } else a.global[r] && a.global[r][s] && (d = a.global[r][s]);
                for (var l = 0; l < d.length; l++) {
                    var h = d[l],
                        c = e._subtract_timespan_zones(h.zones, t.zones);
                    if (c.length) h.zones = c;
                    else {
                        d.splice(l, 1), l--;
                        for (var u = e._marked_timespans_ids[h.id], v = 0; v < u.length; v++)
                            if (u[v] == h) {
                                u.splice(v, 1);
                                break
                            }
                    }
                }
                for (var l in e._marked_timespans.timeline)
                    for (var f in e._marked_timespans.timeline[l])
                        for (var v in e._marked_timespans.timeline[l][f]) v === s && delete e._marked_timespans.timeline[l][f][v];

            }, e.deleteMarkedTimespan = function(t) {
                if (arguments.length || (e._marked_timespans = {
                        global: {}
                    }, e._marked_timespans_ids = {}, e._marked_timespans_types = {}), "object" != typeof t) e._delete_marked_timespan_by_id(t);
                else {
                    t.start_date && t.end_date || (t.days || (t.days = "fullweek"), t.zones || (t.zones = "fullday"));
                    var a = [];
                    if (t.type) a.push(t.type);
                    else
                        for (var i in e._marked_timespans_types) a.push(i);
                    for (var n = e._prepare_timespan_options(t), r = 0; r < n.length; r++)
                        for (var s = n[r], d = 0; d < a.length; d++) {
                            var o = e._lame_clone(s);
                            o.type = a[d],
                                e._delete_marked_timespan_by_config(o)
                        }
                }
            }, e._get_types_to_render = function(e, t) {
                var a = e ? e : {};
                for (var i in t || {}) t.hasOwnProperty(i) && (a[i] = t[i]);
                return a
            }, e._get_configs_to_render = function(e) {
                var t = [];
                for (var a in e) e.hasOwnProperty(a) && t.push.apply(t, e[a]);
                return t
            }, e._on_scale_add_marker = function(t, a) {
                if (!e._table_view || "month" == e._mode) {
                    var i = a.getDay(),
                        n = a.valueOf(),
                        r = this._mode,
                        s = e._marked_timespans,
                        d = [],
                        o = [];
                    if (this._props && this._props[r]) {
                        var _ = this._props[r],
                            l = _.options,
                            h = e._get_unit_index(_, a),
                            c = l[h];

                        if (_.days > 1) {
                            var u = 864e5,
                                v = Math.floor((a - e._min_date) / u);
                            a = e.date.add(e._min_date, Math.floor(v / l.length), "day"), a = e.date.date_part(a)
                        } else a = e.date.date_part(new Date(this._date));
                        if (i = a.getDay(), n = a.valueOf(), s[r] && s[r][c.key]) {
                            var f = s[r][c.key],
                                g = e._get_types_to_render(f[i], f[n]);
                            d.push.apply(d, e._get_configs_to_render(g))
                        }
                    }
                    var m = s.global,
                        p = m[n] || m[i];
                    d.push.apply(d, e._get_configs_to_render(p));
                    for (var x = 0; x < d.length; x++) o.push.apply(o, e._render_marked_timespan(d[x], t, a));
                    return o
                }
            }, e.attachEvent("onScaleAdd", e._on_scale_add_marker),
            e.dblclick_dhx_marked_timespan = function(t, a) {
                e.config.dblclick_create || e.callEvent("onScaleDblClick", [e.getActionData(t).date, a, t]), e.addEventNow(e.getActionData(t).date, null, t)
            }
    }, e._temp_limit_scope()
});