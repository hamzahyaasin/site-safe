# Editable figures

Every diagram in report V8 has two editable copies here, written by
`docs/figures/make_figures.py` each time it runs:

| File | Open with | Notes |
|---|---|---|
| `*.drawio` | [diagrams.net](https://app.diagrams.net) (free, in the browser or the desktop app), or the Draw.io Integration extension in VS Code | Best for changing a diagram: every box, arrow and label is a separate shape, text sits inside its box, and arrows that end on a box are attached to it, so moving the box keeps them together. |
| `*.svg` | Figma, Inkscape, Adobe Illustrator, Affinity Designer | Vector copy with live text. Canva also takes an SVG upload, but it treats it as one picture: you can recolour it, not edit the text. |

The two screenshot figures (4.3 and 4.4) are photos, not diagrams. Their
source screenshots are in `docs/manual/`.

## Figure to file

| Figure | File |
|---|---|
| 3.1 Use Case Diagram | `fig_use_case` |
| 3.2 System Context Diagram | `fig_system_context` |
| 3.3 Three-Tier System Architecture | `fig_three_tier` |
| 3.4 Level-1 Data Flow Diagram | `fig_dfd_level1` |
| 3.5 Workforce Activity Monitoring Pipeline | `fig_activity_pipeline` |
| 3.6 Smart Vest Block Diagram | `fig_vest_block` |
| 3.7 SOS and Location Alert Flowchart | `fig_sos_flowchart` |
| 3.8 Mobile Application Screen Wireframes | `fig_mobile_wireframes` |
| 3.9 System Workflow Activity Diagram | `fig_activity_workflow` |
| 3.10 Level-0 Data Flow Diagram | `fig_dfd_level0` |
| 4.1 PPE Model Training and Evaluation Pipeline | `fig_training_pipeline` |
| 4.2 Entity Relationship Diagram | `fig_erd` |
| 4.5 Component View | `fig_component_view` |
| 4.6 Deployment View | `fig_deployment_view` |
| 4.7 Camera Pipeline Class Structure | `fig_camera_classes` |
| 4.8 Vest Telemetry and SOS Sequence | `fig_seq_vest_telemetry` |
| 4.9 Camera Event to Dashboard Sequence | `fig_seq_camera_event` |

## Two ways to change a figure

1. **Change the script** (recommended for anything that names code: 3.9, 3.10,
   4.1, 4.2, 4.7). Edit the figure's function in `make_figures.py`, run
   `.venv/bin/python docs/figures/make_figures.py`, then rebuild the report.
   The script checks model fields and class names against the code, and all
   three copies (PNG, .drawio, .svg) stay in step.
2. **Edit the .drawio file by hand.** Export it with File > Export as > PNG,
   zoom 230% (about 220 dpi), no border, and save it over
   `docs/figures/<same name>.png`. Then rebuild the report. Note that the next
   run of `make_figures.py` overwrites both the PNG and the .drawio file, so
   copy a hand-edited diagram into the script before regenerating, or keep
   your edited file somewhere else.

Rebuild commands are in the docstring of `docs/build_report_v8.py`.
