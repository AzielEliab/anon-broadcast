/**
 * AnonBroadcast landing.
 * Author: Aziel Eliab only.
 */

export const VERSION = "0.1.0";
export const TITLE = "AnonBroadcast — Aziel Eliab";
export const DESCRIPTION =
  "Text becomes a local desk reel: a formant voice, a metadata-culled MP4, and a SHA-256 receipt.";
export const AUTHOR = "Aziel Eliab";
export const HOST = "https://anon-broadcast-download-tracker.vibelock.workers.dev";
export const DEFAULT_ASSET = "anon-broadcast-0.1.0.tar.gz";
export const GITHUB = "https://github.com/AzielEliab/anon-broadcast";
const INSTALL_LINE = `curl -fsSL ${HOST}/install.sh | bash`;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function citePayload() {
  return {
    type: "software",
    title: "AnonBroadcast",
    version: VERSION,
    author: AUTHOR,
    license: "Apache-2.0",
    url: GITHUB,
    download: `${HOST}/download?asset=${DEFAULT_ASSET}`,
    note: "No DOI is invented here.",
  };
}

export function jsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "AnonBroadcast",
    applicationCategory: "MultimediaApplication",
    operatingSystem: "macOS, Windows, Linux",
    softwareVersion: VERSION,
    description: DESCRIPTION,
    author: { "@type": "Person", name: AUTHOR },
    license: "https://www.apache.org/licenses/LICENSE-2.0",
    codeRepository: GITHUB,
    downloadUrl: `${HOST}/download?asset=${DEFAULT_ASSET}`,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  };
}

function sitemapXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${HOST}/</loc></url>
  <url><loc>${HOST}/download?asset=${DEFAULT_ASSET}</loc></url>
</urlset>
`;
}

function robotsTxt() {
  return `User-agent: *\nAllow: /\nSitemap: ${HOST}/sitemap.xml\n`;
}

function llmsTxt() {
  return `# AnonBroadcast

${DESCRIPTION}

Author: ${AUTHOR}
Version: ${VERSION}
License: Apache-2.0
Source: ${GITHUB}
Download: ${HOST}/download?asset=${DEFAULT_ASSET}

The package renders on the computer where it is installed. It needs Python 3.11+ and ffmpeg. The MP4 and the SHA-256 receipt stay on that computer.

