# Writing a post

1. Copy `_template/` to a new folder named how the URL should read, e.g.
   `posts/rewatching-la-haine/` → `conorshields.ie/blog/rewatching-la-haine/`.
   Lowercase words and dashes only.
2. Edit `index.md`: set the title, date (`YYYY-MM-DD`) and summary, and
   delete the `draft: true` line when it's ready to go live.
3. Drop photos in the same folder and reference them by file name.
4. Commit and push. The **Build blog** workflow publishes it within a
   couple of minutes and adds it to the home page and the RSS feed.

**Embeds:** a link alone on its own line becomes a player or card:
Spotify, Apple Music, YouTube, Letterboxd films (poster and your rating when
the film is in your recent Letterboxd activity) and Bandcamp (a link card).

**Photos** are resized to 1600px wide and stripped of metadata, including
the GPS location phones record, so originals can go in as they are.

**Preview locally** (optional):

```sh
pip install -r .github/scripts/requirements-blog.txt
python .github/scripts/build_blog.py
python -m http.server 8000 --directory docs   # then open localhost:8000/blog/
```

Folders starting with `_` and posts marked `draft: true` are never published.
