/* UoA Sensory Map — dedicated place detail page.
   Fetches a single location from /api/locations/<id>/ and renders it. */

(function () {
  "use strict";

  const locationEl = document.getElementById("location-id");
  if (!locationEl) return;

  const LOCATION_ID = JSON.parse(locationEl.textContent);

  const SCALE_COLOURS = ["#2e7d32", "#7cb342", "#f9a825", "#ef6c00", "#c62828"];

  const el = (id) => document.getElementById(id);

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  function scaleColour(value) {
    const v = Math.min(5, Math.max(1, Math.round(value)));
    return SCALE_COLOURS[v - 1];
  }

  function categoryLabel(cat) {
    const labels = {
      teaching_building: "Teaching Building",
      cultural_space: "Cultural Space",
      conference_events: "Conference / Events",
      library: "Library",
      social_building: "Social Building",
      student_services: "Student Services",
      research_laboratory: "Research / Labs",
      garden: "Garden",
    };
    return labels[cat] || cat;
  }

  function hoursRow(label, open, close) {
    const time = (open && close)
      ? open.slice(0, 5) + " – " + close.slice(0, 5)
      : "Closed";

    return `<tr><th>${escapeHtml(label)}</th><td>${time}</td></tr>`;
  }

  function renderFacilities(wrap, facilities) {
    if (!facilities.length) {
      wrap.innerHTML = '<p class="empty">No facilities listed.</p>';
      return;
    }

    wrap.innerHTML = facilities
      .map(
        (f) => `
          <span class="facility ${f.status ? "on" : "off"}">
            ${f.status ? "✓" : "—"} ${escapeHtml(f.name)}
          </span>`
      )
      .join("");
  }

  function renderSensory(profiles) {
    const wrap = el("dp-sensory");

    if (!profiles.length) {
      wrap.innerHTML = '<p class="empty">No sensory profile yet.</p>';
      el("dp-sensory-section").hidden = true;
      return;
    }

    el("dp-sensory-section").hidden = false;

    wrap.innerHTML = profiles
      .map(
        (p) => `
        <div class="sensory-line">
          <span class="s-label">${escapeHtml(p.attribute)}</span>
          <span class="s-bar">
            <b style="width:${(p.rating / 5) * 100}%; background:${scaleColour(p.rating)}"></b>
          </span>
          <span class="val">${p.rating}/5</span>
        </div>`
      )
      .join("");
  }

  function renderSpaces(spaces) {
    const wrap = el("dp-spaces");

    if (!spaces.length) {
      wrap.innerHTML =
        '<p class="empty">No individual spaces listed for this place yet.</p>';
      el("dp-spaces-section").hidden = true;
      return;
    }

    el("dp-spaces-section").hidden = false;

    wrap.innerHTML = spaces
      .map((s) => {
        const flags =
          (s.is_quiet_zone
            ? '<span class="chip quiet">Quiet zone</span>'
            : "") +
          (s.is_safe_space_neurodivergent_students
            ? '<span class="chip nd">ND-safe</span>'
            : "");

        const profiles = (s.sensory_profiles || [])
          .map(
            (p) => `
            <div class="sensory-line small">
              <span class="s-label">${escapeHtml(p.attribute)}</span>
              <span class="s-bar">
                <b style="width:${(p.rating / 5) * 100}%; background:${scaleColour(p.rating)}"></b>
              </span>
              <span class="val">${p.rating}/5</span>
            </div>`
          )
          .join("");

        return `
          <article class="space-card">
            <header>
              <span class="space-type-badge">${escapeHtml(
                s.space_type_display || s.space_type
              )}</span>
              <h4>${escapeHtml(s.name)}</h4>
              ${flags}
            </header>

            ${s.description ? `<p>${escapeHtml(s.description)}</p>` : ""}

            ${
              s.sensory_experience
                ? `<p class="muted-note"><strong>Sensory:</strong> ${escapeHtml(
                    s.sensory_experience
                  )}</p>`
                : ""
            }

            ${profiles ? `<div class="space-sensory">${profiles}</div>` : ""}
          </article>`;
      })
      .join("");
  }

  function renderGallery(images) {
    const wrap = el("dp-gallery");
    const section = el("dp-gallery-section");

    if (!wrap || !section) return;

    section.hidden = false;
    wrap.innerHTML = "";

    if (!images || !images.length) {
      wrap.innerHTML = '<p class="empty">No gallery images yet.</p>';
      return;
    }

    wrap.innerHTML = images
      .map(
        (img) => `
      <a href="${escapeHtml(img.image)}" target="_blank" rel="noopener">
        <img
          src="${escapeHtml(img.thumbnail || img.image)}"
          alt="${escapeHtml(img.alt_text || "Gallery image")}"
          loading="lazy">
      </a>`
      )
      .join("");
  }

  function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const tabId = button.dataset.tab;

        document.querySelectorAll(".tab-btn").forEach((btn) => {
          btn.classList.remove("active");
        });

        document.querySelectorAll(".tab-panel").forEach((panel) => {
          panel.classList.remove("active");
        });

        button.classList.add("active");

        const panel = document.getElementById(tabId);
        if (panel) panel.classList.add("active");
      });
    });
  }

  async function loadDetail() {
    try {
      const res = await fetch("/api/locations/" + LOCATION_ID + "/");

      if (!res.ok)
        throw new Error("Request failed: " + res.status);

      const d = await res.json();

      el("dp-name").textContent = d.name;
      el("dp-category").textContent =
        d.category_display || categoryLabel(d.category);

      el("dp-sub").textContent =
        (d.category_display || categoryLabel(d.category)) +
        (d.campus_display ? " · " + d.campus_display : "");

      el("dp-also").textContent = d.also_known_as
        ? "Also known as " + d.also_known_as
        : "";

      el("dp-desc").textContent =
        d.description || "No description provided.";

      el("dp-access").innerHTML =
        `<span class="facility ${d.id_access_needed ? "" : "on"}">` +
        (d.id_access_needed
          ? "🪪 University ID required"
          : "✓ Open access") +
        "</span>" +
        (d.additional_access_notes
          ? `<p class="muted-note">${escapeHtml(
              d.additional_access_notes
            )}</p>`
          : "");

      el("dp-hours").innerHTML =
        hoursRow("Mon–Fri", d.weekday_open_time, d.weekday_close_time) +
        hoursRow("Saturday", d.saturday_open_time, d.saturday_close_time) +
        hoursRow(
          "Sun / holidays",
          d.sunday_holiday_open_time,
          d.sunday_holiday_close_time
        );

      el("dp-hours-notes").textContent =
        d.opening_hrs_notes || "";

      renderFacilities(el("dp-facilities"), d.facilities || []);
      renderSensory(d.sensory_profiles || []);
      renderSpaces(d.spaces || []);
      renderGallery(d.gallery_images || []);

      const wayfinding = document.getElementById("tab-wayfinding");
      if (wayfinding)
        wayfinding.innerHTML = `<p>${escapeHtml(
          d.wayfinding || "No information available."
        )}</p>`;


      const mapLink = el("dp-map-link");

      if (d.uoa_map_link) {
        mapLink.href = d.uoa_map_link;
      } else {
        mapLink.hidden = true;
      }

      el("detail-loader").hidden = true;
      el("detail-card").hidden = false;

      setupTabs();

    } catch (err) {
      el("detail-loader").hidden = true;
      el("detail-error").hidden = false;
      el("detail-error").textContent =
        "Could not load place details: " + err.message;
    }
  }

  loadDetail();

})();