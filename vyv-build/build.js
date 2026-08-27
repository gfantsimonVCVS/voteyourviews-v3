#!/usr/bin/env node
/**
 * VYV precompile — turns the in-browser-Babel site into a plain-JS site.
 *
 * Why: index.html ships ~370KB of JSX that Babel Standalone compiles in the
 * visitor's browser on every load (plus a ~2.8MB babel.min.js download).
 * Precompiling moves that work to build time.
 *
 * What it does:
 *   - extracts the single <script type="text/babel"> block from index.html
 *   - compiles JSX -> JS with @babel/preset-react (same transform the browser ran)
 *   - drops the Babel Standalone CDN tag
 *   - writes the compiled page
 *
 * SOURCE OF TRUTH stays ../index.html — always edit that file. It keeps working
 * when opened directly in a browser (Babel Standalone still compiles it locally).
 *
 * Usage:
 *   node vyv-build/build.js                 -> writes vyv-build/dist/index.html (local check)
 *   node vyv-build/build.js --emit-to index.html   -> overwrites index.html (Netlify build only)
 */
const fs = require('fs');
const path = require('path');
const babel = require('@babel/core');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'index.html');

// --emit-to <relpath>: path (relative to repo root) to write the compiled page to.
// Default is a throwaway dist/ dir so a local run never touches the source.
const argIdx = process.argv.indexOf('--emit-to');
const OUT = argIdx !== -1 && process.argv[argIdx + 1]
  ? path.join(ROOT, process.argv[argIdx + 1])
  : path.join(__dirname, 'dist', 'index.html');

const html = fs.readFileSync(SRC, 'utf8');

const OPEN = '<script type="text/babel">';
const CLOSE = '</script>';
const i = html.indexOf(OPEN);
if (i === -1) throw new Error('no <script type="text/babel"> block found in index.html');
if (html.indexOf(OPEN, i + 1) !== -1) throw new Error('more than one text/babel block — build.js handles exactly one');
const j = html.indexOf(CLOSE, i);
if (j === -1) throw new Error('unterminated text/babel block');
const jsx = html.slice(i + OPEN.length, j);

const t0 = Date.now();
const out = babel.transformSync(jsx, {
  // Absolute path: Netlify runs the build from the repo root, where Babel's
  // relative preset resolution would not find vyv-build/node_modules.
  presets: [[require.resolve('@babel/preset-react'), { runtime: 'classic' }]],
  cwd: __dirname,
  compact: false,          // keep output inspectable; line numbers shift but code is readable
  babelrc: false, configFile: false,
  filename: 'index.html.jsx',
});
console.log(`compiled ${(jsx.length / 1024).toFixed(0)}KB JSX in ${Date.now() - t0}ms -> ${(out.code.length / 1024).toFixed(0)}KB JS`);

let compiled = html.slice(0, i) + '<script>\n' + out.code + '\n' + html.slice(j);

// Remove the now-unneeded Babel Standalone tag.
const babelTag = /[ \t]*<script src="https:\/\/unpkg\.com\/@babel\/standalone[^"]*"><\/script>\n?/;
if (!babelTag.test(compiled)) throw new Error('Babel Standalone tag not found — did the CDN URL change?');
compiled = compiled.replace(babelTag, '  <!-- Babel Standalone removed: JSX is precompiled at build time (vyv-build/build.js) -->\n');

// Sanity gates — never emit a page that would break in production.
if (/babel\/standalone/.test(compiled)) throw new Error('FAIL: Babel Standalone still referenced');
if (/type="text\/babel"/.test(compiled)) throw new Error('FAIL: uncompiled JSX block still present');
new Function(out.code); // throws on a syntax error in the compiled JS

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, compiled);
console.log(`wrote ${OUT} (${(compiled.length / 1024).toFixed(0)}KB, was ${(html.length / 1024).toFixed(0)}KB)`);
