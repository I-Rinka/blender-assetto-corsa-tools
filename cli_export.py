#!/usr/bin/env python3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# CLI interactive export script for Blender -> Assetto Corsa KN5.
# Usage: blender --background model.blend --python cli_export.py -- output.kn5
#
# Options (after --):
#   output.kn5                  Output KN5 file path (required)
#   --settings path             Path to settings.json (default: next to output)
#   --non-interactive           Skip prompts, use saved config only
#   --auto-assign               Auto-match objects to car part roles by name

import sys
import os
import json
import re

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from utils.constants import CAR_PART_ROLES, REQUIRED_CAR_PARTS
from exporter.exporter_utils import read_settings, write_settings
from exporter.kn5_writer import KN5Writer
from exporter.texture_writer import TextureWriter
from exporter.material_writer import MaterialWriter
from exporter.node_writer import NodeWriter
from utils.constants import KN5_HEADER_BYTES


# --- Auto-matching ---

ROLE_KEYWORDS = {
    'WHEEL_LF': [r'wheel.*(?:lf|fl|left.*front|front.*left)'],
    'WHEEL_RF': [r'wheel.*(?:rf|fr|right.*front|front.*right)'],
    'WHEEL_LR': [r'wheel.*(?:lr|rl|left.*rear|rear.*left|left.*back|back.*left)'],
    'WHEEL_RR': [r'wheel.*(?:rr|right.*rear|rear.*right|right.*back|back.*right)'],
    'STEER_HR': [r'steer.*(?:hr|hi|high)', r'steering.*wheel'],
    'STEER_LR': [r'steer.*(?:lr|lo|low)'],
    'SUSP_LF': [r'susp.*(?:lf|fl|left.*front|front.*left)'],
    'SUSP_RF': [r'susp.*(?:rf|fr|right.*front|front.*right)'],
    'SUSP_LR': [r'susp.*(?:lr|rl|left.*rear|rear.*left)'],
    'SUSP_RR': [r'susp.*(?:rr|right.*rear|rear.*right)'],
    'HUB_LF': [r'hub.*(?:lf|fl|left.*front|front.*left)'],
    'HUB_RF': [r'hub.*(?:rf|fr|right.*front|front.*right)'],
    'HUB_LR': [r'hub.*(?:lr|rl|left.*rear|rear.*left)'],
    'HUB_RR': [r'hub.*(?:rr|right.*rear|rear.*right)'],
    'DISC_LF': [r'(?:disc|brake).*(?:lf|fl|left.*front|front.*left)'],
    'DISC_RF': [r'(?:disc|brake).*(?:rf|fr|right.*front|front.*right)'],
    'DISC_LR': [r'(?:disc|brake).*(?:lr|rl|left.*rear|rear.*left)'],
    'DISC_RR': [r'(?:disc|brake).*(?:rr|right.*rear|rear.*right)'],
    'COCKPIT_HR': [r'cockpit.*(?:hr|hi|high)', r'interior.*(?:hr|hi|high)'],
    'COCKPIT_LR': [r'cockpit.*(?:lr|lo|low)', r'interior.*(?:lr|lo|low)'],
    'CINTURE_ON': [r'(?:cinture|seatbelt|belt).*on'],
    'CINTURE_OFF': [r'(?:cinture|seatbelt|belt).*off'],
    'MOTORHOOD': [r'(?:motor.*hood|bonnet|engine.*hood|hood)'],
    'REARHOOD': [r'(?:rear.*hood|trunk|boot)'],
    'REAR_WING': [r'(?:rear.*wing|spoiler|wing.*rear)'],
}


