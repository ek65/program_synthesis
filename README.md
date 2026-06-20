# narrated_demo

Synthesize executable **Scenic** programs and **finite-state machines (FSMs)** for
soccer tactical scenarios from *narrated demonstrations* (short videos with language
annotations), then run / visualize them in the companion **TacticalMR** Unity project.

The pipeline is:

```
narrated demo (video + annotations)
        │   v2/auto_synthesis.py
        ▼
Scenic program  ──►  v2/auto_fsm.py  ──►  FSM (JSON)  ──►  Unity (TacticalMR)
        ▲                                                        │
        └──────────────  v2/auto_feedback.py  ◄──── new narrated demo (press "B")
```

> This is the `soccer-vr` line of work. The synthesis/translation layer understands
> **soccer** annotations (passes, receptions, shots, etc.). Demonstrations from other
> domains (e.g. factory/"Packaging" tasks) are **not** supported on this branch.

---

## 1. Prerequisites

- **conda** (Miniconda/Anaconda). Tested on macOS (Apple Silicon & Intel), Python 3.11.
- **OpenAI API key** (synthesis uses `gpt-5` / `gpt-5-mini` by default) and a **Gemini
  API key** (imported by some utilities).
- **The TacticalMR repository** (the Unity project + Scenic runtime) checked out locally.
  It is a separate repo and is **not** vendored here. The pipeline reads helper files
  from it and writes its outputs into it.
