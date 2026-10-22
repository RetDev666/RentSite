(function () {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  const header = document.querySelector(".site-header");
  const progress = document.querySelector(".scroll-progress");
  const onScroll = () => {
    if (header) header.classList.toggle("is-scrolled", window.scrollY > 12);
    if (!progress) return;
    const height = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.transform = "scaleX(" + (height > 0 ? window.scrollY / height : 0) + ")";
  };
  const motion = document.documentElement.classList.contains("motion");
  const hero = document.querySelector(".hero");
  const heroFrame = document.querySelector(".hero-frame");
  const heroCopy = document.querySelector(".hero-copy");
  const paint = () => {
    onScroll();
    if (!motion || !hero || !heroFrame) return;
    const y = Math.min(window.scrollY, hero.offsetHeight);
    heroFrame.style.translate = "0 " + (y * 0.22) + "px";
    if (heroCopy) {
      heroCopy.style.translate = "0 " + (y * -0.08) + "px";
      heroCopy.style.opacity = String(Math.max(0.15, 1 - y / (hero.offsetHeight * 0.9)));
    }
  };
  paint();
  window.addEventListener("scroll", paint, { passive: true });

  if (motion) {
    const groups = document.querySelectorAll(".card-grid, .points, .steps, .review-grid, .spec-grid, .faq, .channel-grid");
    groups.forEach((group) => {
      [...group.children].forEach((child, index) => {
        child.style.setProperty("--d", (index * 120) + "ms");
      });
    });
    const items = document.querySelectorAll(".card-grid > *, .points > article, .steps > *, .review-grid > *, .spec-grid > article, .faq > details, .channel-grid > *, .section-head, .page-intro");
    const show = (node) => node.classList.add("is-in");
    if ("IntersectionObserver" in window) {
      const watcher = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          show(entry.target);
          watcher.unobserve(entry.target);
        });
      }, { threshold: 0.16, rootMargin: "0px 0px -6% 0px" });
      items.forEach((node) => watcher.observe(node));
    } else {
      items.forEach(show);
    }
    window.setTimeout(() => {
      items.forEach((node) => {
        const box = node.getBoundingClientRect();
        if (box.top < window.innerHeight && box.bottom > 0) show(node);
      });
    }, 1400);
  }

  document.querySelectorAll("[data-gallery]").forEach((gallery) => {
    const main = gallery.querySelector("#gallery-main");
    gallery.querySelectorAll(".thumbs button").forEach((button) => {
      button.addEventListener("click", () => {
        if (main.src.endsWith(button.dataset.src)) return;
        main.classList.add("is-swapping");
        const next = () => {
          main.src = button.dataset.src;
          main.classList.remove("is-swapping");
        };
        window.setTimeout(next, 180);
        gallery.querySelectorAll(".thumbs button").forEach((item) => item.classList.remove("is-active"));
        button.classList.add("is-active");
        button.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      });
    });
  });

  const persons = document.getElementById("filter-persons");
  const size = document.getElementById("filter-size");
  const placeFilter = document.getElementById("filter-place");
  const banner = document.getElementById("zone-banner");
  const empty = document.getElementById("fleet-empty");
  if (persons && size) {
    const cards = [...document.querySelectorAll(".fleet-card")];
    const apply = () => {
      let visible = 0;
      const pVal = (persons.value || "alle").trim();
      const sVal = (size.value || "alle").toLowerCase().trim();

      cards.forEach((card) => {
        let pOk = true;
        if (pVal !== "alle") {
          let cMin = parseInt(card.dataset.capMin, 10);
          let cMax = parseInt(card.dataset.capMax, 10);
          if (isNaN(cMin) || isNaN(cMax)) {
            const pParts = (card.dataset.persons || "").split("-");
            cMin = parseInt(pParts[0], 10) || 1;
            cMax = parseInt(pParts[1], 10) || 10;
          }
          if (pVal.includes("-")) {
            const [rMin, rMax] = pVal.split("-").map(Number);
            pOk = cMax >= rMin && cMin <= rMax;
          } else if (pVal.endsWith("+")) {
            const rMin = parseInt(pVal, 10);
            pOk = cMax >= rMin;
          } else {
            const count = parseInt(pVal, 10);
            pOk = count >= cMin && count <= cMax;
          }
        }

        let sOk = true;
        if (sVal !== "alle") {
          const cardSize = (card.dataset.size || "").toLowerCase().trim();
          if (sVal === "kompakt" || sVal === "s") {
            sOk = cardSize === "kompakt" || cardSize === "s";
          } else if (sVal === "mittel" || sVal === "m") {
            sOk = cardSize === "mittel" || cardSize === "m";
          } else if (sVal === "gross" || sVal === "l" || sVal === "xl") {
            sOk = cardSize === "gross" || cardSize === "l" || cardSize === "xl";
          } else {
            sOk = cardSize === sVal;
          }
        }

        const ok = pOk && sOk;
        card.hidden = !ok;
        if (ok) {
          visible += 1;
          card.classList.add("is-in");
        }
      });
      if (empty) empty.hidden = visible !== 0;
    };
    persons.addEventListener("change", apply);
    size.addEventListener("change", apply);
    let zoneTimer;
    if (placeFilter) placeFilter.addEventListener("input", () => {
      clearTimeout(zoneTimer);
      zoneTimer = setTimeout(async () => {
        const query = placeFilter.value.trim();
        if (query.length < 2) {
          banner.hidden = true;
          return;
        }
        const response = await fetch("/api/zone?q=" + encodeURIComponent(query));
        const data = await response.json();
        banner.hidden = false;
        banner.textContent = data.ok ? "Lieferung: " + data.badge : data.error;
      }, 300);
    });
  }

  const card = document.getElementById("buchen");
  if (!card || document.getElementById("booking-boot")) return;
  const from = document.getElementById("from");
  const to = document.getElementById("to");
  const placeMap = document.getElementById("place-map");
  const placeLabel = document.getElementById("place-label");
  const lines = document.getElementById("price-lines");
  const total = document.getElementById("price-total");
  const error = document.getElementById("book-error");
  const go = document.getElementById("go-book");
  const place = { lat: null, lng: null, address: "" };
  const today = new Date();
  const iso = (date) => {
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return date.getFullYear() + "-" + month + "-" + day;
  };
  from.min = iso(today);
  from.addEventListener("change", () => {
    if (from.value) {
      const next = new Date(from.value + "T00:00:00");
      next.setDate(next.getDate() + 1);
      to.min = iso(next);
      if (to.value && to.value <= from.value) to.value = "";
    }
    sync();
  });
  to.addEventListener("change", sync);
  if (placeMap && window.SaunaMap) {
    SaunaMap.mount(placeMap, {
      interactive: true,
      consent: true,
      onPick: (lat, lng) => {
        place.lat = lat;
        place.lng = lng;
        clearTimeout(placeMap._timer);
        placeMap._timer = setTimeout(async () => {
          const response = await fetch("/api/reverse?lat=" + encodeURIComponent(lat) + "&lng=" + encodeURIComponent(lng));
          const data = await response.json();
          place.address = data.ok ? data.address : "";
          if (placeLabel) placeLabel.textContent = data.ok ? data.address : data.error;
          sync();
        }, 250);
      },
    });
  }

  const busyNote = document.getElementById("busy-note");
  const busyList = document.getElementById("busy-list");
  if (busyNote && card.dataset.modelId) {
    const endDay = new Date(today);
    endDay.setDate(endDay.getDate() + 120);
    fetch("/api/busy?model_id=" + encodeURIComponent(card.dataset.modelId) + "&start=" + iso(today) + "&end=" + iso(endDay))
      .then((response) => response.json())
      .then((data) => {
        const nights = data.busy || [];
        const shown = nights.slice(0, 12);
        if (!shown.length) {
          busyNote.textContent = "In den nächsten 120 Tagen ist keine Nacht belegt.";
          return;
        }
        busyNote.textContent = nights.length > shown.length ? "Belegte Nächte, Auszug:" : "Belegte Nächte:";
        if (busyList) busyList.innerHTML = shown.map((day) => "<li>" + day + "</li>").join("");
      })
      .catch(() => {
        busyNote.textContent = "";
      });
  }

  function syncLink() {
    const params = new URLSearchParams();
    if (from.value) params.set("start", from.value);
    if (to.value) params.set("end", to.value);
    if (place.address) params.set("address", place.address);
    if (place.lat != null) params.set("lat", String(place.lat));
    if (place.lng != null) params.set("lng", String(place.lng));
    const query = params.toString();
    go.href = card.dataset.base + (query ? "?" + query : "");
  }

  async function sync() {
    syncLink();
    error.hidden = true;
    go.classList.remove("is-disabled");
    go.dataset.blocked = "0";
    if (!from.value || !to.value) {
      lines.innerHTML = "";
      total.textContent = "—";
      return;
    }
    const response = await fetch("/api/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({
        model_id: Number(card.dataset.modelId),
        start: from.value,
        end: to.value,
        address: place.address,
        lat: place.lat,
        lng: place.lng,
        extras: []
      })
    });
    const data = await response.json();
    if (!data.ok) {
      error.hidden = false;
      error.textContent = data.error;
      go.classList.add("is-disabled");
      go.dataset.blocked = "1";
      total.textContent = "—";
      lines.innerHTML = "";
      return;
    }
    const rows = [`<div><span>${data.rent_label}</span><span>${data.rent}</span></div>`];
    if (data.needs_address) rows.push("<div><span>Lieferung</span><span>Markierung setzen</span></div>");
    else rows.push(`<div><span>${data.delivery_label}</span><span>${data.delivery}</span></div>`);
    lines.innerHTML = rows.join("");
    total.textContent = data.gross || data.rent;
    if (data.needs_address) {
      go.classList.add("is-disabled");
      go.dataset.blocked = "1";
    }
  }

  go.addEventListener("click", (event) => {
    if (go.dataset.blocked === "1") event.preventDefault();
  });

  function csrf() {
    const match = document.cookie.match(/(?:^|; )csrf=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : readCsrf();
  }
  function readCsrf() {
    return document.querySelector("meta[name=csrf]")?.content || window.__csrf || "";
  }
})();
