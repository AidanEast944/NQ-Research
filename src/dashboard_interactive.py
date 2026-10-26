"""
Client-side interactivity for results/dashboard.html (added 2026-10-26). Pure HTML/CSS/JS: it reads nothing, writes
nothing and changes no number on the page. generate_dashboard.py inserts INTERACTIVE_CSS / TOOLBAR_HTML / INTERACTIVE_JS.
Features: filter chips (all / open now / live / retired), text search across panels, collapse or expand any panel by clicking
its header, collapse-all / expand-all, expandable sortable trade history per track, and remembered choices (localStorage,
wrapped in try/except so the page works with it blocked).
"""
from datetime import datetime


def trade_table_html(trades, default_point_value):
    """Expandable, newest-first closed-trade table for one paper account. Pure formatting of existing numbers."""
    if not trades:
        return ""
    rows = []
    for t in reversed(trades):
        pts = t.get("points_result", 0) or 0
        pv = t.get("point_value_used", default_point_value) or default_point_value
        dollars = pts * pv
        cls = "pos" if dollars > 0 else ("neg" if dollars < 0 else "neu")
        rows.append(
            f'<tr><td title="entry {t.get("entry_price", "")} -> exit {t.get("exit_price", "")}">{t.get("entry_date", t.get("date", ""))}</td>'
            f'<td>{t.get("direction", "")}</td><td>{t.get("reason", "")}</td>'
            f'<td data-v="{pts}" class="{cls}">{pts:+.1f}</td>'
            f'<td data-v="{dollars}" class="{cls}">{dollars:+,.2f}</td></tr>')
    head = "".join(f"<th>{h}</th>" for h in ("DATE", "DIR", "WHY", "PTS", "$"))
    return (f'<details class="trades"><summary>TRADE HISTORY ({len(trades)}) — click column headers to sort</summary>'
            f'<div class="ttwrap"><table class="tt"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')


INTERACTIVE_CSS = """
    .toolbar { position: sticky; top: 0; z-index: 50; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
        background: rgba(10,14,20,0.96); border: 1px solid #2a2e39; padding: 8px 12px; margin-bottom: 16px; }
    .chip, .tbtn { background: #131722; color: #cfd3dc; border: 1px solid #2a2e39; padding: 5px 10px; font: inherit;
        font-size: 11px; letter-spacing: 1px; cursor: pointer; }
    .chip:hover, .tbtn:hover { border-color: #00e5a0; }
    .chip.active { background: #00e5a0; color: #0a0e14; border-color: #00e5a0; font-weight: 700; }
    .search { background: #0a0e14; color: #e6e9ef; border: 1px solid #2a2e39; padding: 5px 10px; font: inherit;
        font-size: 12px; min-width: 240px; }
    .toolbar .count { color: #6b7280; font-size: 11px; margin-left: auto; }
    .panel.hidden { display: none; }
    .panel-header { cursor: pointer; user-select: none; }
    .panel-header::after { content: " \\25BE"; color: #6b7280; float: right; }
    .panel.collapsed .panel-header::after { content: " \\25B8"; }
    .panel.collapsed .panel-body { display: none; }
    details.trades { margin-top: 10px; border-top: 1px solid #1a1e28; padding-top: 8px; }
    details.trades summary { cursor: pointer; font-size: 11px; color: #8b909c; letter-spacing: 1px; }
    .panel { min-width: 0; }
    .ttwrap { overflow-x: auto; max-height: 360px; overflow-y: auto; }
    table.tt { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 10px; }
    table.tt th, table.tt td { white-space: nowrap; }
    table.tt th { text-align: left; color: #6b7280; font-weight: 600; padding: 4px 6px; cursor: pointer;
        border-bottom: 1px solid #2a2e39; user-select: none; }
    table.tt th:hover { color: #00e5a0; }
    table.tt td { padding: 3px 6px; border-bottom: 1px solid #1a1e28; }
"""

