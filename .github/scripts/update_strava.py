import json
import os
import time
import urllib.parse
import urllib.request

STRAVA_CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]

SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}
ACTIVITY_LIMIT = 6
VIEWBOX_W, VIEWBOX_H = 400, 300
PATH_MARGIN = 24

NOMINATIM_USER_AGENT = "conorshields.ie site sync (contact: con.shields1@gmail.com)"


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_access_token():
    data = urllib.parse.urlencode({
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": STRAVA_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request("https://www.strava.com/oauth/token", data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def decode_polyline(polyline_str):
    """Standard Google encoded polyline algorithm. Returns [(lat, lng), ...]."""
    points = []
    index = lat = lng = 0
    length = len(polyline_str)
    while index < length:
        for is_lat in (True, False):
            shift = result = 0
            while True:
                b = ord(polyline_str[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lat:
                lat += delta
            else:
                lng += delta
        points.append((lat / 1e5, lng / 1e5))
    return points


def polyline_to_svg_path(points):
    if len(points) < 2:
        return None
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    lat_min, lat_max = min(lats), max(lats)
    lng_min, lng_max = min(lngs), max(lngs)
    lat_span = max(lat_max - lat_min, 1e-6)
    lng_span = max(lng_max - lng_min, 1e-6)

    avail_w = VIEWBOX_W - 2 * PATH_MARGIN
    avail_h = VIEWBOX_H - 2 * PATH_MARGIN
    scale = min(avail_w / lng_span, avail_h / lat_span)
    draw_w = lng_span * scale
    draw_h = lat_span * scale
    offset_x = (VIEWBOX_W - draw_w) / 2
    offset_y = (VIEWBOX_H - draw_h) / 2

    coords = []
    for lat, lng in points:
        x = offset_x + (lng - lng_min) * scale
        y = offset_y + (lat_max - lat) * scale
        coords.append((round(x, 1), round(y, 1)))

    d = f"M{coords[0][0]},{coords[0][1]} " + " ".join(f"L{x},{y}" for x, y in coords[1:])
    return d, coords[0]


COUNTRY_ABBR = {"United Kingdom": "UK", "United States": "USA"}


def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&zoom=15&format=json"
        data = fetch_json(url, headers={"User-Agent": NOMINATIM_USER_AGENT})
        addr = data.get("address", {})
        area = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district")
        city = addr.get("city") or addr.get("town") or addr.get("village")
        if city == "Greater London":
            city = "London"
        country = addr.get("country")
        if country and " / " in country:
            country = country.split(" / ")[-1]
        country = COUNTRY_ABBR.get(country, country)
        parts = [p for p in (area, city, country) if p]
        return ", ".join(parts) if parts else None
    except Exception:
        return None


def get_photo_urls(activity_id, access_token, limit=2):
    try:
        url = f"https://www.strava.com/api/v3/activities/{activity_id}/photos?size=600"
        photos = fetch_json(url, headers={"Authorization": f"Bearer {access_token}"})
        urls = []
        for p in photos[:limit]:
            u = p.get("urls", {}).get("600")
            if u:
                urls.append(u)
        return urls
    except Exception:
        return []


def format_pace(distance_m, moving_time_s):
    if distance_m <= 0:
        return ""
    km = distance_m / 1000
    mins = moving_time_s / 60
    pace_min_per_km = mins / km
    m = int(pace_min_per_km)
    s = int(round((pace_min_per_km - m) * 60))
    if s == 60:
        m += 1
        s = 0
    h = moving_time_s // 3600
    mm = (moving_time_s % 3600) // 60
    ss = moving_time_s % 60
    time_str = f"{h}:{mm:02d}:{ss:02d}" if h else f"{mm}:{ss:02d}"
    return f"{time_str} · {m}:{s:02d} /km"


DAY_ABBR = {
    "en": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    "es": ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"],
}

ACTIVITY_TYPE_ES = {
    "Run": "Carrera", "TrailRun": "Trail", "Ride": "Ciclismo",
    "MountainBikeRide": "MTB", "Walk": "Caminata", "Hike": "Senderismo",
    "Swim": "Natación",
}

STRINGS = {
    "en": {
        "loc_prefix": "Loc.",
        "loc_unavailable": "Location unavailable",
        "photos_label": "On-Location Stills",
    },
    "es": {
        "loc_prefix": "Ubic.",
        "loc_unavailable": "Ubicación no disponible",
        "photos_label": "Fotos en Exteriores",
    },
}


def get_activities(access_token):
    url = f"https://www.strava.com/api/v3/athlete/activities?per_page={ACTIVITY_LIMIT * 2}"
    raw = fetch_json(url, headers={"Authorization": f"Bearer {access_token}"})

    routes = []
    for act in raw:
        polyline = act.get("map", {}).get("summary_polyline")
        if not polyline:
            continue

        points = decode_polyline(polyline)
        path_result = polyline_to_svg_path(points)
        if not path_result:
            continue
        path_d, start_xy = path_result

        start_latlng = act.get("start_latlng") or []
        location = None
        if len(start_latlng) == 2:
            location = reverse_geocode(*start_latlng)
            time.sleep(1)  # respect Nominatim's usage policy

        # Skip photos for Whoop-synced activities: Whoop auto-attaches a
        # generated strain-summary graphic as the activity's "photo", not
        # an actual picture, and it isn't distinguishable from a real
        # photo via any other field in the API response.
        photos = []
        is_whoop = (act.get("device_name") or "").strip().upper() == "WHOOP"
        if not is_whoop and act.get("total_photo_count", 0) > 0:
            photos = get_photo_urls(act["id"], access_token)

        from datetime import datetime
        dt = datetime.fromisoformat(act["start_date_local"].replace("Z", ""))

        routes.append({
            "name": act.get("name", "Activity"),
            "type": act.get("sport_type", act.get("type", "Run")),
            "distance_km": round(act["distance"] / 1000, 1),
            "meta": format_pace(act["distance"], act["moving_time"]),
            "weekday": dt.weekday(),
            "location": location,
            "path_d": path_d,
            "start_xy": start_xy,
            "photos": photos,
        })

        if len(routes) == ACTIVITY_LIMIT:
            break

    return routes


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_routes_html(routes, lang):
    if not routes:
        return None

    t = STRINGS[lang]
    day_abbr = DAY_ABBR[lang]

    paths_svg = []
    markers_svg = []
    list_items = []
    photos_blocks = []

    for i, r in enumerate(routes):
        active = " active" if i == 0 else ""
        paths_svg.append(f'<path class="route-path{active}" data-route="{i}" d="{r["path_d"]}" />')
        markers_svg.append(
            f'<circle class="route-marker{active}" data-route="{i}" cx="{r["start_xy"][0]}" cy="{r["start_xy"][1]}" r="4" />'
        )

        loc = esc(r["location"]) if r["location"] else t["loc_unavailable"]
        activity_type = ACTIVITY_TYPE_ES.get(r["type"], r["type"]) if lang == "es" else r["type"]
        camera_icon = (
            '<svg class="camera-icon" viewBox="0 0 24 24" fill="none" stroke-width="2">'
            '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>'
            if r["photos"] else ""
        )
        list_items.append(
            f'<button class="route-item{active}" data-route="{i}" data-dist="{r["distance_km"]} km" '
            f'data-meta="{esc(r["meta"])}" data-loc="{loc}" data-photos="{len(r["photos"])}">'
            f'<span class="route-dot"></span>'
            f'<span class="route-body">'
            f'<span class="route-name">{esc(r["name"])}</span>'
            f'<span class="route-meta">{day_abbr[r["weekday"]]} · {esc(activity_type)} {camera_icon}</span>'
            f'</span>'
            f'<span class="route-dist">{r["distance_km"]} km</span>'
            f'</button>'
        )

        if r["photos"]:
            frames = "".join(
                f'<div class="photo-frame"><img class="photo-thumb-img" src="{esc(url)}" loading="lazy" alt="{esc(r["name"])}"></div>'
                for url in r["photos"]
            )
            photos_blocks.append(f'<div class="photos-strip" data-route="{i}"{"" if i == 0 else " hidden"}>{frames}</div>')

    first = routes[0]
    first_loc = esc(first["location"]) if first["location"] else t["loc_unavailable"]

    html = f'''<div class="routes-card">
                    <div class="routes-sketch" id="routes-sketch">
                        <div class="loc-tag" id="routes-loc-tag">{t["loc_prefix"]} <b>{first_loc}</b></div>
                        <svg viewBox="0 0 {VIEWBOX_W} {VIEWBOX_H}" preserveAspectRatio="xMidYMid meet">
                            {"".join(paths_svg)}
                            {"".join(markers_svg)}
                        </svg>
                        <div class="routes-readout">
                            <span class="readout-dist" id="routes-readout-dist">{first["distance_km"]} km</span>
                            <span class="readout-meta" id="routes-readout-meta">{esc(first["meta"])}</span>
                        </div>
                    </div>
                    <div class="routes-list" id="routes-list">
                        {"".join(list_items)}
                    </div>
                    <div class="route-photos{" show" if first["photos"] else ""}" id="route-photos">
                        <span class="photos-label">{t["photos_label"]}</span>
                        {"".join(photos_blocks)}
                    </div>
                </div>'''
    return html


def main():
    access_token = get_access_token()
    routes = get_activities(access_token)

    if not routes:
        print("No routes with GPS data found; leaving site unchanged.")
        return

    import re
    for lang, site_path in SITE_PATHS.items():
        routes_html = render_routes_html(routes, lang)
        with open(site_path, "r") as f:
            html = f.read()
        html = re.sub(
            r"<!-- SITE-ROUTES:START -->.*?<!-- SITE-ROUTES:END -->",
            f"<!-- SITE-ROUTES:START -->\n{routes_html}\n<!-- SITE-ROUTES:END -->",
            html, flags=re.DOTALL,
        )
        with open(site_path, "w") as f:
            f.write(html)

    print(f"Updated {len(SITE_PATHS)} site file(s) with {len(routes)} routes.")


if __name__ == "__main__":
    main()
