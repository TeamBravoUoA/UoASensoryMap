/* UoA Sensory Map — feedback form.
   Renders the sensory rating legend and the icon-led sensory attribute rows.
   Submits a batch of sensory ratings to /api/sensory-feedback/. */

(function () {
  "use strict";

  const ICON_BASE = "/static/sensemap/icons/";

  const el = (id) => document.getElementById(id);

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  function scaleVar(value) {
    const v = Math.min(5, Math.max(1, Number(value) || 1));
    return "var(--s" + v + ")";
  }

  const OVERALL_SCALE = [
    { value: 1, label: "Adverse" },
    { value: 2, label: "Avoid" },
    { value: 3, label: "Average" },
    { value: 4, label: "Comfortable" },
    { value: 5, label: "Welcoming" },
  ];

  const SENSORY_ATTRIBUTES = [
    { key: "auditory", label: "Auditory (Sound)", description: "How loud or quiet is the environment?", icon: "sensory.svg" },
    { key: "visual", label: "Visual (Light)", description: "How bright or dim is the lighting?", icon: "light.svg" },
    { key: "olfactory", label: "Olfactory (Smell)", description: "How pleasant or strong are the smells?", icon: "smell.svg" },
    { key: "thermal", label: "Thermal (Temperature)", description: "How warm or cool does this place feel?", icon: "temp.svg" },
    { key: "tactile", label: "Tactile (Surfaces)", description: "How comfortable are the surfaces and textures?", icon: "touch.svg" },
    { key: "vestibular", label: "Vestibular (Movement)", description: "How easy is it to move and navigate?", icon: "vestibular.svg" },
    { key: "predictability", label: "Predictability", description: "How consistent and easy to understand is the space?", icon: "predict.svg" },
    { key: "safety_feeling", label: "Safety & Comfort", description: "How safe and secure do you feel?", icon: "safety.svg" },
  ];

  function renderOverallScale() {
    const wrap = el("rating-legend");
    if (!wrap) return;
    wrap.innerHTML = OVERALL_SCALE.map(
      (o) =>
        '<div class="scale-chip" style="color:' + scaleVar(o.value) + '">' +
        '<span class="scale-num">' + o.value + "</span>" +
        '<span class="scale-label">' + escapeHtml(o.label) + "</span>" +
        "</div>"
    ).join("");
  }

  function ratingButtons(attrKey) {
    let out = "";
    for (let v = 1; v <= 5; v++) {
      out +=
        '<button type="button" class="rating-btn" data-attr="' + attrKey +
        '" data-value="' + v + '" style="color:' + scaleVar(v) +
        '" aria-pressed="false">' + v + "</button>";
    }
    return out;
  }

  function renderSensoryAttributes() {
    const wrap = el("sensory-attributes");
    if (!wrap) return;
    wrap.innerHTML = SENSORY_ATTRIBUTES.map(
      (a) =>
        '<div class="sensory-item" data-attr="' + a.key + '">' +
        '<div class="sensory-icon"><img src="' + ICON_BASE + a.icon +
        '" alt="" aria-hidden="true"></div>' +
        '<div class="sensory-info">' +
        "<b>" + escapeHtml(a.label) + "</b>" +
        "<p>" + escapeHtml(a.description) + "</p>" +
        "</div>" +
        '<div class="sensory-ratings">' + ratingButtons(a.key) + "</div>" +
        '<input type="hidden" name="sensory_' + a.key + '" id="sensory-' +
        a.key + '-value" value="">' +
        "</div>"
    ).join("");
  }

  function onRatingClick(e) {
    const btn = e.target.closest(".rating-btn");
    if (!btn) return;
    const item = btn.closest(".sensory-item");

    item.querySelectorAll(".rating-btn").forEach((b) => {
      b.classList.remove("selected");
      b.setAttribute("aria-pressed", "false");
      b.style.background = "";
      b.style.color = scaleVar(b.dataset.value);
    });

    btn.classList.add("selected");
    btn.setAttribute("aria-pressed", "true");
    btn.style.background = scaleVar(btn.dataset.value);
    btn.style.color = "#fff";

    el("sensory-" + item.dataset.attr + "-value").value = btn.dataset.value;
  }

  function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  function resetRatings() {
    SENSORY_ATTRIBUTES.forEach((a) => {
      const elVal = el("sensory-" + a.key + "-value");
      if (elVal) elVal.value = "";
    });
    document.querySelectorAll(".rating-btn.selected").forEach((b) => {
      b.classList.remove("selected");
      b.setAttribute("aria-pressed", "false");
      b.style.background = "";
      b.style.color = scaleVar(b.dataset.value);
    });
  }

  async function onFormSubmit(e) {
    e.preventDefault();
    const form = el("feedback-form");
    const status = el("feedback-message");
    if (!form) return;

    const fd = new FormData(form);
    const targetType = fd.get("target_type") || "";
    const targetId = fd.get("target_id") || "";
    if (!targetType || !targetId) {
      if (status) {
        status.textContent = "Please select a location or space.";
        status.className = "feedback-message error";
      }
      return;
    }

    const ratings = {};
    SENSORY_ATTRIBUTES.forEach((a) => {
      const elVal = el("sensory-" + a.key + "-value");
      if (elVal && elVal.value) ratings[a.key] = parseInt(elVal.value, 10);
    });

    if (Object.keys(ratings).length === 0) {
      if (status) {
        status.textContent = "Please rate at least one sensory attribute.";
        status.className = "feedback-message error";
      }
      return;
    }

    const payload = {
      is_anonymous: (fd.get("feedback_anonymous") || "anonymous") === "anonymous",
      reporter_name: fd.get("feedback_name") || "",
      reporter_email: fd.get("feedback_text") || "",
      ratings: ratings,
    };
    payload[targetType] = parseInt(targetId, 10);

    try {
      const res = await fetch("/api/sensory-feedback/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.ratings || "Submission failed");

      if (status) {
        status.textContent = "Thank you! Your sensory feedback has been added in real time.";
        status.className = "feedback-message ok";
      }
      form.reset();
      resetRatings();
      loadUpdatedProfile(targetType, parseInt(targetId, 10));
    } catch (err) {
      if (status) {
        status.textContent = "Could not submit feedback: " + err.message;
        status.className = "feedback-message error";
      }
    }
  }

  async function loadUpdatedProfile(type, id) {
    const section = el("live-profile");
    const grid = el("live-profile-grid");
    if (!section || !grid) return;

    section.hidden = false;
    grid.innerHTML = "<p>Loading updated profile&hellip;</p>";

    const endpoint =
      type === "space" ? "/api/spaces/" + id + "/" : "/api/locations/" + id + "/";

    try {
      const res = await fetch(endpoint);
      if (!res.ok) throw new Error("Request failed: " + res.status);
      const d = await res.json();
      const profiles = d.sensory_profiles || [];

      if (!profiles.length) {
        grid.innerHTML = "<p>No sensory profile available yet.</p>";
        return;
      }

      grid.innerHTML = profiles
        .map(
          (p) => `
          <div class="sensory-line">
            <span class="s-label">${escapeHtml(p.attribute)}</span>
            <span class="s-bar">
              <b style="width:${(p.rating / 5) * 100}%; background:${scaleVar(p.rating)}"></b>
            </span>
            <span class="val">${p.rating}/5</span>
          </div>`
        )
        .join("");
    } catch (err) {
      grid.innerHTML = "<p>Could not load updated profile: " + escapeHtml(err.message) + "</p>";
    }
  }

  function prefillTarget() {
    const params = new URLSearchParams(window.location.search);
    const locId = params.get("location_id") || "";
    const locName = params.get("location") || params.get("location_name") || "";
    const spaceId = params.get("space_id") || "";
    const spaceName = params.get("space") || "";
    const form = el("feedback-form");

    let type = "";
    let id = "";
    let name = "";
    if (locId) {
      type = "location";
      id = locId;
      name = locName;
    } else if (spaceId) {
      type = "space";
      id = spaceId;
      name = spaceName;
    } else if (locName) {
      type = "location";
      name = locName;
    } else if (spaceName) {
      type = "space";
      name = spaceName;
    }

    if (form) {
      const typeInput = document.createElement("input");
      typeInput.type = "hidden";
      typeInput.name = "target_type";
      typeInput.value = type;
      form.appendChild(typeInput);

      const idInput = document.createElement("input");
      idInput.type = "hidden";
      idInput.name = "target_id";
      idInput.value = id;
      form.appendChild(idInput);
    }

    const search = el("search-location");
    if (search && name) search.value = decodeURIComponent(name);
  }

  function initSensoryForm() {
    renderOverallScale();
    renderSensoryAttributes();
    const wrap = el("sensory-attributes");
    if (wrap) wrap.addEventListener("click", onRatingClick);

    const form = el("feedback-form");
    if (form) form.addEventListener("submit", onFormSubmit);

    el("feedback-loader").hidden = true;
    el("feedback-card").hidden = false;
  }

  initSensoryForm();
  prefillTarget();
})();