TOOLBAR_HTML = """
    <div class="toolbar" id="toolbar">
        <button class="chip active" data-filter="all">ALL</button>
        <button class="chip" data-filter="open">OPEN NOW</button>
        <button class="chip" data-filter="live">LIVE</button>
        <button class="chip" data-filter="retired">RETIRED</button>
        <input class="search" id="panel-search" type="search" placeholder="search panels (e.g. YM, pairs)">
        <button class="tbtn" id="collapse-all">COLLAPSE ALL</button>
        <button class="tbtn" id="expand-all">EXPAND ALL</button>
        <button class="tbtn" id="toggle-trades">TRADE HISTORIES</button>
        <span class="count" id="panel-count"></span>
    </div>
"""

INTERACTIVE_JS = """
<script>
(function () {
  var panels = Array.prototype.slice.call(document.querySelectorAll('.panel'));
  var filter = 'all', query = '';
  function store(k, v) { try { localStorage.setItem('nqdash.' + k, v); } catch (e) {} }
  function recall(k) { try { return localStorage.getItem('nqdash.' + k); } catch (e) { return null; } }
  function kind(p) {
    var t = (p.querySelector('.panel-header') || {}).textContent || '';
    return /RETIRED/.test(t) ? 'retired' : (/LIVE/.test(t) ? 'live' : 'other');
  }
  function apply() {
    var shown = 0;
    panels.forEach(function (p) {
      var ok = true;
      if (filter === 'open') ok = p.getAttribute('data-open') === '1';
      else if (filter === 'live') ok = kind(p) === 'live';
      else if (filter === 'retired') ok = kind(p) === 'retired';
      if (ok && query) ok = p.textContent.toLowerCase().indexOf(query) !== -1;
      p.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });
    document.getElementById('panel-count').textContent = shown + ' of ' + panels.length + ' panels';
  }
  document.querySelectorAll('.chip').forEach(function (c) {
    c.addEventListener('click', function () {
      document.querySelectorAll('.chip').forEach(function (x) { x.classList.remove('active'); });
      c.classList.add('active'); filter = c.getAttribute('data-filter'); store('filter', filter); apply();
    });
  });
  var s = document.getElementById('panel-search');
  s.addEventListener('input', function () { query = s.value.trim().toLowerCase(); apply(); });
  panels.forEach(function (p, i) {
    var h = p.querySelector('.panel-header');
    if (!h) return;
    var key = 'collapsed.' + (h.textContent || i).trim().slice(0, 40);
    if (recall(key) === '1') p.classList.add('collapsed');
    h.addEventListener('click', function () { p.classList.toggle('collapsed'); store(key, p.classList.contains('collapsed') ? '1' : '0'); });
  });
  function setAll(c) { panels.forEach(function (p) { p.classList.toggle('collapsed', c); }); }
  document.getElementById('collapse-all').addEventListener('click', function () { setAll(true); });
  document.getElementById('expand-all').addEventListener('click', function () { setAll(false); });
  var tradesOpen = false;
  document.getElementById('toggle-trades').addEventListener('click', function () {
    tradesOpen = !tradesOpen;
    document.querySelectorAll('details.trades').forEach(function (d) { d.open = tradesOpen; });
    if (tradesOpen) setAll(false);
  });
  document.querySelectorAll('table.tt').forEach(function (tb) {
    tb.querySelectorAll('th').forEach(function (th, idx) {
      var asc = false;
      th.addEventListener('click', function () {
        asc = !asc;
        var body = tb.tBodies[0], rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[idx], y = b.cells[idx];
          var xv = x.getAttribute('data-v'), yv = y.getAttribute('data-v');
          var r = (xv !== null && yv !== null) ? (parseFloat(xv) - parseFloat(yv)) : x.textContent.localeCompare(y.textContent);
          return asc ? r : -r;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });
  var saved = recall('filter');
  if (saved) { var btn = document.querySelector('.chip[data-filter="' + saved + '"]'); if (btn) btn.click(); } else { apply(); }
})();
</script>
"""
