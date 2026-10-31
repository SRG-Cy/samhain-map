// Samhain Map: tales and verified places come from web/data, written by scripts/verify.py.
const DATA_VERSION = 5;
const BOOKS = {
  croker1825: {
    source: "Thomas Crofton Croker, Fairy Legends and Traditions of the South of Ireland (1825)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/39752" target="_blank" rel="noopener">Read the 1825 book on Project Gutenberg</a>`,
  },
  mcanally1888: {
    source: "D. R. McAnally, Irish Wonders (1888)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/19486" target="_blank" rel="noopener">Read the 1888 book on Project Gutenberg</a>`,
  },
  curtin1895: {
    source: "Jeremiah Curtin, Tales of the Fairies and of the Ghost World (1895)",
    link: (t) => t.pages && `<a href="https://archive.org/details/cu31924029910563/page/${t.pages[0]}/mode/1up" target="_blank" rel="noopener">Read the 1895 page scan (p. ${t.pages[0]})</a>`,
  },
  seymour1914: {
    source: "Seymour & Neligan, True Irish Ghost Stories (1914)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/14099" target="_blank" rel="noopener">Read the 1914 book on Project Gutenberg</a>`,
  },
};
const BEING_LABEL = {
  ghost: "Ghost", fairy: "Fairy", banshee: "Banshee", pooka: "Púca",
  mermaid_or_seal_woman: "Seal woman", devil: "Devil", dead_returning: "The dead return",
  changeling: "Changeling", fairy_doctor: "Fairy doctor", saint: "Saint", other: "Other",
  poltergeist: "Poltergeist", death_warning: "Death warning",
};

const state = { tales: [], byId: new Map(), places: null, sites: [], filter: null, layer: null, siteLayer: null };
const SITES = "sites"; // the "Haunted sites" chip: only famous haunted sites and their stories
const panel = document.getElementById("panel-body");

const map = L.map("map", { zoomControl: true, minZoom: 6 }).setView([53.4, -8.0], 7);
// standard OSM tiles, darkened in CSS (.dark-tiles) to suit the candlelit theme
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 16,
  className: "dark-tiles",
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const isPinned = (p) => p.status?.startsWith("pinned");

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const beingTags = (t) => t.beings.map((b) => `<span class="tag">${esc(BEING_LABEL[b] || b)}</span>`).join("");
const isSiteTale = (t) => state.sites.some((s) => s.tale === t.id);
const visible = (t) => !state.filter || (state.filter === SITES ? isSiteTale(t) : t.beings.includes(state.filter));
const GHOST = L.divIcon({
  className: "ghost-pin",
  html: `<svg viewBox="0 0 24 28" width="26" height="30" aria-hidden="true"><path d="M12 1C6.5 1 3 5.2 3 10.5V26l3-2.5 3 2.5 3-2.5 3 2.5 3-2.5 3 2.5V10.5C21 5.2 17.5 1 12 1z"/><circle cx="9" cy="11" r="1.6"/><circle cx="15" cy="11" r="1.6"/></svg>`,
  iconSize: [26, 30], iconAnchor: [13, 28], tooltipAnchor: [0, -26],
});

function taleCard(t) {
  return `<button class="tale-card" data-tale="${t.id}">
    <div class="t">${esc(t.title)}</div>
    <div class="s">${esc(t.summary || "")}</div>
    <div class="tags">${beingTags(t)}</div>
  </button>`;
}

// on a phone the panel sits below the map: bring it into view when a place or story opens
const narrow = window.matchMedia("(max-width: 860px)");
const reveal = () => { if (narrow.matches) document.getElementById("panel").scrollIntoView({ behavior: "smooth" }); };

function bindCards() {
  panel.querySelectorAll("[data-tale]").forEach((el) => el.addEventListener("click", () => showTale(+el.dataset.tale)));
  panel.querySelectorAll("[data-place]").forEach((el) => el.addEventListener("click", () => focusPlace(el.dataset.place)));
  panel.querySelectorAll("[data-site]").forEach((el) => el.addEventListener("click", () => showSite(+el.dataset.site)));
  panel.querySelector(".back")?.addEventListener("click", showHome);
}

function showHome() {
  const all = state.tales.flatMap((t) => t.places);
  const ok = all.filter(isPinned).length;
  const thrown = all.filter((p) => !isPinned(p) && !p.status?.startsWith("listed")).length;
  panel.innerHTML = `
    <h2>Click a place on the map</h2>
    <p class="lede">In the 1890s Jeremiah Curtin sat by firesides in Kerry and wrote down the stories people told him: ghosts on the road to Sneem, fairy cows, the dead coming back. In 1914 a Tipperary rector and a police district inspector printed ghost accounts sent in from all over the country: haunted rectories, banshees, poltergeists. Each glowing place is somewhere a story names; each pale ghost is a famous haunted site that one of these old books tells.</p>
    <div class="stat-row">
      <div class="stat"><b>${state.tales.length}</b><span>stories</span></div>
      <div class="stat"><b>${ok}</b><span>place names checked and pinned</span></div>
      <div class="stat"><b>${thrown}</b><span>place names the checker would not pin</span></div>
    </div>
    <h3>Famous haunted sites</h3>
    <div class="site-list">${state.sites.map((s, i) => `<button class="site-btn" data-site="${i}">${esc(s.name)}<span>Co. ${esc(s.county)}</span></button>`).join("")}</div>
    <h3>${state.filter === SITES ? "Stories of the haunted sites" : "All stories"}</h3>
    ${state.tales.filter(visible).map(taleCard).join("")}`;
  bindCards();
}

function showSite(i) {
  const s = state.sites[i];
  const t = state.byId.get(s.tale);
  panel.innerHTML = `
    <button class="back">← All stories</button>
    <h2>${esc(s.name)}</h2>
    <p class="eyebrow">Famous haunted site · County ${esc(s.county)}</p>
    <blockquote>“${esc(s.quote)}”</blockquote>
    <p class="eyebrow">From ${esc(BOOKS[t.book].source)}</p>
    ${s.note ? `<p>${esc(s.note)} <a href="${esc(s.note_source)}" target="_blank" rel="noopener">Source</a></p>` : ""}
    <h3>The story</h3>
    ${taleCard(t)}
    <p class="eyebrow" style="margin-top:16px">Only sites a public-domain book tells are here; code checked that this quote is word for word in the story. Location: ${esc(s.located)}.</p>`;
  bindCards();
  reveal();
  map.setView([s.lat, s.lon], Math.max(map.getZoom(), 10));
}

function showPlace(props) {
  const tales = props.tales.map((id) => state.byId.get(id)).filter(visible);
  panel.innerHTML = `
    <button class="back">← All tales</button>
    <h2>${esc(props.name)}</h2>
    <p class="eyebrow">County ${esc(props.county)} · ${tales.length} tale${tales.length === 1 ? "" : "s"}</p>
    ${tales.map(taleCard).join("") || "<p class='lede'>No tales here match the filter.</p>"}`;
  bindCards();
  reveal();
}

function showTale(id) {
  const t = state.byId.get(id);
  const book = BOOKS[t.book];
  const pageLink = book.link(t) || "";
  const where = t.chapter ? `${esc(book.source)}, chapter “${esc(t.chapter)}”` : esc(book.source);
  const rows = t.places.map((p) => {
    const label = isPinned(p)
      ? `<button data-place="${esc(p.place_id)}">${esc(p.matched_name)}</button>, Co. ${esc(p.county)}<span class="st ok">✓ ${esc(p.status)}</span>`
      : `${esc(p.name)}<span class="st ${p.status?.startsWith("listed") ? "" : "bad"}">${p.status?.startsWith("listed") ? "·" : "✗"} ${esc(p.status)}</span>`;
    const note = p.note ? `<span class="q">${esc(p.note)}</span>` : "";
    return `<li>${label}<span class="q">“${esc(p.quote)}”</span>${note}</li>`;
  }).join("");
  panel.innerHTML = `
    <button class="back">← All tales</button>
    <h2>${esc(t.title)}</h2>
    <p class="eyebrow">${where}<br>${t.teller ? `Told by ${esc(t.teller)} · ` : ""}${pageLink}</p>
    <div class="tags">${beingTags(t)}</div>
    <p>${esc(t.summary || "")}</p>
    ${t.beings_quote ? `<blockquote>“${esc(t.beings_quote)}”</blockquote>` : ""}
    <h3>Places in this tale</h3>
    <ul class="place-list">${rows || "<li>None named.</li>"}</ul>
    <details><summary>Read the whole story</summary><div class="tale-text">${esc(t.text)}</div></details>
    <p class="eyebrow" style="margin-top:16px">Summary and places read by ${esc(t.model)}${t.title_by === "gemma" ? "; the book gives this story no title, so Gemma named it, and code cut the story at the paragraph Gemma said it starts" : ""}. Only places whose quote is in the story and whose name is a real place in Ireland are pinned.</p>`;
  bindCards();
  reveal();
  const pins = t.places.filter((p) => p.lat).map((p) => [p.lat, p.lon]);
  if (pins.length) map.fitBounds(pins, { padding: [60, 60], maxZoom: 11 });
}

function focusPlace(id) {
  state.layer.eachLayer((l) => {
    if (l.feature.properties.id === id) {
      const b = l.getBounds ? l.getBounds() : L.latLngBounds([l.getLatLng(), l.getLatLng()]);
      map.fitBounds(b, { maxZoom: 13 });
      showPlace(l.feature.properties);
    }
  });
}

function drawSites() {
  if (state.siteLayer) state.siteLayer.remove();
  state.siteLayer = L.layerGroup(state.sites.map((s, i) => L.marker([s.lat, s.lon], { icon: GHOST, zIndexOffset: 1000, title: s.name })
    .bindTooltip(`${s.name} · famous haunted site`, { direction: "top" })
    .on("click", () => showSite(i)))).addTo(map);
}

function drawPlaces() {
  if (state.layer) state.layer.remove();
  const glow = { color: "#f2a33a", weight: 1.5, fillColor: "#f2a33a", fillOpacity: 0.35 };
  state.layer = L.geoJSON(state.places, {
    filter: (f) => state.filter !== SITES && f.properties.tales.some((id) => visible(state.byId.get(id))),
    style: () => glow,
    pointToLayer: (f, latlng) => L.circleMarker(latlng, { ...glow, radius: 7, fillOpacity: 0.7 }),
    onEachFeature: (f, l) => {
      l.bindTooltip(`${f.properties.name} · ${f.properties.tales.length} tale${f.properties.tales.length === 1 ? "" : "s"}`, { direction: "top" });
      l.on("click", () => showPlace(f.properties));
    },
  }).addTo(map);
  // townland polygons are tiny at county zoom: add a dot at each so they can be found
  state.places.features.forEach((f) => {
    if (f.geometry.type !== "Point" && state.filter !== SITES && f.properties.tales.some((id) => visible(state.byId.get(id)))) {
      L.circleMarker([f.properties.lat, f.properties.lon], { ...glow, radius: 5, fillOpacity: 0.7 })
        .bindTooltip(`${f.properties.name} · ${f.properties.tales.length} tale${f.properties.tales.length === 1 ? "" : "s"}`, { direction: "top" })
        .on("click", () => showPlace(f.properties))
        .addTo(state.layer);
    }
  });
}

function drawFilters() {
  const counts = {};
  state.tales.forEach((t) => t.beings.forEach((b) => (counts[b] = (counts[b] || 0) + 1)));
  const keys = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const el = document.getElementById("filters");
  el.innerHTML = [`<button class="chip" data-b="" aria-pressed="${!state.filter}">All</button>`,
    `<button class="chip site-chip" data-b="${SITES}" aria-pressed="${state.filter === SITES}">Haunted sites<span class="n">${state.sites.length}</span></button>`]
    .concat(keys.map((b) => `<button class="chip" data-b="${b}" aria-pressed="${state.filter === b}">${esc(BEING_LABEL[b] || b)}<span class="n">${counts[b]}</span></button>`))
    .join("");
  el.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => {
    state.filter = c.dataset.b || null;
    drawFilters(); drawPlaces(); showHome();
  }));
}

async function init() {
  const [counties, tales, places, sites] = await Promise.all(
    // data/* is cached for an hour (render.yaml): bump DATA_VERSION whenever verify.py output changes
    ["data/counties.geojson", "data/tales.json", "data/places.geojson", "data/sites.json"].map((u) => fetch(`${u}?v=${DATA_VERSION}`).then((r) => r.json())));
  L.geoJSON(counties, {
    style: { color: "#6b5a4b", weight: 1, fillColor: "#2a221c", fillOpacity: 0.25 },
    onEachFeature: (f, l) => l.bindTooltip(`County ${f.properties.county}`, { sticky: true }),
    interactive: true,
  }).addTo(map);
  state.tales = tales;
  tales.forEach((t) => state.byId.set(t.id, t));
  state.places = places;
  state.sites = sites;
  drawFilters();
  drawPlaces();
  drawSites();
  showHome();
}

init().catch((e) => { panel.innerHTML = `<p class="lede">Could not load the map data: ${esc(e.message)}</p>`; });
