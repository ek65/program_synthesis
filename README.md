# program_synthesis

Synthesize executable **Scenic** programs and **finite-state machines (FSMs)** for
soccer tactical scenarios from *narrated demonstrations* (short videos with language
annotations), then (optionally) run / visualize them in the companion **TacticalMR**
Unity project.

```
narrated demo (video + annotations)
        │   v2/auto_synthesis.py
        ▼
Scenic program  ──►  v2/auto_fsm.py  ──►  FSM (JSON)  ──►  Unity (TacticalMR, optional)
        ▲                                                        │
        └──────────────  v2/auto_feedback.py  ◄──── new narrated demo (press "B")
```

> **Runs standalone.** A small example demonstration is bundled so you can verify the
> synthesis pipeline end-to-end **without installing TacticalMR or Unity** — see
> [§3 Quick test](#3-quick-test-standalone-no-tacticalmr).

> The synthesis/translation layer understands **soccer** annotations (passes, receptions,
> shots, etc.). Demonstrations from other domains (e.g. factory/"Packaging" tasks) are
> **not** supported.

---

## 1. Prerequisites

- **conda** (Miniconda/Anaconda). Tested on macOS (Apple Silicon & Intel), Python 3.11.
- **OpenAI API key** (synthesis uses `gpt-5` / `gpt-5-mini` by default). A **Gemini API
  key** is also imported by some utility modules (only needed for the optional Gemini
  code paths, but the name must be defined).
- **(Optional) TacticalMR** — the Unity project + Scenic runtime, a *separate* repo.
  Only needed to **visualize** FSMs in Unity and to **record new feedback
  demonstrations**. It is **not** required for synthesis, FSM-JSON generation, or the
  quick test below.

---

## 2. Setup

### 2.1 Create the conda environment

```bash
conda env create -f environment.yml      # creates an env named "tacticalmr"
conda activate tacticalmr
```

If you already created the environment, just `conda activate tacticalmr`.

### 2.2 Configure API keys

Copy the template to `v2/apiKey.py` and paste in your keys:

```bash
cp v2/apiKey.template.py v2/apiKey.py
# then edit v2/apiKey.py
```

```python
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"   # https://platform.openai.com/api-keys
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"   # https://aistudio.google.com/app/apikey
```

`v2/apiKey.py` is **git-ignored**, so your real keys are never committed.

---

## 3. Quick test (standalone, no TacticalMR)

The repo bundles a small example (`v2/data/_NARRATED_DEMOS/example/`, two soccer demos
with video) so you can confirm everything is wired up:

```bash
conda activate tacticalmr
python v2/auto_synthesis.py example
```

What to expect:
- it loads the 2 example demonstrations, samples video frames, calls OpenAI, and runs a
  syntax-check pass;
- it writes `v2/data/_SYNTHESIZED_PROGRAM/example/distribute-example-openai.scenic`;
- it prints a line like `Note: TACTICAL_MR_DIR ('/path/to/TacticalMR') not found —
  skipping copy to the Unity project.` **This is expected** when running without
  TacticalMR;
- it ends with `Synthesis completed successfully!`.

You can also generate the FSM JSON locally (no Unity needed) — it is saved under
`v2/data/_FSM/example/`:

```bash
python v2/auto_fsm.py example
```

> These make real, billable OpenAI calls (a synthesis run is ~100k tokens on `gpt-5`).

---

## 4. Paths / environment variables (for the full TacticalMR + Unity workflow)

Paths are read from environment variables with sensible defaults. For the standalone
quick test you don't need to set anything. For Unity integration, set `TACTICAL_MR_DIR`:

```bash
export TACTICAL_MR_DIR=/path/to/TacticalMR
```

| Variable             | Needed when…                         | Default                                                | Used for |
|----------------------|--------------------------------------|--------------------------------------------------------|----------|
| `TACTICAL_MR_DIR`    | using Unity / TacticalMR             | `/path/to/TacticalMR` (placeholder)                    | Copying programs / FSMs into Unity; reading scenario "suffix" files (falls back to the bundled `v2/scenic_suffix/` when unset) |
| `DATA_BASE_PATH`     | never (auto-detected)                | `<repo>/v2/data`                                       | Where demonstrations, programs, and FSMs live |
| `UNITY_FSM_PATH`     | optional override                    | `$TACTICAL_MR_DIR/UnityProject/Assets/Resources/_FSM`  | Where `auto_fsm.py` copies `fsm.json` for Unity |
| `TACTICAL_MR_OUTPUT` | using the feedback workflows         | `$TACTICAL_MR_DIR/output/participant0/Test`            | Where `auto_feedback.py` pulls the latest recorded demonstration |

When `TACTICAL_MR_DIR` is not a real directory, the Unity copy steps are **skipped with a
note** and synthesis uses the bundled scene-suffix templates — so the pipeline still runs.

---

## 5. Demonstration data

Synthesis reads demonstrations from:

```
v2/data/_NARRATED_DEMOS/<pilot>/<data-folder>/demonstration<N>/
    ├── json_segments/   *.json      # annotated segment(s)
    └── videos/          *.mp4        # demonstration video(s)
```

- `<pilot>` is the top-level argument you pass (e.g. `example`, `pilot0`).
- `<data-folder>` must contain a **scenario keyword** — one of `check`, `overlap`,
  `distribute` (e.g. `distribute-pilot18`, or the bundled `example-distribute`); the
  scenario is detected from this name.
- Each `demonstration<N>` needs **both** a `json_segments/*.json` and a `videos/*.mp4`;
  folders without a video are skipped.

**Bundled example:** `example/example-distribute/` ships with two demos (videos
included) so the quick test works out of the box. Note that demonstration videos
(`*.mp4`) are otherwise git-ignored, so for your own pilots you supply the data locally.

**Recording your own:** demonstrations are produced in the TacticalMR Unity app and land
under `TACTICAL_MR_OUTPUT` (default `TacticalMR/output/participant0/Test`). To synthesize
a new pilot, create `v2/data/_NARRATED_DEMOS/<pilot>/<scenario>-<pilot>/` and copy the
relevant `demonstration<N>` folders into it.

---

## 6. The pipeline in detail

### 6.1 Initial synthesis — `auto_synthesis.py`

```bash
python v2/auto_synthesis.py <pilot>
```

Loads the demonstrations, samples video frames, prompts the LLM (`gpt-5`) to produce a
Scenic program, and runs an automatic syntax-check/repair pass. Output:
`v2/data/_SYNTHESIZED_PROGRAM/<pilot>/<scenario>-<pilot>-openai.scenic` (and, if
`TACTICAL_MR_DIR` is set, copied into TacticalMR as `synthesized_program.scenic`).

### 6.2 Generate & view the FSM — `auto_fsm.py`

```bash
python v2/auto_fsm.py <pilot>
```

Converts the latest synthesized program into an FSM JSON
(`v2/data/_FSM/<pilot>/...-fsm0.json`). If `TACTICAL_MR_DIR` is set it also copies it to
`$UNITY_FSM_PATH/fsm.json`.

**View in Unity (requires TacticalMR):** open `Scenes/zmq_demo_controller.unity`, and in
the Hierarchy enable the **`Canvas`** object to display the FSM.

### 6.3 Provide feedback (requires TacticalMR/Unity, optional)

In Unity, press **`B`** to start recording a feedback demonstration and **`B`** again to
stop. This creates a new narrated demonstration under `TACTICAL_MR_OUTPUT`.

### 6.4 Generate new programs after feedback — `auto_feedback.py`

```bash
python v2/auto_feedback.py <pilot> --fsm        # after FSM feedback
python v2/auto_feedback.py <pilot> --feedback   # after program feedback
```

Both modes automatically pull the latest demonstration from `TACTICAL_MR_OUTPUT`, combine
it with the existing program/FSM as context, synthesize an updated program (with a
syntax-check pass), and copy the result back into Unity.

---

## 7. Troubleshooting

- **`No data subfolder found in .../<pilot>`** — the pilot folder has no data subfolder
  (with a scenario keyword) containing a `demonstration<N>/videos/*.mp4`. Synthesis
  requires demonstration **videos**.
- **`This ANNOTATION type (X) is not handled yet`** — the demonstration uses annotations
  from an unsupported domain. Supported (soccer) annotations include `Pass`,
  `ReceiveBall`, `Through Pass`, `Shoot Goal`, `Point`, `TriggerPass`, `PauseAction`,
  `Reference`, `Intercept`, `Pick Up`, `Put Down`. (Factory/`Packaging` demos are not
  supported.)
- **`Note: TACTICAL_MR_DIR ... not found — skipping copy to the Unity project`** — this is
  expected when running standalone; set `TACTICAL_MR_DIR` to enable Unity integration.
- **`TacticalMR output directory does not exist`** (feedback) — set `TACTICAL_MR_DIR`
  (or `TACTICAL_MR_OUTPUT`) to a folder that contains `demonstration<N>` folders.
- **Model / cost** — the default model is `gpt-5` (`OPENAI_MODEL` near the top of
  `auto_synthesis.py` / `auto_feedback.py`). Each synthesis/feedback run makes real,
  billable API calls.

---

## License

Released under the [MIT License](LICENSE).
