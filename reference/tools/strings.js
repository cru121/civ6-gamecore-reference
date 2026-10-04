// Game text: lets a reader supply their own game strings. Nothing is uploaded; everything stays in this browser.
//   - a "strings file" (JSON) is loaded from disk and kept in IndexedDB; text keys on the pages (span[data-loc]) show the reader's own text
//   - the builder on the Game text page makes that file from the reader's own game folder (only the keys this reference uses)
// Strings file: {"format":"civ6-ref-strings","version":1,"created":"...","languages":{"en_US":{"LOC_KEY":"text",...},"zh_Hans_CN":{...}}}
(function () {
  'use strict';
  var FORMAT = 'civ6-ref-strings';

  // ------------------------------------------------------------ extraction (shared by the builder and the tests)
  function decode(s) {
    var m = /^\s*<!\[CDATA\[([\s\S]*)\]\]>\s*$/.exec(s);
    if (m) return m[1];
    return s.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|amp|lt|gt|quot|apos);/g, function (_, e) {
      if (e === 'amp') return '&'; if (e === 'lt') return '<'; if (e === 'gt') return '>'; if (e === 'quot') return '"'; if (e === 'apos') return "'";
      return String.fromCodePoint(e[1] === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10));
    });
  }
  // text: the content of one game text XML file; needed: object {key:true}; out: {lang:{key:text}} (later calls override earlier ones)
  function langFromPath(path) { var m = /\/text\/([a-z]{2}_[A-Za-z_]+)\//i.exec(String(path || '').replace(/[\\]/g, '/')); return m ? m[1] : null; }
  function extractText(text, needed, out, path) {
    var defLang = /<EnglishText[\s>]/.test(text) ? 'en_US' : langFromPath(path);
    var re = /<(?:Row|Replace)\b([^>]*?)>\s*<Text>([\s\S]*?)<\/Text>/g, m, n = 0;
    while ((m = re.exec(text))) {
      var attrs = {}, a, ar = /(\w+)\s*=\s*"([^"]*)"/g;
      while ((a = ar.exec(m[1]))) attrs[a[1]] = a[2];
      var tag = attrs.Tag, lang = attrs.Language || defLang;
      if (!tag || !lang || !needed[tag]) continue;
      (out[lang] = out[lang] || {})[tag] = decode(m[2]);
      n++;
    }
    return n;
  }
  // order in which game folders override each other: base game, other DLC, expansion 1, expansion 2
  function priority(path) {
    var p = path.toLowerCase();
    if (/\/expansion2\//.test(p)) return 3;
    if (/\/expansion1\//.test(p)) return 2;
    if (/\/dlc\//.test(p)) return 1;
    return 0;
  }
  function isTextFile(path) { return /\.xml$/i.test(path) && /\/text\//i.test(path.replace(/\\/g, '/')) && !/removetext/i.test(path); }
  function clean(t) {
    return String(t).replace(/\[NEWLINE\]/g, ' · ').replace(/\[ICON_([A-Za-z0-9_]+)\]/g, '⟨$1⟩')
      .replace(/\[\/?(COLOR[A-Za-z0-9_:]*|ENDCOLOR|LINK[^\]]*|ENDLINK|B|\/B)\]/g, '').replace(/\[[A-Za-z0-9_:]+\]/g, '');
  }
  var api = { FORMAT: FORMAT, langFromPath: langFromPath, extractText: extractText, priority: priority, isTextFile: isTextFile, clean: clean, decode: decode };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof document === 'undefined') return;

  // ------------------------------------------------------------ storage (IndexedDB; the page works without it)
  function idb(cb) {
    try { var r = indexedDB.open('civ6ref', 1); r.onupgradeneeded = function () { r.result.createObjectStore('kv'); }; r.onsuccess = function () { cb(r.result); }; r.onerror = function () { cb(null); }; }
    catch (e) { cb(null); }
  }
  function dbOp(mode, fn, cb) {
    idb(function (db) {
      if (!db) return cb(null);
      try { var t = db.transaction('kv', mode), req = fn(t.objectStore('kv')); t.oncomplete = function () { cb(req && req.result !== undefined ? req.result : true); }; t.onerror = t.onabort = function () { cb(null); }; }
      catch (e) { cb(null); }
    });
  }
  function getRoot() { try { return ROOT; } catch (e) { return ''; } }
  var S = { data: null, lang: null, map: null };
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }

  function lookup(key) {
    if (!S.data) return null;
    var L = S.data.languages, t = L[S.lang] && L[S.lang][key];
    return t || (L.en_US && L.en_US[key]) || null;
  }
  function apply(root) {
    var els = (root || document).querySelectorAll('[data-loc]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i], key = el.getAttribute('data-loc'), t = lookup(key);
      if (t) { el.textContent = clean(t); el.classList.add('loc-ok'); el.title = key; }
      else if (el.classList.contains('loc-ok')) { el.classList.remove('loc-ok'); el.innerHTML = '<code></code>'; el.firstChild.textContent = key; el.title = ''; }
    }
  }
  function validate(d) {
    if (!d || d.format !== FORMAT || !d.languages || typeof d.languages !== 'object') throw new Error('This is not a Civ VI reference strings file.');
    var n = 0; for (var l in d.languages) n += Object.keys(d.languages[l]).length;
    if (!n) throw new Error('The strings file has no text.');
    return d;
  }
  function setData(d, persist, cb) {
    S.data = d;
    var langs = Object.keys(d.languages), want = lsGet('civ6ref.lang');
    S.lang = langs.indexOf(want) >= 0 ? want : (langs.indexOf('en_US') >= 0 ? 'en_US' : langs[0]);
    apply(); renderPanel();
    if (persist) dbOp('readwrite', function (s) { return s.put(d, 'strings'); }, function (ok) { if (cb) cb(ok); }); else if (cb) cb(true);
  }
  function clear() { S.data = null; apply(); renderPanel(); dbOp('readwrite', function (s) { return s.delete('strings'); }, function () { }); }

  // ------------------------------------------------------------ panel in the sidebar
  var panel;
  function el(tag, props, kids) { var e = document.createElement(tag); for (var k in (props || {})) { if (k === 'text') e.textContent = props[k]; else e.setAttribute(k, props[k]); } (kids || []).forEach(function (c) { e.appendChild(c); }); return e; }
  function renderPanel() {
    if (!panel) return;
    panel.innerHTML = '';
    var root = getRoot();
    if (!S.data) {
      var inp = el('input', { type: 'file', accept: '.json,application/json', id: 'gt-file', style: 'display:none' });
      inp.addEventListener('change', function () { var f = inp.files[0]; if (f) loadFile(f); });
      panel.appendChild(el('div', { class: 'gt-t', text: 'Game text: not loaded' }));
      var b = el('a', { href: '#', text: 'Load strings file' }); b.addEventListener('click', function (e) { e.preventDefault(); inp.click(); });
      panel.appendChild(b); panel.appendChild(inp);
      panel.appendChild(el('a', { href: root + 'game-text.html', text: 'What is this?' }));
    } else {
      var langs = Object.keys(S.data.languages);
      panel.appendChild(el('div', { class: 'gt-t', text: 'Game text: loaded' }));
      var sel = el('select', { id: 'gt-lang' });
      langs.forEach(function (l) { var o = el('option', { value: l, text: l + ' (' + Object.keys(S.data.languages[l]).length + ')' }); if (l === S.lang) o.selected = true; sel.appendChild(o); });
      sel.addEventListener('change', function () { S.lang = sel.value; lsSet('civ6ref.lang', S.lang); apply(); });
      panel.appendChild(sel);
      var c = el('a', { href: '#', text: 'Clear' }); c.addEventListener('click', function (e) { e.preventDefault(); clear(); });
      panel.appendChild(c);
    }
  }
  function loadFile(f) {
    var r = new FileReader();
    r.onload = function () {
      try { setData(validate(JSON.parse(r.result)), true, function (ok) { if (ok === null) alert('Loaded, but this browser would not keep it between visits (private window?).'); }); }
      catch (e) { alert(e.message || e); }
    };
    r.readAsText(f);
  }

  // ------------------------------------------------------------ search by in-game wording
  function getMap(cb) {
    if (S.map) return cb(S.map);
    fetch(getRoot() + 'keymap.json').then(function (r) { return r.json(); }).then(function (m) { S.map = m; cb(m); }).catch(function () { cb({}); });
  }
  api.loaded = function () { return !!S.data; };
  // calls cb(list of {t:text, u:url, s:label}) for texts containing the query (substring, case-insensitive; works for Chinese etc.)
  api.search = function (q, cb) {
    q = (q || '').trim().toLowerCase();
    if (!S.data || q.length < 2) return cb([]);
    getMap(function (map) {
      var out = [], keys = Object.keys(map), langs = [S.lang].concat(Object.keys(S.data.languages).filter(function (l) { return l !== S.lang; }));
      for (var i = 0; i < keys.length && out.length < 40; i++) {
        var k = keys[i], t = null;
        for (var j = 0; j < langs.length && !t; j++) { var x = S.data.languages[langs[j]][k]; if (x && clean(x).toLowerCase().indexOf(q) >= 0) t = x; }
        if (!t) continue;
        map[k].forEach(function (e) { if (out.length < 40) out.push({ t: clean(t), u: e[1], s: e[0] }); });
      }
      cb(out);
    });
  };
  window.CIV6 = api;

  // ------------------------------------------------------------ builder (Game text page)
  function buildUI(host) {
    var root = getRoot();
    host.innerHTML = '';
    var st = el('div', { class: 'gt-status', text: 'Choose your Civilization VI game folder (the one that contains Base and DLC), or just its Text folders.' });
    var inp = el('input', { type: 'file', id: 'gt-dir', multiple: '' });
    inp.setAttribute('webkitdirectory', ''); inp.setAttribute('directory', '');
    var out = el('div', { class: 'gt-out' });
    host.appendChild(inp); host.appendChild(st); host.appendChild(out);
    var result = null;
    inp.addEventListener('change', function () {
      var files = Array.prototype.slice.call(inp.files).filter(function (f) { return isTextFile(f.webkitRelativePath || f.name); });
      if (!files.length) { st.textContent = 'No game text files found in that folder. Pick the game folder or a Text folder.'; return; }
      files.sort(function (a, b) { return priority(a.webkitRelativePath) - priority(b.webkitRelativePath) || (a.webkitRelativePath < b.webkitRelativePath ? -1 : 1); });
      fetch(root + 'strings_keys.json').then(function (r) { return r.json(); }).then(function (keys) {
        var needed = {}; keys.forEach(function (k) { needed[k] = true; });
        var langs = {}, i = 0;
        function step() {
          if (i >= files.length) return done(keys.length, langs);
          st.textContent = 'Reading ' + (i + 1) + ' / ' + files.length + ': ' + files[i].name;
          files[i].text().then(function (t) { extractText(t, needed, langs, files[i].webkitRelativePath); i++; setTimeout(step, 0); });
        }
        step();
      }).catch(function (e) { st.textContent = 'Could not load the key list: ' + e; });
    });
    function done(nkeys, langs) {
      result = langs;
      var names = Object.keys(langs).sort();
      if (!names.length) { st.textContent = 'No text for the keys of this reference was found. Is it a Civilization VI folder?'; return; }
      st.textContent = 'Found text in ' + names.length + ' language(s) for the ' + nkeys + ' keys this reference uses. Choose what to include:';
      out.innerHTML = '';
      var boxes = {};
      names.forEach(function (l) {
        var cb = el('input', { type: 'checkbox' }); cb.checked = (l === 'en_US') || names.length === 1; boxes[l] = cb;
        out.appendChild(el('label', { style: 'display:block' }, [cb, el('span', { text: ' ' + l + ' (' + Object.keys(langs[l]).length + ' of ' + nkeys + ' keys)' })]));
      });
      function pick() { var d = { format: FORMAT, version: 1, created: new Date().toISOString(), languages: {} }; names.forEach(function (l) { if (boxes[l].checked) d.languages[l] = langs[l]; }); return d; }
      var save = el('button', { type: 'button', text: 'Download strings file' });
      save.addEventListener('click', function () {
        var d = pick(); if (!Object.keys(d.languages).length) return alert('Select at least one language.');
        var a = el('a', { href: URL.createObjectURL(new Blob([JSON.stringify(d)], { type: 'application/json' })), download: 'civ6-strings.json' });
        document.body.appendChild(a); a.click(); a.remove();
      });
      var use = el('button', { type: 'button', text: 'Use it now in this browser' });
      use.addEventListener('click', function () { var d = pick(); if (!Object.keys(d.languages).length) return alert('Select at least one language.'); setData(d, true, function () { st.textContent = 'Loaded. Text keys on the pages now show your game text.'; }); });
      out.appendChild(save); out.appendChild(document.createTextNode(' ')); out.appendChild(use);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var nav = document.querySelector('nav'), res = document.getElementById('res');
    if (nav && res) { panel = el('div', { id: 'gt', class: 'gt' }); nav.insertBefore(panel, res.nextSibling); renderPanel(); }
    dbOp('readonly', function (s) { return s.get('strings'); }, function (d) { if (d && d !== true) { try { setData(validate(d), false); } catch (e) { } } });
    var host = document.getElementById('gt-builder'); if (host) buildUI(host);
  });
})();
