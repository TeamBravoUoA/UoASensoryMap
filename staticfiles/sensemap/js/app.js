/* UoA Sensory Map — front-end controller
   Pattern: fetch from the Django REST API -> render map markers + list -> detail panel.
   Keeps everything dependency-light (Leaflet via CDN). */

(function () {
  "use strict";

  // --- Config ---------------------------------------------------------------
  const CAMPUS_CENTER = [57.1648, -2.1015]; // Old Aberdeen campus

  // Free CARTO basemap tiles require a key as of Aug 2026 (unkeyed requests
  // get a watermarked "API KEY REQUIRED" placeholder instead of real tiles).
  const CARTO_API_KEY = "cb1_3n6e_1_884f8bbb347c4251b96b30f8";

  // Used for the CARTO-failure fallback layer and the campus spotlight layer,
  // replacing raw tile.openstreetmap.org for both so traffic growth doesn't
  // risk tripping OSM's tile usage policy again (get one at maptiler.com).
  const MAPTILER_KEY = "PGouwGPUKGUTyZtokLe0";

  // Circular "spotlight" around each UoA campus.
  // All campuses share ONE extra full-colour tile layer (SPOTLIGHT_PANE); the
  // outer/mid/core rings below are rendered as CSS mask-image radial-gradient
  // stops on that single pane rather than separate tile layers per ring. An
  // earlier version stacked 3 unbounded OSM tile layers per campus (9 total)
  // using clip-path, which multiplied tile requests ~10x on every pan/zoom
  // and tripped OpenStreetMap's tile usage policy (requests started coming
  // back as branded "Access blocked" placeholder tiles instead of real ones).
  const CAMPUS_SPOTLIGHTS = [
    {
      name: "old",
      center: CAMPUS_CENTER,
      steps: [
        { radius: 1050, opacity: 0.25 },
        { radius: 850, opacity: 0.55 },
        { radius: 650, opacity: 1 },
      ],
    },
    {
      name: "hillhead",
      center: [57.1763, -2.1032],
      steps: [
        { radius: 750, opacity: 0.25 },
        { radius: 600, opacity: 0.55 },
        { radius: 450, opacity: 1 },
      ],
    },
    {
      name: "foresterhill",
      center: [57.1560, -2.1359],
      steps: [
        { radius: 750, opacity: 0.25 },
        { radius: 600, opacity: 0.55 },
        { radius: 450, opacity: 1 },
      ],
    },
  ];

  const SPOTLIGHT_PANE = "campus-spotlight-tiles";

  // Campus targets used by the clickable map arrows.
  const TOUR_STOPS = [
    { key: "old", campus: "old_aberdeen", label: "Old Aberdeen", center: CAMPUS_CENTER, zoom: 16 },
    { key: "foresterhill", campus: "foresterhill", label: "Foresterhill", center: [57.1560, -2.1359], zoom: 16 },
    { key: "hillhead", campus: "hillhead", label: "Hillhead", center: [57.1763, -2.1032], zoom: 16 },
  ];
  // Point a fraction of the way from `a` to `b` (0 = at a, 1 = at b). Used to
  // place a jump arrow near the edge of the departure campus, pointing at
  // the destination.
  function pointBetween(a, b, frac) {
    return [a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac];
  }

  // Screen-space bearing used to rotate each map arrow toward its destination.
  function bearingDeg(fromLatLng, toLatLng) {
    const pA = map.latLngToLayerPoint(fromLatLng);
    const pB = map.latLngToLayerPoint(toLatLng);
    return Math.atan2(pB.x - pA.x, -(pB.y - pA.y)) * (180 / Math.PI);
  }

  // Builds a permanent, clickable "jump arrow" between every pair of
  // campuses (adapted from a Leaflet chevron-overlay pattern): each arrow
  // sits between the two campuses, points at its target, carries a label,
  // and flies the map there on click.
  function buildJumpArrows() {
    if (!map) return;
    if (jumpArrowLayer) {
      jumpArrowLayer.clearLayers();
    } else {
      jumpArrowLayer = L.layerGroup().addTo(map);
    }

    TOUR_STOPS.forEach((from) => {
      TOUR_STOPS.forEach((to) => {
        if (from.key === to.key) return;

        const arrowPos = pointBetween(from.center, to.center, 0.32);
        const angle = bearingDeg(arrowPos, to.center);

        const icon = L.divIcon({
          className: "jump-arrow-wrap",
          html: '<div class="jump-arrow" style="transform:rotate(' + angle + 'deg)"></div>',
          iconSize: [26, 24],
          iconAnchor: [13, 12],
        });

        const marker = L.marker(arrowPos, {
          icon: icon,
          keyboard: true,
          title: "Jump to " + to.label,
          alt: "Jump to " + to.label,
        });

        marker.bindTooltip(to.label, {
          direction: "bottom",
          offset: [0, 8],
          permanent: true,
          className: "flyover-label",
        });

        marker.on("click", () => {
          map.flyTo(to.center, to.zoom, { duration: 1.1 });
        });

        marker.addTo(jumpArrowLayer);
      });
    });
  }

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
  let campusOutlineLayers = [];
  let jumpArrowLayer = null; // permanent clickable chevrons between campuses
  // radar chart removed
  let selectedId = null;
  let selectedSpaceId = null;
  let detailCache = {};
  let spaceDetailCache = {};
  let detailPollTimer = null;
  const DETAIL_POLL_MS = 20000;
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
    campusOutlineLayers.forEach((layer) => map.removeLayer(layer));
    campusOutlineLayers = [];

    CAMPUS_SPOTLIGHTS.forEach((campus) => {
      const core = campus.steps[campus.steps.length - 1];
      const layer = L.circle(campus.center, {
        radius: core.radius,
        color: "#ffffff",
        weight: 1.2,
        opacity: 0.4,
        fill: false,
        dashArray: "4 7",
        interactive: false,
      }).addTo(map);
      campusOutlineLayers.push(layer);
    });
  }

  // Paints the circular campus "spotlight" rings as a CSS mask-image on the
  // single shared SPOTLIGHT_PANE, instead of clipping several separate tile
  // layers. Each campus contributes one radial-gradient with hard stops at
  // its outer/mid/core radii (matching the step opacities); the gradients
  // are combined in one mask-image since campuses don't overlap. The mask is
  // expressed in the pane's own local pixel space, so panning (a CSS
  // transform on the pane) carries it along with the tiles for free — this
  // only needs recalculating when the zoom level (and so metres-per-pixel)
  // changes.
  function updateCampusSpotlight() {
    if (!map) return;
    const pane = map.getPane(SPOTLIGHT_PANE);
    if (!pane) return;
    const zoom = map.getZoom();

    // Leaflet panes hold only absolutely-positioned tile <img>s, so with no
    // explicit size they stay a 0x0 box (children don't contribute to auto
    // sizing). mask-image needs a real, sized canvas to rasterize the
    // gradient onto — on a 0x0 box there's nothing to rasterize, so the
    // whole layer silently renders as fully hidden. Sizing the pane to the
    // current viewport gives the mask something to paint onto; the overflow
    // stays visible so panned-in tiles outside this box still show through.
    const mapSize = map.getSize();
    pane.style.width = mapSize.x + "px";
    pane.style.height = mapSize.y + "px";

    const gradients = CAMPUS_SPOTLIGHTS.map((campus) => {
      const centerPoint = map.project(L.latLng(campus.center), zoom).subtract(map.getPixelOrigin());
      const metersPerPixel =
        (156543.03392 * Math.cos((campus.center[0] * Math.PI) / 180)) / Math.pow(2, zoom);

      // steps are outer -> core (largest radius first); walk core -> outer
      // so the gradient stops start at the centre (0px) and grow outward.
      let prevPx = 0;
      const stops = [];
      campus.steps
        .slice()
        .reverse()
        .forEach((step) => {
          const px = step.radius / metersPerPixel;
          stops.push("rgba(255,255,255," + step.opacity + ") " + prevPx + "px");
          stops.push("rgba(255,255,255," + step.opacity + ") " + px + "px");
          prevPx = px;
        });
      stops.push("transparent " + prevPx + "px");

      return (
        "radial-gradient(circle at " + centerPoint.x + "px " + centerPoint.y + "px, " +
        stops.join(", ") + ")"
      );
    });

    const maskValue = gradients.join(", ");
    pane.style.maskImage = maskValue;
    pane.style.webkitMaskImage = maskValue;
  }

  // --- Map ------------------------------------------------------------------
  function initMap() {
    map = L.map("map", { scrollWheelZoom: true }).setView(CAMPUS_CENTER, 16);

    // Base layer: light, label-free tiles everywhere. This is what shows through
    // for anywhere off-campus, so the city around Old Aberdeen recedes into the
    // background instead of competing with the campus markers.
    const cartoBase = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png?key=" + CARTO_API_KEY, {
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
        L.tileLayer("https://api.maptiler.com/maps/streets-v4/256/{z}/{x}/{y}.png?key=" + MAPTILER_KEY, {
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, ' +
            '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
        }).addTo(map);
      }
    });

    // Single full-colour tile layer shared by every campus; updateCampusSpotlight()
    // masks it into the per-campus "spotlight" rings via CSS mask-image instead of
    // clip-path, so this stays one unbounded tile layer instead of one per ring.
    // MapTiler (not raw OSM) so traffic growth doesn't risk tripping OSM's
    // tile usage policy again — this is the layer that generates the most
    // request volume since it's shared across all three campuses.
    const spotlightPane = map.createPane(SPOTLIGHT_PANE);
    spotlightPane.style.zIndex = "230";
    spotlightPane.style.pointerEvents = "none";
    L.tileLayer("https://api.maptiler.com/maps/bright-v2/256/{z}/{x}/{y}.png?key=" + MAPTILER_KEY, {
      maxZoom: 19,
      pane: SPOTLIGHT_PANE,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, ' +
        '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a>',
    }).addTo(map);

    // Recompute the mask whenever zoom changes (metres-per-pixel and the
    // pane's pixel origin both change); panning is handled for free since
    // the mask travels with the pane's own CSS transform.
    map.on("zoomend viewreset resize", updateCampusSpotlight);
    updateCampusSpotlight();

    drawCampusOutline();

    buildJumpArrows();
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

  // Makes a marker's icon arrive with a small pop/bounce instead of just appearing.
  function animateMarkerIn(marker, delayMs) {
    if (!marker) return;
    const node = marker.getElement && marker.getElement();
    if (!node) return;
    node.classList.remove("pin-pop");
    void node.offsetWidth; // force reflow so the animation can restart
    setTimeout(() => node.classList.add("pin-pop"), delayMs || 0);
  }

  function renderMarkers(locations, activeSpaceType) {
    Object.values(markers).forEach((m) => map.removeLayer(m));
    markers = {};
    locations.forEach((loc, idx) => {
      const marker = L.marker([loc.latitude, loc.longitude], {
        icon: makeIcon(loc, activeSpaceType),
        keyboard: true,
        title: loc.name,
        alt: loc.name + (loc.has_quiet_zone && !(loc.space_types || []).includes("quiet") ? " (quiet zone)" : ""),
      });
      marker.on("click", () => selectLocation(loc.id, true));
      marker.addTo(map);
      markers[loc.id] = marker;
      animateMarkerIn(marker, Math.min(idx * 18, 450));
    });
  }

  function renderSpaceMarkers(spaces) {
    if (!spaces || !spaces.length) return;
    spaces.forEach((space, idx) => {
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
        selectSpace(space.id, true);
      });
      marker.addTo(map);
      markers["space-" + space.id] = marker;
      animateMarkerIn(marker, Math.min(idx * 18, 450));
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
        const facilityBadges = (loc.facilities_available || [])
          .map((f) => {
            const label = escapeHtml(f.name) + (f.notes ? " \u2014 " + escapeHtml(f.notes) : "");
            const safeLabel = label.replace(/"/g, "&quot;");
            if (f.icon) {
              return (
                '<img class="sidebar-facility-icon" src="' + escapeHtml(f.icon) + '" alt="" ' +
                'aria-label="' + safeLabel + '" title="' + safeLabel + '">'
              );
            }
            return '<span class="sidebar-facility-name" title="' + safeLabel + '">' + escapeHtml(f.name) + '</span>';
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
          (facilityBadges ? '<span class="mini-facilities" aria-hidden="true">' + facilityBadges + "</span>" : "") +
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

    startDetailPolling(id);
  }

  // Poll the API while the detail panel is open so sensory ratings and other
  // data update in near real time without a page refresh.
  function startDetailPolling(id) {
    stopDetailPolling();
    detailPollTimer = setInterval(async () => {
      if (selectedId !== id || document.hidden) return;
      try {
        const res = await fetch("/api/locations/" + id + "/");
        if (!res.ok) return;
        const fresh = await res.json();
        if (JSON.stringify(fresh) !== JSON.stringify(detailCache[id])) {
          detailCache[id] = fresh;
          if (selectedId === id) renderDetail(fresh);
        }
      } catch (err) {
        /* network hiccup — try again on the next tick */
      }
    }, DETAIL_POLL_MS);
  }

  function stopDetailPolling() {
    if (detailPollTimer) {
      clearInterval(detailPollTimer);
      detailPollTimer = null;
    }
  }

  function closeDetail() {
    stopDetailPolling();
    detailEl.classList.remove("open");
    detailEl.setAttribute("aria-hidden", "true");
    selectedId = null;
    selectedSpaceId = null;
    listEl.querySelectorAll(".location-item").forEach((b) =>
      b.setAttribute("aria-current", "false")
    );
  }

  // --- Space detail panel --------------------------------------------------
  async function selectSpace(id, focusPanel) {
    selectedSpaceId = id;
    selectedId = null;

    const space = allSpaces.find((s) => s.id === id);
    if (space && space.latitude && space.longitude) {
      map.setView([space.latitude, space.longitude], 18, { animate: true });
    }

    closeSidebar();
    detailEl.classList.add("open");
    detailEl.setAttribute("aria-hidden", "false");
    el("detail-title").textContent = space ? space.name : "Loading\u2026";
    if (focusPanel) el("detail-title").focus();

    try {
      if (!spaceDetailCache[id]) {
        const res = await fetch("/api/spaces/" + id + "/");
        if (!res.ok) throw new Error("Request failed: " + res.status);
        spaceDetailCache[id] = await res.json();
      }
      if (selectedSpaceId === id) renderSpaceDetail(spaceDetailCache[id]);
    } catch (err) {
      el("detail-desc").textContent = "Could not load details: " + err.message;
    }
  }

  function renderSpaceDetail(s) {
    var loc = s.location || {};
    var meta = SPACE_TYPE_META[s.space_type] || FALLBACK_SPACE;

    el("detail-title").textContent = s.name;
    el("detail-sub").textContent =
      (s.space_type_display || meta.label) +
      (loc.name ? " \u00B7 " + loc.name : "") +
      (loc.campus_display ? " \u00B7 " + loc.campus_display : "");
    el("detail-also").textContent = "";
    el("detail-desc").textContent = s.description || "No description provided.";

    // access
    el("detail-access").innerHTML =
      '<span class="facility ' +
      (loc.id_access_needed ? "" : "on") +
      '">' +
      (loc.id_access_needed ? "\uD83E\uDE93 University ID required" : "\u2713 Open access") +
      "</span>";

    // opening hours
    el("detail-hours").innerHTML =
      hoursRow("Mon\u2013Fri", s.weekday_open_time, s.weekday_close_time) +
      hoursRow("Saturday", s.saturday_open_time, s.saturday_close_time) +
      hoursRow("Sun / holidays", s.sunday_holiday_open_time, s.sunday_holiday_close_time);
    el("detail-hours-notes").textContent = s.opening_hrs_notes || "";

    // facilities
    renderFacilities(el("location-facilities"), s.facilities || []);

    // sensory profile
    renderSensory(s.sensory_profiles || []);

    // hide spaces list and gallery for space detail
    var spacesSection = document.getElementById("spaces-section");
    if (spacesSection) spacesSection.hidden = true;
    var gallerySection = document.getElementById("gallery-section");
    if (gallerySection) gallerySection.hidden = true;

    el("detail-map-link").innerHTML = "";
    el("detail-more-link").href = "/space/" + s.id + "/";
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
      .map((f) => {
        const icon = f.status ? f.icon_available : f.icon_unavailable;
        const label =
          escapeHtml(f.name) +
          (f.status ? " \u2014 available" : " \u2014 not available") +
          (f.notes ? " \u2014 " + escapeHtml(f.notes) : "");
        const safeLabel = label.replace(/"/g, "&quot;");
        if (icon) {
          return (
            '<div class="facility-item">' +
            '<img class="facility-icon ' + (f.status ? "on" : "off") + '" ' +
            'src="' + escapeHtml(icon) + '" ' +
            'alt="" ' +
            'aria-label="' + safeLabel + '" ' +
            'title="' + safeLabel + '">' +
            (f.notes ? '<small class="facility-note">' + escapeHtml(f.notes) + '</small>' : '') +
            '</div>'
          );
        }
        return (
          '<span class="facility ' + (f.status ? "on" : "") + '"' +
          (f.notes ? ' title="' + escapeHtml(f.notes) + '"' : "") +
          ">" +
          (f.status ? "\u2713 " : "\u2014 ") +
          escapeHtml(f.name) +
          "</span>"
        );
      })
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
    var spacesSection = document.getElementById("spaces-section");
    if (spacesSection) spacesSection.hidden = false;
    renderSpaces(d.spaces || []);
    renderGallery(d.gallery_images || []);

    el("detail-map-link").innerHTML = d.uoa_map_link
      ? '<a href="' + d.uoa_map_link + '" target="_blank" rel="noopener">View on the University map \u2197</a>'
      : "";
    el("detail-more-link").href = "/place/" + d.slug + "/";
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
      renderSpaceMarkers(allSpaces);
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