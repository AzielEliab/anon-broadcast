import { handleSeoRoutes, installScript, renderHome, DEFAULT_ASSET } from "./home.js";
import { classifyRequest, readBotManagement } from "./classify.js";
import {
  isolatedKeys,
  isReservedCounterKey,
  shapeCountBody,
  shapeHumanBotFields,
} from "./stats-shape.js";

/**
 * AnonBroadcast download tracker.
 *
 * GET  /download increments KV and serves the gzip package (no 302).
 * GET  /count and /stats do not increment.
 * POST /event records a download for a branch or fork.
 *
 * Isolated: Worker anon-broadcast-download-tracker, KV binding DOWNLOADS.
 * Create namespace ANON_BROADCAST_DOWNLOADS at deploy. Do not reuse another
 * product's KV id.
 *
 * Author: Aziel Eliab only.
 */

const PROJECT = "anon-broadcast";
const KEYS = isolatedKeys(PROJECT);
const DEFAULT_OWNER = "AzielEliab";
const DEFAULT_REPO = "anon-broadcast";
const DEFAULT_BRANCH = "main";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, User-Agent",
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}

function splitOwnerRepo(value, fallbackOwner, fallbackRepo) {
  if (typeof value === "string" && value.includes("/")) {
    const [o, r] = value.split("/").filter(Boolean);
    if (o && r) return { owner: o, repo: r };
  }
  return { owner: fallbackOwner, repo: fallbackRepo };
}

function parseDims(src) {
  const get = (k) => {
    if (src == null) return null;
    if (typeof src.get === "function") {
      const v = src.get(k);
      return v == null || v === "" ? null : v;
    }
    const v = src[k];
    return v == null || v === "" ? null : v;
  };

  let owner = get("owner") || DEFAULT_OWNER;
  let repo = get("repo") || DEFAULT_REPO;
  if (typeof repo === "string" && repo.includes("/")) {
    const split = splitOwnerRepo(repo, owner, DEFAULT_REPO);
    owner = split.owner;
    repo = split.repo;
  }

  const branch = get("branch") || DEFAULT_BRANCH;
  const tag = get("tag") || "latest";
  const asset = get("asset") || "";

  const forkRaw = get("fork");
  let fork = "0";
  if (forkRaw === 1 || forkRaw === true || forkRaw === "1" || forkRaw === "true") {
    fork = "1";
  } else if (typeof forkRaw === "string" && forkRaw.includes("/")) {
    const split = splitOwnerRepo(forkRaw, owner, repo);
    owner = split.owner;
    repo = split.repo;
    fork = "1";
  } else if (forkRaw != null && forkRaw !== 0 && forkRaw !== false && forkRaw !== "0" && forkRaw !== "false") {
    fork = "1";
  }

  if (`${owner}/${repo}`.toLowerCase() !== `${DEFAULT_OWNER}/${DEFAULT_REPO}`.toLowerCase()) {
    fork = "1";
  }

  return { project: PROJECT, owner, repo, branch, fork, tag, asset };
}

function kvKey(dims) {
  return `${dims.project}|${dims.owner}|${dims.repo}|${dims.branch}|${dims.fork}`;
}

function viewsKey() {
  return PROJECT + "|__views__";
}

function totalKey() {
  return PROJECT + "|__total__";
}

function safeAssetName(name) {
  if (typeof name !== "string" || !/^[A-Za-z0-9._-]+$/.test(name)) return null;
  if (name !== DEFAULT_ASSET) return null;
  return name;
}

async function bump(env, key) {
  const n = parseInt((await env.DOWNLOADS.get(key)) || "0", 10) + 1;
  await env.DOWNLOADS.put(key, String(n));
  return n;
}

async function incrementSplit(env, humanKey, botKey, request) {
  const cls = classifyRequest(request);
  const splitKey = cls.bucket === "human" ? humanKey : botKey;
  await bump(env, splitKey);
  return cls;
}

async function increment(env, dims, request) {
  if (!env.DOWNLOADS) return 0;
  const key = kvKey(dims);
  const n = parseInt((await env.DOWNLOADS.get(key)) || "0", 10) + 1;
  await env.DOWNLOADS.put(key, String(n));
  const tot = parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10) + 1;
  await env.DOWNLOADS.put(totalKey(), String(tot));
  if (request) await incrementSplit(env, KEYS.downloads_human, KEYS.downloads_bot, request);
  return tot;
}

async function incrementViews(env, request) {
  if (!env.DOWNLOADS) return 0;
  const n = parseInt((await env.DOWNLOADS.get(viewsKey())) || "0", 10) + 1;
  await env.DOWNLOADS.put(viewsKey(), String(n));
  if (request) await incrementSplit(env, KEYS.views_human, KEYS.views_bot, request);
  return n;
}

