/* map.js — Leaflet map for map.html */
(async function () {
  const TYPE_COLOR = {
    trail:          '#5a7a4a',
    beach:          '#a8c8e8',
    'nature-center':'#8faf8f',
    'splash-pad':   '#64b5f6',
    'aquatic-center':'#1976d2',
    farm:           '#d4a85a',
    fairground:     '#c87878',
    playground:     '#f06292',
  };
  const TYPE_LABEL = {
    trail:'Trail', beach:'Beach/Swimming', 'nature-center':'Nature Center',
    'splash-pad':'Splash Pad', 'aquatic-center':'Aquatic Center',
    farm:'Farm/Seasonal', fairground:'Fair/Festival', playground:'Playground'
  };
  const TYPE_ICON = {
    trail:'🥾', beach:'🏖️', 'nature-center':'🦋',
    'splash-pad':'💦', 'aquatic-center':'🏊',
    farm:'🌽', fairground:'🎪', playground:'🛝'
  };

  // Leaflet map centered on Lake County / Kenosha region
  const map = L.map('map').setView([42.42, -87.97], 10);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18,
  }).addTo(map);

  // Build legend
  const legendEl = document.getElementById('map-legend');
  if (legendEl) {
    legendEl.innerHTML = Object.entries(TYPE_COLOR).map(([type, color]) =>
      `<span class="legend-item">
        <span class="legend-dot" style="background:${color};border:2px solid rgba(0,0,0,.2);"></span>
        ${TYPE_ICON[type]||''} ${TYPE_LABEL[type]||type}
      </span>`
    ).join('');
  }

  function makeIcon(type) {
    const color = TYPE_COLOR[type] || '#8faf8f';
    const emoji = TYPE_ICON[type] || '📍';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="44" viewBox="0 0 36 44">
      <path d="M18 0C8.06 0 0 8.06 0 18c0 13.5 18 26 18 26S36 31.5 36 18C36 8.06 27.94 0 18 0z"
        fill="${color}" stroke="rgba(0,0,0,.25)" stroke-width="1.5"/>
      <text x="18" y="24" text-anchor="middle" font-size="16">${emoji}</text>
    </svg>`;
    return L.divIcon({
      html: svg,
      iconSize: [36, 44],
      iconAnchor: [18, 44],
      popupAnchor: [0, -44],
      className: '',
    });
  }

  let allMarkers = [];
  let activeType = 'all';

  let allPlaces = [];
  try {
    const res  = await fetch('data/places.json');
    const data = await res.json();
    allPlaces  = (data.places || []).filter(p => p.lat && p.lng);
  } catch {
    document.getElementById('map').innerHTML =
      '<div class="empty-state"><div class="empty-icon">🌧️</div><h3>Couldn\'t load map data</h3></div>';
    return;
  }

  function buildPopup(p) {
    const costBadge = p.cost === 'free'
      ? '<span class="badge badge-free" style="font-size:.7rem;">FREE</span>'
      : '<span class="badge badge-paid" style="font-size:.7rem;">Paid</span>';
    const tags = (p.tags||[]).slice(0,4).map(t =>
      `<span class="place-tag" style="font-size:.7rem;">${t.replace(/-/g,' ')}</span>`).join(' ');
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.address||p.name)}`;
    return `<div style="max-width:220px;">
      <div class="popup-name">${p.name}</div>
      <div class="popup-meta">${TYPE_ICON[p.type]||''} ${TYPE_LABEL[p.type]||p.type} &bull; ${p.town}</div>
      <div style="margin-bottom:.4rem;">${costBadge} ${p.cost_detail ? `<span style="font-size:.75rem;color:var(--text-lt);">${p.cost_detail}</span>` : ''}</div>
      <p style="font-size:.82rem;color:var(--text-lt);margin-bottom:.4rem;">${p.description.slice(0,120)}${p.description.length>120?'…':''}</p>
      <div style="display:flex;flex-wrap:wrap;gap:.2rem;margin-bottom:.4rem;">${tags}</div>
      <div style="display:flex;gap:.75rem;">
        ${p.url ? `<a class="popup-link" href="${p.url}" target="_blank" rel="noopener">Website →</a>` : ''}
        <a class="popup-link" href="${mapsUrl}" target="_blank" rel="noopener">Directions →</a>
      </div>
    </div>`;
  }

  function renderMarkers() {
    allMarkers.forEach(({marker}) => map.removeLayer(marker));
    allMarkers = [];

    const visible = activeType === 'all'
      ? allPlaces
      : allPlaces.filter(p => p.type === activeType);

    visible.forEach(p => {
      const marker = L.marker([p.lat, p.lng], { icon: makeIcon(p.type) })
        .addTo(map)
        .bindPopup(buildPopup(p), { maxWidth: 240 });
      allMarkers.push({ marker, place: p });
    });
  }

  // Type filter buttons
  document.querySelectorAll('#type-filters .map-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#type-filters .map-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeType = btn.dataset.type;
      renderMarkers();
    });
  });

  // Check URL param for type
  const urlType = new URLSearchParams(location.search).get('type');
  if (urlType) {
    const btn = document.querySelector(`#type-filters .map-type-btn[data-type="${urlType}"]`);
    if (btn) {
      document.querySelectorAll('#type-filters .map-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeType = urlType;
    }
  }

  renderMarkers();
})();
