from markupsafe import Markup

def _svg(body: str) -> str:
    return (
        '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


ICONS = {
    "users": _svg(
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="3"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "flame": _svg(
        '<path d="M12 3s5 4 5 8a5 5 0 0 1-10 0c0-2 1.5-3.5 2-5 1.2 1.4 2 2.2 3 3 0-2 .8-4 0-6z"/>'
    ),
    "window": _svg(
        '<rect x="4" y="4" width="16" height="16" rx="2"/>'
        '<path d="M12 4v16M4 12h16"/>'
    ),
    "eye": _svg(
        '<path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12z"/>'
        '<circle cx="12" cy="12" r="2.5"/>'
    ),
    "bolt": _svg('<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>'),
    "door": _svg(
        '<path d="M5 21V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17"/>'
        '<path d="M3 21h18"/>'
        '<circle cx="14.5" cy="12" r="0.8" fill="currentColor" stroke="none"/>'
    ),
    "leaf": _svg('<path d="M5 19C5 11 11 5 20 4 19 13 13 19 5 19z"/><path d="M8 16c2-2 4-5 6-8"/>'),
    "spark": _svg(
        '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.2 2.2M16.2 16.2l2.2 2.2M18.4 5.6l-2.2 2.2M7.8 16.2l-2.2 2.2"/>'
    ),
    "pin": _svg('<path d="M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11z"/><circle cx="12" cy="10" r="2.2"/>'),
    "truck": _svg(
        '<path d="M3 7h11v8H3z"/><path d="M14 10h4l3 3v2h-7"/>'
        '<circle cx="7" cy="17.5" r="1.6"/><circle cx="17" cy="17.5" r="1.6"/>'
    ),
    "check": _svg('<path d="M20 6 9 17l-5-5"/>'),
    "card": _svg('<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>'),
    "cash": _svg(
        '<rect x="2" y="6" width="20" height="12" rx="2"/>'
        '<circle cx="12" cy="12" r="2.5"/>'
        '<path d="M6 12h.01M18 12h.01"/>'
    ),
    "paypal": _svg(
        '<path d="M7 20l2.5-13h5.5a3.5 3.5 0 0 1 0 7h-4.2l-1.3 6H7z"/>'
    ),
    "clock": _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<polyline points="12 7 12 12 15 14"/>'
    ),
    "lock": _svg('<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>'),
    "calendar": _svg('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
    "mail": _svg('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>'),
    "plus": _svg('<path d="M12 5v14M5 12h14"/>'),
    "minus": _svg('<path d="M5 12h14"/>'),
}


def render(name: str) -> Markup:
    return Markup(ICONS.get(name) or ICONS["spark"])