def auto_match_objects(objects):
    assignments = {}
    used_objects = set()
    obj_names = {obj.name: obj for obj in objects if not obj.name.startswith("__")}

    for role, patterns in ROLE_KEYWORDS.items():
        for obj_name in obj_names:
            if obj_name in used_objects:
                continue
            # Exact name match first
            if obj_name.upper() == role:
                assignments[role] = obj_name
                used_objects.add(obj_name)
                break
            # Regex match
            for pattern in patterns:
                if re.search(pattern, obj_name, re.IGNORECASE):
                    assignments[role] = obj_name
                    used_objects.add(obj_name)
                    break
            if role in assignments:
                break

    return assignments


# --- Display helpers ---

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_object_tree(obj, indent=0):
    prefix = "  " * (indent + 1)
    type_tag = f"[{obj.type}]"

    info_parts = []
    if obj.type == "MESH":
        mesh = obj.data
        info_parts.append(f"verts: {len(mesh.vertices)}")
        mat_names = [s.material.name for s in obj.material_slots if s.material]
        if mat_names:
            info_parts.append(f"materials: {', '.join(mat_names)}")
        else:
            info_parts.append("no material")

    info = f" ({', '.join(info_parts)})" if info_parts else ""
    role = obj.assettoCorsa.carPartRole
    role_tag = f" -> {role}" if role != 'NONE' else ""
    print(f"{prefix}{type_tag} {obj.name}{info}{role_tag}")

    for child in obj.children:
        print_object_tree(child, indent + 1)


def print_scene_info(context):
    print_header("Scene Objects")
    root_objects = sorted(
        [obj for obj in context.blend_data.objects if not obj.parent],
        key=lambda o: o.name
    )
    for obj in root_objects:
        if not obj.name.startswith("__"):
            print_object_tree(obj)

    print_header("Materials")
    materials = [m for m in context.blend_data.materials if not m.name.startswith("__") and m.users > 0]
    if materials:
        for mat in sorted(materials, key=lambda m: m.name):
            shader = mat.assettoCorsa.shaderName if hasattr(mat, 'assettoCorsa') else "unknown"
            tex_nodes = []
            if mat.node_tree:
                tex_nodes = [n.image.name for n in mat.node_tree.nodes
                             if hasattr(n, 'image') and n.image]
            tex_info = f", textures: {', '.join(tex_nodes)}" if tex_nodes else ""
            print(f"  {mat.name} (shader: {shader}{tex_info})")
    else:
        print("  (none)")

    print_header("Textures")
    images = [img for img in context.blend_data.images if not img.name.startswith("__")]
    if images:
        for img in sorted(images, key=lambda i: i.name):
            size = f"{img.size[0]}x{img.size[1]}" if img.size[0] > 0 else "unknown size"
            fmt = os.path.splitext(img.name)[1] or img.file_format
            print(f"  {img.name} ({size}, {fmt})")
    else:
        print("  (none)")


# --- Interactive assignment ---

