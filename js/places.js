/* places.js — filter + render logic for places.html */
(async function () {
  const gridEl    = document.getElementById('places-grid');
  const barEl     = document.getElementById('results-bar');
  const clearBtn  = document.getElementById('clear-filters');
  const toggleBtn = document.getElementById('filter-toggle');
  const sidebar   = document.getElementById('filter-sidebar');
  const filterBadge = document.getElementById('filter-badge');
  const filterArrow = document.getElementById('filter-arrow');

  gridEl.innerHTML = '<div class="loading" style="grid-column:1/-1"><div class="spinner"></div> Loading places…</div>';

  let allPlaces = [];
  try {
    const res  = await fetch('data/places.json');
    const data = await res.json();
    allPlaces  = data.places || [];
  } catch {
    gridEl.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🌧️</div><h3>Couldn\'t load places</h3><p>Try refreshing the page.</p></div>';
    return;
  }

  const TYPE_ICON = {
    trail: '🥾', beach: '🏖️', 'nature-center': '🦋',
    'splash-pad': '💦', 'aquatic-center': '🏊',
    farm: '🌽', fairground: '🎪', playground: '🛝'
  };
  const TYPE_LABEL = {
    trail: 'Trail', beach: 'Beach / Swimming', 'nature-center': 'Nature Center',
    'splash-pad': 'Splash Pad', 'aquatic-center': 'Aquatic Center',
    farm: 'Farm / Seasonal', fairground: 'Fair / Festival', playground: 'Playground'
  };
  const COUNTY_LABEL = {
    'lake-il': 'Lake County IL', 'kenosha-wi': 'Kenosha County WI',
    'chicago-day-trip': 'Chicago Day Trip', 'milwaukee-day-trip': 'Milwaukee Day Trip'
  };

  function getFilters() {
    const checked = (name) =>
      [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(i => i.value);
    const radio = (name) => {
      const el = document.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : null;
    };
    return {
      counties: checked('county'),
      types:    checked('type'),
      cost:     radio('cost'),
      tags:     checked('tag'),
    };
  }

  function countActiveFilters(f) {
    let n = 0;
    n += f.counties.length + f.types.length + f.tags.length;
    if (f.cost !== 'all') n++;
    return n;
  }

  function filterPlaces(places, f) {
    return places.filter(p => {
      if (f.counties.length && !f.counties.includes(p.county)) return false;
      if (f.types.length    && !f.types.includes(p.type))     return false;
      if (f.cost === 'free' && p.cost !== 'free')              return false;
      if (f.tags.length && !f.tags.some(t => (p.tags||[]).includes(t))) return false;
      return true;
    });
  }

  function pushParams(f) {
    const p = new URLSearchParams();
    f.counties.forEach(v => p.append('county', v));
    f.types.forEach(v   => p.append('type', v));
    if (f.cost !== 'all') p.set('cost', f.cost);
    f.tags.forEach(v    => p.append('tag', v));
    const str = p.toString();
    history.replaceState(null, '', str ? '?' + str : location.pathname);
  }

  function applyParams() {
    const p = new URLSearchParams(location.search);
    ['county','type','tag'].forEach(name => {
      p.getAll(name).forEach(v => {
        const el = document.querySelector(`input[name="${name}"][value="${v}"]`);
        if (el) el.checked = true;
      });
    });
    if (p.has('cost')) {
      const el = document.querySelector(`input[name="cost"][value="${p.get('cost')}"]`);
      if (el) { document.querySelectorAll('input[name="cost"]').forEach(i=>i.checked=false); el.checked=true; }
    }
  }

  function renderCard(p) {
    const icon = TYPE_ICON[p.type] || '📍';
    const typeLabel = TYPE_LABEL[p.type] || p.type;
    const countyLabel = COUNTY_LABEL[p.county] || p.county;
    const costBadge = p.cost === 'free'
      ? '<span class="badge badge-free">FREE</span>'
      : `<span class="badge badge-paid">Paid</span>`;
    const tags = (p.tags||[]).slice(0,5).map(t =>
      `<span class="place-tag">${t.replace(/-/g,' ')}</span>`).join('');
    const highlightsList = p.highlights && p.highlights.length
      ? `<ul style="padding-left:1rem;list-style:disc;font-size:.82rem;color:var(--text-lt);margin-top:.3rem;">${
          p.highlights.map(h=>`<li>${h}</li>`).join('')
        }</ul>` : '';
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.address||p.name)}`;
    const seasonStr = p.season && p.season !== 'year-round' ? `<span class="place-tag">📅 ${p.season}</span>` : '';

    return `<div class="place-card">
      <div class="place-card-header">
        <div>
          <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.15rem;">
            <span style="font-size:1.4rem;">${icon}</span>
            <span class="badge badge-cat" style="font-size:.7rem;">${typeLabel}</span>
            ${costBadge}
          </div>
          <div class="place-name">${p.url ? `<a href="${p.url}" target="_blank" rel="noopener">${p.name}</a>` : p.name}</div>
          <div class="place-town">📍 ${p.town} &bull; ${countyLabel}</div>
        </div>
      </div>
      <p class="place-desc">${p.description}</p>
      ${highlightsList}
      <div class="place-tags">${tags}${seasonStr}</div>
      ${p.cost_detail ? `<div class="text-sm text-lt">💰 ${p.cost_detail}</div>` : ''}
      <div class="place-links">
        ${p.url ? `<a href="${p.url}" target="_blank" rel="noopener">Website →</a>` : ''}
        <a href="${mapsUrl}" target="_blank" rel="noopener">Directions →</a>
        ${p.hours ? `<span class="text-lt">🕐 ${p.hours}</span>` : ''}
      </div>
    </div>`;
  }

  function render() {
    const f = getFilters();
    const filtered = filterPlaces(allPlaces, f);
    pushParams(f);

    const activeCount = countActiveFilters(f);
    if (filterBadge) {
      filterBadge.style.display = activeCount > 0 ? 'inline' : 'none';
      filterBadge.textContent = activeCount;
    }

    barEl.innerHTML = `<span class="results-count">${filtered.length} place${filtered.length !== 1 ? 's' : ''}</span>`;

    if (filtered.length === 0) {
      gridEl.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🔍</div><h3>No places match these filters</h3><p>Try removing some filters.</p></div>';
    } else {
      gridEl.innerHTML = filtered.map(renderCard).join('');
    }
  }

  window.clearAllFilters = function() {
    document.querySelector('input[name="cost"][value="all"]').checked = true;
    document.querySelectorAll('input[name="county"], input[name="type"], input[name="tag"]')
      .forEach(i => i.checked = false);
    render();
  };

  if (clearBtn) clearBtn.addEventListener('click', window.clearAllFilters);

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      const collapsed = sidebar.classList.toggle('collapsed');
      toggleBtn.setAttribute('aria-expanded', String(!collapsed));
      if (filterArrow) filterArrow.textContent = collapsed ? '▼' : '▲';
    });
    sidebar.classList.add('collapsed');
  }

  document.querySelectorAll('.filter-sidebar input').forEach(input => {
    input.addEventListener('change', render);
  });

  applyParams();
  render();
})();
