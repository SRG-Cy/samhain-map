// Samhain Map: tales and verified places come from web/data, written by scripts/verify.py and scripts/sites.py.
const DATA_VERSION = 6;
const BOOKS = {
  croker1825: {
    source: "Thomas Crofton Croker, Fairy Legends and Traditions of the South of Ireland (1825)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/39752" target="_blank" rel="noopener">the 1825 book on Project Gutenberg</a>`,
  },
  mcanally1888: {
    source: "D. R. McAnally, Irish Wonders (1888)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/19486" target="_blank" rel="noopener">the 1888 book on Project Gutenberg</a>`,
  },
  curtin1895: {
    source: "Jeremiah Curtin, Tales of the Fairies and of the Ghost World (1895)",
    link: (t) => t.pages && `<a href="https://archive.org/details/cu31924029910563/page/${t.pages[0]}/mode/1up" target="_blank" rel="noopener">the scanned 1895 page ${t.pages[0]}</a>`,
  },
  seymour1914: {
    source: "Seymour and Neligan, True Irish Ghost Stories (1914)",
    link: () => `<a href="https://www.gutenberg.org/ebooks/14099" target="_blank" rel="noopener">the 1914 book on Project Gutenberg</a>`,
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
const FIRE = "#e8913a";

const map = L.map("map", { zoomControl: true, minZoom: 6 }).setView([53.4, -8.0], 7);
// standard OSM tiles, turned to a moonlit night in CSS (.dark-tiles)
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 16,
  className: "dark-tiles",
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const isPinned = (p) => p.status?.startsWith("pinned");
const beingsLine = (t) => t.beings.map((b) => BEING_LABEL[b] || b).join(", ");
const isSiteTale = (t) => state.sites.some((s) => s.tale === t.id);
const visible = (t) => !state.filter || (state.filter === SITES ? isSiteTale(t) : t.beings.includes(state.filter));
const GHOST_PATH = "M12 1C6.5 1 3 5.2 3 10.5V26l3-2.5 3 2.5 3-2.5 3 2.5 3-2.5 3 2.5V10.5C21 5.2 17.5 1 12 1z";
const GHOST = L.divIcon({
  className: "ghost-pin",
  html: `<svg viewBox="0 0 24 28" width="26" height="30" aria-hidden="true"><path d="${GHOST_PATH}"/><circle cx="9" cy="11" r="1.6"/><circle cx="15" cy="11" r="1.6"/></svg>`,
  iconSize: [26, 30], iconAnchor: [13, 28], tooltipAnchor: [0, -26],
});

// on a phone the leaf sits below the map: bring it into view when a place or story opens
const narrow = window.matchMedia("(max-width: 860px)");
const reveal = () => {
  const leaf = document.getElementById("panel");
  leaf.scrollTop = 0; // desktop: a new view starts at its top, not where the list was scrolled to
  if (narrow.matches) leaf.scrollIntoView({ behavior: "smooth" });
};
const back = `<button class="back">Back to all stories</button>`;
// Commons serves fixed thumbnail widths; the list uses the small one
const thumb = (src) => src.replace(/\/\d+px-([^/]+)$/, "/250px-$1");

function photo(s) {
  const im = s.image;
  if (!im) return "";
  const licence = im.licence_url ? `<a href="${esc(im.licence_url)}" target="_blank" rel="noopener">${esc(im.licence)}</a>` : esc(im.licence);
  return `<figure class="photo">
    <img src="${esc(im.src)}" alt="${esc(s.name)}" loading="lazy" decoding="async">
    <figcaption>Image: ${esc(im.author)}, ${licence}, via <a href="${esc(im.page)}" target="_blank" rel="noopener">Wikimedia Commons</a>.</figcaption>
  </figure>`;
}

function storyRow(t) {
  return `<li><button class="story" data-tale="${t.id}">
    <div class="t">${esc(t.title)}</div>
    <div class="s">${esc(t.summary || "")}</div>
    ${t.beings.length ? `<div class="b">${esc(beingsLine(t))}</div>` : ""}
  </button></li>`;
}

function bind() {
  panel.querySelectorAll("[data-tale]").forEach((el) => el.addEventListener("click", () => showTale(+el.dataset.tale)));
  panel.querySelectorAll("[data-place]").forEach((el) => el.addEventListener("click", () => focusPlace(el.dataset.place)));
  panel.querySelectorAll("[data-site]").forEach((el) => el.addEventListener("click", () => showSite(+el.dataset.site)));
  panel.querySelectorAll("[data-b]").forEach((c) => c.addEventListener("click", () => {
    state.filter = c.dataset.b || null;
    drawPlaces();
    showHome();
  }));
  panel.querySelector(".back")?.addEventListener("click", () => { showHome(); panel.parentElement.scrollTop = 0; });
}

function filters() {
  const counts = {};
  state.tales.forEach((t) => t.beings.forEach((b) => (counts[b] = (counts[b] || 0) + 1)));
  const keys = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  return `<div class="filters" role="group" aria-label="Show stories with">
    <button class="chip" data-b="" aria-pressed="${!state.filter}">All</button>
    <button class="chip moon" data-b="${SITES}" aria-pressed="${state.filter === SITES}">Haunted sites<span class="n">${state.sites.length}</span></button>
    ${keys.map((b) => `<button class="chip" data-b="${b}" aria-pressed="${state.filter === b}">${esc(BEING_LABEL[b] || b)}<span class="n">${counts[b]}</span></button>`).join("")}
  </div>`;
}

function showHome() {
  const all = state.tales.flatMap((t) => t.places);
  const pinned = all.filter(isPinned).length;
  const refused = all.filter((p) => !isPinned(p) && !p.status?.startsWith("listed")).length;
  const shown = state.tales.filter(visible);
  panel.innerHTML = `
    <h2>Where the dead walk</h2>
    <p class="intro">On Samhain night the wall between this world and the other wears thin. These are the stories people told about it, from four old books, each put back on the road, house or lake where it happened.</p>
    <p class="counts">Orange lights are places a story names. White ghosts are famous haunted sites. <b>${state.tales.length}</b> stories; <b>${pinned}</b> place names checked against real townlands and pinned; <b>${refused}</b> the checker refused.</p>
    <h3>Famous haunted sites</h3>
    <ul class="sites">${state.sites.map((s, i) => `<li><button class="site" data-site="${i}">${s.image
      ? `<img src="${esc(thumb(s.image.src))}" alt="" loading="lazy" decoding="async">`
      : `<span class="noimg"><svg viewBox="0 0 24 28" aria-hidden="true"><path d="${GHOST_PATH}"/></svg></span>`}<span><b>${esc(s.name)}</b><br><span>County ${esc(s.county)}</span></span></button></li>`).join("")}</ul>
    <h3>Stories</h3>
    ${filters()}
    <ul class="stories">${shown.map(storyRow).join("") || `<li class="empty">No stories match.</li>`}</ul>
    <details class="sources"><summary>Sources and licences</summary>
      <p>Jeremiah Curtin, <em>Tales of the Fairies and of the Ghost World</em> (1895), public domain, scan by Cornell University Library via <a href="https://archive.org/details/cu31924029910563">archive.org</a>. St John D. Seymour and Harry L. Neligan, <em>True Irish Ghost Stories</em> (1914), T. Crofton Croker (1825) and D. R. McAnally (1888), public domain, via <a href="https://www.gutenberg.org/">Project Gutenberg</a>.</p>
      <p>Townlands © Tailte Éireann, CC BY 4.0. Northern Ireland townlands and counties: OSNI Open Data, OGL v3. Places: <a href="https://www.geonames.org/">GeoNames</a>, CC BY 4.0. Map © OpenStreetMap contributors.</p>
      <p>Images of the haunted sites from Wikimedia Commons, each credited on its site page with its licence (CC BY-SA).</p>
      <p>Summaries and place reading by Gemma, an open-weight model. Every pin is checked by code. <a href="https://github.com/SRG-Cy/samhain-map">Code on GitHub</a>.</p>
    </details>`;
  bind();
}

function showSite(i) {
  const s = state.sites[i];
  const t = state.byId.get(s.tale);
  panel.innerHTML = `
    ${back}
    <h2>${esc(s.name)}</h2>
    <p class="meta">A famous haunted site in County ${esc(s.county)}</p>
    ${photo(s)}
    <blockquote class="moon">${esc(s.quote)}</blockquote>
    <p class="meta">From ${esc(BOOKS[t.book].source)}.</p>
    ${s.note ? `<p class="summary">${esc(s.note)} <a href="${esc(s.note_source)}" target="_blank" rel="noopener">Source</a></p>` : ""}
    <h3>The story</h3>
    <ul class="stories">${storyRow(t)}</ul>
    <p class="fine">Only sites an old public-domain book tells are on the map, and code checked this quote is in the story word for word. Location: ${esc(s.located)}.</p>`;
  bind();
  reveal();
  map.setView([s.lat, s.lon], Math.max(map.getZoom(), 10));
}

function showPlace(props) {
  const tales = props.tales.map((id) => state.byId.get(id)).filter(visible);
  panel.innerHTML = `
    ${back}
    <h2>${esc(props.name)}</h2>
    <p class="meta">${plural(tales.length, "story")} in County ${esc(props.county)}</p>
    <ul class="stories">${tales.map(storyRow).join("") || `<li class="empty">No stories here match the filter.</li>`}</ul>`;
  bind();
  reveal();
}

function evidence(p) {
  const why = p.status.replace(/^(listed|refused|not pinned): /, "");
  const kind = isPinned(p) ? "yes" : p.status.startsWith("listed") ? "info" : "no";
  const name = isPinned(p)
    ? `<button data-place="${esc(p.place_id)}">${esc(p.matched_name)}</button>, County ${esc(p.county)}`
    : esc(p.name);
  const reason = isPinned(p)
    ? [p.status === "pinned" ? "" : why, p.note].filter(Boolean).join("; ")
    : (p.status.startsWith("refused") ? "Refused: " : "") + why;
  return `<li class="${kind}">${name}${reason ? `<span class="why">${esc(reason.charAt(0).toUpperCase() + reason.slice(1))}</span>` : ""}<q>${esc(p.quote)}</q></li>`;
}

function showTale(id) {
  const t = state.byId.get(id);
  const book = BOOKS[t.book];
  const paras = t.text.split(/\n\s*\n/).map((p) => `<p>${esc(p.replace(/\s*\n\s*/g, " "))}</p>`).join("");
  const long = t.text.length > 1400;
  panel.innerHTML = `
    ${back}
    <h2>${esc(t.title)}</h2>
    <p class="meta">From ${esc(book.source)}${t.chapter ? `, in the chapter “${esc(t.chapter)}”` : ""}.${t.teller ? ` Told by ${esc(t.teller)}.` : ""}</p>
    ${t.beings.length ? `<p class="beings">${esc(beingsLine(t))}</p>` : ""}
    <p class="summary">${esc(t.summary || "")}</p>
    ${t.beings_quote ? `<blockquote>${esc(t.beings_quote)}</blockquote>` : ""}
    <div class="reader">
      <div class="page${long ? " folded" : ""}">${paras}</div>
      ${long ? `<button class="more">Read the whole story</button>` : ""}
      <p class="meta">Read it in ${book.link(t) || "the book"}.</p>
    </div>
    <h3>Where it happened</h3>
    <ul class="evidence">${t.places.map(evidence).join("") || `<li class="info">The story names no place.</li>`}</ul>
    <p class="fine">Summary and places read by ${esc(t.model)}${t.title_by === "gemma" ? ". The book gives this story no title, so Gemma named it, and code cut the story where Gemma said it starts" : ""}. A place is pinned only if its quote is in the story word for word and its name is a real place in Ireland.</p>`;
  bind();
  panel.querySelector(".more")?.addEventListener("click", (e) => {
    panel.querySelector(".page").classList.remove("folded");
    e.target.remove();
  });
  reveal();
  const pins = t.places.filter((p) => p.lat).map((p) => [p.lat, p.lon]);
  if (pins.length) map.fitBounds(pins, { padding: [60, 60], maxZoom: 11 });
}

function focusPlace(id) {
  state.layer.eachLayer((l) => {
    if (l.feature?.properties.id === id) {
      const b = l.getBounds ? l.getBounds() : L.latLngBounds([l.getLatLng(), l.getLatLng()]);
      map.fitBounds(b, { maxZoom: 13 });
      showPlace(l.feature.properties);
    }
  });
}

function drawSites() {
  if (state.siteLayer) state.siteLayer.remove();
  state.siteLayer = L.layerGroup(state.sites.map((s, i) => L.marker([s.lat, s.lon], { icon: GHOST, zIndexOffset: 1000, title: s.name, alt: s.name })
    .bindTooltip(`${s.name}, a famous haunted site`, { direction: "top" })
    .on("click", () => showSite(i)))).addTo(map);
}

function drawPlaces() {
  if (state.layer) state.layer.remove();
  const light = { color: FIRE, weight: 1.5, fillColor: FIRE, fillOpacity: 0.3 };
  const tip = (p) => `${p.name}: ${plural(p.tales.length, "story")}`;
  const shown = (f) => state.filter !== SITES && f.properties.tales.some((id) => visible(state.byId.get(id)));
  state.layer = L.geoJSON(state.places, {
    filter: shown,
    style: () => light,
    pointToLayer: (f, latlng) => L.circleMarker(latlng, { ...light, radius: 6, fillOpacity: 0.75 }),
    onEachFeature: (f, l) => {
      l.bindTooltip(tip(f.properties), { direction: "top" });
      l.on("click", () => showPlace(f.properties));
    },
  }).addTo(map);
  // townland polygons are tiny at county zoom: add a light at each so they can be found
  state.places.features.forEach((f) => {
    if (f.geometry.type !== "Point" && shown(f)) {
      L.circleMarker([f.properties.lat, f.properties.lon], { ...light, radius: 5, fillOpacity: 0.75 })
        .bindTooltip(tip(f.properties), { direction: "top" })
        .on("click", () => showPlace(f.properties))
        .addTo(state.layer);
    }
  });
}

async function init() {
  const [counties, tales, places, sites] = await Promise.all(
    // data/* is cached for an hour (render.yaml): bump DATA_VERSION whenever verify.py output changes
    ["data/counties.geojson", "data/tales.json", "data/places.geojson", "data/sites.json"].map((u) => fetch(`${u}?v=${DATA_VERSION}`).then((r) => r.json())));
  L.geoJSON(counties, {
    style: { color: "#4a5e78", weight: 1, fillColor: "#121a24", fillOpacity: 0.15 },
    onEachFeature: (f, l) => l.bindTooltip(`County ${f.properties.county}`, { sticky: true }),
  }).addTo(map);
  state.tales = tales;
  tales.forEach((t) => state.byId.set(t.id, t));
  state.places = places;
  state.sites = sites;
  drawPlaces();
  drawSites();
  showHome();
}

init().catch((e) => { panel.innerHTML = `<p class="empty">The map data didn't load (${esc(e.message)}). Reload the page to try again.</p>`; });