Counted download routes: GET /download, GET /count, GET /stats, POST /event.
`;
}

export function handleSeoRoutes(request, url) {
  if (request.method !== "GET" && request.method !== "HEAD") return null;
  const path = url.pathname;
  const head = request.method === "HEAD";
  const send = (body, contentType) =>
    new Response(head ? null : body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "private, no-store",
      },
    });
  if (path === "/cite.json") return send(JSON.stringify(citePayload(), null, 2), "application/json; charset=utf-8");
  if (path === "/sitemap.xml") return send(sitemapXml(), "application/xml; charset=utf-8");
  if (path === "/robots.txt") return send(robotsTxt(), "text/plain; charset=utf-8");
  if (path === "/llms.txt") return send(llmsTxt(), "text/plain; charset=utf-8");
  if (path === "/openapi.json") {
    const spec = {
      openapi: "3.1.0",
      info: {
        title: "AnonBroadcast download tracker",
        version: VERSION,
        description: `${DESCRIPTION} Author: ${AUTHOR}.`,
      },
      paths: {
        "/download": { get: { summary: "Counted gzip of the source package" } },
        "/count": { get: { summary: "views, downloads, and total" } },
        "/stats": { get: { summary: "counts by repo, branch, and fork" } },
        "/event": { post: { summary: "record a download from a fork or branch" } },
      },
    };
    return send(JSON.stringify(spec, null, 2), "application/json; charset=utf-8");
  }
  return null;
}

function breakdownList(stats) {
  const rows = Array.isArray(stats.breakdown) ? stats.breakdown : [];
  if (!rows.length) return "<li>No counted downloads yet.</li>";
  return rows
    .map((row) => {
      const repo = escapeHtml(`${row.owner}/${row.repo}`);
      const branch = escapeHtml(row.branch);
      const fork = row.fork === "1" ? "fork" : "upstream";
      return `<li><code>${repo}</code> branch <code>${branch}</code> ${fork} — ${Number(row.count) || 0}</li>`;
    })
    .join("");
}

export function renderHome(stats) {
  const downloads = Number(stats.downloads != null ? stats.downloads : stats.total) || 0;
  const n = downloads.toLocaleString("en-US");
  const ld = JSON.stringify(jsonLd());
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${TITLE}</title>
<meta name="description" content="${escapeHtml(DESCRIPTION)}">
<meta name="author" content="${AUTHOR}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="${HOST}/">
<link rel="icon" type="image/png" href="/sigil.png">
<meta property="og:type" content="website">
<meta property="og:title" content="${TITLE}">
<meta property="og:description" content="${escapeHtml(DESCRIPTION)}">
<meta property="og:url" content="${HOST}/">
<meta property="og:image" content="${HOST}/preview.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${TITLE}">
<meta name="twitter:description" content="${escapeHtml(DESCRIPTION)}">
<meta name="twitter:image" content="${HOST}/preview.png">
<script type="application/ld+json">${ld}</script>
<style>
  :root {
    color-scheme: light;
    --bg: #f4f0e6;
    --ink: #1c1914;
    --muted: #3f3a32;
    --card: #fffdf8;
    --line: #d4cbb8;
    --button: #1c1914;
    --button-ink: #f7f4ee;
    --focus: #6d4f12;
    --shadow: 0 16px 40px #1c191414;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg: #14120e;
      --ink: #f4f0e6;
      --muted: #d7d0c3;
      --card: #221f1a;
      --line: #3d382f;
      --button: #f4f0e6;
      --button-ink: #1c1914;
      --focus: #f0d78c;
      --shadow: 0 16px 40px #00000066;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
  body {
    font: 1.05rem/1.5 system-ui, "Segoe UI", sans-serif;
    min-height: 100vh;
  }
  a { color: var(--ink); }
  a:hover { text-decoration-thickness: 2px; }
  :focus { outline: none; }
  :focus-visible {
    outline: 3px solid var(--focus);
    outline-offset: 3px;
  }
  .skip {
    position: absolute;
    left: 0.75rem;
    top: 0.75rem;
    background: var(--button);
    color: var(--button-ink);
    padding: 0.5rem 0.8rem;
    border-radius: 8px;
    transform: translateY(-160%);
  }
  .skip:focus { transform: none; }
  .wrap { max-width: 42rem; margin: 0 auto; padding: 1.25rem 1.15rem 3rem; }
  header.hero { padding-top: 0.4rem; }
  .brand { display: flex; align-items: center; gap: 0.7rem; margin: 0 0 1rem; }
  .brandmark { width: 36px; height: 36px; border-radius: 9px; }
  h1 { font-size: clamp(2.1rem, 8vw, 3.4rem); line-height: 1.05; letter-spacing: -0.03em; margin: 0 0 0.7rem; }
  .lede { margin: 0 0 1.25rem; font-size: 1.15rem; max-width: 36rem; }
  .download {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 3.25rem;
    padding: 0.9rem 1.2rem;
    border-radius: 14px;
    background: var(--button);
    color: var(--button-ink);
    text-decoration: none;
    font-weight: 700;
    font-size: 1.2rem;
    box-shadow: var(--shadow);
  }
  .os { color: var(--muted); margin: 0.85rem 0 0; font-size: 0.95rem; }
  .countline { color: var(--muted); margin: 0.35rem 0 0; font-size: 0.95rem; }
  section { margin-top: 2rem; }
  h2 { font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 0.75rem; color: var(--muted); font-weight: 700; }
  .features { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.7rem; }
  .features li {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 0.9rem 1rem;
  }
  .features h3 { margin: 0 0 0.2rem; font-size: 1.05rem; }
  .features p { margin: 0; color: var(--muted); }
  figure { margin: 0; }
  figure img { width: 100%; height: auto; border-radius: 16px; border: 1px solid var(--line); display: block; background: var(--card); }
  figcaption { color: var(--muted); font-size: 0.92rem; margin-top: 0.55rem; }
  details { margin-top: 1rem; }
  summary { cursor: pointer; min-height: 2.75rem; display: flex; align-items: center; }
  pre {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    overflow: auto;
    font-size: 0.82rem;
  }
  .copy {
    margin-top: 0.4rem;
    min-height: 2.75rem;
    padding: 0.55rem 0.9rem;
    border-radius: 10px;
    border: 1px solid var(--line);
    background: var(--card);
    color: var(--ink);
    font: inherit;
    cursor: pointer;
  }
  .breakdown { padding-left: 1.1rem; color: var(--muted); }
  .breakdown code { color: var(--ink); }
  footer { margin-top: 2.4rem; color: var(--muted); font-size: 0.92rem; }
  footer p { margin: 0.25rem 0; }
  @media (min-width: 800px) {
    .wrap { padding-top: 2.4rem; }
    .download { width: auto; min-width: 16rem; }
    .features { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>
  <a class="skip" href="#download">Skip to download</a>
  <div class="wrap">
    <header class="hero">
      <p class="brand"><img class="brandmark" src="/sigil.png" width="36" height="36" alt="" decoding="async"></p>
      <h1>AnonBroadcast</h1>
      <p class="lede">${escapeHtml(DESCRIPTION)}</p>
      <a class="download" id="download" href="/download?asset=${DEFAULT_ASSET}">Download</a>
      <p class="os" id="os-note">One Python package. Rendering needs Python 3.11+ and ffmpeg.</p>
      <p class="countline">${n} counted downloads on this Worker, across branches and forks.</p>
    </header>

    <section aria-labelledby="features-title">
      <h2 id="features-title">In the package</h2>
      <ul class="features">
        <li><h3>Text in</h3><p>A note, a UTF-8 file, or stdin. Up to 480 characters.</p></li>
        <li><h3>Formant voice</h3><p>A small English voice, synthesized on this computer at 16 kHz.</p></li>
        <li><h3>Desk reel</h3><p>The words appear on a paper card, then land in an MP4.</p></li>
        <li><h3>SHA-256 receipt</h3><p>A receipt file beside the MP4. Title, comment, artist, date, location, and encoder name are left out.</p></li>
      </ul>
    </section>

    <section aria-labelledby="preview-title">
      <h2 id="preview-title">Desk reel</h2>
      <figure>
        <img src="/preview.png" width="960" height="540" alt="Desk reel frame: a paper card on a desk with the note, The note stays on this desk.">
        <figcaption>A frame from the renderer for the sentence “The note stays on this desk.”</figcaption>
      </figure>
    </section>

    <section aria-labelledby="install-title">
      <h2 id="install-title">Install</h2>
      <p class="os">Download saves <code>${DEFAULT_ASSET}</code> from this Worker. The count moves on that request.</p>
      <details>
        <summary>Terminal install</summary>
        <pre id="install-cmd">${INSTALL_LINE}</pre>
        <button type="button" class="copy" id="install-btn">Copy install command</button>
      </details>
      <h2>By repo, branch, and fork</h2>
      <ul class="breakdown">${breakdownList(stats)}</ul>
      <p class="os"><a href="/stats">JSON stats</a> · <a href="/count">Count</a> · <a href="${GITHUB}">GitHub</a></p>
    </section>

    <footer>
      <p>Apache-2.0 · ${AUTHOR} · AnonBroadcast ${VERSION}</p>
      <p>No DOI is invented here.</p>
    </footer>
  </div>
  <script>
  (function () {
    var note = document.getElementById("os-note");
    var ua = navigator.userAgent || "";
    var os = "this computer";
    if (/Windows/i.test(ua)) os = "Windows";
    else if (/Mac OS X|Macintosh/i.test(ua)) os = "macOS";
    else if (/Android/i.test(ua)) os = "Android";
    else if (/iPhone|iPad/i.test(ua)) os = "iOS";
    else if (/Linux/i.test(ua)) os = "Linux";
    if (note) {
      note.textContent = "This browser is " + os + ". The download is the same Python package everywhere. Rendering needs Python 3.11+ and ffmpeg on the computer that makes the reel.";
    }
    var btn = document.getElementById("install-btn");
    var cmd = ${JSON.stringify(INSTALL_LINE)};
    if (btn) {
      btn.addEventListener("click", function () {
        function done(ok) { btn.textContent = ok ? "Copied" : "Select the command and copy it"; }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(cmd).then(function () { done(true); }).catch(function () { done(false); });
        } else {
          done(false);
        }
      });
    }
  })();
  </script>
</body>
</html>`;
}

