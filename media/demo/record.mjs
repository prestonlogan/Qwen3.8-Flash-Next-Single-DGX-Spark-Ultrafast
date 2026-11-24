// Record the README demo: DeepSeek Harness running prompt.txt against the Spark, in a private headless Chrome.
// Nothing touches the desktop, mouse, keyboard or window focus. See media/demo/README.md.
//
//   node media/demo/record.mjs <out-dir>
//
// Writes <out-dir>/frames/NNNNNN.jpg (one per screencast frame, 1920x1200), <out-dir>/frames.json
// (frame timestamps) and <out-dir>/events.json (send time, finish time, session URL).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch, dshCookie, sleep } from './cdp.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(process.argv[2] || 'demo-recording');
const W = 1280, H = 800, SCALE = 1.5;            // 1920x1200 frames, the size of the original video
const EFFORT = process.env.EFFORT || 'Low';
const MODEL = process.env.MODEL || 'Qwen3.8 Flash Next Hibana Fast';
const PROVIDER = process.env.PROVIDER || '';       // model-picker tab label, needed only to switch models
const MAX_MIN = Number(process.env.MAX_MIN || 12);
const PROMPT = fs.readFileSync(path.resolve(HERE, process.env.PROMPT_FILE || 'prompt.txt'), 'utf8').trim();

fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
const log = (...a) => console.log(new Date().toLocaleTimeString('en-US', { timeZone: 'America/New_York' }), ...a);
const c = await launch({ width: W, height: H, scale: SCALE });
const ev = {};
try {
  await c.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: SCALE, mobile: false });
  await c.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'dark' }] });
  await c.send('Network.enable');
  await c.send('Network.setCookie', dshCookie());
  await c.send('Page.navigate', { url: 'http://127.0.0.1:3080/' });
  await sleep(7000);

  // Click the centre of the first visible element matching a selector (and optional exact text).
  const click = async (sel, text) => {
    const r = await c.evaluate(`(() => { const els = [...document.querySelectorAll(${JSON.stringify(sel)})]
      .filter(e => e.offsetParent && (${JSON.stringify(text ?? null)} === null || e.innerText.trim() === ${JSON.stringify(text ?? '')}));
      if (!els.length) return null; const b = els[0].getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()`);
    if (!r) return false;
    for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
      await c.send('Input.dispatchMouseEvent', { type, x: r[0], y: r[1], button: 'left', clickCount: 1 });
    await sleep(900);
    return true;
  };
  const labels = () => c.evaluate(`[...document.querySelectorAll('button')].map(b => (b.getAttribute('aria-label') || b.innerText).trim())`);

  // Setup: dismiss the preview notice, collapse the sidebar to its icon rail, pick the model and effort.
  await click('button', 'Continue');
  await click('button[aria-label^="Collapse sidebar"]');
  if (await c.evaluate(`!![...document.querySelectorAll('*')].find(e => e.offsetParent && e.innerText?.trim() === 'Workspaces')`)) {
    await click('[data-sidebar-toggle]');
  }
  const current = () => c.evaluate(`[...document.querySelectorAll('button')].map(b => b.getAttribute('aria-label') || '')
    .find(t => t.startsWith('Select model'))`);
  if (!(await current()).startsWith(`Select model, current ${MODEL}, `) && PROVIDER) {
    // Switch models in the picker: Select model -> Model -> provider tab -> model row.
    await click('button[aria-label^="Select model"]');
    await c.evaluate(`[...document.querySelectorAll('*')].filter(e => e.offsetParent && e.innerText?.trim() === 'Model').pop()?.click(); 1`);
    await sleep(900);
    await click(`[role="tab"][aria-label=${JSON.stringify(PROVIDER)}]`);
    await click(`[role="menuitemradio"][title=${JSON.stringify(MODEL)}]`);
    await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await sleep(700);
  }
  if (!(await current()).startsWith(`Select model, current ${MODEL}, `))
    throw new Error(`model ${MODEL} is not selected (${await current()}); pick it once in the app or set PROVIDER`);
  const cur = await c.evaluate(`[...document.querySelectorAll('button')].map(b => b.innerText.trim()).find(t => t.startsWith(${JSON.stringify(MODEL)}))`);
  if (!cur.endsWith(EFFORT)) {
    await c.evaluate(`[...document.querySelectorAll('button')].find(b => b.innerText.trim().startsWith(${JSON.stringify(MODEL)})).click()`);
    await sleep(700);
    await click('*', 'Effort');
    await click('[role="menuitemradio"], [role="menuitem"], [role="option"], div, button', EFFORT);
  }
  // DeepSeek Harness 0.2.3 collapses activity groups and Think rows; keep them open so the streaming text is
  // visible (the DSH 0.2.2 default, as in the first video). Class names are from the 0.2.3 build.
  const expander = `setInterval(() => {
    document.querySelectorAll('button.r52wTW_title[aria-expanded="false"], div.ijfCxa_row[aria-expanded="false"]')
      .forEach(e => e.click());
  }, 250);`;
  await c.send('Page.addScriptToEvaluateOnNewDocument', { source: expander });   // survives a full page load
  await c.evaluate(expander + ' 1');
  // The session page opens an "Environment" side card; hiding it (header "Session panel" toggle) centres the chat.
  const hidePanels = async () => {
    if (await c.evaluate(`[...document.querySelectorAll('h2')].some(e => e.offsetParent && e.textContent.trim() === 'Environment')`))
      await click('button', 'Session panel');   // "Session panel" is the button's text, not its aria-label
    const r = await c.evaluate(`(() => { const b = document.querySelector('button[aria-label="Collapse right sidebar"]');
      return b && b.getBoundingClientRect().x < innerWidth; })()`);
    if (r) await click('button[aria-label="Collapse right sidebar"]');
  };
  log('composer:', await current());

  // Screencast: every changed frame, with its timestamp.
  const frames = [];
  c.on('Page.screencastFrame', async p => {
    const n = frames.length;
    fs.writeFileSync(path.join(OUT, 'frames', String(n).padStart(6, '0') + '.jpg'), Buffer.from(p.data, 'base64'));
    frames.push(p.metadata.timestamp);
    c.send('Page.screencastFrameAck', { sessionId: p.sessionId }).catch(() => {});
  });
  await c.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: W * SCALE, maxHeight: H * SCALE, everyNthFrame: 1 });
  await sleep(1500);

  // Type the prompt (inserted at once, like a paste), hold it on screen, then send.
  await click('textarea, [contenteditable="true"]');
  await c.send('Input.insertText', { text: PROMPT });
  ev.typed = Date.now() / 1000;
  await sleep(2500);
  if (!(await click('button[aria-label="Send message"]'))) throw new Error('send button not found');
  ev.sent = Date.now() / 1000;
  log('sent');

  // Wait for the agent to finish: no Stop button for 15 s in a row.
  let idle = 0, tick = 0;
  while ((Date.now() / 1000 - ev.sent) < MAX_MIN * 60) {
    await sleep(1000); tick++;
    if (tick < 20 || tick % 10 === 0) await hidePanels();
    const L = await labels();
    const running = L.some(t => /^(stop|interrupt|cancel)/i.test(t)) || !L.includes('Send message');
    if (tick === 20) log('buttons while running:', L.filter(t => t.length < 40).slice(-12));
    idle = running ? 0 : idle + 1;
    if (tick % 30 === 0) log(`t+${tick}s running=${running} frames=${frames.length}`);
    if (tick > 30 && idle >= 15) break;
  }
  ev.finished = Date.now() / 1000 - idle;
  if (idle < 15) {   // hit MAX_MIN: stop the agent so it does not keep running in the harness after the take
    ev.stoppedAtLimit = true;
    await c.evaluate(`document.querySelector('button[aria-label="Stop generating"]')?.click(); 1`);
    log(`time limit reached (${MAX_MIN} min): stopped the agent`);
  }
  ev.url = await c.evaluate('location.href');
  await sleep(2000);
  await c.send('Page.stopScreencast');
  fs.writeFileSync(path.join(OUT, 'frames.json'), JSON.stringify(frames));
  fs.writeFileSync(path.join(OUT, 'events.json'), JSON.stringify(ev, null, 2));
  log(`done: ${frames.length} frames, run ${(ev.finished - ev.sent).toFixed(0)} s, ${ev.url}`);
} finally {
  await c.close();
}
