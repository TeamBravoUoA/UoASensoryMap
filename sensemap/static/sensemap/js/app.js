/* UoA Sensory Map — front-end controller
   Pattern: fetch from the Django REST API -> render map markers + list -> detail panel.
   Keeps everything dependency-light (Leaflet via CDN). */

(function () {
  "use strict";

  // --- Config ---------------------------------------------------------------
  const CAMPUS_CENTER = [57.1648, -2.1015]; // Old Aberdeen campus

  // Circular "spotlight" around Old Aberdeen campus (centred on CAMPUS_CENTER),
  // similar in spirit to TCD Sense Map's campus vignette. Radii are hard-coded
  // in metres and comfortably cover all seeded Old Aberdeen locations
  // (lat 57.16259–57.167984, lng -2.106355–-2.093883). Used to restrict the
  // "real" full-colour tiles to a circle around campus, so everywhere else
  // falls back to the darkened base layer.
  const CAMPUS_RADIUS_METERS = 420; // core: fully opaque circle around campus
  const CAMPUS_FADE_STEPS = [
    {
      pane: "campus-tiles-mid",
      radius: 560,
      opacity: 0.55,
      zIndex: 240,
    },
    {
      pane: "campus-tiles-core",
      radius: CAMPUS_RADIUS_METERS,
      opacity: 1,
      zIndex: 250,
    },
  ];
  // const SCALE_COLOURS = ["#2e7d32", "#7cb342", "#f9a825", "#ef6c00", "#c62828"];
  const SCALE_COLOURS = ["#c62828", "#ef6c00", "#f9a825", "#7cb342", "#2e7d32"];
  const QUIET_COLOUR = "#5e35b1";

  const ICON_BASE = "/static/sensemap/icons/";

  // Location category metadata (matches Location.CATEGORY_CHOICES). Drives the
  // map marker icon/colour and the on-map "Place categories" legend.
  const CATEGORY_META = {
    teaching_building: { label: "Teaching Building", iconUrl: "study.svg", color: "#1565c0", desc: "Lecture theatres, seminar and class rooms." },
    cultural_space: { label: "Cultural Space", iconUrl: "social.svg", color: "#f9a825", desc: "Museums, galleries and exhibitions." },
    conference_events: { label: "Conference / Events", iconUrl: "social.svg", color: "#f9a825", desc: "Event and conference venues." },
    library: { label: "Library", iconUrl: "study.svg", color: "#1565c0", desc: "Libraries and study collections." },
    social_building: { label: "Social Building", iconUrl: "social.svg", color: "#f9a825", desc: "Hubs, unions and social spaces." },
    student_services: { label: "Student Services", iconUrl: "facility.svg", color: "#2e7d32", desc: "Support, advice and wellbeing services." },
    research_laboratory: { label: "Research / Labs", iconUrl: "study.svg", color: "#1565c0", desc: "Research buildings and laboratories." },
    garden: { label: "Garden", iconUrl: "garden.svg", color: "#558b2f", desc: "Gardens and outdoor green space." },
    cafe: { label: "Cafeteria", iconUrl: "food_drink.svg", color: "#ef6c00", desc: "Cafes and food outlets." },
    outdoor: { label: "Outdoor", iconUrl: "garden.svg", color: "#607d8b", desc: "Outdoor and miscellaneous spaces." },
    sports_facility: { label: "Sports Facility", iconUrl: "sports.svg", color: "#7b1fa2", desc: "Gyms, sports halls and recreational facilities." },
  };
  
  const CATEGORY_ORDER = [
    "library", "teaching_building", "social_building", "student_services",
    "cultural_space", "research_laboratory", "conference_events", "garden", "cafe", "outdoor", "sports_facility"
  ];
  const FALLBACK_CATEGORY = { label: "Place", iconUrl: "facility.svg", color: "#607d8b", desc: "" };

  // Location marker on the map: all locations are shown with a facility/building icon.
  // The badge background uses the location's category colour, but the SVG icon is always a facility.
  const BUILDING_META = { label: "Building", iconUrl: "facility.svg" };

  // Space type metadata (matches Space.SPACE_TYPE_CHOICES).
  const SPACE_TYPE_META = {
    study: { label: "Study Space", iconUrl: "study.svg", color: "#1565c0", desc: "Focused work, desks and reading areas." },
    quiet: { label: "Quiet Space", iconUrl: "quiet.svg", color: "#5e35b1", desc: "Low-stimulation areas to rest and decompress." },
    social: { label: "Social Space", iconUrl: "social.svg", color: "#f9a825", desc: "Lounges and meeting spots, often lively." },
    food_drink: { label: "Cafeteria", iconUrl: "food_drink.svg", color: "#ef6c00", desc: "Cafes, food courts and places to eat." },
    // facility: { label: "Facility", iconUrl: "facility.svg", color: "#00838f", desc: "General support and service facilities." },
    // sensory: { label: "Sensory Room", iconUrl: "sensory.svg", color: "#d81b60", desc: "Calming rooms designed for sensory regulation." },
    sport: { label: "Sport / Fitness", iconUrl: "sports.svg", color: "#7b1fa2", desc: "Gyms, sports halls and recreational facilities." },
    outdoor: { label: "Outdoor", iconUrl: "garden.svg", color: "#2e7d32", desc: "Outdoor and miscellaneous spaces." },
  
  };
  const SPACE_TYPE_ORDER = ["study", "quiet", "social", "food_drink", "sport", "outdoor"];
  const FALLBACK_SPACE = { label: "Space", iconUrl: "facility.svg", color: "#607d8b", desc: "" };

  // --- State ----------------------------------------------------------------
  let allLocations = [];
  let allSpaces = [];
  let markers = {}; // id -> L.marker
  let map;
  let campusOutlineLayer;
  // radar chart removed
  let selectedId = null;
  let detailCache = {};
  let metaData = null;

  // --- DOM ------------------------------------------------------------------
  const el = (id) => document.getElementById(id);
  const listEl = el("location-list");
  const countEl = el("result-count");
  const detailEl = el("detail");

  // --- Helpers --------------------------------------------------------------
  function scaleColour(value, isQuiet) {
    if (isQuiet) return QUIET_COLOUR;
    const v = Math.min(5, Math.max(1, Math.round(value)));
    return SCALE_COLOURS[v - 1];
  }

  function iconImg(meta, alt) {
    return (
      '<img src="' + ICON_BASE + meta.iconUrl +
      '" alt="' + escapeHtml(alt || meta.label || "") +
      '" class="icon-svg" loading="lazy">'
    );
  }

  function getCookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }

  function feedbackPageUrl() {
    const btn = el("open-feedback-btn");
    const params = new URLSearchParams();
    if (btn && btn.dataset.locationId) params.set("location_id", btn.dataset.locationId);
    if (btn && btn.dataset.locationName) params.set("location_name", btn.dataset.locationName);
    const query = params.toString();
    return query ? "/feedback/?" + query : "/feedback/";
  }

  function drawCampusOutline() {
    if (!map) return;
    if (campusOutlineLayer) map.removeLayer(campusOutlineLayer);

    campusOutlineLayer = L.circle(CAMPUS_CENTER, {
      radius: CAMPUS_RADIUS_METERS,
      color: "#ffffff",
      weight: 1.2,
      opacity: 0.4,
      fill: false,
      dashArray: "4 7",
      interactive: false,
    }).addTo(map);
  }

  // Keeps the circular campus "spotlight" panes clipped to a circle (rather
  // than Leaflet's rectangular tile `bounds`) so the reveal around campus
  // matches a round vignette, e.g. TCD Sense Map's campus view. The clip-path
  // is expressed in the pane's own local pixel space, so panning (a CSS
  // transform on the pane) carries the clip along with the tiles for free —
  // this only needs recalculating when the zoom level (and so metres-per-pixel)
  // changes.
  function updateCampusClip() {
    if (!map) return;
    const zoom = map.getZoom();
    const centerPoint = map.project(L.latLng(CAMPUS_CENTER), zoom).subtract(map.getPixelOrigin());
    const metersPerPixel =
      (156543.03392 * Math.cos((CAMPUS_CENTER[0] * Math.PI) / 180)) / Math.pow(2, zoom);

    CAMPUS_FADE_STEPS.forEach((step) => {
      const pane = map.getPane(step.pane);
      if (!pane) return;
      const radiusPx = step.radius / metersPerPixel;
      const clip = "circle(" + radiusPx + "px at " + centerPoint.x + "px " + centerPoint.y + "px)";
      pane.style.clipPath = clip;
      pane.style.webkitClipPath = clip;
    });
  }

  // --- Map ------------------------------------------------------------------
  function initMap() {
    map = L.map("map", { scrollWheelZoom: true }).setView(CAMPUS_CENTER, 16);

    // Base layer: light, label-free tiles everywhere. This is what shows through
    // for anywhere off-campus, so the city around Old Aberdeen recedes into the
    // background instead of competing with the campus markers.
    const cartoBase = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, ' +
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    // CARTO can intermittently fail (rate limits / network), leaving gray
    // tiles. Retry each failed tile once; if failures keep happening, swap
    // the base layer to OpenStreetMap so the map never stays gray.
    let cartoErrorCount = 0;
    let baseFallbackDone = false;
    cartoBase.on("tileerror", (e) => {
      const tile = e.tile;
      // Retry the tile once with a cache-busting query param.
      if (tile && !tile.dataset.retried) {
        tile.dataset.retried = "1";
        setTimeout(() => {
          tile.src = e.tile.src.split("#")[0] + "#retry";
        }, 500);
        return;
      }
      cartoErrorCount++;
      if (cartoErrorCount >= 5 && !baseFallbackDone) {
        baseFallbackDone = true;
        map.removeLayer(cartoBase);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
      }
    });

    // Three stacked overlays create a soft transition from campus to surroundings.
    // Each pane holds a full (unbounded) tile layer; a CSS circular clip-path
    // (see updateCampusClip) restricts what's actually visible to a circle
    // around campus, instead of Leaflet's rectangular `bounds` option.
    CAMPUS_FADE_STEPS.forEach((step) => {
      const pane = map.createPane(step.pane);
      pane.style.zIndex = String(step.zIndex);
      pane.style.pointerEvents = "none";

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        pane: step.pane,
        opacity: step.opacity,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
    });

    // Recompute the circular clip whenever zoom changes (metres-per-pixel and
    // the pane's pixel origin both change); panning is handled for free since
    // the clip travels with the pane's own CSS transform.
    map.on("zoomend viewreset resize", updateCampusClip);
    updateCampusClip();

    drawCampusOutline();
  }

  function markerMeta(loc, activeSpaceType) {
    if (activeSpaceType && SPACE_TYPE_META[activeSpaceType]) {
      return SPACE_TYPE_META[activeSpaceType];
    }
    return CATEGORY_META[loc.category] || FALLBACK_CATEGORY;
  }

  function makeIcon(loc, activeSpaceType) {
    const catMeta = markerMeta(loc, activeSpaceType);
    // Border colour conveys average sensory intensity; fill colour comes from the
    // category; the SVG icon is always a building for locations.
    const border = loc.avg_sensory == null ? "#9e9e9e" : scaleColour(loc.avg_sensory, false);
    const ring = loc.has_quiet_zone ? "box-shadow:0 0 0 4px rgba(94,53,177,0.35);" : "";
    return L.divIcon({
      className: "sensory-pin",
      html:
        '<span class="pin-badge" style="background:' +
        catMeta.color +
        ";border-color:" +
        border +
        ";" +
        ring +
        '">' +
        iconImg(BUILDING_META, loc.name) +
        "</span>",
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -18],
    });
  }

  function renderMarkers(locations, activeSpaceType) {
    Object.values(markers).forEach((m) => map.removeLayer(m));
    markers = {};
    locations.forEach((loc) => {
      const marker = L.marker([loc.latitude, loc.longitude], {
        icon: makeIcon(loc, activeSpaceType),
        keyboard: true,
        title: loc.name,
        alt: loc.name + (loc.has_quiet_zone && !(loc.space_types || []).includes("quiet") ? " (quiet zone)" : ""),
      });
      marker.on("click", () => selectLocation(loc.id, true));
      marker.addTo(map);
      markers[loc.id] = marker;
    });
  }

  function renderSpaceMarkers(spaces) {
    if (!spaces || !spaces.length) return;
    spaces.forEach((space) => {
      if (!space.latitude || !space.longitude) return;
      const meta = SPACE_TYPE_META[space.space_type] || FALLBACK_SPACE;
      const icon = L.divIcon({
        className: "sensory-pin space-pin",
        html:
          '<span class="pin-badge" style="background:' +
          meta.color +
          '">' +
          iconImg(meta, space.name) +
          "</span>",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14],
      });
      const marker = L.marker([space.latitude, space.longitude], {
        icon: icon,
        keyboard: true,
        title: space.name + " - " + (space.location?.name || ""),
        alt: space.name,
      });
      marker.bindTooltip(space.name + " - " + (space.location?.name || ""), {
        direction: "top",
        offset: [0, -10],
        className: "space-tooltip",
      });
      marker.on("click", () => {
        if (space.location?.id) {
          selectLocation(space.location.id, true);
        }
      });
      marker.addTo(map);
      markers["space-" + space.id] = marker;
    });
  }

  // --- Sidebar list ---------------------------------------------------------
  function renderList(locations) {
    countEl.textContent =
      locations.length + (locations.length === 1 ? " place" : " places") + " found";

    if (locations.length === 0) {
      listEl.innerHTML = '<li class="empty">No places match your filters.</li>';
      return;
    }

    listEl.innerHTML = locations
      .map((loc) => {
        const colour = loc.avg_sensory == null ? "#9e9e9e" : scaleColour(loc.avg_sensory, loc.has_quiet_zone);
        const badges =
          (loc.has_quiet_zone && !(loc.space_types || []).includes("quiet") ? '<span class="chip">Quiet zone</span>' : "") +
          (loc.has_neurodivergent_safe ? '<span class="chip nd">ND-safe</span>' : "");
        const spaceBadges = (loc.space_types || [])
          .map((t) => {
            const m = SPACE_TYPE_META[t] || FALLBACK_SPACE;
            return '<span class="space-tag" title="' + escapeHtml(m.label) + '" style="background:' + m.color + '">' + iconImg(m, m.label) + "</span>";
          })
          .join("");
        return (
          '<li><button type="button" class="location-item" data-id="' +
          loc.id +
          '" aria-current="' +
          (loc.id === selectedId) +
          '">' +
          '<span class="li-top"><span style="display:flex;gap:.5rem;align-items:center">' +
          '<span class="dot" style="background:' +
          colour +
          '"></span><h3>' +
          escapeHtml(loc.name) +
          "</h3></span>" +
          badges +
          "</span>" +
          '<span class="li-cat">' +
          escapeHtml(loc.category_display || categoryLabel(loc.category)) +
          (loc.campus_display ? " &middot; " + escapeHtml(loc.campus_display) : "") +
          "</span>" +
          '<span class="mini-sensory" aria-hidden="true">' +
          spaceBadges +
          "</span>" +
          "</button></li>"
        );
      })
      .join("");

    listEl.querySelectorAll(".location-item").forEach((btn) => {
      btn.addEventListener("click", () =>
        selectLocation(parseInt(btn.dataset.id, 10), true)
      );
    });
  }

  function categoryLabel(cat) {
    return (CATEGORY_META[cat] && CATEGORY_META[cat].label) || cat;
  }

  // --- Legend ---------------------------------------------------------------
  // A larger row used by the standalone "Space types" modal.
  function spaceTypeRow(t) {
    const meta = SPACE_TYPE_META[t];
    if (!meta) return "";
    return (
      '<div class="legend-item large">' +
      '<span class="legend-badge" style="background:' + meta.color + '">' +
      iconImg(meta) +
      "</span>" +
      '<span class="legend-text"><span class="legend-name">' +
      escapeHtml(meta.label) +
      "</span>" +
      '<span class="legend-desc">' + escapeHtml(meta.desc) + "</span>" +
      "</span></div>"
    );
  }

  // Row explaining the building/location marker shown on the map.
  function buildingRow() {
    return (
      '<div class="legend-item large">' +
      '<span class="legend-badge" style="background:#003466">' +
      iconImg(BUILDING_META, "Building / Location") +
      "</span>" +
      '<span class="legend-text"><span class="legend-name">Building / Location</span>' +
      '<span class="legend-desc">This icon marks a building or location on the map. Click it to see the spaces inside.</span>' +
      "</span></div>"
    );
  }

  function renderLegend() {
    el("space-types-grid").innerHTML =
      buildingRow() + SPACE_TYPE_ORDER.map((t) => spaceTypeRow(t)).join("");
  }

  // Quick space-type filter chips shown over the map.
  function renderChips() {
    const chips = [{ key: "", label: "All places", iconUrl: "place.svg", color: "#003466" }].concat(
      SPACE_TYPE_ORDER.map((k) => ({
        key: k,
        label: SPACE_TYPE_META[k].label,
        iconUrl: SPACE_TYPE_META[k].iconUrl,
        color: SPACE_TYPE_META[k].color,
      }))
    );
    el("filter-chips").innerHTML = chips
      .map(
        (c) =>
          '<button type="button" class="chip-filter" data-st="' +
          c.key +
          '"><span class="chip-ic"' +
          (c.color ? ' style="background:' + c.color + '"' : "") +
          ">" +
          iconImg(c, c.label) +
          "</span>" +
          escapeHtml(c.label) +
          "</button>"
      )
      .join("");
    el("filter-chips")
      .querySelectorAll(".chip-filter")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          el("filter-space-type").value = btn.dataset.st;
          const mobile = el("filter-space-type-mobile");
          if (mobile) mobile.value = btn.dataset.st;
          applyFilters();
        });
      });
    const mobileSelect = el("filter-space-type-mobile");
    if (mobileSelect) mobileSelect.value = el("filter-space-type").value;
    setActiveChip(el("filter-space-type").value);
  }

  function setActiveChip(st) {
    el("filter-chips")
      .querySelectorAll(".chip-filter")
      .forEach((b) => b.classList.toggle("active", b.dataset.st === st));
  }

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

  // --- Detail panel ---------------------------------------------------------
  async function selectLocation(id, focusPanel) {
    selectedId = id;
    const loc = allLocations.find((l) => l.id === id);

    // sync list highlight
    listEl.querySelectorAll(".location-item").forEach((b) => {
      b.setAttribute("aria-current", String(parseInt(b.dataset.id, 10) === id));
    });

    if (loc) map.setView([loc.latitude, loc.longitude], 17, { animate: true });

    closeSidebar();
    detailEl.classList.add("open");
    detailEl.setAttribute("aria-hidden", "false");
    el("detail-title").textContent = loc ? loc.name : "Loading\u2026";
    if (focusPanel) el("detail-title").focus();

    try {
      if (!detailCache[id]) {
        const res = await fetch("/api/locations/" + id + "/");
        if (!res.ok) throw new Error("Request failed: " + res.status);
        detailCache[id] = await res.json();
      }
      if (selectedId === id) renderDetail(detailCache[id]);
    } catch (err) {
      el("detail-desc").textContent = "Could not load details: " + err.message;
    }
  }

  function closeDetail() {
    detailEl.classList.remove("open");
    detailEl.setAttribute("aria-hidden", "true");
    selectedId = null;
    listEl.querySelectorAll(".location-item").forEach((b) =>
      b.setAttribute("aria-current", "false")
    );
  }

  function fmtTime(t) {
    return t ? String(t).slice(0, 5) : null;
  }

  function hoursRow(label, open, close) {
    const o = fmtTime(open);
    const c = fmtTime(close);
    const val = o && c ? o + " \u2013 " + c : "Closed";
    return "<tr><th>" + label + "</th><td>" + val + "</td></tr>";
  }

  function renderFacilities(wrap, facs) {
    if (!facs.length) {
      wrap.innerHTML = '<span class="empty">No facilities listed.</span>';
      return;
    }
    wrap.innerHTML = facs
      .map(
        (f) =>
          '<span class="facility ' +
          (f.status ? "on" : "") +
          '"' +
          (f.notes ? ' title="' + escapeHtml(f.notes) + '"' : "") +
          ">" +
          (f.status ? "\u2713 " : "\u2014 ") +
          escapeHtml(f.name) +
          "</span>"
      )
      .join("");
  }

  function renderSensory(profiles) {
    const section = el("loc-sensory-section");
    if (!profiles.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;
    el("sensory-grid").innerHTML = profiles
      .map((p) => {
        const pct = (p.rating / 5) * 100;
        return (
          '<div class="sensory-row"><span class="lbl">' +
          escapeHtml(p.attribute) +
          "</span>" +
          '<span class="bar"><i style="width:' +
          pct +
          "%;background:" +
          scaleColour(p.rating, false) +
          '"></i></span>' +
          '<span class="val">' +
          p.rating +
          "/5</span></div>"
        );
      })
      .join("");
    // radar chart removed
  }

  function renderSpaces(spaces) {
    const wrap = el("spaces-list");
    if (!spaces.length) {
      wrap.innerHTML = '<p class="empty">No individual spaces listed for this place yet.</p>';
      return;
    }
    wrap.innerHTML = spaces
      .map((s) => {
        const m = SPACE_TYPE_META[s.space_type] || FALLBACK_SPACE;
        const flags =
          (s.is_quiet_zone && s.space_type !== "quiet" ? '<span class="chip">Quiet zone</span>' : "") +
          (s.is_safe_space_neurodivergent_students ? '<span class="chip nd">ND-safe</span>' : "");
        const bars = (s.sensory_profiles || [])
          .map(
            (p) =>
              '<span class="space-bar"><small>' +
              escapeHtml(p.attribute) +
              '</small><b><i style="width:' +
              (p.rating / 5) * 100 +
              "%;background:" +
              scaleColour(p.rating, false) +
              '"></i></b></span>'
          )
          .join("");

        const facs = (s.facilities || [])
          .map(
            (f) =>
              '<span class="facility small ' +
              (f.status ? "on" : "") +
              '" title="' +
              (f.notes ? escapeHtml(f.notes).replace(/"/g, '&quot;') : "") +
              '">' +
              (f.status ? "\u2713 " : "\u2014 ") +
              escapeHtml(f.name) +
              "</span>"
          )
          .join("");
        return (
          '<article class="space-card">' +
          '<header><span class="space-type-badge" style="background:' +
          m.color +
          '">' +
          iconImg(m, m.label) +
          " " +
          escapeHtml(s.space_type_display || m.label) +
          "</span>" +
          "<h4>" +
          escapeHtml(s.name) +
          "</h4>" +
          flags +
          "</header>" +
          (s.thumbnail_image
            ? '<img class="space-thumb" src="' +
              escapeHtml(s.thumbnail_image) +
              '" alt="' + escapeHtml(s.name) + '" loading="lazy" style="max-width:100%;height:auto;display:block">'
            : "") +
          (s.id ? '<p class="detail-more"><a href="/space/' + s.id + '/">Space details &rarr;</a></p>' : "") +
          (s.description ? "<p>" + escapeHtml(s.description) + "</p>" : "") +
          (s.wayfinding
            ? '<p class="muted-note"><strong>Wayfinding:</strong> ' + escapeHtml(s.wayfinding) + "</p>"
            : "") +
          (bars ? '<div class="space-bars">' + bars + "</div>" : "") +
          (facs ? '<div class="facilities">' + facs + "</div>" : "") +
          "</article>"
        );
      })
      .join("");
  }

  function renderGallery(imgs) {
    const section = el("gallery-section");
    if (!imgs.length) {
      section.hidden = true;
      return;
    }
    section.hidden = false;
    el("gallery").innerHTML = imgs
      .map(
        (g) =>
          "<figure><img src=\"" +
          g.image +
          '" alt="' +
          escapeHtml(g.caption || "") +
          '" loading="lazy" />' +
          (g.caption ? "<figcaption>" + escapeHtml(g.caption) + "</figcaption>" : "") +
          "</figure>"
      )
      .join("");
  }

  function renderDetail(d) {
    el("detail-title").textContent = d.name;
    el("detail-sub").textContent =
      (d.category_display || categoryLabel(d.category)) +
      (d.campus_display ? " \u00B7 " + d.campus_display : "");
    el("detail-also").textContent = d.also_known_as ? "Also known as " + d.also_known_as : "";
    el("detail-desc").textContent = d.description || "No description provided.";

    // access
    el("detail-access").innerHTML =
      '<span class="facility ' +
      (d.id_access_needed ? "" : "on") +
      '">' +
      (d.id_access_needed ? "\uD83E\uDE93 University ID required" : "\u2713 Open access") +
      "</span>" +
      (d.additional_access_notes
        ? '<p class="muted-note">' + escapeHtml(d.additional_access_notes) + "</p>"
        : "");

    // opening hours
    el("detail-hours").innerHTML =
      hoursRow("Mon\u2013Fri", d.weekday_open_time, d.weekday_close_time) +
      hoursRow("Saturday", d.saturday_open_time, d.saturday_close_time) +
      hoursRow("Sun / holidays", d.sunday_holiday_open_time, d.sunday_holiday_close_time);
    el("detail-hours-notes").textContent = d.opening_hrs_notes || "";

    renderFacilities(el("location-facilities"), d.facilities || []);
    renderSensory(d.sensory_profiles || []);
    renderSpaces(d.spaces || []);
    renderGallery(d.gallery_images || []);
    renderFeedback(d.feedback || []);

    el("detail-map-link").innerHTML = d.uoa_map_link
      ? '<a href="' + d.uoa_map_link + '" target="_blank" rel="noopener">View on the University map \u2197</a>'
      : "";
    el("detail-more-link").href = "/place/" + d.slug + "/";

    const btn = el("open-feedback-btn");
    btn.dataset.locationId = d.id;
    btn.dataset.locationName = d.name;
  }

  function renderFeedback(items) {
    const wrap = el("feedback-list");
    if (!items.length) {
      wrap.innerHTML =
        '<li class="empty" style="padding:.5rem 0">No community feedback yet. Be the first to share.</li>';
      return;
    }
    wrap.innerHTML = items
      .map((r) => {
        const when = new Date(r.created_at).toLocaleDateString();
        const who = r.reporter_name ? escapeHtml(r.reporter_name) : "Anonymous";
        return (
          '<li class="report"><div>' +
          (r.comment ? escapeHtml(r.comment) : "<em>No comment</em>") +
          "</div>" +
          '<div class="meta">' +
          who +
          " &middot; " +
          when +
          "</div></li>"
        );
      })
      .join("");
  }

  // --- Filtering ------------------------------------------------------------
  function applyFilters() {
    const search = el("search").value.trim().toLowerCase();
    const campus = el("filter-campus").value;
    const category = el("filter-category").value;
    const spaceType = el("filter-space-type").value;
    const quietOnly = el("filter-quiet").checked;
    const ndOnly = el("filter-nd").checked;

    const filtered = allLocations.filter((loc) => {
      if (campus && loc.campus !== campus) return false;
      if (category && loc.category !== category) return false;
      const hasSpaceType = (key) => (loc.space_types || []).includes(key);
      if (
        spaceType &&
        !hasSpaceType(spaceType) &&
        !(spaceType === "food_drink" && (loc.category === "cafe" || hasSpaceType("other"))) &&
        !(spaceType === "sport" && (loc.category === "sports_facility" || hasSpaceType("other"))) &&
        !(spaceType === "outdoor" && (loc.category === "garden" || loc.category === "outdoor" || hasSpaceType("other")))
      ) return false;
      if (quietOnly && !loc.has_quiet_zone) return false;
      if (ndOnly && !loc.has_neurodivergent_safe) return false;
      if (search) {
        const hay = (loc.name + " " + (loc.description || "") + " " + (loc.also_known_as || "")).toLowerCase();
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

    if (selectedId && !filtered.some((loc) => loc.id === selectedId)) {
      closeDetail();
    }
    renderList(filtered);
    renderMarkers(filtered, spaceType);

    // Also filter and re-render space markers so the map shows spaces, not just locations.
    const filteredSpaces = (allSpaces || []).filter((s) => {
      if (spaceType && s.space_type !== spaceType) return false;
      if (campus && s.location?.campus !== campus) return false;
      if (category && s.location?.category !== category) return false;
      if (quietOnly && !s.is_quiet_zone) return false;
      if (ndOnly && !s.is_safe_space_neurodivergent_students) return false;
      if (search) {
        const hay = (s.name + " " + (s.description || "")).toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    });
    renderSpaceMarkers(filteredSpaces);

    setActiveChip(spaceType);
  }

  // --- Feedback form --------------------------------------------------------
  function setupFeedbackForm() {
    const openBtn = el("open-feedback-btn");
    if (openBtn) {
      openBtn.addEventListener("click", function () {
        window.location.href = feedbackPageUrl();
      });
    }

    const backdrop = el("feedback-modal");
    const form = el("feedback-form");
    const status = el("feedback-status");
    const anon = el("feedback-anon");

    // The home page can run without the inline feedback modal.
    if (!backdrop || !form || !status || !anon) return;

    function syncAnon() {
      const show = !anon.checked;
      el("feedback-name-field").hidden = !show;
      el("feedback-email-field").hidden = !show;
    }
    anon.addEventListener("change", syncAnon);

    function closeModal() {
      backdrop.classList.remove("open");
    }
    el("feedback-cancel").addEventListener("click", closeModal);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeModal();
    });

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const payload = {
        location: parseInt(el("feedback-location-id").value, 10),
        comment: el("feedback-comment").value.trim(),
        is_anonymous: anon.checked,
        reporter_name: el("feedback-name").value.trim(),
        reporter_email: el("feedback-email").value.trim(),
      };

      status.textContent = "Submitting\u2026";
      status.className = "form-status";
      try {
        const res = await fetch("/api/feedback/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const msg = Object.values(errData).flat().join(" ") || "Server responded " + res.status;
          throw new Error(msg);
        }
        delete detailCache[payload.location];
        status.textContent =
          "Thank you! Your feedback was submitted and will appear once a moderator approves it.";
        status.className = "form-status ok";
        setTimeout(closeModal, 2400);
      } catch (err) {
        status.textContent = "Sorry, could not submit: " + err.message;
        status.className = "form-status err";
      }
    });
  }

  // --- Wire up --------------------------------------------------------------
  function setupControls() {
    ["search", "filter-campus", "filter-category", "filter-space-type", "filter-space-type-mobile", "filter-quiet", "filter-nd"].forEach((id) => {
      const node = el(id);
      if (!node) return;
      const evt = node.type === "checkbox" || node.tagName === "SELECT" ? "change" : "input";
      node.addEventListener(evt, (e) => {
        if (e.target && e.target.id === "filter-space-type-mobile") {
          const desktop = el("filter-space-type");
          if (desktop) desktop.value = e.target.value;
        }
        applyFilters();
      });
    });
    const detailClose = el("detail-close");
    if (detailClose) detailClose.addEventListener("click", closeDetail);
    setupLegend();
    setupNavSearch();
    setupSidebar();
    document.addEventListener("keydown", (e) => {
      const feedbackModal = el("feedback-modal");
      const helpModal = el("help-modal");
      const spaceTypesModal = el("space-types-modal");
      const sidebar = el("sidebar");
      if (e.key === "Escape") {
        if (feedbackModal && feedbackModal.classList.contains("open")) {
          feedbackModal.classList.remove("open");
        } else if (helpModal && helpModal.classList.contains("open")) {
          closeHelp();
        } else if (spaceTypesModal && spaceTypesModal.classList.contains("open")) {
          closeSpaceTypes();
        } else if (detailEl.classList.contains("open")) {
          closeDetail();
        } else if (sidebar && sidebar.classList.contains("open")) {
          closeSidebar();
        }
      }
    });
  }

  // --- Collapsible places / filters panel -----------------------------------
  function closeSidebar() {
    el("sidebar").classList.remove("open");
    el("toggle-list").setAttribute("aria-expanded", "false");
  }

  function setupSidebar() {
    // The floating "Places" button opens the dedicated full-page browser.
    const toggleList = el("toggle-list");
    if (toggleList) toggleList.addEventListener("click", () => {
      window.location.href = "/places/";
    });
    const sidebarClose = el("sidebar-close");
    if (sidebarClose) sidebarClose.addEventListener("click", closeSidebar);
  }

  // --- Legend controls ------------------------------------------------------
  function closeSpaceTypes() {
    el("space-types-modal").classList.remove("open");
  }

  function closeHelp() {
    el("help-modal").classList.remove("open");
  }

  function setupLegend() {
    // Open the standalone "Space types" panel.
    const modal = el("space-types-modal");
    const openSpaceTypes = el("open-space-types");
    if (openSpaceTypes) openSpaceTypes.addEventListener("click", () => {
      modal.classList.add("open");
      el("space-types-title").focus();
    });
    const closeSpaceTypesBtn = el("space-types-close");
    if (closeSpaceTypesBtn) closeSpaceTypesBtn.addEventListener("click", closeSpaceTypes);
    if (modal) modal.addEventListener("click", (e) => {
      if (e.target === modal) closeSpaceTypes();
    });

    // Open the Help modal.
    const helpModal = el("help-modal");
    const openHelp = el("open-help");
    if (openHelp) openHelp.addEventListener("click", () => {
      helpModal.classList.add("open");
      el("help-title").focus();
    });
    const helpClose = el("help-close");
    if (helpClose) helpClose.addEventListener("click", closeHelp);
    if (helpModal) helpModal.addEventListener("click", (e) => {
      if (e.target === helpModal) closeHelp();
    });
  }

  // --- Navbar search (jump straight to a location's detail) -----------------
  let navResults = [];
  let navActive = -1;

  function setupNavSearch() {
    const input = el("nav-search-input");
    const box = el("nav-search-results");
    const icon = document.querySelector(".nav-search-icon");
    if (icon) icon.addEventListener("click", () => input.focus());

    function close() {
      box.hidden = true;
      box.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
      navResults = [];
      navActive = -1;
    }

    function open(matches) {
      navResults = matches;
      navActive = -1;
      box.innerHTML = matches
        .map((loc, i) => {
          const meta = CATEGORY_META[loc.category] || FALLBACK_CATEGORY;
          const sub =
            escapeHtml(loc.category_display || categoryLabel(loc.category)) +
            (loc.campus_display ? " \u00B7 " + escapeHtml(loc.campus_display) : "");
          return (
            '<li role="option"><button type="button" class="nav-result" data-i="' +
            i +
            '">' +
            '<span class="nr-badge" style="background:' +
            meta.color +
            '">' +
            iconImg(meta) +
            "</span>" +
            '<span class="nr-text"><span class="nr-name">' +
            escapeHtml(loc.name) +
            '</span><span class="nr-sub">' +
            sub +
            "</span></span></button></li>"
          );
        })
        .join("");
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");

      box.querySelectorAll(".nav-result").forEach((btn) => {
        btn.addEventListener("click", () =>
          choose(parseInt(btn.dataset.i, 10))
        );
      });
    }

    function choose(i) {
      const loc = navResults[i];
      if (!loc) return;
      selectLocation(loc.id, true);
      input.value = "";
      close();
    }

    function highlight() {
      box.querySelectorAll(".nav-result").forEach((b, i) =>
        b.classList.toggle("active", i === navActive)
      );
    }

    function search(q) {
      const needle = q.trim().toLowerCase();
      // Empty query: show the whole list of places.
      if (!needle) {
        if (!allLocations.length) {
          close();
          return;
        }
        open(allLocations);
        return;
      }
      const matches = allLocations
        .map((loc) => ({ loc, score: searchScore(loc, needle) }))
        .filter(({ score }) => score > 0)
        .sort((a, b) => {
          if (b.score !== a.score) return b.score - a.score;
          return a.loc.name.localeCompare(b.loc.name);
        })
        .map(({ loc }) => loc);

      if (!matches.length) {
        navResults = [];
        navActive = -1;
        box.innerHTML = '<li class="nav-result-empty">No places match that search.</li>';
        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
        return;
      }
      open(matches);
    }

    input.addEventListener("input", () => search(input.value));
    // Clicking / focusing the search opens the full list straight away.
    input.addEventListener("focus", () => search(input.value));
    input.addEventListener("click", () => search(input.value));

    input.addEventListener("keydown", (e) => {
      if (box.hidden || !navResults.length) {
        if (e.key === "Enter") e.preventDefault();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        navActive = (navActive + 1) % navResults.length;
        highlight();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        navActive = (navActive - 1 + navResults.length) % navResults.length;
        highlight();
      } else if (e.key === "Enter") {
        e.preventDefault();
        choose(navActive >= 0 ? navActive : 0);
      } else if (e.key === "Escape") {
        close();
      }
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".nav-search")) close();
    });
  }

  // Populate the sidebar filter <select>s from the meta endpoint choices.
  function buildFilters() {
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

    const uiSpaceTypes = [
      { key: "study", label: "Study Space" },
      { key: "quiet", label: "Quiet Space" },
      { key: "social", label: "Social Space" },
      { key: "food_drink", label: "Cafeteria" },
      { key: "sport", label: "Sport / Fitness" },
      { key: "outdoor", label: "Outdoor" },
    ];
    const apiSpaceTypes = metaData.space_types || [];
    const byKey = {};
    apiSpaceTypes.forEach((o) => {
      byKey[o.key] = { key: o.key, label: o.label };
    });
    uiSpaceTypes.forEach((o) => {
      if (!byKey[o.key]) byKey[o.key] = o;
    });
    fill("filter-space-type", Object.values(byKey), "Any space type");
    fill("filter-space-type-mobile", Object.values(byKey), "All places");
  }

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
      allSpaces = spaceRes.ok ? await spaceRes.json() : [];

      buildFilters();
      renderLegend();
      renderChips();

      if (!allLocations.length) {
        listEl.innerHTML =
          '<li class="empty">No locations yet. Run <code>python manage.py seed</code>.</li>';
        countEl.textContent = "0 places";
        return;
      }
      renderList(allLocations);
      renderMarkers(allLocations, el("filter-space-type").value);
      const bounds = L.latLngBounds(allLocations.map((l) => [l.latitude, l.longitude]));
      if (bounds.isValid()) map.fitBounds(bounds.pad(0.2));

      // Deep link: /?location=<id> (e.g. "More info" from the Places page)
      // opens that location's detail panel straight away.
      const wanted = parseInt(new URLSearchParams(window.location.search).get("location"), 10);
      if (wanted && allLocations.some((l) => l.id === wanted)) {
        selectLocation(wanted, false);
      }
    } catch (err) {
      listEl.innerHTML = '<li class="empty">Could not load data: ' + err.message + "</li>";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    try {
      initMap();
    } catch (err) {
      console.error("initMap failed", err);
    }
    try {
      setupControls();
    } catch (err) {
      console.error("setupControls failed", err);
    }
    try {
      setupFeedbackForm();
    } catch (err) {
      console.error("setupFeedbackForm failed", err);
    }
    try {
      renderChips();
    } catch (err) {
      console.error("renderChips failed", err);
    }
    loadData();
  });
})();