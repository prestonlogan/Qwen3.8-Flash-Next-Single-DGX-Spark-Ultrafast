// Minimal Chrome DevTools Protocol helpers for the demo recorder (Node 22+, no dependencies).
// Launches a private headless Chrome, so recording never touches the desktop, mouse, keyboard or focus.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
export const sleep = ms => new Promise(r => setTimeout(r, ms));

export async function launch({ width, height, scale = 1, port = 9333 }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsh-demo-chrome-'));
  const proc = spawn(CHROME, [
    '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`,
    `--window-size=${width},${height}`, `--force-device-scale-factor=${scale}`, '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
    '--force-dark-mode', 'about:blank'], { stdio: 'ignore' });
  const c = await connect(port);
  const close = async () => { c.ws.close(); proc.kill(); await new Promise(r => proc.once('exit', r)); fs.rmSync(dir, { recursive: true, force: true, maxRetries: 5 }); };
  return { ...c, close };
}

// Attach to an already running Chrome (first page target).
export async function connect(port = 9333) {
  let targets;
  for (let i = 0; i < 50; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(200); }
  }
  const page = targets.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pending = new Map(); const handlers = new Map();
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
    else if (m.method && handlers.has(m.method)) handlers.get(m.method)(m.params);
  });
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  const on = (method, fn) => handlers.set(method, fn);
  const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result.value;
  return { ws, send, on, evaluate, close: () => ws.close() };
}
// DeepSeek Harness's own browser-session cookie, signed the same way its Chrome native host does
// (~/.dsh/native-host/dsh-native-host.mjs). The secret is read locally and never printed.
export function dshCookie() {
  const lines = fs.readFileSync(path.join(os.homedir(), '.dsh/.credentials.yaml'), 'utf8').split(/\r?\n/);
  const r = lines.findIndex(l => l.trimStart().startsWith('client-connection/browser-session:'));
  const ind = lines[r].length - lines[r].trimStart().length; let secret;
  for (const l of lines.slice(r + 1)) {
    if (!l.trim()) continue;
    if (l.length - l.trimStart().length <= ind) break;
    if (l.trim().startsWith('secret:')) secret = Buffer.from(l.trim().slice(7).trim().replace(/^['"]|['"]$/g, ''), 'base64url');
  }
  const authority = '127.0.0.1:3080', issuedAt = Date.now(), expiresAt = issuedAt + 24 * 3600e3;
  const body = Buffer.from(JSON.stringify({ version: 1, authority, issuedAt, expiresAt })).toString('base64url');
  const sig = crypto.createHmac('sha256', secret).update(body).digest('base64url');
  return { name: 'dsh-auth-' + crypto.createHash('sha256').update(authority).digest('base64url'), value: `v1.${body}.${sig}`,
    domain: '127.0.0.1', path: '/', httpOnly: true, expires: expiresAt / 1000 };
}
