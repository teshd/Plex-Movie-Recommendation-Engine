const grid = document.getElementById("grid");
const form = document.getElementById("filters");
const statusEl = document.getElementById("status");
const statsEl = document.getElementById("stats");
const refreshBtn = document.getElementById("refresh");
const cardTpl = document.getElementById("card");

async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
  return body;
}

function showStats({ total, watched }) {
  statsEl.textContent = `${total} movies in your library · ${watched} watched`;
}

async function loadGenres() {
  const { genres } = await getJSON("/api/genres");
  const select = form.elements.genre;
  const current = select.value;
  select.length = 1;
  for (const g of genres) select.add(new Option(g, g));
  select.value = current;
}

function render(recs) {
  grid.replaceChildren();
  if (!recs.length) {
    statusEl.textContent = "No recommendations match these filters.";
    return;
  }
  statusEl.textContent = "";
  for (const rec of recs) {
    const node = cardTpl.content.cloneNode(true);
    const img = node.querySelector("img");
    img.src = rec.poster;
    img.alt = `Poster for ${rec.title}`;
    img.onerror = () => { img.removeAttribute("src"); img.alt = ""; };
    node.querySelector("h2").textContent = rec.title;
    const match = rec.score > 0 ? ` · ${Math.round(rec.score * 100)}% match` : "";
    node.querySelector(".meta").textContent =
      [rec.year, rec.genres.slice(0, 3).join(", ")].filter(Boolean).join(" · ") + match;
    node.querySelector(".reason").textContent = rec.reasons.join(" ");
    node.querySelector(".summary").textContent = rec.summary || "No summary available.";
    grid.appendChild(node);
  }
}

async function loadRecommendations() {
  const params = new URLSearchParams();
  for (const [k, v] of new FormData(form)) if (v) params.set(k, v);
  statusEl.textContent = "Finding movies for you…";
  try {
    const { recommendations } = await getJSON(`/api/recommendations?${params}`);
    render(recommendations);
  } catch (err) {
    grid.replaceChildren();
    statusEl.textContent = err.message;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  loadRecommendations();
});

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  statusEl.textContent = "Reloading library from Plex…";
  try {
    showStats(await getJSON("/api/refresh", { method: "POST" }));
    await loadGenres();
    await loadRecommendations();
  } catch (err) {
    statusEl.textContent = err.message;
  } finally {
    refreshBtn.disabled = false;
  }
});

(async () => {
  try {
    showStats(await getJSON("/api/stats"));
    await loadGenres();
  } catch (err) {
    statsEl.textContent = `Could not reach Plex: ${err.message}`;
  }
  loadRecommendations();
})();
