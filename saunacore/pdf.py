from __future__ import annotations

from saunacore import service

WINDOW_LABELS = {
    "vormittag": "Vormittag",
    "nachmittag": "Nachmittag",
    "flexibel": "Flexibel",
}


def _latin(text: str) -> bytes:
    cleaned = (
        str(text)
        .replace("€", " EUR")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
    )
    return cleaned.encode("latin-1", "replace")


def _escape(text: str) -> bytes:
    return _latin(text).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _stream(lines: list[str]) -> bytes:
    parts = [b"BT /F1 11 Tf 48 800 Td 14 TL"]
    for index, line in enumerate(lines[:48]):
        size = b"16" if index == 0 else b"11"
        parts.append(b"/F1 " + size + b" Tf (" + _escape(line) + b") Tj T*")
    parts.append(b"ET")
    return b"\n".join(parts)


def _pdf(lines: list[str]) -> bytes:
    stream = _stream(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)


def invoice_pdf(booking, settings: dict, extras: list) -> bytes:
    invoice = booking["payment_method"] == "invoice"
    lines = [
        "RECHNUNG" if invoice else "BELEG",
        "",
        str(settings.get("owner_name") or settings.get("company_name") or ""),
        str(settings.get("street") or ""),
        f"{settings.get('postal_code', '')} {settings.get('city', '')}".strip(),
        str(settings.get("email") or ""),
        f"USt-IdNr. {settings.get('vat_id')}" if settings.get("vat_id") else "",
        "Angaben aus den Einstellungen. Vorlage, keine gepruefte Steuerberatung.",
        "",
        f"Nummer {booking['number']}",
        f"Datum {service.format_dt(booking['created_at'])}",
        f"Status {service.STATUS_LABELS.get(booking['status'], booking['status'])}",
        f"Zahlung {service.PAYMENTS.get(booking['payment_method'], booking['payment_method'])} / {booking['payment_status']}",
        "",
        f"{booking['first_name']} {booking['last_name']}",
        booking["email"],
        booking["phone"],
    ]
    if booking["company"]:
        lines.append(booking["company"])
    if booking["company_vat"]:
        lines.append(f"USt-IdNr. Kunde {booking['company_vat']}")
    lines.extend(
        [
            booking["address"],
            f"{booking['postal_code']} {booking['city']}".strip(),
            booking["zone_name"],
            "",
            booking["model_name"],
            f"{booking['start_date']} bis {booking['end_date']} ({booking['nights']} Naechte)",
        ]
    )
    window = WINDOW_LABELS.get(booking["arrival_window"] or "", "")
    if window:
        lines.append(f"Lieferfenster {window}")
    lines.append("")
    lines.append(f"Miete {service.format_euro(booking['rent_cents'])}")
    delivery = booking["delivery_cents"]
    lines.append("Lieferung kostenlos" if not delivery else f"Lieferung {service.format_euro(delivery)}")
    for extra in extras:
        lines.append(f"{extra.get('qty', 1)}x {extra.get('name', '')} {extra.get('line', '')}")
    if int(booking["deposit_cents"] or 0):
        lines.append(f"Kaution {service.format_euro(booking['deposit_cents'])}")
    if int(booking["voucher_cents"] or 0):
        lines.append(f"Gutschein {booking['voucher_code']} -{service.format_euro(booking['voucher_cents'])}")
    lines.append(f"Gesamt {service.format_euro(booking['gross_cents'])}")
    lines.append(f"darin MwSt. {service.format_euro(booking['vat_cents'])}")
    if booking["payment_status"] == "simulated":
        lines.append("Demo: es wurde kein Geld abgebucht.")
    elif booking["payment_status"] == "unpaid":
        lines.append("Offen, bis die Zahlung erfasst ist.")
    return _pdf([line for line in lines if line is not None])
