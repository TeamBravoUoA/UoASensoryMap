/* UoA Sensory Map - full-page Places browser.
   Fetches the lightweight /api/locations/ payload and renders every place as a
   card with a thumbnail, description and space-type badges. */

(function () {
  "use strict";

  const ICON_BASE = "/static/sensemap/icons/";

  // Space-type metadata (kept in sync with app.js SPACE_TYPE_META).
  const SPACE_TYPE_META = {
    study: { label: "Study Space", iconUrl: "study.svg", color: "#1565c0" },
    quiet: { label: "Quiet Space", iconUrl: "quiet.svg", color: "#5e35b1" },
    social: { label: "Social Space", iconUrl: "social.svg", color: "#f9a825" },
    food_drink: { label: "Cafeteria", iconUrl: "food_drink.svg", color: "#ef6c00" },
    facility: { label: "Facility", iconUrl: "facility.svg", color: "#00838f" },
    sensory: { label: "Sensory Room", iconUrl: "sensory.svg", color: "#d81b60" },
    other: { label: "Other", iconUrl: "other.svg", color: "#2e7d32" },
  };

  // --- State ---------------------------------------------------------------
  let allLocations = [];
  let metaData = null;
  const activeFacilities = new Set();

  // --- DOM -----------------------------------------------------------------
  const el = (id) => document.getElementById(id);
  const listEl = el("places-list");
  const countEl = el("showing-count");

  // --- Helpers -------------------------------------------------------------
  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  function searchScore(loc, needle) {
    const name = (loc.name || "").toLowerCase();
    const aka = ((loc.also_known_as || "")).toLowerCase();
    const desc = ((loc.description || "")).toLowerCase();
    const spaceTypes = (loc.space_types || []).join(" ").toLowerCase();

    if (name === needle) return 100;
    if (name.startsWith(needle + " ") || name.startsWith(needle)) return 80;
    if (name.includes(" " + needle)) return 60;
    if (name.includes(needle)) return 40;
    if (aka.includes(needle)) return 30;
    if (spaceTypes.includes(needle)) return 20;
    if (desc.includes(needle)) return 10;
    return 0;
  }

  function iconImg(meta, alt) {
    return (
      '<img src="' + ICON_BASE + meta.iconUrl +
      '" alt="' + escapeHtml(alt || meta.label || "") +
      '" class="icon-svg" loading="lazy">'
    );
  }

  function asPlace(space) {
    const loc = space.location || {};
    return {
      id: space.id,
      name: space.name,
      description: space.description,
      thumbnail: space.thumbnail_image,
      space_types: [space.space_type],
      slug: loc.slug,
      category: loc.category,
      category_display: loc.category_display,
      campus: loc.campus,
      campus_display: loc.campus_display,
      has_quiet_zone: space.is_quiet_zone,
      has_neurodivergent_safe: space.is_safe_space_neurodivergent_students,
      wayfinding: space.wayfinding,
      id_access_needed: loc.id_access_needed,
      facilities_available: (space.facilities || [])
        .filter((f) => f.status)
        .map((f) => f.name),
    };
  }

  function thumbHtml(loc) {
    if (loc.thumbnail) {
      return '<img src="' + loc.thumbnail + '" alt="" loading="lazy" />';
    }
    // Placeholder block tinted by the first space type (or grey).
    const m = SPACE_TYPE_META[(loc.space_types || [])[0]];
    const color = m ? m.color : "#1f3b57";
    return (
      '<div class="thumb-fallback" style="background:' + color + '">' +
      (m ? iconImg(m, m.label) : "&#9673;") +
      "</div>"
    );
  }

  function badgesHtml(loc) {
    let html = "";
    if (loc.has_quiet_zone && !(loc.space_types || []).includes("quiet")) html += '<span class="pill quiet">Quiet zone</span>';
    if (loc.has_neurodivergent_safe) html += '<span class="pill nd">ND-safe</span>';
    if (loc.id_access_needed) html += '<span class="pill id">ID needed</span>';
    (loc.space_types || []).forEach((t) => {
      const m = SPACE_TYPE_META[t];
      if (m) {
        html +=
          '<span class="pill type" title="' + escapeHtml(m.label) +
          '" style="background:' + m.color + ';color:#fff;border-color:transparent">' +
          iconImg(m, m.label) + " " + escapeHtml(m.label) + "</span>";
      }
    });
    return html;
  }

  function cardHtml(loc) {
    const sub =
      escapeHtml(loc.category_display || "") +
      (loc.campus_display ? " &middot; " + escapeHtml(loc.campus_display) : "");
    return (
      '<li class="place-card">' +
      '<div class="place-thumb">' + thumbHtml(loc) + "</div>" +
      '<div class="place-main">' +
      "<h3>" + escapeHtml(loc.name) + "</h3>" +
      '<p class="place-sub">' + sub + "</p>" +
      '<p class="place-desc">' +
      escapeHtml(loc.description || "No description provided.") +
      "</p>" +
      (loc.wayfinding
        ? '<p class="place-wayfinding"><strong>Wayfinding:</strong> ' + escapeHtml(loc.wayfinding) + "</p>"
        : "") +
      '<div class="place-pills">' + badgesHtml(loc) + "</div>" +
      '<a class="more-info" href="/place/' + loc.slug + '/">Full details &rarr;</a>' +
      "</div>" +
      "</li>"
    );
  }

  function applyFilters() {
    const search = el("places-search").value.trim().toLowerCase();
    const campus = el("filter-campus").value;
    const category = el("filter-category").value;
    const spaceType = el("filter-space-type").value;
    const quietOnly = el("filter-quiet").checked;
    const ndOnly = el("filter-nd").checked;

    const filtered = allLocations.filter((loc) => {
      if (campus && loc.campus !== campus) return false;
      if (category && loc.category !== category) return false;
      if (spaceType && !(loc.space_types || []).includes(spaceType)) return false;
      if (quietOnly && !loc.has_quiet_zone) return false;
      if (ndOnly && !loc.has_neurodivergent_safe) return false;
      if (activeFacilities.size) {
        const have = new Set(loc.facilities_available || []);
        for (const f of activeFacilities) if (!have.has(f)) return false;
      }
      if (search) {
        const hay = (
          loc.name + " " + (loc.also_known_as || "") + " " + (loc.description || "")
        ).toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    });

    if (search) {
      filtered.sort((a, b) => {
        const scoreA = searchScore(a, search);
        const scoreB = searchScore(b, search);
        if (scoreB !== scoreA) return scoreB - scoreA;
        return a.name.localeCompare(b.name);
      });
    }

    render(filtered);
  }

  function render(locations) {
    countEl.textContent =
      "Showing " + locations.length +
      (locations.length === 1 ? " place" : " places");
    if (!locations.length) {
      listEl.innerHTML = '<li class="empty">No places match your filters.</li>';
      return;
    }
    listEl.innerHTML = locations.map(cardHtml).join("");
  }

  // --- Filter controls -----------------------------------------------------
  function buildSelects() {
    if (!metaData) return;
    const fill = (id, items, allLabel) => {
      el(id).innerHTML =
        '<option value="">' + allLabel + "</option>" +
        items
          .map((o) => '<option value="' + o.key + '">' + escapeHtml(o.label) + "</option>")
          .join("");
    };
    fill("filter-campus", metaData.campuses || [], "All campuses");
    fill("filter-category", metaData.categories || [], "All categories");
    fill("filter-space-type", metaData.space_types || [], "Any space type");
  }

  function buildFacilityChips() {
    const facilities = (metaData && metaData.facilities) || [];
    el("facility-chips").innerHTML = facilities
      .map(
        (name) =>
          '<button type="button" class="facility-chip" data-facility="' +
          escapeHtml(name) + '">' + escapeHtml(name) + "</button>"
      )
      .join("");
    el("facility-chips")
      .querySelectorAll(".facility-chip")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          const f = btn.dataset.facility;
          if (activeFacilities.has(f)) {
            activeFacilities.delete(f);
            btn.classList.remove("active");
          } else {
            activeFacilities.add(f);
            btn.classList.add("active");
          }
          applyFilters();
        });
      });
  }

  function setupControls() {
    ["filter-campus", "filter-category", "filter-space-type"].forEach((id) =>
      el(id).addEventListener("change", applyFilters)
    );
    ["filter-quiet", "filter-nd"].forEach((id) =>
      el(id).addEventListener("change", applyFilters)
    );
    el("places-search").addEventListener("input", applyFilters);
    el("clear-filters").addEventListener("click", () => {
      el("places-search").value = "";
      ["filter-campus", "filter-category", "filter-space-type"].forEach(
        (id) => (el(id).value = "")
      );
      el("filter-quiet").checked = false;
      el("filter-nd").checked = false;
      activeFacilities.clear();
      el("facility-chips")
        .querySelectorAll(".facility-chip")
        .forEach((b) => b.classList.remove("active"));
      applyFilters();
    });
  }

  // --- Init ----------------------------------------------------------------
  async function loadData() {
    try {
      const [metaRes, locRes, spaceRes] = await Promise.all([
        fetch("/api/meta/"),
        fetch("/api/locations/"),
        fetch("/api/spaces/"),
      ]);
      if (!locRes.ok) throw new Error("Request failed: " + locRes.status);
      metaData = metaRes.ok ? await metaRes.json() : null;
      allLocations = await locRes.json();

      if (spaceRes.ok) {
        const spaces = await spaceRes.json();
        allLocations = allLocations.concat(spaces.map(asPlace));
      }

      buildSelects();
      buildFacilityChips();
      render(allLocations);
    } catch (err) {
      listEl.innerHTML = '<li class="empty">Could not load places: ' + err.message + "</li>";
      countEl.textContent = "";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupControls();
    loadData();
  });
})();
