/* events.js — full filter + render logic for events.html */
(async function () {
  const listEl   = document.getElementById('events-list');
  const barEl    = document.getElementById('results-bar');
  const clearBtn = document.getElementById('clear-filters');
  const toggleBtn = document.getElementById('filter-toggle');
  const sidebar   = document.getElementById('filter-sidebar');
  const filterBadge = document.getElementById('filter-badge');
  const filterArrow = document.getElementById('filter-arrow');

  listEl.innerHTML = '<div class="loading"><div class="spinner"></div> Loading events…</div>';

  let allEvents = [];
  try {
    const res  = await fetch('data/events.json');
    const data = await res.json();
    allEvents  = data.events || [];
  } catch {
    listEl.innerHTML = '<div class="empty-state"><div class="empty-icon">🌧️</div><h3>Couldn\'t load events</h3><p>Try refreshing the page.</p></div>';
    return;
  }

  // ── Filter state ──────────────────────────────────────────────
  function getFilters() {
    const checked = (name) =>
      [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(i => i.value);
    const radio = (name) => {
      const el = document.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : null;
    };
    return {
      date:     radio('date'),
      counties: checked('county'),
      cost:     radio('cost'),
      cats:     checked('cat'),
      days:     checked('dow').map(Number),
      reg:      radio('reg'),
    };
  }

  function countActiveFilters(f) {
    let n = 0;
    if (f.date !== 'all') n++;
    n += f.counties.length;
    if (f.cost !== 'all') n++;
    n += f.cats.length;
    n += f.days.length;
    if (f.reg !== 'all') n++;
    return n;
  }

  // ── Date helpers ──────────────────────────────────────────────
  const today = new Date(); today.setHours(0,0,0,0);
  function weekEnd()  { const d = new Date(today); d.setDate(d.getDate() + (7 - d.getDay())); return d; }
  function monthEnd() { return new Date(today.getFullYear(), today.getMonth() + 1, 0); }
  function next30()   { const d = new Date(today); d.setDate(d.getDate() + 30); return d; }

  function filterEvents(events, f) {
    const we = weekEnd(), me = monthEnd(), n30 = next30();
    return events.filter(e => {
      const d = new Date(e.date + 'T00:00:00');
      if (d < today) return false;
      if (f.date === 'week'   && d > we)  return false;
      if (f.date === 'month'  && d > me)  return false;
      if (f.date === 'next30' && d > n30) return false;
      if (f.counties.length && !f.counties.includes(e.county)) return false;
      if (f.cost === 'free' && e.cost !== 'free') return false;
      if (f.cats.length && !f.cats.some(c => (e.categories||[]).includes(c))) return false;
      if (f.days.length && !f.days.includes(d.getDay())) return false;
      if (f.reg === 'no-reg' && e.registration_required) return false;
      return true;
    });
  }

  // ── URL param sync ────────────────────────────────────────────
  function pushParams(f) {
    const p = new URLSearchParams();
    if (f.date !== 'all') p.set('date', f.date);
    f.counties.forEach(v => p.append('county', v));
    if (f.cost !== 'all') p.set('cost', f.cost);
    f.cats.forEach(v => p.append('cat', v));
    f.days.forEach(v => p.append('dow', v));
    if (f.reg !== 'all') p.set('reg', f.reg);
    const str = p.toString();
    history.replaceState(null, '', str ? '?' + str : location.pathname);
  }

  function applyParams() {
    const p = new URLSearchParams(location.search);
    if (p.has('date')) {
      const el = document.querySelector(`input[name="date"][value="${p.get('date')}"]`);
      if (el) { document.querySelectorAll('input[name="date"]').forEach(i=>i.checked=false); el.checked=true; }
    }
    p.getAll('county').forEach(v => {
      const el = document.querySelector(`input[name="county"][value="${v}"]`);
      if (el) el.checked = true;
    });
    if (p.has('cost')) {
      const el = document.querySelector(`input[name="cost"][value="${p.get('cost')}"]`);
      if (el) { document.querySelectorAll('input[name="cost"]').forEach(i=>i.checked=false); el.checked=true; }
    }
    p.getAll('cat').forEach(v => {
      const el = document.querySelector(`input[name="cat"][value="${v}"]`);
      if (el) el.checked = true;
    });
    p.getAll('dow').forEach(v => {
      const el = document.querySelector(`input[name="dow"][value="${v}"]`);
      if (el) el.checked = true;
    });
    if (p.has('reg')) {
      const el = document.querySelector(`input[name="reg"][value="${p.get('reg')}"]`);
      if (el) { document.querySelectorAll('input[name="reg"]').forEach(i=>i.checked=false); el.checked=true; }
    }
  }

  // ── Rendering ─────────────────────────────────────────────────
  const MONTH = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const DOW   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const CAT_LABEL = {
    nature:'Nature', hiking:'Hiking', science:'Science', art:'Art', library:'Library',
    museum:'Museum', festival:'Festival', farm:'Farm', fishing:'Fishing', beach:'Beach'
  };
  const COUNTY_LABEL = {
    'lake-il':'Lake County IL', 'kenosha-wi':'Kenosha County WI',
    'chicago-day-trip':'Chicago Day Trip', 'milwaukee-day-trip':'Milwaukee Day Trip'
  };

  function renderCard(e) {
    const d = new Date(e.date + 'T00:00:00');
    const costBadge = e.cost === 'free'
      ? '<span class="badge badge-free">FREE</span>'
      : `<span class="badge badge-paid">${e.cost_detail ? '$&thinsp;' + e.cost_detail : 'Paid'}</span>`;
    const catBadges = (e.categories||[]).map(c =>
      `<span class="badge badge-cat">${CAT_LABEL[c]||c}</span>`).join('');
    const regBadge = e.registration_required
      ? '<span class="badge" style="background:var(--berry);color:#fff;">Registration required</span>' : '';
    const timeStr = e.time ? `${e.time}${e.end_time ? ' – '+e.end_time : ''}` : '';
    const srcLink = e.source_url
      ? `<a href="${e.source_url}" target="_blank" rel="noopener">${e.source}</a>` : e.source;
    const regLink = (e.registration_required && e.registration_url)
      ? ` &bull; <a href="${e.registration_url}" target="_blank" rel="noopener">Register →</a>` : '';
    const titleEl = e.source_url
      ? `<a href="${e.source_url}" target="_blank" rel="noopener">${e.title}</a>` : e.title;
    const countyLabel = COUNTY_LABEL[e.county] || e.county;

    return `<div class="event-card mb-1">
      <div class="event-date-block">
        <div class="month">${MONTH[d.getMonth()]}</div>
        <div class="day">${d.getDate()}</div>
        <div class="dow">${DOW[d.getDay()]}</div>
      </div>
      <div class="event-body">
        <div class="event-title">${titleEl}</div>
        <div class="event-meta">
          ${timeStr ? `<span>🕐 ${timeStr}</span>` : ''}
          <span>📍 ${e.location_name}</span>
          <span>🗺️ ${countyLabel}</span>
          ${e.ages && e.ages !== 'all' ? `<span>👧 Ages ${e.ages}</span>` : ''}
        </div>
        <p class="text-sm text-lt" style="margin-bottom:.4rem;">${e.description}</p>
        <div class="event-badges">${costBadge}${catBadges}${regBadge}</div>
        <div class="event-source mt-1">${srcLink}${regLink}</div>
      </div>
    </div>`;
  }

  function renderActiveFilters(f) {
    const chips = [];
    if (f.date !== 'all') {
      const labels = {week:'This week', month:'This month', next30:'Next 30 days'};
      chips.push({label: labels[f.date]||f.date, key:'date'});
    }
    f.counties.forEach(v => chips.push({label: COUNTY_LABEL[v]||v, key:'county', val:v}));
    if (f.cost !== 'all') chips.push({label:'Free only', key:'cost'});
    f.cats.forEach(v => chips.push({label: CAT_LABEL[v]||v, key:'cat', val:v}));
    f.days.forEach(v => chips.push({label: DOW[v], key:'dow', val:v}));
    if (f.reg !== 'all') chips.push({label:'No registration', key:'reg'});
    return chips;
  }

  function render() {
    const f = getFilters();
    const filtered = filterEvents(allEvents, f);
    pushParams(f);

    const activeCount = countActiveFilters(f);
    if (filterBadge) {
      filterBadge.style.display = activeCount > 0 ? 'inline' : 'none';
      filterBadge.textContent = activeCount;
    }

    const chips = renderActiveFilters(f);
    const chipHtml = chips.map(c =>
      `<span class="active-filter-chip" data-key="${c.key}" data-val="${c.val||''}">
        ${c.label}
        <button aria-label="Remove filter" onclick="removeFilter('${c.key}','${c.val||''}')">✕</button>
      </span>`).join('');

    barEl.innerHTML = `
      <span class="results-count">${filtered.length} event${filtered.length !== 1 ? 's' : ''}</span>
      <div class="active-filters">
        ${chipHtml}
        ${chips.length > 1 ? '<button class="clear-all-btn" onclick="clearAllFilters()">Clear all</button>' : ''}
      </div>`;

    if (filtered.length === 0) {
      listEl.innerHTML = '<div class="empty-state"><div class="empty-icon">🌦️</div><h3>No events match these filters</h3><p>Try removing some filters, or check back after the Monday update.</p></div>';
    } else {
      listEl.innerHTML = filtered.map(renderCard).join('');
    }
  }

  // ── Remove individual filter chip ─────────────────────────────
  window.removeFilter = function(key, val) {
    if (key === 'date') {
      document.querySelector('input[name="date"][value="all"]').checked = true;
    } else if (key === 'cost') {
      document.querySelector('input[name="cost"][value="all"]').checked = true;
    } else if (key === 'reg') {
      document.querySelector('input[name="reg"][value="all"]').checked = true;
    } else {
      const el = document.querySelector(`input[name="${key}"][value="${val}"]`);
      if (el) el.checked = false;
    }
    render();
  };

  window.clearAllFilters = function() {
    document.querySelector('input[name="date"][value="all"]').checked = true;
    document.querySelector('input[name="cost"][value="all"]').checked = true;
    document.querySelector('input[name="reg"][value="all"]').checked = true;
    document.querySelectorAll('input[name="county"], input[name="cat"], input[name="dow"]')
      .forEach(i => i.checked = false);
    render();
  };

  if (clearBtn) clearBtn.addEventListener('click', window.clearAllFilters);

  // ── Mobile filter toggle ──────────────────────────────────────
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      const collapsed = sidebar.classList.toggle('collapsed');
      toggleBtn.setAttribute('aria-expanded', String(!collapsed));
      if (filterArrow) filterArrow.textContent = collapsed ? '▼' : '▲';
    });
    sidebar.classList.add('collapsed');
  }

  // ── Wire up all filter inputs ─────────────────────────────────
  document.querySelectorAll('.filter-sidebar input').forEach(input => {
    input.addEventListener('change', render);
  });

  // ── Init ──────────────────────────────────────────────────────
  applyParams();
  render();
})();