export function installScript() {
  return `#!/usr/bin/env bash
# AnonBroadcast install. The curl below is the counted download.
set -euo pipefail
HOST="${HOST}"
ASSET="${DEFAULT_ASSET}"
ROOT="\${ANON_BROADCAST_HOME:-\$HOME/.local/share/anon-broadcast}"
mkdir -p "\$ROOT"
tmp="\$(mktemp -d)"
curl -fsSL -A 'Mozilla/5.0' "\${HOST}/download?asset=\${ASSET}" -o "\$tmp/\$ASSET"
tar -xzf "\$tmp/\$ASSET" -C "\$tmp"
rm -rf "\$ROOT/anon-broadcast-${VERSION}"
mv "\$tmp/anon-broadcast-${VERSION}" "\$ROOT/"
rm -rf "\$tmp"
mkdir -p "\$HOME/.local/bin"
cat > "\$HOME/.local/bin/anon-broadcast" << EOF
#!/usr/bin/env bash
export PYTHONPATH="\${ROOT}/anon-broadcast-${VERSION}\\\${PYTHONPATH:+:\\\$PYTHONPATH}"
exec python3 -m anonbroadcast "\\\$@"
EOF
chmod +x "\$HOME/.local/bin/anon-broadcast"
echo "Installed AnonBroadcast ${VERSION}."
echo "If needed, add \$HOME/.local/bin to PATH."
echo "Render: anon-broadcast render --text 'A short note.' --out communique.mp4"
echo "ffmpeg must be on PATH. The MP4 stays on this computer."
echo "Author: ${AUTHOR}."
`;
}