async function listAllKeys(env) {
  if (!env.DOWNLOADS) return [];
  const keys = [];
  let cursor;
  do {
    const page = await env.DOWNLOADS.list(cursor ? { cursor } : {});
    keys.push(...page.keys);
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return keys;
}

async function collectStats(env, request) {
  const keys = await listAllKeys(env);
  let summed = 0;
  const by_repo = {};
  const by_branch = {};
  const by_fork = { "0": 0, "1": 0 };
  const breakdown = [];

  for (const k of keys) {
    const name = k.name;
    if (isReservedCounterKey(name, PROJECT)) continue;
    const n = parseInt((await env.DOWNLOADS.get(name)) || "0", 10);
    if (!Number.isFinite(n) || n <= 0) continue;
    const parts = name.split("|");
    if (parts.length < 5) continue;
    const [project, owner, repo, branch, fork] = parts;
    summed += n;
    const repoId = `${owner}/${repo}`;
    by_repo[repoId] = (by_repo[repoId] || 0) + n;
    by_branch[branch] = (by_branch[branch] || 0) + n;
    const forkFlag = fork === "1" ? "1" : "0";
    by_fork[forkFlag] = (by_fork[forkFlag] || 0) + n;
    breakdown.push({ project, owner, repo, branch, fork: forkFlag, count: n });
  }

  const downloadsDirect = env.DOWNLOADS ? parseInt((await env.DOWNLOADS.get(totalKey())) || "0", 10) : 0;
  const downloads = Number.isFinite(downloadsDirect) && downloadsDirect > 0 ? downloadsDirect : summed;
  const views = env.DOWNLOADS ? parseInt((await env.DOWNLOADS.get(viewsKey())) || "0", 10) || 0 : 0;
  const __hbViewsHuman = parseInt((await env.DOWNLOADS.get(KEYS.views_human)) || "0", 10) || 0;
  const __hbDownloadsHuman = parseInt((await env.DOWNLOADS.get(KEYS.downloads_human)) || "0", 10) || 0;
  const __hbBotMgmt = request ? readBotManagement(request).available : false;

  return {
    ...shapeHumanBotFields({
      views,
      downloads,
      views_human: __hbViewsHuman,
      downloads_human: __hbDownloadsHuman,
      botManagementAvailable: __hbBotMgmt,
    }),
    project: PROJECT,
    views,
    downloads,
    total: downloads,
    by_repo,
    by_branch,
    by_fork,
    breakdown,
    note: "Isolated AnonBroadcast counter. Key layout: project|owner|repo|branch|fork. Page views are separate from downloads.",
  };
}

async function serveAsset(request, env, asset, { head = false } = {}) {
  if (!env.ASSETS) return json({ error: "assets binding missing" }, 500);
  const assetUrl = new URL("/" + asset, request.url);
  const assetRes = await env.ASSETS.fetch(new Request(assetUrl, { method: "GET" }));
  if (!assetRes.ok) return json({ error: "asset not hosted", asset, status: assetRes.status }, 404);
  const headers = new Headers();
  headers.set("Content-Type", "application/gzip");
  headers.set("Content-Disposition", 'attachment; filename="' + asset.replaceAll('"', "") + '"');
  headers.set("Cache-Control", "private, no-store");
  const len = assetRes.headers.get("Content-Length");
  if (len) headers.set("Content-Length", len);
  for (const [k, v] of Object.entries(corsHeaders())) headers.set(k, v);
  if (head) return new Response(null, { status: 200, headers });
  return new Response(assetRes.body, { status: 200, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const seo = handleSeoRoutes(request, url);
    if (seo) return seo;

    if ((url.pathname === "/install.sh" || url.pathname === "/install.sh/") && (request.method === "GET" || request.method === "HEAD")) {
      return new Response(request.method === "HEAD" ? null : installScript(), {
        status: 200,
        headers: {
          "Content-Type": "text/x-shellscript; charset=utf-8",
          "Cache-Control": "private, no-store",
          ...corsHeaders(),
        },
      });
    }

    if (url.pathname === "/" && request.method === "GET") {
      await incrementViews(env, request);
      return new Response(renderHome(await collectStats(env, request)), {
        headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "private, no-store", ...corsHeaders() },
      });
    }
    if (url.pathname === "/" && request.method === "HEAD") {
      return new Response(null, { status: 200, headers: { "Content-Type": "text/html; charset=utf-8", ...corsHeaders() } });
    }

    if (url.pathname === "/count" && request.method === "GET") {
      const stats = await collectStats(env, request);
      return json(shapeCountBody({
        project: PROJECT,
        views: stats.views || 0,
        downloads: stats.downloads || 0,
        total: stats.total || 0,
        views_human: stats.views_human,
        downloads_human: stats.downloads_human,
        botManagementAvailable: readBotManagement(request).available,
      }));
    }

    if (url.pathname === "/stats" && request.method === "GET") {
      return json(await collectStats(env, request));
    }

    if (url.pathname === "/event" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "JSON body required" }, 400);
      }
      const dims = parseDims(body || {});
      const asset = safeAssetName(dims.asset || DEFAULT_ASSET);
      if (!asset) return json({ error: "unknown asset" }, 404);
      dims.asset = asset;
      const count = await increment(env, dims, request);
      return json({
        ok: true,
        key: kvKey(dims),
        count,
        owner: dims.owner,
        repo: dims.repo,
        branch: dims.branch,
        fork: dims.fork,
        asset,
      });
    }

    if ((url.pathname === "/download" || url.pathname.startsWith("/download/") || url.pathname === "/go") && (request.method === "GET" || request.method === "HEAD")) {
      const dims = parseDims(url.searchParams);
      if (!dims.asset && url.pathname.startsWith("/download/")) {
        dims.asset = decodeURIComponent(url.pathname.slice("/download/".length));
      }
      const asset = safeAssetName(dims.asset || DEFAULT_ASSET);
      if (!asset) return json({ error: "unknown asset" }, 404);
      dims.asset = asset;
      if (request.method === "GET") await increment(env, dims, request);
      return serveAsset(request, env, asset, { head: request.method === "HEAD" });
    }

    return json({ error: "not found" }, 404);
  },
};
