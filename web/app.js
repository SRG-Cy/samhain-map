// Samhain Map: tales and verified places come from web/data, written by scripts/verify.py.
const DATA_VERSION = 4;
const BOOKS = {
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

const state = { tales: [], byId: new Map(), places: null, filter: null, layer: null };
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
const visible = (t) => !state.filter || t.beings.includes(state.filter);

function taleCard(t) {
  return `<button class="tale-card" data-tale="${t.id}">
    <div class="t">${esc(t.title)}</div>
    <div class="s">${esc(t.summary || "")}</div>
    <div class="tags">${beingTags(t)}</div>
  </button>`;
}

function bindCards() {
  panel.querySelectorAll("[data-tale]").forEach((el) => el.addEventListener("click", () => showTale(+el.dataset.tale)));
  panel.querySelectorAll("[data-place]").forEach((el) => el.addEventListener("click", () => focusPlace(el.dataset.place)));
  panel.querySelector(".back")?.addEventListener("click", showHome);
}

function showHome() {
  const all = state.tales.flatMap((t) => t.places);
  const ok = all.filter(isPinned).length;
  const thrown = all.filter((p) => !isPinned(p) && !p.status?.startsWith("listed")).length;
  panel.innerHTML = `
    <h2>Click a place on the map</h2>
    <p class="lede">In the 1890s Jeremiah Curtin sat by firesides in Kerry and wrote down the stories people told him: ghosts on the road to Sneem, fairy cows, the dead coming back. In 1914 a Tipperary rector and a police district inspector printed ghost accounts sent in from all over the country: haunted rectories, banshees, poltergeists. Each glowing place is somewhere a story names.</p>
    <div class="stat-row">
      <div class="stat"><b>${state.tales.length}</b><span>stories</span></div>
      <div class="stat"><b>${ok}</b><span>place names checked and pinned</span></div>
      <div class="stat"><b>${thrown}</b><span>place names the checker would not pin</span></div>
    </div>
    <h3>All stories</h3>
    ${state.tales.filter(visible).map(taleCard).join("")}`;
  bindCards();
}

function showPlace(props) {
  const tales = props.tales.map((id) => state.byId.get(id)).filter(visible);
  panel.innerHTML = `
    <button class="back">← All tales</button>
    <h2>${esc(props.name)}</h2>
    <p class="eyebrow">County ${esc(props.county)} · ${tales.length} tale${tales.length === 1 ? "" : "s"}</p>
    ${tales.map(taleCard).join("") || "<p class='lede'>No tales here match the filter.</p>"}`;
  bindCards();
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

function drawPlaces() {
  if (state.layer) state.layer.remove();
  const glow = { color: "#f2a33a", weight: 1.5, fillColor: "#f2a33a", fillOpacity: 0.35 };
  state.layer = L.geoJSON(state.places, {
    filter: (f) => f.properties.tales.some((id) => visible(state.byId.get(id))),
    style: () => glow,
    pointToLayer: (f, latlng) => L.circleMarker(latlng, { ...glow, radius: 7, fillOpacity: 0.7 }),
    onEachFeature: (f, l) => {
      l.bindTooltip(`${f.properties.name} · ${f.properties.tales.length} tale${f.properties.tales.length === 1 ? "" : "s"}`, { direction: "top" });
      l.on("click", () => showPlace(f.properties));
    },
  }).addTo(map);
  // townland polygons are tiny at county zoom: add a dot at each so they can be found
  state.places.features.forEach((f) => {
    if (f.geometry.type !== "Point" && f.properties.tales.some((id) => visible(state.byId.get(id)))) {
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
  el.innerHTML = [`<button class="chip" data-b="" aria-pressed="${!state.filter}">All</button>`]
    .concat(keys.map((b) => `<button class="chip" data-b="${b}" aria-pressed="${state.filter === b}">${esc(BEING_LABEL[b] || b)}<span class="n">${counts[b]}</span></button>`))
    .join("");
  el.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => {
    state.filter = c.dataset.b || null;
    drawFilters(); drawPlaces(); showHome();
  }));
}

async function init() {
  const [counties, tales, places] = await Promise.all(
    // data/* is cached for an hour (render.yaml): bump DATA_VERSION whenever verify.py output changes
    ["data/counties.geojson", "data/tales.json", "data/places.geojson"].map((u) => fetch(`${u}?v=${DATA_VERSION}`).then((r) => r.json())));
  L.geoJSON(counties, {
    style: { color: "#6b5a4b", weight: 1, fillColor: "#2a221c", fillOpacity: 0.25 },
    onEachFeature: (f, l) => l.bindTooltip(`County ${f.properties.county}`, { sticky: true }),
    interactive: true,
  }).addTo(map);
  state.tales = tales;
  tales.forEach((t) => state.byId.set(t.id, t));
  state.places = places;
  drawFilters();
  drawPlaces();
  showHome();
}

init().catch((e) => { panel.innerHTML = `<p class="lede">Could not load the map data: ${esc(e.message)}</p>`; });
