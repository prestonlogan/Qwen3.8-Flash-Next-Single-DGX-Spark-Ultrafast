#!/usr/bin/env python3
"""Cut a record.mjs recording into the README demo (MP4 + GIF). Needs ffmpeg. See media/demo/README.md.

  # 1. Contact sheet: one thumbnail every STEP seconds, labelled with seconds since the prompt was sent.
  python3 media/demo/make_video.py sheet <rec-dir> [STEP]          -> <rec-dir>/sheet-*.jpg

  # 2. Pick real-time segments (seconds since send; negative = before send) in a cuts file, one per line:
  #      -3.5 4      # prompt typed, send, first thinking tokens
  #      212 218     # file write streaming
  #      hold 218 3  # freeze the frame at 218 s for 3 s
  python3 media/demo/make_video.py cut <rec-dir> <cuts.txt> <out-dir>  -> dsh-agentic-demo.mp4 / .gif

Each segment plays at real speed (no speed-up); segments are joined with hard jump cuts.
"""
import json
import subprocess
import sys
from pathlib import Path

FPS, GIF_FPS = 30, 8


def load(rec: Path):
    ts = json.loads((rec / 'frames.json').read_text())
    ev = json.loads((rec / 'events.json').read_text())
    return ts, ev


def frame_at(ts: list, t: float) -> int:
    """Index of the last screencast frame shown at time t (frames arrive only when the page changes)."""
    lo, hi = 0, len(ts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ts[mid] <= t:
            lo = mid
        else:
            hi = mid - 1
    return lo


def sheet(rec: Path, step: float) -> None:
    from PIL import Image, ImageDraw  # Pillow; only the contact sheet needs it
    ts, ev = load(rec)
    t0, t1 = ev['sent'], min(ev.get('finished', ts[-1]) + 3, ts[-1])
    times = []
    t = max(ts[0], t0 - 5)
    while t < t1:
        times.append(t)
        t += step
    for p in rec.glob('sheet-*.jpg'):
        p.unlink()
    for s in range(0, len(times), 16):
        page = Image.new('RGB', (4 * 480, 4 * 300))
        for k, t in enumerate(times[s:s + 16]):
            im = Image.open(rec / 'frames' / f'{frame_at(ts, t):06d}.jpg').resize((480, 300))
            ImageDraw.Draw(im).text((6, 4), f'{t - t0:+.1f}s', fill='yellow', font_size=26)
            page.paste(im, ((k % 4) * 480, (k // 4) * 300))
        page.save(rec / f'sheet-{s // 16:02d}.jpg', quality=85)
    print(f'{len(times)} thumbnails -> {rec}/sheet-*.jpg')


def cut(rec: Path, cuts_file: Path, out: Path) -> None:
    ts, ev = load(rec)
    segs = []
    for line in cuts_file.read_text().splitlines():
        line = line.split('#')[0].strip()
        if line.startswith('hold'):               # hold <t> <seconds>: freeze the frame at t
            _, t, d = line.split()[:3]
            segs.append(('hold', float(t), float(d)))
        elif line:
            a, b = map(float, line.split()[:2])
            segs.append((a, b))
    out.mkdir(parents=True, exist_ok=True)
    lst = out / 'concat.txt'
    with lst.open('w') as f:
        for seg in segs:
            if seg[0] == 'hold':
                times = [seg[1]] * round(seg[2] * FPS)
            else:
                times = [seg[0] + k / FPS for k in range(round((seg[1] - seg[0]) * FPS))]
            for t in times:
                i = frame_at(ts, ev['sent'] + t)
                f.write(f"file '{(rec / 'frames' / f'{i:06d}.jpg').resolve()}'\nduration {1 / FPS:.6f}\n")
    mp4, gif = out / 'dsh-agentic-demo.mp4', out / 'dsh-agentic-demo.gif'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst),
                    '-vf', f'fps={FPS},scale=1920:1200,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow',
                    '-crf', '24', '-movflags', '+faststart', str(mp4)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-filter_complex',
                    f'fps={GIF_FPS},scale=960:600:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=diff[p];'
                    '[b][p]paletteuse=dither=none:diff_mode=rectangle', str(gif)], check=True)
    total = sum(s[2] if s[0] == 'hold' else s[1] - s[0] for s in segs)
    print(f'{len(segs)} segments, {total:.1f} s -> {mp4} ({mp4.stat().st_size / 1e6:.1f} MB), '
          f'{gif} ({gif.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'sheet':
        sheet(Path(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif len(sys.argv) == 5 and sys.argv[1] == 'cut':
        cut(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        sys.exit(__doc__)
