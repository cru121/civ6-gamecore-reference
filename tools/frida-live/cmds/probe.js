// probe TEXT [ms=3000] [max=300]: temporarily hook up to `max` (cap 40) mapped functions whose name contains TEXT, count calls per function and thread, report the busiest.
// Use it to find a function that runs regularly on the game thread (candidate tick hook). Hooks are switched off afterwards (never detached: detaching hot hooks hung the game).
defcmd('probe', 'probe TEXT [ms] [max]: which functions matching TEXT are called, by which thread (finds a tick hook candidate)', function (a) {
  const text = a[0] || '', ms = a[1] ? parseInt(a[1]) : 3000, max = a[2] ? parseInt(a[2]) : 300;
  const found = (/^0x/i.test(text) ? text.split(',').map(function (x) { return { name: x.trim(), rva: x.trim() }; }) : sym(text)).slice(0, Math.min(max, 40));
  const counts = {}, ls = [];
  state.probing = true;
  found.forEach(function (f) {
    const key = f.name;
    try {
      hook('probe:' + key, f.name, { onEnter: function () {
        if (!state.probing) return;
        const t = Process.getCurrentThreadId();
        const c = counts[key] || (counts[key] = {});
        c[t] = (c[t] || 0) + 1;
      } });
      ls.push(key);
    } catch (e) { /* skip functions that cannot be hooked */ }
  });
  log('probe: hooked ' + ls.length + ' functions for ' + ms + ' ms');
  return new Promise(function (res) {
    setTimeout(function () {
      state.probing = false; ls.forEach(function (k) { unhook('probe:' + k); });
      const rows = Object.keys(counts).map(function (k) {
        const per = counts[k]; const total = Object.keys(per).reduce(function (s, t) { return s + per[t]; }, 0);
        return { total: total, text: total + '  ' + k.replace('GameCore::', '') + '  threads ' + JSON.stringify(per) };
      }).sort(function (x, y) { return y.total - x.total; });
      res(rows.length ? rows.slice(0, 25).map(function (r) { return r.text; }).join('\n') : 'no calls in ' + ms + ' ms (' + found.length + ' functions hooked)');
    }, ms);
  });
});
