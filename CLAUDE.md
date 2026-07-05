# Blender Assetto Corsa Tools — Claude Project Guide

## Project Overview

Blender addon (Python) that exports scenes to Assetto Corsa's KN5 binary format. Supports track and car model export. Includes a CLI interactive export tool for headless workflows.

GitHub repo: `https://github.com/I-Rinka/blender-assetto-corsa-tools`

## Architecture

```
__init__.py              # Addon entry (bl_info, register/unregister)
exporter/
  __init__.py            # ExportKN5 operator, KN5FileWriter orchestrator
  kn5_writer.py          # Binary serialization primitives (struct-based)
  node_writer.py         # Scene graph traversal, node/mesh writing, car part name override
  material_writer.py     # Shader properties, blend modes, texture mappings
  texture_writer.py      # Embeds PNG/DDS image data
  exporter_utils.py      # Coordinate conversion (Z-up→Y-up), settings.json I/O
ui/
  __init__.py            # Registers all UI sub-modules
  nodes_ui.py            # NodeProperties PropertyGroup on bpy.types.Object (incl. carPartRole)
  materials_ui.py        # MaterialProperties on bpy.types.Material
  textures_ui.py         # TextureProperties on bpy.types.ShaderNodeTexImage
  car_parts_ui.py        # Car part assignment panel, auto-origin operator, summary/validation
utils/
  __init__.py            # register_recursive / unregister_recursive
  constants.py           # KN5 header, AC object patterns, CAR_PART_ROLES, REQUIRED_CAR_PARTS
cli_export.py            # Standalone CLI script (not part of addon registration)
```

### Key Patterns

- **PropertyGroups** attach to Blender types via `bpy.types.X.assettoCorsa = PointerProperty(type=...)`
- **Export layer** has mirror Python classes that copy from `obj.assettoCorsa` at export time
- **Node names**: `node_writer._get_node_name(obj)` returns `carPartRole` if set, else `obj.name`
- **Coordinate conversion**: `convert_vector3()` swaps Y↔Z and negates: `(x, z, -y)`
- **Registration order matters**: PropertyGroups must register before panels that reference them
- **settings.json**: regex-matched overrides for materials/nodes + `carParts` bindings dict

### KN5 Binary Format

Header (`sc6969` + version 5) → Textures (embedded PNG/DDS) → Materials → Nodes (recursive scene tree). Three node classes: Node (1, transform-only), Mesh (2, geometry), SkinnedMesh (3, not implemented).

## Development

### Lint

```bash
pylint --rcfile=.pylintrc *.py exporter/ ui/ utils/
```

### Test in Blender

```bash
# Install addon from directory (symlink or copy to Blender addons path)
blender --python-expr "import bpy; bpy.ops.preferences.addon_install(filepath='path/to/zip')"

# Headless export test
blender --background test.blend --python cli_export.py -- --auto-assign /tmp/test.kn5
```

### Syntax Check (no Blender dependency)

```bash
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['cli_export.py','exporter/__init__.py','exporter/node_writer.py','ui/car_parts_ui.py','utils/constants.py']]"
```

## Conventions

- Follow existing `REGISTER_CLASSES` tuple + `register()`/`unregister()` pattern for new modules
- Operators use `bl_idname` format: `"category.action"` (e.g., `"ac_car.auto_calculate_origin"`)
- Objects/materials prefixed with `"__"` are excluded from export
- All binary writes use little-endian via Python `struct` module
- Strings in KN5 are UTF-8 with uint32 length prefix

## Pushing Code to GitHub

This machine cannot directly reach GitHub. Use the remote relay:

```bash
# 1. Bundle
git bundle create /tmp/ac-tools-push.bundle main

# 2. Upload
sshpass -p 'RinkaAL_02' sftp -o StrictHostKeyChecking=no -o PubkeyAuthentication=no zicheng.wzc@11.158.228.175 <<'EOF'
put /tmp/ac-tools-push.bundle /home/zicheng.wzc/source/ac-tools-push.bundle
EOF

# 3. Push from remote
sshpass -p 'RinkaAL_02' ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no zicheng.wzc@11.158.228.175 \
  'cd ~/source/blender-assetto-corsa-tools && \
   git fetch ~/source/ac-tools-push.bundle main:tmpbranch 2>&1 && \
   git checkout -B main tmpbranch 2>&1 && \
   git push origin main --force 2>&1'
```

Remote machine: `zicheng.wzc@11.158.228.175`, password: `RinkaAL_02`.
