/* Presentation enhancements. All content remains visible without this file. */
(function () {
  "use strict";
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var progress = document.querySelector(".reading-progress");
  var links = Array.from(document.querySelectorAll(".contents a[href^='#']"));
  var sections = links.map(function (link) {
    return { link: link, section: document.getElementById(link.hash.slice(1)) };
  }).filter(function (row) { return row.section && row.section.id !== "main-content"; });
  var queued = false;

  function updateReading() {
    queued = false;
    var distance = document.documentElement.scrollHeight - window.innerHeight;
    if (progress) progress.style.transform = "scaleX(" + (distance > 0 ? Math.min(1, Math.max(0, window.scrollY / distance)) : 0) + ")";
    var active = sections[0];
    sections.forEach(function (row) {
      if (row.section.getBoundingClientRect().top <= 170) active = row;
    });
    sections.forEach(function (row) {
      if (row === active) row.link.setAttribute("aria-current", "location");
      else row.link.removeAttribute("aria-current");
    });
  }
  function scheduleReading() {
    if (!queued) { queued = true; window.requestAnimationFrame(updateReading); }
  }
  window.addEventListener("scroll", scheduleReading, { passive: true });
  window.addEventListener("resize", scheduleReading);
  document.addEventListener("toggle", scheduleReading, true);
  updateReading();

  function updateEdition(animate) {
    var visible = Array.from(document.querySelectorAll(".card:not([hidden])")).sort(function (a, b) {
      return Number(a.dataset.editionOrder || 0) - Number(b.dataset.editionOrder || 0);
    });
    var photos = visible.slice(0, 12).filter(function (card) { return card.querySelector(".story-image:not(.image-unavailable) img"); });
    var lead = photos.find(function (card) { return !Number(card.dataset.imageWidth) || Number(card.dataset.imageWidth) >= 600; }) || photos[0] || visible[0];
    if (lead) visible = [lead].concat(visible.filter(function (card) { return card !== lead; }));
    document.querySelectorAll(".card").forEach(function (card) { card.classList.remove("is-lead", "is-latest-lead"); });
    if (lead) lead.classList.add("is-lead");
    if (visible[1]) visible[1].classList.add("is-latest-lead");
    var front = document.querySelector(".edition-front");
    if (front) {
      var top = document.querySelector('[data-edition-column="top"]');
      var main = document.querySelector('[data-edition-column="lead"]');
      var latest = document.querySelector('[data-edition-column="latest"]');
      var more = document.querySelector('[data-edition-column="more"]');
      visible.forEach(function (card, index) {
        (index === 0 ? main : index < 4 ? latest : index < 7 ? top : more).appendChild(card);
        var image = card.querySelector("img");
        if (image) image.loading = index === 0 ? "eager" : "lazy";
      });
      top.hidden = visible.length <= 4;
      latest.hidden = visible.length <= 1;
      more.hidden = visible.length <= 7;
      front.hidden = !visible.length;
      front.classList.toggle("is-solo", visible.length === 1);
      front.classList.toggle("is-compact", visible.length > 1 && visible.length <= 4);
    }
    var count = document.querySelector(".edition-count");
    var selected = document.querySelector("[data-filter][aria-pressed=true]");
    if (count && selected) count.textContent = selected.dataset.filter === "following" ? "Your saved questions" : visible.length + " stories · " + selected.textContent;
    if (animate && !reduced.matches) visible.slice(0, 6).forEach(function (card, index) {
      if (typeof card.animate === "function") card.animate([
        { opacity: .35, transform: "translateY(8px)" }, { opacity: 1, transform: "translateY(0)" }
      ], { duration: 300, delay: index * 30, easing: "ease-out" });
    });
  }
  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-filter]")) { updateEdition(true); scheduleReading(); }
    if (event.target.closest("[data-choose]")) scheduleReading();
  });
  updateEdition(false);

  function imageFailed(image) {
    var fallback = image.getAttribute("data-image-fallback");
    if (fallback) {
      image.removeAttribute("data-image-fallback");
      image.src = fallback;
      return;
    }
    var figure = image.closest(".story-image");
    if (figure) figure.classList.add("image-unavailable");
    var card = image.closest(".card");
    if (card) card.classList.remove("has-image");
  }
  document.addEventListener("error", function (event) {
    if (event.target.matches && event.target.matches(".story-image img")) imageFailed(event.target);
  }, true);
  function imageLoaded(image) {
    var figure = image.closest(".story-image");
    if (figure && image.naturalWidth) figure.style.setProperty("--image-native-width", image.naturalWidth + "px");
  }
  document.addEventListener("load", function (event) {
    if (event.target.matches && event.target.matches(".story-image img")) imageLoaded(event.target);
  }, true);
  document.querySelectorAll(".story-image img").forEach(function (image) {
    if (image.complete && image.naturalWidth === 0) imageFailed(image);
    else if (image.complete) imageLoaded(image);
  });

  var categoryNav = document.getElementById("category-nav");
  if (categoryNav) {
    var indicator = categoryNav.querySelector(".nav-indicator");
    var scrollButtons = Array.from(document.querySelectorAll("[data-category-scroll]"));
    var categoryButtons = Array.from(categoryNav.querySelectorAll("[data-filter]"));
    categoryNav.setAttribute("data-enhanced", "true");
    scrollButtons.forEach(function (button) { button.hidden = false; });

    function updateCategoryBar() {
      var selected = categoryNav.querySelector("[aria-pressed=true]");
      if (selected && indicator) {
        indicator.style.width = selected.offsetWidth + "px";
        indicator.style.transform = "translateX(" + selected.offsetLeft + "px)";
      }
      var end = categoryNav.scrollWidth - categoryNav.clientWidth;
      scrollButtons.forEach(function (button) {
        button.disabled = Number(button.dataset.categoryScroll) < 0 ? categoryNav.scrollLeft <= 2 : categoryNav.scrollLeft >= end - 2;
      });
    }
    function revealCategory(button) {
      categoryNav.scrollTo({
        left: button.offsetLeft - (categoryNav.clientWidth - button.offsetWidth) / 2,
        behavior: reduced.matches ? "instant" : "smooth"
      });
      updateCategoryBar();
    }
    scrollButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        categoryNav.scrollBy({ left: Number(button.dataset.categoryScroll) * Math.max(180, categoryNav.clientWidth * .65), behavior: reduced.matches ? "instant" : "smooth" });
      });
    });
    categoryNav.addEventListener("click", function (event) {
      var button = event.target.closest("[data-filter]");
      if (!button) return;
      // reader.js applies the filter at document level before we read its state.
      window.requestAnimationFrame(function () {
        revealCategory(button);
        var bar = categoryNav.closest(".edition-toolbar");
        var mast = document.querySelector(".mast");
        var anchor = document.getElementById("edition-start");
        var start = anchor ? anchor.getBoundingClientRect().top + window.scrollY : 0;
        if (bar && mast && anchor && window.scrollY > start - mast.offsetHeight + 12) {
          window.scrollTo({ top: start - mast.offsetHeight, behavior: reduced.matches ? "instant" : "smooth" });
        }
      });
    });
    categoryNav.addEventListener("keydown", function (event) {
      var index = categoryButtons.indexOf(event.target);
      if (index < 0 || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      var next = event.key === "Home" ? 0 : event.key === "End" ? categoryButtons.length - 1 : Math.max(0, Math.min(categoryButtons.length - 1, index + (event.key === "ArrowRight" ? 1 : -1)));
      categoryButtons[next].focus({ preventScroll: true });
      categoryButtons[next].click();
    });
    categoryNav.addEventListener("scroll", updateCategoryBar, { passive: true });
    categoryNav.addEventListener("focusin", function (event) {
      if (event.target.matches("[data-filter]")) revealCategory(event.target);
    });
    window.addEventListener("resize", function () {
      var selected = categoryNav.querySelector("[aria-pressed=true]");
      if (selected) revealCategory(selected);
      else updateCategoryBar();
    });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(updateCategoryBar);
    updateCategoryBar();
  }
})();
