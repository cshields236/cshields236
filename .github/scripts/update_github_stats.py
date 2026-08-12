import json
import os
import re
import urllib.request

GITHUB_USERNAME = "cshields236"
SEARCH_URL = f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}"
SITE_PATHS = ["docs/index.html", "docs/es/index.html"]


def fetch_json(url):
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "User-Agent": "conorshields.ie site sync (contact: con.shields1@gmail.com)",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_commit_count():
    data = fetch_json(SEARCH_URL)
    return data["total_count"]


def format_count(count):
    return f"{count:,}"


def main():
    count = get_commit_count()
    if count <= 0:
        raise SystemExit(f"refusing to write a non-positive commit count: {count}")
    formatted = format_count(count)

    for site_path in SITE_PATHS:
        with open(site_path, "r") as f:
            html = f.read()
        html, n = re.subn(
            r"<!-- SITE-BOX-OFFICE:START -->.*?<!-- SITE-BOX-OFFICE:END -->",
            f"<!-- SITE-BOX-OFFICE:START -->{formatted}<!-- SITE-BOX-OFFICE:END -->",
            html, flags=re.DOTALL,
        )
        if n == 0:
            raise SystemExit(f"SITE-BOX-OFFICE marker not found in {site_path}")
        with open(site_path, "w") as f:
            f.write(html)

    print(f"Updated {len(SITE_PATHS)} site file(s): {formatted} commits.")


if __name__ == "__main__":
    main()
