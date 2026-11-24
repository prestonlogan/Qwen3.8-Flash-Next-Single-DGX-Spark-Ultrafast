# How the README demo video is made

`media/dsh-agentic-demo.mp4` and `.gif` show DeepSeek Harness running one fixed agentic coding prompt
([`prompt.txt`](prompt.txt): build a small Python inventory CLI with 6 files and 3 unit tests) on this recipe at its
default tuning (`TUNING=v1.1`), reasoning effort Xhigh. The clip plays in real time, with no speed-up.

The recording runs in a private headless Chrome that DeepSeek Harness's web UI is loaded into. It does not
open a window, move the mouse, type on the keyboard or take focus, so you can keep working while it records.

## Requirements

- The Spark is serving the recipe at the tuning you want to show. For the default:
  `TUNING=v1.1` (overlay `HIBANA_ACCEPT_DEFAULT: '3:2.0'`, `HIBANA_ACCEPT_SOFT: '0.35'`).
- The DeepSeek Harness desktop app is running on the Mac. Its web UI is at `http://127.0.0.1:3080`.
  You have picked the model **Qwen3.8 Flash Next Hibana Fast** in its composer at least once, or you pass
  `PROVIDER` (the provider tab label in the model picker, for example `DGX Spark`) so the script can pick it.
- Google Chrome, Node 22 or newer, ffmpeg, and Python 3 with Pillow.
- The default workspace has no `data.csv`, `inventory/` or `test_inventory.py`. If an earlier take left them,
  move them to the Trash; the prompt expects an empty directory.

`cdp.mjs` signs DeepSeek Harness's browser-session cookie with the local secret in `~/.dsh/.credentials.yaml`,
the same way the harness's own Chrome native host does. The secret is never printed or written anywhere.

## 1. Record

```bash
EFFORT=Xhigh node media/demo/record.mjs ~/demo-take
```

Options (environment variables): `EFFORT` (default `Low`; the current video uses `Xhigh`), `MODEL`, `PROVIDER`,
`PROMPT_FILE` (default `prompt.txt`, relative to this folder) and `MAX_MIN` (default 12: after that the script
clicks Stop so the agent does not keep running in the harness).

The script:

1. starts headless Chrome at 1280x800 CSS pixels with a device scale of 1.5, so frames are 1920x1200;
2. opens DeepSeek Harness, dismisses the preview notice, collapses the sidebar to its icon rail, checks the
   model (switching it if `PROVIDER` is set) and sets the effort;
3. keeps the thinking groups and Think rows expanded, so the reasoning text visibly streams
   (DeepSeek Harness 0.2.3 collapses them by default), and hides the Environment side card with the header's
   "Session panel" button (that is the button's text, not its aria-label);
4. starts a CDP screencast, pastes the prompt, holds it on screen for 2.5 s, and clicks Send;
5. waits until the Stop button has been gone for 15 s, then writes `frames/`, `frames.json`
   (the timestamp of each frame) and `events.json` (send time, finish time, session URL).

The take of 2026-11-24 ran 34 s and produced about 1,900 frames (about 100 MB).

## 2. Pick the clips

```bash
python3 media/demo/make_video.py sheet ~/demo-take 4      # one labelled thumbnail every 4 s
```

Open `~/demo-take/sheet-*.jpg`. Each thumbnail is labelled with the seconds since Send. Write the clips you
want into a cuts file, one `start end` pair per line in seconds since Send, or `hold <t> <seconds>` to freeze
a frame. The cuts used for the current video are in [`cuts.txt`](cuts.txt): one clip from +12.0 s to +26.6 s,
from the file writes to the tests passing, ending with the footer at 143 tok/s.

When the run completes, the page jumps back to the top of the session. End a clip before that moment
(check the last frames of the take) so the video does not end on the jump.

## 3. Cut and encode

```bash
python3 media/demo/make_video.py cut ~/demo-take media/demo/cuts.txt ~/demo-out
```

This writes `dsh-agentic-demo.mp4` (1920x1200, 30 fps, H.264) and `dsh-agentic-demo.gif` (960x600, 8 fps,
48 colours; kept under about 10 MB for the README). Watch both, then copy them over `media/dsh-agentic-demo.*`
and update the caption in the main README if the effort, tuning, prompt or harness version changed.

## Notes

- The `tok/s` in DeepSeek Harness's footer is decode speed: output tokens divided by the time from each step's
  first token to its end, summed over the steps of the session. Prefill and tool time are not counted, and
  thinking, prose and code are averaged together.
- DeepSeek Harness sends no temperature, so the model's default (1.0) applies. The bench's 132 tok/s is at
  temperature 0, so footer readings vary with the prompt and effort.
- The class names `r52wTW_title` (activity group header) and `ijfCxa_row` (Think row) in `record.mjs` come
  from the DeepSeek Harness 0.2.3 web build. A new harness version can rename them. If the thinking stays
  collapsed in a take, inspect the header button in the web UI and update the selector.
- Delete the take directory afterwards; the frames are large.
