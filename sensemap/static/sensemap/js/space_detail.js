/* UoA Sensory Map — dedicated space detail page.
   Fetches a single space from /api/spaces/<id>/ and renders it. */

(function () {
  "use strict";

  const spaceEl = document.getElementById("space-id");
  if (!spaceEl) return;

  const SPACE_ID = JSON.parse(spaceEl.textContent);

  const SCALE_COLOURS = ["#c62828", "#ef6c00", "#f9a825", "#7cb342", "#2e7d32"];

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

  function hoursRow(label, open, close) {
    const time = open && close ? open.slice(0, 5) + " – " + close.slice(0, 5) : "Closed";
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
          <span class="facility ${f.status ? "on" : "off"}" title="${
            f.notes ? escapeHtml(f.notes).replace(/"/g, "&quot;") : ""
          }">
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

  function setSection(id, text) {
    const wrap = el(id);
    const section = document.getElementById(id.replace("dp-", "") + "-section");
    if (!text) {
      if (section) section.hidden = true;
      return;
    }
    wrap.textContent = text;
    if (section) section.hidden = false;
  }

  async function loadDetail() {
    try {
      const res = await fetch("/api/spaces/" + SPACE_ID + "/");

      if (!res.ok) throw new Error("Request failed: " + res.status);

      const s = await res.json();
      const loc = s.location || {};

      el("dp-name").textContent = s.name;

      const thumb = el("dp-thumb");
      if (thumb) {
        if (s.thumbnail_image) {
          thumb.src = s.thumbnail_image;
          thumb.alt = s.name || "";
          thumb.hidden = false;
        } else {
          thumb.removeAttribute("src");
          thumb.hidden = true;
        }
      }

      el("dp-category").textContent = s.space_type_display || s.space_type;

      el("dp-sub").textContent =
        (loc.name ? "Inside " + escapeHtml(loc.name) : "") +
        (loc.campus_display ? " · " + escapeHtml(loc.campus_display) : "");

      el("dp-desc").textContent = s.description || "No description provided.";

      el("dp-hours").innerHTML =
        hoursRow("Mon–Fri", s.weekday_open_time, s.weekday_close_time) +
        hoursRow("Saturday", s.saturday_open_time, s.saturday_close_time) +
        hoursRow("Sun / holidays", s.sunday_holiday_open_time, s.sunday_holiday_close_time);

      el("dp-hours-notes").textContent = s.opening_hrs_notes || "";

      renderFacilities(el("dp-facilities"), s.facilities || []);
      renderSensory(s.sensory_profiles || []);
      setSection("dp-wayfinding", s.wayfinding);

      if (loc.slug) {
        const back = el("dp-back");
        back.href = "/place/" + encodeURIComponent(loc.slug) + "/";
        back.textContent = "Back to " + escapeHtml(loc.name || "place");
      }

      el("dp-feedback-link").href =
        "/feedback/?space_id=" + encodeURIComponent(s.id) + "&space=" + encodeURIComponent(s.name);

      el("detail-loader").hidden = true;
      el("detail-card").hidden = false;
    } catch (err) {
      el("detail-loader").hidden = true;
      el("detail-error").hidden = false;
      el("detail-error").textContent = "Could not load space details: " + err.message;
    }
  }

  loadDetail();
})();
