// Client-side search over function_index.json: rows are
// [name, symbolRva, currentRva, size, category, luaName, mapCategory, signature, curatedId, ceWrapped]
document.addEventListener('DOMContentLoaded', function () {
  var app = document.getElementById('fnapp');
  if (!app) return;
  var data = null, rows = [], cats = [];
  function safe(s) { return s.replace(/[^A-Za-z0-9_.-]/g, '_'); }
  function curatedHref(id) {
    var rest = id.slice(7), cls = rest.split('@')[0], ns = cls.split('::')[0];
    return ROOT + 'native/' + safe(ns) + '.html#' + safe(rest).toLowerCase();
  }
  function build() {
    app.innerHTML = '';
    var box = document.createElement('div');
    box.innerHTML = '<input id="fq" type="search" placeholder="name, Lua method, signature or address" style="width:60%;padding:6px"> ' +
      '<select id="fcat"><option value="">all categories</option>' + cats.map(function (c) { return '<option>' + c + '</option>'; }).join('') + '</select> ' +
      '<label><input type="checkbox" id="fmap"> mapped to the current build</label> ' +
      '<label><input type="checkbox" id="fcur"> detailed entries only (★)</label>' +
      '<div id="fcount" style="margin:8px 0;font-size:14px"></div><div id="fres"></div>';
    app.appendChild(box);
    ['fq', 'fcat', 'fmap', 'fcur'].forEach(function (id) { document.getElementById(id).addEventListener('input', run); });
    run();
  }
  function esc(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function run() {
    var q = document.getElementById('fq').value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    var cat = document.getElementById('fcat').value, mapped = document.getElementById('fmap').checked, cur = document.getElementById('fcur').checked;
    var out = [], total = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (cat && r[4] !== cat) continue;
      if (mapped && !r[2]) continue;
      if (cur && !r[8]) continue;
      if (q.length) {
        var hay = (r[0] + ' ' + r[1] + ' ' + r[2] + ' ' + r[5] + ' ' + r[7]).toLowerCase();
        var ok = true;
        for (var k = 0; k < q.length; k++) if (hay.indexOf(q[k]) < 0) { ok = false; break; }
        if (!ok) continue;
      }
      total++;
      if (out.length < 300) out.push(r);
    }
    document.getElementById('fcount').textContent = total + ' matching functions' + (total > out.length ? ' (showing the first ' + out.length + '; refine the search)' : '');
    var h = '<table><tr><th>Function</th><th>Category</th><th>Symbol</th><th>Current</th><th>Size</th><th>Lua</th><th>Signature (Linux)</th></tr>';
    out.forEach(function (r) {
      var name = esc(r[0]);
      if (r[8]) name = '<a href="' + curatedHref(r[8]) + '">' + name + ' ★</a>';
      if (r[9]) name += ' <small>(wrapped by CE)</small>';
      h += '<tr><td>' + name + '</td><td>' + r[4] + '</td><td><code>' + r[1] + '</code></td><td>' + (r[2] ? '<code>' + r[2] + '</code>' : '—') + '</td><td>' + r[3] +
        '</td><td>' + esc(r[5]) + '</td><td>' + (r[7] ? '<code>' + esc(r[7]) + '</code>' : '') + '</td></tr>';
    });
    document.getElementById('fres').innerHTML = h + '</table>';
  }
  fetch(ROOT + 'function_index.json').then(function (r) { return r.json(); }).then(function (d) {
    data = d; rows = d.rows; cats = d.cats; build();
  }).catch(function (e) {
    app.innerHTML = 'The index could not be loaded (' + e + '). Open the site through a web server (for example GitHub Pages); browsers block loading data files from local file:// pages.';
  });
});
