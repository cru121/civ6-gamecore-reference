// Client-side search over exe_function_index.json. Rows: [name, linuxVa, windowsRva, confidence(h|m|l|e|u), category, size, notes]
document.addEventListener('DOMContentLoaded', function () {
  var app = document.getElementById('exefnapp');
  if (!app) return;
  var rows = [], cats = [];
  var CONF = { h: 'high', m: 'medium', l: 'low', e: 'export', u: 'unmapped' };
  function esc(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function build() {
    app.innerHTML = '';
    var box = document.createElement('div');
    box.innerHTML = '<input id="eq" type="search" placeholder="name, Lua method, note, or address (Windows RVA or Linux address)" style="width:60%;padding:6px"> ' +
      '<select id="ecat"><option value="">all categories</option>' + cats.map(function (c) { return '<option>' + c + '</option>'; }).join('') + '</select> ' +
      '<select id="econf"><option value="">any confidence</option><option value="h">high</option><option value="m">medium</option><option value="l">low (unreliable)</option><option value="e">Windows export</option><option value="u">unmapped</option></select> ' +
      '<label><input type="checkbox" id="emap"> has a Windows address</label>' +
      '<div id="ecount" style="margin:8px 0;font-size:14px"></div><div id="eres"></div>';
    app.appendChild(box);
    ['eq', 'ecat', 'econf', 'emap'].forEach(function (id) { document.getElementById(id).addEventListener('input', run); });
    run();
  }
  function run() {
    var q = document.getElementById('eq').value.toLowerCase().trim().split(/\s+/).filter(Boolean).map(function (t) { return t.replace(/^0x/, ''); });
    var cat = document.getElementById('ecat').value, conf = document.getElementById('econf').value, mapped = document.getElementById('emap').checked;
    var out = [], total = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (cat && r[4] !== cat) continue;
      if (conf && r[3] !== conf) continue;
      if (mapped && !r[2]) continue;
      if (q.length) {
        var hay = (r[0] + ' ' + r[1] + ' ' + r[2] + ' ' + (r[6] || '')).toLowerCase();
        var ok = true;
        for (var k = 0; k < q.length; k++) if (hay.indexOf(q[k]) < 0) { ok = false; break; }
        if (!ok) continue;
      }
      total++;
      if (out.length < 300) out.push(r);
    }
    document.getElementById('ecount').textContent = total + ' matching functions' + (total > out.length ? ' (showing the first ' + out.length + '; refine the search)' : '');
    var h = '<table><tr><th>Function (Linux name)</th><th>Category</th><th>Windows RVA</th><th>Confidence</th><th>Linux address</th><th>Size</th><th>Notes</th></tr>';
    out.forEach(function (r) {
      h += '<tr><td>' + esc(r[0]) + '</td><td>' + esc(r[4]) + '</td><td>' + (r[2] ? '<code>0x' + r[2] + '</code>' : '—') + '</td><td>' + CONF[r[3]] + '</td><td>' + (r[1] ? '<code>0x' + r[1] + '</code>' : '—') +
        '</td><td>' + (r[5] || '') + '</td><td>' + esc(r[6] || '') + '</td></tr>';
    });
    document.getElementById('eres').innerHTML = h + '</table>';
  }
  fetch(ROOT + 'exe_function_index.json').then(function (r) { return r.json(); }).then(function (d) {
    rows = d.rows; cats = d.cats; build();
  }).catch(function (e) {
    app.innerHTML = 'The index could not be loaded (' + e + '). Open the site through a web server (for example GitHub Pages); browsers block loading data files from local file:// pages.';
  });
});