def interactive_assign(context, existing_bindings):
    bindings = dict(existing_bindings)
    available_objects = [
        obj for obj in context.blend_data.objects
        if not obj.name.startswith("__")
    ]
    obj_names = [obj.name for obj in sorted(available_objects, key=lambda o: o.name)]

    role_categories = [
        ("Wheels (Required)", ['WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR']),
        ("Steering", ['STEER_HR', 'STEER_LR']),
        ("Cockpit", ['COCKPIT_HR', 'COCKPIT_LR']),
        ("Suspension", ['SUSP_LF', 'SUSP_RF', 'SUSP_LR', 'SUSP_RR']),
        ("Hubs", ['HUB_LF', 'HUB_RF', 'HUB_LR', 'HUB_RR']),
        ("Brake Discs", ['DISC_LF', 'DISC_RF', 'DISC_LR', 'DISC_RR']),
        ("Seatbelt", ['CINTURE_ON', 'CINTURE_OFF']),
        ("Body Panels", ['MOTORHOOD', 'REARHOOD']),
        ("Aero", ['REAR_WING']),
    ]

    print_header("Car Part Assignment")
    print("  Type 'auto' to auto-match by name, 'skip' to skip remaining, or a number to select.")
    print()

    for category, roles in role_categories:
        print(f"\n  --- {category} ---")
        for role in roles:
            role_desc = ""
            for r_id, r_disp, r_desc in CAR_PART_ROLES:
                if r_id == role:
                    role_desc = r_desc
                    break

            current = bindings.get(role)
            required_tag = "[Required] " if role in REQUIRED_CAR_PARTS else ""
            current_tag = f" (current: {current})" if current else ""

            print(f"\n  {required_tag}{role} - {role_desc}{current_tag}")
            print(f"    0. (skip/unassign)")
            for i, name in enumerate(obj_names, 1):
                used_tag = ""
                for r, n in bindings.items():
                    if n == name and r != role:
                        used_tag = f" [used as {r}]"
                        break
                print(f"    {i}. {name}{used_tag}")

            while True:
                try:
                    choice = input(f"  Select [0-{len(obj_names)}]: ").strip()
                except EOFError:
                    return bindings

                if choice.lower() == 'auto':
                    auto = auto_match_objects(available_objects)
                    bindings.update(auto)
                    print("  Auto-matched:")
                    for r, n in sorted(auto.items()):
                        print(f"    {r} -> {n}")
                    return bindings
                if choice.lower() == 'skip':
                    return bindings
                if choice == '' and current:
                    break
                try:
                    idx = int(choice)
                except ValueError:
                    print("  Invalid input, try again.")
                    continue
                if idx == 0:
                    bindings.pop(role, None)
                    break
                if 1 <= idx <= len(obj_names):
                    bindings[role] = obj_names[idx - 1]
                    break
                print(f"  Out of range, enter 0-{len(obj_names)}.")

    return bindings


# --- Validation ---

def validate_scene(context, bindings):
    print_header("Export Checklist")
    issues = []
    warnings = []

    # Car part assignments
    for role_id, display, desc in CAR_PART_ROLES:
        if role_id == 'NONE':
            continue
        obj_name = bindings.get(role_id)
        if obj_name:
            obj = context.blend_data.objects.get(obj_name)
            if obj:
                print(f"  [ok] {role_id} -> {obj_name}")
            else:
                print(f"  [!!] {role_id} -> {obj_name} (OBJECT NOT FOUND)")
                issues.append(f"Object '{obj_name}' for {role_id} not found in scene")
        elif role_id in REQUIRED_CAR_PARTS:
            print(f"  [!!] {role_id} NOT assigned (REQUIRED)")
            issues.append(f"Missing required car part: {role_id}")
        else:
            print(f"  [  ] {role_id} not assigned (optional)")

    print()

    # Material check
    mesh_objects = [obj for obj in context.blend_data.objects if obj.type == "MESH" and not obj.name.startswith("__")]
    no_material = [obj.name for obj in mesh_objects if not obj.data.materials or not any(s.material for s in obj.material_slots)]
    if no_material:
        for name in no_material:
            print(f"  [!!] Object '{name}' has no material assigned")
            issues.append(f"Object '{name}' has no material")
    else:
        print(f"  [ok] All {len(mesh_objects)} mesh objects have materials")

    # UV check
    no_uv = [obj.name for obj in mesh_objects if obj.data.uv_layers is None or len(obj.data.uv_layers) == 0]
    if no_uv:
        for name in no_uv:
            print(f"  [!!] Object '{name}' has no UV layer (will use flat projection)")
            warnings.append(f"Object '{name}' missing UV layer")
    else:
        print(f"  [ok] All mesh objects have UV layers")

    # Texture format check
    images = set()
    for mat in context.blend_data.materials:
        if mat.users == 0 or mat.name.startswith("__") or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if hasattr(node, 'image') and node.image:
                images.add(node.image)

    bad_format = []
    for img in images:
        ext = os.path.splitext(img.name)[1].lower()
        if ext not in ('.png', '.dds', ''):
            bad_format.append(img.name)
    if bad_format:
        for name in bad_format:
            print(f"  [!!] Texture '{name}' is not PNG/DDS (will be converted)")
            warnings.append(f"Texture '{name}' will be converted to PNG")
    else:
        print(f"  [ok] All textures are PNG/DDS format")

    # Duplicate check
    role_counts = {}
    for role, obj_name in bindings.items():
        role_counts.setdefault(role, []).append(obj_name)
    dupes = {r: names for r, names in role_counts.items() if len(names) > 1}
    if dupes:
        for role, names in dupes.items():
            print(f"  [!!] Duplicate role {role}: {', '.join(names)}")
            issues.append(f"Duplicate role {role}")
    else:
        print(f"  [ok] No duplicate role assignments")

    print()
    return issues, warnings


