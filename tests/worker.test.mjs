import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import worker from "../workers/download-tracker/src/index.js";
import { DEFAULT_ASSET } from "../workers/download-tracker/src/home.js";

class MemoryKv {
  constructor() {
    this.map = new Map();
  }
  async get(key) {
    return this.map.has(key) ? this.map.get(key) : null;
  }
  async put(key, value) {
    this.map.set(key, String(value));
  }
  async list(opts = {}) {
    const keys = [...this.map.keys()].map((name) => ({ name }));
    return { keys, list_complete: true, cursor: opts.cursor };
  }
}

function envWith(bytes) {
  return {
    DOWNLOADS: new MemoryKv(),
    ASSETS: {
      async fetch(request) {
        const name = new URL(request.url).pathname.slice(1);
        if (name !== DEFAULT_ASSET) return new Response("missing", { status: 404 });
        return new Response(bytes, { headers: { "Content-Length": String(bytes.length) } });
      },
    },
  };
}

test("landing, counted download, and fork breakdown", async () => {
  const bytes = await readFile(new URL("../workers/download-tracker/public/" + DEFAULT_ASSET, import.meta.url));
  assert.equal(bytes[0], 0x1f);
  assert.equal(bytes[1], 0x8b);
  const env = envWith(bytes);

  const home = await worker.fetch(new Request("https://tracker.test/", { headers: { "User-Agent": "Mozilla/5.0" } }), env);
  assert.equal(home.status, 200);
  const html = await home.text();
  assert.match(html, /AnonBroadcast/);
  assert.match(html, /href="\/download\?asset=anon-broadcast-0\.1\.0\.tar\.gz"/);
  assert.match(html, /prefers-color-scheme: dark/);
  assert.match(html, /:focus-visible/);
  assert.doesNotMatch(html, /THIS IS NOT/);

  const download = await worker.fetch(
    new Request("https://tracker.test/download?asset=" + DEFAULT_ASSET, { headers: { "User-Agent": "Mozilla/5.0" } }),
    env,
  );
  assert.equal(download.status, 200);
  assert.match(download.headers.get("Content-Type"), /gzip/);
  const body = new Uint8Array(await download.arrayBuffer());
  assert.equal(body[0], 0x1f);
  assert.equal(body[1], 0x8b);

  const fork = await worker.fetch(
    new Request("https://tracker.test/download?owner=someone&repo=anon-broadcast&branch=dev", {
      headers: { "User-Agent": "Mozilla/5.0" },
    }),
    env,
  );
  assert.equal(fork.status, 200);
  await fork.arrayBuffer();

  const event = await worker.fetch(
    new Request("https://tracker.test/event", {
      method: "POST",
      headers: { "Content-Type": "application/json", "User-Agent": "Mozilla/5.0" },
      body: JSON.stringify({ owner: "Ada", repo: "anon-broadcast", branch: "feature", fork: "1", asset: DEFAULT_ASSET }),
    }),
    env,
  );
  assert.equal(event.status, 200);

  const count = await worker.fetch(new Request("https://tracker.test/count"), env);
  const countBody = await count.json();
  assert.equal(countBody.project, "anon-broadcast");
  assert.equal(countBody.downloads, 3);
  assert.equal(countBody.total, 3);
  assert.equal(countBody.downloads, countBody.downloads_human + countBody.downloads_bot);
  assert.equal(countBody.views, countBody.views_human + countBody.views_bot);

  const stats = await worker.fetch(new Request("https://tracker.test/stats"), env);
  const statsBody = await stats.json();
  assert.equal(statsBody.by_branch.main, 1);
  assert.equal(statsBody.by_branch.dev, 1);
  assert.equal(statsBody.by_branch.feature, 1);
  assert.equal(statsBody.by_fork["1"], 2);
  assert.ok(statsBody.by_repo["someone/anon-broadcast"]);
  assert.ok(statsBody.by_repo["Ada/anon-broadcast"]);

  const missing = await worker.fetch(new Request("https://tracker.test/download?asset=missing.bin"), env);
  assert.equal(missing.status, 404);
  const after = await (await worker.fetch(new Request("https://tracker.test/count"), env)).json();
  assert.equal(after.downloads, 3);
});