- **Demonstration data** (video + JSON). ⚠️ Demonstration **videos (`*.mp4`) are
  git-ignored and are NOT shipped in this repo** — see [§4](#4-demonstration-data).

---

## 2. Setup

### 2.1 Create the conda environment

```bash
conda env create -f environment.yml      # creates an env named "tacticalmr"
conda activate tacticalmr
```

If you already created the environment, just `conda activate tacticalmr`.

### 2.2 Configure API keys

Create **`v2/apiKey.py`** (this file is git-ignored — never commit real keys):

```python
OPENAI_API_KEY = 'YOUR_OPENAI_KEY'
GEMINI_API_KEY = 'YOUR_GEMINI_KEY'
```

### 2.3 Configure paths (environment variables)

Paths are read from environment variables with sensible defaults, so in most cases you
only need to set **one**: the location of your local TacticalMR checkout.

```bash
export TACTICAL_MR_DIR=/path/to/TacticalMR
```

| Variable             | Required | Default                                                      | Used for |
|----------------------|----------|--------------------------------------------------------------|----------|
| `TACTICAL_MR_DIR`    | yes      | `/path/to/TacticalMR` (placeholder)                          | Copying synthesized programs / FSMs into Unity; reading scenario "suffix" files |
| `DATA_BASE_PATH`     | no       | `<repo>/v2/data` (auto-detected)                             | Where demonstrations, programs, and FSMs live |
| `UNITY_FSM_PATH`     | no       | `$TACTICAL_MR_DIR/UnityProject/Assets/Resources/_FSM`        | Where `auto_fsm.py` copies `fsm.json` for Unity |
| `TACTICAL_MR_OUTPUT` | no       | `$TACTICAL_MR_DIR/output/participant0/Test`                  | Where `auto_feedback.py` pulls the latest recorded demonstration |

> Tip: add the `export` lines to your shell profile, or prefix each command,
> e.g. `TACTICAL_MR_DIR=/path/to/TacticalMR python v2/auto_synthesis.py pilot0`.

---

## 3. Quick start

```bash
conda activate tacticalmr
export TACTICAL_MR_DIR=/path/to/TacticalMR

python v2/auto_synthesis.py pilot0      # 1. demos  -> Scenic program
python v2/auto_fsm.py        pilot0      # 2. program -> FSM (JSON) -> Unity
# 3. open the scene in Unity to view the FSM (see §5.2)
python v2/auto_feedback.py   pilot0 --fsm        # 4a. new program after FSM feedback
python v2/auto_feedback.py   pilot0 --feedback   # 4b. new program after program feedback
```

The argument (`pilot0`) is the name of a folder under
`v2/data/_NARRATED_DEMOS/`. It may be any `pilot<N>` or `participant<N>`.

---

## 4. Demonstration data

Synthesis reads demonstrations from:

```
v2/data/_NARRATED_DEMOS/<pilot>/<scenario>-<pilot>/demonstration<N>/
    ├── json_segments/   *.json      # annotated segment(s)
    └── videos/          *.mp4        # demonstration video(s)  ← git-ignored, not shipped
```

- `<pilot>` is the top-level argument you pass (e.g. `pilot0`).
- `<scenario>` must be one of: **`check`**, **`overlap`**, **`distribute`**
  (the scenario type is detected from this folder name).
- Each `demonstration<N>` folder needs **both** a `json_segments/*.json` and a
  `videos/*.mp4`; folders without a video are skipped.

**Where the data comes from:** demonstrations are recorded in the TacticalMR Unity app
and land under `TACTICAL_MR_OUTPUT` (default `TacticalMR/output/participant0/Test`).
To synthesize a new pilot, create `v2/data/_NARRATED_DEMOS/<pilot>/<scenario>-<pilot>/`
and copy the relevant `demonstration<N>` folders into it.

> Because `*.mp4` files are git-ignored, a fresh clone will not contain demonstration
> videos. `pilot0` ships with sample JSON segments and a pre-synthesized program/FSM so
> you can try `auto_fsm.py` and the Unity step immediately, but to run **`auto_synthesis.py`
> yourself you must add demonstration data (with videos)** as described above.

---

## 5. The pipeline in detail

### 5.1 Initial synthesis — `auto_synthesis.py`

```bash
python v2/auto_synthesis.py pilot0
```

- Loads the demonstrations, samples video frames, and prompts the LLM (`gpt-5`) to
  produce a Scenic program, then runs an automatic syntax-check/repair pass.
- Output: `v2/data/_SYNTHESIZED_PROGRAM/<pilot>/<scenario>-<pilot>-openai.scenic`
  (also copied into TacticalMR as
  `Scenic-main/examples/unity/_SYNTHESIZED_PROGRAM/synthesized_program.scenic`).

### 5.2 Generate & view the FSM — `auto_fsm.py`

```bash
python v2/auto_fsm.py pilot0
```

- Converts the latest synthesized Scenic program into an FSM JSON
  (`v2/data/_FSM/<pilot>/...-fsm0.json`) and copies it to Unity as
  `$UNITY_FSM_PATH/fsm.json`.
- **View in Unity:** open `Scenes/zmq_demo_controller.unity`, and in the Hierarchy make
  sure the **`Canvas`** object is enabled to display the FSM.

### 5.3 Provide feedback (optional)

In Unity, press **`B`** to start recording a feedback demonstration and **`B`** again to
stop. This creates a new narrated demonstration under `TACTICAL_MR_OUTPUT`.

### 5.4 Generate new programs after feedback — `auto_feedback.py`

```bash
# After FSM feedback:
python v2/auto_feedback.py pilot0 --fsm

# After program feedback:
python v2/auto_feedback.py pilot0 --feedback
```

Both modes automatically pull the latest demonstration from `TACTICAL_MR_OUTPUT`
(you do **not** need to move demonstration data manually), combine it with the existing
program/FSM as context, and synthesize an updated program (with a syntax-check pass),
copying the result back into Unity.

---

## 6. Troubleshooting

- **`No data subfolder found in .../<pilot>`** — the pilot folder has no
  `<scenario>-<pilot>` subfolder containing a `demonstration<N>/videos/*.mp4`.
  Synthesis requires demonstration **videos**; add them (see [§4](#4-demonstration-data)).
- **`This ANNOTATION type (X) is not handled yet`** — the demonstration uses annotations
  from an unsupported domain. This branch handles **soccer** annotations
  (`Pass`, `ReceiveBall`, `Through Pass`, `Shoot Goal`, `Point`, `TriggerPass`,
  `PauseAction`, `Reference`, `Intercept`, `Pick Up`, `Put Down`, …). Use soccer
  demonstration data (e.g. factory/`Packaging` demos are not supported here).
- **`TacticalMR output directory does not exist`** (feedback) — set `TACTICAL_MR_DIR`
  (or `TACTICAL_MR_OUTPUT`) to a folder that contains `demonstration<N>` folders.
- **Model / cost** — the default model is `gpt-5` (`OPENAI_MODEL` near the top of
  `auto_synthesis.py` / `auto_feedback.py`). Each synthesis/feedback run makes real,
  billable API calls.