# --- Export ---

def do_export(context, filepath, settings, root_node_name, bindings, warnings_list):
    # Apply car part roles to objects
    for role, obj_name in bindings.items():
        obj = context.blend_data.objects.get(obj_name)
        if obj:
            obj.assettoCorsa.carPartRole = role

    output_file = open(filepath, "wb")
    try:
        writer = KN5Writer(output_file)
        # Write header
        output_file.write(KN5_HEADER_BYTES)
        writer.write_uint(5)
        # Write textures
        texture_writer = TextureWriter(output_file, context, warnings_list)
        texture_writer.write()
        # Write materials
        material_writer = MaterialWriter(output_file, context, settings, warnings_list)
        material_writer.write()
        # Write nodes
        node_writer = NodeWriter(output_file, context, settings, warnings_list, material_writer,
                                 root_node_name=root_node_name)
        node_writer.write()
    finally:
        output_file.close()


# --- Argument parsing ---

def parse_args():
    try:
        separator = sys.argv.index("--")
    except ValueError:
        print("Usage: blender --background model.blend --python cli_export.py -- [options] output.kn5")
        print("\nOptions:")
        print("  --settings path      Path to settings.json")
        print("  --non-interactive    Skip prompts, use saved config")
        print("  --auto-assign        Auto-match objects to roles by name")
        sys.exit(1)

    args = sys.argv[separator + 1:]
    settings_path = None
    non_interactive = False
    auto_assign = False
    output_path = None

    i = 0
    while i < len(args):
        if args[i] == '--settings' and i + 1 < len(args):
            settings_path = args[i + 1]
            i += 2
        elif args[i] == '--non-interactive':
            non_interactive = True
            i += 1
        elif args[i] == '--auto-assign':
            auto_assign = True
            i += 1
        elif not args[i].startswith('--'):
            output_path = args[i]
            i += 1
        else:
            print(f"Unknown option: {args[i]}")
            sys.exit(1)

    if not output_path:
        print("Error: output .kn5 file path is required")
        sys.exit(1)

    return output_path, settings_path, non_interactive, auto_assign


# --- Main ---

