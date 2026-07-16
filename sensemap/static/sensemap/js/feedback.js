/* UoA Sensory Map — feedback form.
   Renders the sensory rating legend and the icon-led sensory attribute rows.
   Follows the same conventions as place_detail.js / app.js / places.js:
   an IIFE, an el() lookup helper, escapeHtml(), an ICON_BASE constant, and
   array-driven rendering via .map().join(") rather than hand-written markup. */

(function () {
  "use strict";

  const ICON_BASE = "/static/sensemap/icons/";

  const el = (id) => document.getElementById(id);

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  // properties already defined in styles.css for the sensory scale.
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

  // None of the icons shipped in sensemap/static/sensemap/icons/ were made
  // for these six sensory attributes, so — per instructions — existing
  // icons from the shared set are reused rather than inventing new assets.
  const SENSORY_ATTRIBUTES = [
    {
      key: "olfactory",
      label: "Olfactory (Smell)",
      description: "How pleasant or strong are the smells?",
      icon: "smell.svg",
    },
    {
      key: "auditory",
      label: "Auditory (Sound)",
      description: "How loud or quiet is the environment?",
      icon: "sensory.svg",
    },
    {
      key: "visual",
      label: "Visual (Light)",
      description: "How bright or dim is the lighting?",
      icon: "light.svg",
    },
    {
      key: "thermal",
      label: "Thermal (Temperature)",
      description: "How warm or cool does this place feel?",
      icon: "temp.svg",
    },
    {
      key: "crowding",
      label: "Crowding (People)",
      description: "How busy or crowded is this space?",
      icon: "crowd.svg",
    },
    {
      key: "tactile",
      label: "Tactile (Surfaces)",
      description: "How comfortable are the surfaces and textures?",
      icon: "touch.svg",
    },
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

  function initSensoryForm() {
    renderOverallScale();
    renderSensoryAttributes();
    const wrap = el("sensory-attributes");
    if (wrap) wrap.addEventListener("click", onRatingClick);

    el("feedback-loader").hidden = true;
    el("feedback-card").hidden = false;
  }

  initSensoryForm();
})();
