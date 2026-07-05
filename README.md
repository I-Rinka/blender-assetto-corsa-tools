# Blender Assetto Corsa Tools

Blender addon for exporting scenes to Assetto Corsa's KN5 file format. Supports both **track** and **car model** export workflows, with an interactive CLI tool for headless batch processing.

Based on Thomas Hagnhofer's original KN5 exporter, extended with car part role assignment, origin remapping, and a command-line export pipeline.

## Features

- Export Blender scenes to KN5 format (version 5)
- **Track export**: mesh geometry, textures, materials, AC logical objects (start positions, pit stops, timing gates)
- **Car model export**: assign AC car part roles (STEER_HR, WHEEL_LF, etc.) via dropdown, auto-rename nodes on export
- Auto-calculate rotation origins for car parts (bounding box center / top-center for suspension)
- Scene-level car parts summary panel with validation (missing wheels, duplicate roles)
- `settings.json` support for batch material/node overrides and persistent car part bindings
- CLI interactive export tool (`cli_export.py`) for headless Blender workflows
- Auto-matching objects to car part roles by name patterns

## Requirements

Blender 3.0.0 or later.

## Install

1. Download the addon zip from the [latest Release](https://github.com/moppius/blender-assetto-corsa-tools/releases/latest), or clone this repo and zip the folder
2. In Blender: Edit > Preferences > Add-ons > Install...
3. Select the zip file and enable **"Assetto Corsa (.kn5)"**

## Usage — Track Export

1. Set up a track scene with geometry and AC helper objects (`AC_START_0`, `AC_PIT_0`, etc.)
2. File > Export > Assetto Corsa (.kn5)
3. Place a `settings.json` in the export directory for material/node overrides

For track creation guides, see [assettocorsamods.net](https://assettocorsamods.net/threads/build-your-first-track-basic-guide.12/).

## Usage — Car Model Export

### In Blender GUI

1. Select an object, open **Object Properties > AC Car Part** panel
2. Choose a car part role from the dropdown (e.g., WHEEL_LF, STEER_HR)
3. Click **Auto-Calculate Origin** to set the rotation pivot point
4. Fine-tune with the **Origin Offset** vector if needed
5. Check **Scene Properties > AC Car Parts Summary** for validation
6. Export via File > Export > Assetto Corsa (.kn5)
   - Root node name auto-detects: uses the filename for car models, "BlenderFile" for tracks

### Supported Car Parts

| Category | Parts |
|----------|-------|
| Wheels (required) | `WHEEL_LF`, `WHEEL_RF`, `WHEEL_LR`, `WHEEL_RR` |
| Steering | `STEER_HR` (high-res), `STEER_LR` (low-res) |
| Cockpit | `COCKPIT_HR`, `COCKPIT_LR` |
| Suspension | `SUSP_LF`, `SUSP_RF`, `SUSP_LR`, `SUSP_RR` |
| Hubs | `HUB_LF`, `HUB_RF`, `HUB_LR`, `HUB_RR` |
| Brake Discs | `DISC_LF`, `DISC_RF`, `DISC_LR`, `DISC_RR` |
| Seatbelt | `CINTURE_ON`, `CINTURE_OFF` |
| Body | `MOTORHOOD`, `REARHOOD` |
| Aero | `REAR_WING` |

## CLI Export Tool

For headless / batch export without opening Blender's GUI:

```bash
# Interactive mode — prompts for car part assignment
blender --background model.blend --python cli_export.py -- output.kn5

# Auto-match objects to roles by name patterns
blender --background model.blend --python cli_export.py -- --auto-assign output.kn5

# Non-interactive — use saved settings.json config
blender --background model.blend --python cli_export.py -- --non-interactive output.kn5

# Custom settings file
blender --background model.blend --python cli_export.py -- --settings my_config.json output.kn5
```

### CLI Workflow

1. **Scene inspection** — prints object tree, materials, textures
2. **Load saved config** — reads car part bindings from `settings.json`
3. **Interactive assignment** — select objects for each car part role, or type `auto` for name-based matching
4. **Validation checklist** — checks required parts, materials, UVs, textures, duplicates
5. **Save config** — writes bindings to `settings.json` for reuse
6. **Export** — generates the KN5 file

## settings.json

Place next to the export target. Supports material overrides, node overrides, and car part bindings:

```json
{
  "carParts": {
    "WHEEL_LF": "WheelFrontLeft",
    "WHEEL_RF": "WheelFrontRight",
    "WHEEL_LR": "WheelRearLeft",
    "WHEEL_RR": "WheelRearRight",
    "STEER_HR": "SteeringWheel"
  },
  "materials": {
    "Road*": {
      "shaderName": "ksPerPixel",
      "alphaBlendMode": "Opaque"
    }
  },
  "nodes": {
    "TREE_*": {
      "transparent": true,
      "castShadows": false
    }
  }
}
```

Keys in `materials` and `nodes` support `|` for alternatives and `*` for wildcards.

## Limitations

- **Export only** — no KN5 import
- **No skinned meshes** — SkinnedMesh (node class 3) is not implemented; no bone/animation export
- **No AI line data** — AI paths need separate tools
- **No INI generation** — `surfaces.ini`, `cameras.ini`, etc. must be created manually
- **65,536 vertex limit** per mesh (uint16 indices; auto-split for larger meshes)
- **Mesh objects cannot have children** — use Empty objects as hierarchy containers
- **Image textures only** — procedural Blender textures are not exported

## License

GPL v3 — see [LICENSE.txt](LICENSE.txt).

Original addon by Thomas Hagnhofer (2014), updated by Paul Greveson. Car model features and CLI tool added 2026.