def main():
    output_path, settings_path, non_interactive, auto_assign = parse_args()
    context = bpy.context

    # Ensure addon properties are registered
    if not hasattr(bpy.types.Object, 'assettoCorsa'):
        from ui.nodes_ui import register as register_nodes_ui
        register_nodes_ui()
    if not hasattr(bpy.types.Material, 'assettoCorsa'):
        from ui.materials_ui import register as register_materials_ui
        register_materials_ui()
    if not hasattr(bpy.types.ShaderNodeTexImage, 'assettoCorsa'):
        from ui.textures_ui import register as register_textures_ui
        register_textures_ui()

    # Load settings
    if settings_path:
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                settings = json.loads(f.read())
        else:
            settings = {}
    else:
        settings = read_settings(output_path)

    car_parts = settings.get("carParts", {})

    # Stage 1: Scene inspection
    print_scene_info(context)

    # Stage 2: Load / show existing config
    if car_parts:
        print_header("Loaded Car Part Bindings")
        for role, obj_name in sorted(car_parts.items()):
            exists = "ok" if context.blend_data.objects.get(obj_name) else "NOT FOUND"
            print(f"  {role} -> {obj_name} [{exists}]")

    # Stage 3: Assignment
    if non_interactive:
        bindings = dict(car_parts)
        if auto_assign:
            auto = auto_match_objects(context.blend_data.objects)
            for role, name in auto.items():
                if role not in bindings:
                    bindings[role] = name
            if auto:
                print_header("Auto-Assigned Car Parts")
                for role, name in sorted(auto.items()):
                    if role not in car_parts:
                        print(f"  {role} -> {name}")
    else:
        if car_parts:
            try:
                choice = input("\n  Use these bindings? [Y/n/edit]: ").strip().lower()
            except EOFError:
                choice = 'y'
            if choice in ('', 'y', 'yes'):
                bindings = dict(car_parts)
            elif choice == 'edit':
                bindings = interactive_assign(context, car_parts)
            else:
                if auto_assign:
                    bindings = auto_match_objects(context.blend_data.objects)
                    print_header("Auto-Assigned Car Parts")
                    for role, name in sorted(bindings.items()):
                        print(f"  {role} -> {name}")
                else:
                    bindings = interactive_assign(context, {})
        else:
            if auto_assign:
                bindings = auto_match_objects(context.blend_data.objects)
                print_header("Auto-Assigned Car Parts")
                for role, name in sorted(bindings.items()):
                    print(f"  {role} -> {name}")
                if bindings:
                    try:
                        choice = input("\n  Accept auto-assignments? [Y/n/edit]: ").strip().lower()
                    except EOFError:
                        choice = 'y'
                    if choice in ('edit', 'e'):
                        bindings = interactive_assign(context, bindings)
                    elif choice not in ('', 'y', 'yes'):
                        bindings = interactive_assign(context, {})
            else:
                bindings = interactive_assign(context, {})

    # Stage 4: Validation
    issues, warnings = validate_scene(context, bindings)

    # Determine root node name
    root_name = os.path.splitext(os.path.basename(output_path))[0] if bindings else "BlenderFile"

    print(f"  Root node name: {root_name}")

    if issues:
        print(f"\n  Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"    - {issue}")

    if not non_interactive:
        if issues:
            try:
                proceed = input("\n  There are issues. Proceed with export anyway? [y/N]: ").strip().lower()
            except EOFError:
                proceed = 'n'
            if proceed not in ('y', 'yes'):
                print("  Export cancelled.")
                sys.exit(1)
        else:
            try:
                proceed = input("\n  Proceed with export? [Y/n]: ").strip().lower()
            except EOFError:
                proceed = 'y'
            if proceed not in ('', 'y', 'yes'):
                print("  Export cancelled.")
                sys.exit(0)
    elif issues:
        print("\n  Non-interactive mode: aborting due to issues.")
        sys.exit(1)

    # Stage 5: Save configuration
    if bindings:
        save_data = {"carParts": bindings}
        if settings_path:
            merged = dict(settings)
            merged.update(save_data)
            with open(settings_path, "w") as f:
                json.dump(merged, f, indent=2)
            print(f"\n  Settings saved to {settings_path}")
        else:
            write_settings(output_path, save_data)
            settings_dir = os.path.dirname(os.path.abspath(output_path))
            print(f"\n  Settings saved to {os.path.join(settings_dir, 'settings.json')}")

    # Stage 6: Export
    print_header("Exporting")
    export_warnings = []
    try:
        do_export(context, output_path, settings, root_name, bindings, export_warnings)
        print(f"\n  Exported successfully: {output_path}")
        if export_warnings:
            print(f"\n  Warnings ({len(export_warnings)}):")
            for w in export_warnings:
                print(f"    - {w}")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Export FAILED: {e}")
        try:
            os.remove(output_path)
        except OSError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
