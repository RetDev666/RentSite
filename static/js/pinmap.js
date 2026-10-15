(function () {
  const BERLIN = [52.52, 13.405];

  function pinIcon() {
    if (!pinIcon.cached) {
      pinIcon.cached = L.divIcon({
        className: "sauna-pin",
        html: "<span></span>",
        iconSize: [28, 28],
        iconAnchor: [14, 26],
        popupAnchor: [0, -24],
      });
    }
    return pinIcon.cached;
  }

  function liveMount(element, opts) {
    const start = opts.lat != null && opts.lng != null && opts.lat !== "" && opts.lng !== ""
      ? [Number(opts.lat), Number(opts.lng)]
      : BERLIN;
    const map = L.map(element, {
      scrollWheelZoom: true,
      zoomControl: true,
    }).setView(start, opts.zoom || (opts.lat != null && opts.lat !== "" ? 14 : 11));
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);
    let marker = null;
    const interactive = opts.interactive !== false;

    function place(lat, lng, silent) {
      const point = [lat, lng];
      if (!marker) {
        marker = L.marker(point, { draggable: interactive, icon: pinIcon() }).addTo(map);
        if (interactive) {
          marker.on("dragend", () => {
            const next = marker.getLatLng();
            if (opts.onPick) opts.onPick(next.lat, next.lng);
          });
        }
      } else {
        marker.setLatLng(point);
      }
      if (!silent && opts.onPick) opts.onPick(lat, lng);
      return marker;
    }

    if (interactive) {
      map.on("click", (event) => place(event.latlng.lat, event.latlng.lng, false));
    }
    if (opts.lat != null && opts.lng != null && opts.lat !== "" && opts.lng !== "") {
      place(Number(opts.lat), Number(opts.lng), true);
    }
    const refresh = () => map.invalidateSize();
    setTimeout(refresh, 50);
    setTimeout(refresh, 400);
    window.addEventListener("load", refresh);
    return { map, place, invalidate: refresh };
  }

  function remembered() {
    try {
      return localStorage.getItem("saunacore-map") === "1";
    } catch (_error) {
      return false;
    }
  }

  function remember() {
    try {
      localStorage.setItem("saunacore-map", "1");
    } catch (_error) {
      /* private mode */
    }
  }

  function deferredMount(element, opts) {
    element.classList.add("is-pending");
    element.innerHTML = '<button type="button" class="map-consent">Karte laden</button><p>Die Karte holt Kacheln von OpenStreetMap, erst nach diesem Klick.</p>';
    let live = null;
    const queued = [];
    const handle = {
      get map() {
        return live && live.map;
      },
      place(lat, lng, silent) {
        if (live) return live.place(lat, lng, silent);
        queued.push([lat, lng, silent]);
        return null;
      },
      invalidate() {
        if (live) live.invalidate();
      },
    };
    element.querySelector("button").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      remember();
      element.classList.remove("is-pending");
      element.innerHTML = "";
      live = liveMount(element, opts);
      queued.forEach((args) => live.place(args[0], args[1], args[2]));
    });
    return handle;
  }

  function mount(element, options) {
    const opts = options || {};
    if (!element || !window.L) return null;
    if (opts.consent && !remembered()) return deferredMount(element, opts);
    return liveMount(element, opts);
  }

  function pins(element, items) {
    if (!element || !window.L) return null;
    const map = L.map(element, { scrollWheelZoom: true }).setView(BERLIN, 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);
    const bounds = [];
    (items || []).forEach((item) => {
      if (item.lat == null || item.lng == null) return;
      const marker = L.marker([item.lat, item.lng], { icon: pinIcon() }).addTo(map);
      const safeLabel = String(item.label || "Buchung").replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      }[ch]));
      const label = item.href ? '<a href="' + item.href + '">' + safeLabel + "</a>" : safeLabel;
      marker.bindPopup(label);
      bounds.push([item.lat, item.lng]);
    });
    if (bounds.length === 1) map.setView(bounds[0], 12);
    else if (bounds.length > 1) map.fitBounds(bounds, { padding: [28, 28] });
    setTimeout(() => map.invalidateSize(), 60);
    return map;
  }

  window.SaunaMap = { mount, pins, berlin: BERLIN };
})();
