(function () {
  const bootNode = document.getElementById("booking-boot");
  if (!bootNode) return;
  const boot = JSON.parse(bootNode.textContent);
  const byId = (id) => document.getElementById(id);
  const months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];

  const state = {
    start: (boot.prefill && boot.prefill.start) || "",
    end: (boot.prefill && boot.prefill.end) || "",
    address: (boot.prefill && boot.prefill.address) || "",
    lat: boot.prefill && boot.prefill.lat ? Number(boot.prefill.lat) : null,
    lng: boot.prefill && boot.prefill.lng ? Number(boot.prefill.lng) : null,
    delivery_type: "delivery",
    qty: {},
    step: 1,
    quote: null,
    busy: new Set(),
    token: readToken(),
  };
  boot.extras.forEach((extra) => {
    state.qty[extra.id] = 0;
  });

  function readToken() {
    const key = "saunacore:" + boot.model.slug;
    try {
      const saved = sessionStorage.getItem(key);
      if (saved) return saved;
      const created = (crypto.randomUUID && crypto.randomUUID()) || ("t-" + Date.now().toString(36) + Math.random().toString(36).slice(2));
      sessionStorage.setItem(key, created);
      return created;
    } catch (_error) {
      return "t-" + Date.now().toString(36) + Math.random().toString(36).slice(2);
    }
  }

  function forgetToken() {
    try {
      sessionStorage.removeItem("saunacore:" + boot.model.slug);
    } catch (_error) {
      /* private mode */
    }
  }

  function iso(date) {
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return date.getFullYear() + "-" + month + "-" + day;
  }

  function parseIso(value) {
    const parts = value.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function showError(message) {
    const banner = byId("error-banner");
    banner.hidden = !message;
    banner.textContent = message || "";
  }

  function goStep(step) {
    state.step = step;
    document.querySelectorAll(".step-panel").forEach((panel) => {
      panel.hidden = Number(panel.dataset.step) !== step;
    });
    document.querySelectorAll("#stepper li").forEach((item) => {
      const current = Number(item.dataset.step);
      item.classList.toggle("is-current", current === step);
      item.classList.toggle("is-done", current < step);
    });
    byId("step-kicker").textContent = "Schritt " + String(step).padStart(2, "0") + "/04";
    showError("");
    window.scrollTo(0, 0);
    if (step === 1) setTimeout(() => { if (pinMap) pinMap.invalidate(); }, 40);
  }

  let view = state.start ? parseIso(state.start) : parseIso(boot.today);
  view = new Date(view.getFullYear(), view.getMonth(), 1);

  function paintRange() {
    document.querySelectorAll("#cal-grid button[data-date]").forEach((button) => {
      const key = button.dataset.date;
      button.classList.toggle("is-start", key === state.start);
      button.classList.toggle("is-end", Boolean(state.end) && key === state.end);
      button.classList.toggle("in-range", Boolean(state.start && state.end && key > state.start && key < state.end));
    });
    const label = byId("range-label");
    if (state.quote && state.quote.range_label) label.textContent = state.quote.range_label;
    else if (state.start && state.end) label.textContent = "Zeitraum wird geprüft";
    else if (state.start) label.textContent = "Abreise wählen";
    else label.textContent = "Bitte An- und Abreise wählen";
  }

  function renderCalendar() {
    byId("cal-title").textContent = months[view.getMonth()] + " " + view.getFullYear();
    const grid = byId("cal-grid");
    grid.innerHTML = "";
    const first = new Date(view.getFullYear(), view.getMonth(), 1);
    const lead = (first.getDay() + 6) % 7;
    const days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
    for (let index = 0; index < lead; index += 1) {
      const blank = document.createElement("button");
      blank.type = "button";
      blank.disabled = true;
      blank.className = "is-out";
      blank.tabIndex = -1;
      grid.appendChild(blank);
    }
    for (let day = 1; day <= days; day += 1) {
      const date = new Date(view.getFullYear(), view.getMonth(), day);
      const key = iso(date);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = String(day);
      button.dataset.date = key;
      if (key < boot.today) {
        button.disabled = true;
        button.classList.add("is-past");
      } else if (state.busy.has(key)) {
        button.classList.add("is-busy");
        button.addEventListener("click", () => pick(key));
      } else {
        button.addEventListener("click", () => pick(key));
      }
      grid.appendChild(button);
    }
    paintRange();
  }

  function nightsBetween(start, end) {
    return Math.round((parseIso(end) - parseIso(start)) / 86400000);
  }

  function rangeBusy(start, end) {
    const cursor = parseIso(start);
    const stop = end;
    while (iso(cursor) < stop) {
      if (state.busy.has(iso(cursor))) return true;
      cursor.setDate(cursor.getDate() + 1);
    }
    return false;
  }

  function pick(key) {
    if (key < boot.today) return;
    const restart = !state.start || state.end || key <= state.start;
    if (restart) {
      if (state.busy.has(key)) {
        showError("Dieser Tag ist belegt.");
        return;
      }
      state.start = key;
      state.end = "";
      state.quote = null;
      showError("");
      paintRange();
      scheduleQuote();
      return;
    }
    const nights = nightsBetween(state.start, key);
    if (nights < boot.minNights) {
      showError(boot.minNights === 1 ? "Mindestens 1 Nacht." : "Mindestens " + boot.minNights + " Nächte.");
      return;
    }
    if (nights > boot.maxNights) {
      showError("Höchstens " + boot.maxNights + " Nächte am Stück.");
      return;
    }
    if (rangeBusy(state.start, key)) {
      showError("In diesem Zeitraum ist die Sauna bereits belegt.");
      return;
    }
    state.end = key;
    showError("");
    paintRange();
    scheduleQuote();
  }

  async function loadBusy() {
    const from = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    const to = new Date(view.getFullYear(), view.getMonth() + 4, 1);
    const url = "/api/busy?model_id=" + boot.model.id + "&start=" + iso(from) + "&end=" + iso(to);
    const response = await fetch(url);
    const data = await response.json();
    if (data.ok) state.busy = new Set(data.busy);
    renderCalendar();
  }

  byId("cal-prev").addEventListener("click", () => {
    view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    loadBusy();
  });
  byId("cal-next").addEventListener("click", () => {
    view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
    loadBusy();
  });

  const address = byId("address");
  const addressConfirm = byId("address-confirm");

  function showPlace(text) {
    address.textContent = text || "Noch keine Markierung";
    addressConfirm.value = text || "";
  }
  showPlace(state.address);

  let pinTimer;
  async function onPin(lat, lng) {
    state.lat = lat;
    state.lng = lng;
    clearTimeout(pinTimer);
    pinTimer = setTimeout(async () => {
      const response = await fetch("/api/reverse?lat=" + encodeURIComponent(lat) + "&lng=" + encodeURIComponent(lng));
      const data = await response.json();
      if (!data.ok) {
        state.address = "";
        showPlace("");
        byId("zone-badge").textContent = data.error;
        showError(data.error);
        return;
      }
      state.address = data.address;
      showPlace(data.address);
      byId("zone-badge").textContent = data.zone ? data.zone.badge : "Außerhalb des Liefergebiets";
      showError("");
      scheduleQuote();
    }, 250);
  }

  const pinMap = window.SaunaMap && SaunaMap.mount(byId("pin-map"), {
    lat: state.lat,
    lng: state.lng,
    interactive: true,
    consent: true,
    onPick: onPin,
  });
  if (state.lat != null && state.lng != null) onPin(state.lat, state.lng);

  const btnDelivery = byId("btn-delivery");
  const btnPickup = byId("btn-pickup");
  const pickupInfoBox = byId("pickup-info-box");
  const deliveryFine = byId("delivery-fine");
  const windowPickWrap = byId("window-pick-wrap");

  function setDeliveryMode(mode) {
    state.delivery_type = mode;
    if (mode === "pickup") {
      if (btnPickup) { btnPickup.classList.add("is-active"); btnPickup.classList.remove("ghost"); }
      if (btnDelivery) { btnDelivery.classList.remove("is-active"); btnDelivery.classList.add("ghost"); }
      if (pickupInfoBox) pickupInfoBox.style.display = "block";
      if (deliveryFine) deliveryFine.style.display = "none";
      if (windowPickWrap) windowPickWrap.style.display = "none";

      state.lat = 52.0911;
      state.lng = 12.8711;
      state.address = "Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)";
      showPlace(state.address);
      byId("zone-badge").textContent = "Kostenlose Selbstabholung (0 €)";
      if (pinMap) {
        if (pinMap.place) pinMap.place(52.0911, 12.8711, true);
        if (pinMap.map) pinMap.map.setView([52.0911, 12.8711], 13);
      }
      scheduleQuote();
    } else {
      if (btnDelivery) { btnDelivery.classList.add("is-active"); btnDelivery.classList.remove("ghost"); }
      if (btnPickup) { btnPickup.classList.remove("is-active"); btnPickup.classList.add("ghost"); }
      if (pickupInfoBox) pickupInfoBox.style.display = "none";
      if (deliveryFine) deliveryFine.style.display = "block";
      if (windowPickWrap) windowPickWrap.style.display = "block";

      if (state.address && state.address.includes("Treuenbrietzen")) {
        state.address = "";
        state.lat = null;
        state.lng = null;
        showPlace("");
        byId("zone-badge").textContent = "Lieferzone nach Markierung";
      }
      scheduleQuote();
    }
  }

  if (btnDelivery) btnDelivery.addEventListener("click", () => setDeliveryMode("delivery"));
  if (btnPickup) btnPickup.addEventListener("click", () => setDeliveryMode("pickup"));

  document.querySelectorAll(".extra-card").forEach((card) => {
    const id = Number(card.dataset.extraId);
    const output = card.querySelector("output");
    const add = card.querySelector("[data-add]");
    const setQty = (qty) => {
      state.qty[id] = qty;
      if (output) output.textContent = String(qty);
      if (add) {
        add.textContent = qty ? "Entfernen" : "Hinzufügen";
        add.classList.toggle("is-on", qty > 0);
      }
      scheduleQuote();
    };
    if (add) add.addEventListener("click", () => setQty(state.qty[id] ? 0 : 1));
    const less = card.querySelector("[data-dec]");
    const more = card.querySelector("[data-inc]");
    if (less) less.addEventListener("click", () => setQty(Math.max(0, (state.qty[id] || 0) - 1)));
    if (more) more.addEventListener("click", () => setQty(Math.min(10, (state.qty[id] || 0) + 1)));
  });

  function chosenExtras() {
    return boot.extras
      .map((extra) => ({ id: extra.id, qty: state.qty[extra.id] || 0 }))
      .filter((extra) => extra.qty > 0);
  }

  function line(label, value) {
    return '<p class="sum-row"><span>' + escapeHtml(label) + "</span><span>" + escapeHtml(value) + "</span></p>";
  }

  function renderSummary() {
    const quote = state.quote;
    const rows = [];
    byId("summary-model").innerHTML = quote
      ? "<strong>" + escapeHtml(quote.model_name) + "</strong><span>" + escapeHtml(quote.range_label) + "</span>"
      : "<strong>" + escapeHtml(boot.model.name) + "</strong><span>" + escapeHtml(boot.model.unit) + " / Tag</span>";
    if (quote) {
      rows.push(line(quote.rent_label, quote.rent));
      rows.push(line(quote.needs_address ? "Lieferung" : quote.delivery_label, quote.needs_address ? "—" : quote.delivery));
      (quote.extras || []).forEach((item) => {
        const label = item.qty > 1 ? item.name + " × " + item.qty : item.name;
        rows.push(line(label, item.line));
      });
      if (quote.deposit_cents) rows.push(line("Kaution", quote.deposit));
      if (quote.voucher_cents) rows.push(line("Gutschein " + (quote.voucher_code || ""), quote.voucher));
    }
    byId("summary-lines").innerHTML = rows.join("");
    byId("invoice-lines").innerHTML = rows.join("");
    const gross = quote && quote.gross ? quote.gross : "—";
    byId("summary-total").textContent = gross;
    byId("invoice-sub").textContent = gross;
    byId("invoice-total").textContent = gross;
    byId("summary-vat").textContent = quote && quote.vat ? quote.vat_text + ": " + quote.vat : "";
    byId("invoice-vat-label").textContent = quote && quote.vat_text ? quote.vat_text : "inkl. MwSt.";
    byId("invoice-vat").textContent = quote && quote.vat ? quote.vat : "—";
    paintRange();
  }

  let quoteTimer;
  function scheduleQuote() {
    clearTimeout(quoteTimer);
    quoteTimer = setTimeout(() => { runQuote(); }, 200);
  }

  async function runQuote() {
    clearTimeout(quoteTimer);
    if (!state.start || !state.end) {
      state.quote = null;
      renderSummary();
      return null;
    }
    const response = await fetch("/api/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrf },
      body: JSON.stringify({
        model_id: boot.model.id,
        delivery_type: state.delivery_type || "delivery",
        start: state.start,
        end: state.end,
        address: state.address.trim(),
        lat: state.lat,
        lng: state.lng,
        extras: chosenExtras(),
        voucher_code: (byId("voucher") && byId("voucher").value.trim()) || "",
      }),
    });
    const data = await response.json();
    if (!data.ok) {
      state.quote = null;
      showError(data.error);
      renderSummary();
      return null;
    }
    state.quote = data;
    showError("");
    renderSummary();
    return data;
  }

  function windowValue() {
    const field = byId("arrival-window");
    return field ? field.value : "";
  }

  function accessReady() {
    const boxes = document.querySelectorAll(".access-check");
    return boxes.length > 0 && Array.from(boxes).every((box) => box.checked);
  }

  byId("btn-to-extras").addEventListener("click", async () => {
    if (!state.start || !state.end) {
      showError("Bitte An- und Abreise wählen.");
      return;
    }
    if (!windowValue()) {
      showError("Bitte wähle ein Lieferfenster.");
      return;
    }
    if (state.lat == null || state.lng == null || state.address.trim().length < 5) {
      showError("Bitte setze die Markierung auf der Karte.");
      return;
    }
    const quote = await runQuote();
    if (!quote || quote.needs_address || !quote.gross) {
      if (!byId("error-banner").textContent) showError("Bitte gib eine Lieferadresse im Liefergebiet an.");
      return;
    }
    goStep(2);
  });

  byId("btn-to-data").addEventListener("click", () => goStep(3));
  byId("btn-back-extras").addEventListener("click", () => goStep(2));
  byId("edit-data").addEventListener("click", () => goStep(3));

  function customerError() {
    const first = byId("first-name").value.trim();
    const last = byId("last-name").value.trim();
    const email = byId("email").value.trim();
    const phone = byId("phone").value.trim();
    if (first.length < 1 || first.length > 60 || last.length < 1 || last.length > 60) return "Bitte gib Vor- und Nachname an.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Bitte gib eine gültige E-Mail an.";
    if ((phone.match(/\d/g) || []).length < 6) return "Bitte gib eine gültige Telefonnummer an.";
    if (state.lat == null || state.address.trim().length < 5) return "Bitte setze die Markierung auf der Karte.";
    return "";
  }

  function renderWho() {
    byId("who").innerHTML = [
      "<p><strong>" + escapeHtml(byId("first-name").value.trim()) + " " + escapeHtml(byId("last-name").value.trim()) + "</strong></p>",
      "<p>" + escapeHtml(byId("email").value.trim()) + "</p>",
      "<p>" + escapeHtml(byId("phone").value.trim()) + "</p>",
      "<p>" + escapeHtml(state.address.trim()) + "</p>",
      windowValue() ? "<p>Lieferfenster: " + escapeHtml(windowValue()) + "</p>" : "",
    ].join("");
  }

  const voucherField = byId("voucher");
  if (voucherField) voucherField.addEventListener("input", scheduleQuote);

  byId("btn-to-pay").addEventListener("click", async () => {
    const problem = customerError();
    if (problem) {
      showError(problem);
      return;
    }
    if (!accessReady()) {
      showError("Bitte bestätige Zufahrt, Stellfläche, Übergabe und die Mietbedingungen.");
      return;
    }
    const quote = await runQuote();
    if (!quote || quote.needs_address) {
      showError("Bitte prüfe Datum und Lieferadresse.");
      return;
    }
    renderWho();
    goStep(4);
  });

  document.querySelectorAll('input[name="pay"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      document.querySelectorAll(".pay-option").forEach((option) => {
        option.classList.toggle("is-selected", option.querySelector("input").checked);
      });
      byId("card-fields").hidden = boot.stripe || document.querySelector('input[name="pay"]:checked').value !== "card";
    });
  });
  if (boot.stripe) byId("card-fields").hidden = true;

  byId("card-number").addEventListener("input", (event) => {
    const digits = event.target.value.replace(/\D/g, "").slice(0, 19);
    event.target.value = digits.replace(/(.{4})/g, "$1 ").trim();
  });
  byId("card-exp").addEventListener("input", (event) => {
    const digits = event.target.value.replace(/\D/g, "").slice(0, 4);
    event.target.value = digits.length > 2 ? digits.slice(0, 2) + "/" + digits.slice(2) : digits;
  });

  function luhn(digits) {
    if (digits.length < 13 || digits.length > 19) return false;
    let sum = 0;
    let alt = false;
    for (let index = digits.length - 1; index >= 0; index -= 1) {
      let digit = Number(digits[index]);
      if (alt) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
      alt = !alt;
    }
    return sum % 10 === 0;
  }

  function cardBrand(digits) {
    if (/^3[47]/.test(digits)) return "Amex";
    if (/^4/.test(digits)) return "Visa";
    if (/^5[1-5]/.test(digits) || /^2(2[2-9]|[3-6]\d|7[01]\d|720)/.test(digits)) return "Mastercard";
    return "Karte";
  }

  byId("btn-book").addEventListener("click", async () => {
    const problem = customerError();
    if (problem) {
      showError(problem);
      return;
    }
    const method = document.querySelector('input[name="pay"]:checked').value;
    const payload = {
      model_id: boot.model.id,
      delivery_type: state.delivery_type || "delivery",
      start: state.start,
      end: state.end,
      address: state.address.trim(),
      lat: state.lat,
      lng: state.lng,
      extras: chosenExtras(),
      first_name: byId("first-name").value.trim(),
      last_name: byId("last-name").value.trim(),
      email: byId("email").value.trim(),
      phone: byId("phone").value.trim(),
      notes: byId("notes").value.trim(),
      payment_method: method,
      client_token: state.token,
      arrival_window: windowValue() || (state.delivery_type === "pickup" ? "flexibel" : ""),
      access_ok: true,
      voucher_code: (byId("voucher") && byId("voucher").value.trim()) || "",
      company: (byId("company") && byId("company").value.trim()) || "",
      company_vat: (byId("company-vat") && byId("company-vat").value.trim()) || "",
    };
    if (state.delivery_type !== "pickup" && !payload.arrival_window) {
      showError("Bitte wähle ein Lieferfenster.");
      return;
    }
    if (!accessReady()) {
      showError("Bitte bestätige Zufahrt, Stellfläche, Übergabe und die Mietbedingungen.");
      return;
    }
    if (method === "card" && !boot.stripe) {
      const digits = byId("card-number").value.replace(/\D/g, "");
      const exp = byId("card-exp").value.trim();
      const cvc = byId("card-cvc").value.replace(/\D/g, "");
      const name = byId("card-name").value.trim();
      if (!luhn(digits)) {
        showError("Die Kartennummer ist ungültig.");
        return;
      }
      if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(exp)) {
        showError("Das Ablaufdatum braucht das Format MM/JJ.");
        return;
      }
      const month = Number(exp.slice(0, 2));
      const year = 2000 + Number(exp.slice(3));
      const today = parseIso(boot.today);
      if (year < today.getFullYear() || (year === today.getFullYear() && month < today.getMonth() + 1)) {
        showError("Die Karte ist abgelaufen.");
        return;
      }
      if (cvc.length < 3 || cvc.length > 4) {
        showError("Bitte gib den CVC an.");
        return;
      }
      if (name.length < 2) {
        showError("Bitte gib den Namen auf der Karte an.");
        return;
      }
      payload.card_last4 = digits.slice(-4);
      payload.card_brand = cardBrand(digits);
      payload.card_exp = exp;
    }
    const button = byId("btn-book");
    button.disabled = true;
    try {
      const response = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": boot.csrf },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!data.ok || !data.redirect) {
        showError(data.error || "Die Buchung konnte nicht gespeichert werden.");
        button.disabled = false;
        return;
      }
      forgetToken();
      window.location = data.redirect;
    } catch (_error) {
      showError("Die Buchung konnte nicht gesendet werden.");
      button.disabled = false;
    }
  });

  const back = document.getElementById("checkout-back");
  if (back) {
    back.addEventListener("click", (event) => {
      if (state.step > 1) {
        event.preventDefault();
        goStep(state.step - 1);
        if (pinMap) pinMap.invalidate();
      }
    });
  }
  document.querySelectorAll("#stepper li").forEach((item) => {
    item.addEventListener("click", () => {
      const target = Number(item.dataset.step);
      if (target < state.step) goStep(target);
    });
  });

  loadBusy().then(() => {
    if (state.start && state.end) scheduleQuote();
  });
})();
