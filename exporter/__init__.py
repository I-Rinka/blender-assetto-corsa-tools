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
# Copyright (C) 2014  Thomas Hagnhofer


import traceback
import os
import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from .exporter_utils import read_settings, read_car_parts_from_settings, apply_car_parts_to_objects
from .kn5_writer import KN5Writer
from .texture_writer import TextureWriter
from .material_writer import MaterialWriter
from .node_writer import NodeWriter
from ..utils.constants import KN5_HEADER_BYTES, REQUIRED_CAR_PARTS


class ReportOperator(bpy.types.Operator):
    bl_idname = "kn5.report_message"
    bl_label = "Export report"

    is_error: BoolProperty()
    title: StringProperty()
    message: StringProperty()

    def execute(self, context):
        if self.is_error:
            self.report({'WARNING'}, self.message)
        else:
            self.report({'INFO'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return context.window_manager.invoke_popup(self, width=600)

    def draw(self, context):
        if self.is_error:
            self.layout.alert = True
        row = self.layout.row()
        row.alignment = "CENTER"
        row.label(text=self.title)
        for line in self.message.splitlines():
            row = self.layout.row()
            line = line.replace("\t", " " * 4)
            row.label(text=line)
        row = self.layout.row()
        row.operator("kn5.report_clipboard").content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    bl_idname = "kn5.report_clipboard"
    bl_label = "Copy to clipboard"

    content: StringProperty()

    def execute(self, context):
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {'FINISHED'}


class KN5FileWriter(KN5Writer):
    def __init__(self, file, context, settings, warnings, root_node_name="BlenderFile",
                 even_split=False, forward_axis='-Y'):
        super().__init__(file)

        self.context = context
        self.settings = settings
        self.warnings = warnings
        self.root_node_name = root_node_name
        self.even_split = even_split
        self.forward_axis = forward_axis

        self.file_version = 5

    def write(self):
        self._write_header()
        self._write_content()

    def _write_header(self):
        self.file.write(KN5_HEADER_BYTES)
        self.write_uint(self.file_version)

    def _write_content(self):
        texture_writer = TextureWriter(self.file, self.context, self.warnings)
        texture_writer.write()
        material_writer = MaterialWriter(self.file, self.context, self.settings, self.warnings)
        material_writer.write()
        node_writer = NodeWriter(self.file, self.context, self.settings, self.warnings, material_writer,
                                  root_node_name=self.root_node_name, even_split=self.even_split,
                                  forward_axis=self.forward_axis)
        node_writer.write()


class ExportKN5(bpy.types.Operator, ExportHelper):
    bl_idname = "exporter.kn5"
    bl_label = "Export KN5"
    bl_description = "Export KN5"

    filename_ext = ".kn5"

    root_node_name: StringProperty(
        name="Root Node Name",
        default="",
        description="Name for the KN5 root node. Leave empty to auto-detect: "
                    "uses filename stem if car parts are assigned, 'BlenderFile' otherwise")

    even_split_oversized: BoolProperty(
        name="Even Split Oversized Meshes",
        default=False,
        description="Split meshes exceeding 65536 vertices into evenly sized parts. "
                    "If disabled, oversized meshes are split sequentially (original behavior)")

    model_forward_axis: bpy.props.EnumProperty(
        name="Model Forward Axis",
        items=[
            ('-Y', "-Y (Blender default)", "Model front faces Blender -Y"),
            ('+Y', "+Y", "Model front faces Blender +Y"),
            ('+X', "+X", "Model front faces Blender +X"),
            ('-X', "-X", "Model front faces Blender -X"),
        ],
        default='-Y',
        description="Which Blender axis the model's front faces. "
                    "AC expects forward = +Z; a corrective rotation is applied if needed")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "root_node_name")
        layout.prop(self, "model_forward_axis")
        layout.prop(self, "even_split_oversized")

        if self.model_forward_axis != '-Y':
            box = layout.box()
            box.label(text=f"Forward correction: {self.model_forward_axis} -> AC +Z", icon='ORIENTATION_NORMAL')

        oversized = self._find_oversized_meshes(context)
        if oversized:
            box = layout.box()
            box.label(text="Oversized meshes detected:", icon='ERROR')
            for name, count in oversized:
                box.label(text=f"  {name}: {count} vertices")
            if self.even_split_oversized:
                box.label(text="Will be split into even parts", icon='CHECKMARK')
            else:
                box.label(text="Will use sequential split", icon='INFO')

    @staticmethod
    def _find_oversized_meshes(context):
        limit = 2**16
        oversized = []
        for obj in context.blend_data.objects:
            if obj.type != "MESH" or obj.name.startswith("__"):
                continue
            if len(obj.data.vertices) > limit:
                oversized.append((obj.name, len(obj.data.vertices)))
        return oversized

    def _has_car_parts(self, context):
        return any(
            obj.assettoCorsa.carPartRole != 'NONE'
            for obj in context.blend_data.objects
        )

    def _validate_car_parts(self, context, warnings):
        assignments = {}
        for obj in context.blend_data.objects:
            role = obj.assettoCorsa.carPartRole
            if role != 'NONE':
                assignments.setdefault(role, []).append(obj.name)

        missing = REQUIRED_CAR_PARTS - set(assignments.keys())
        for part in sorted(missing):
            warnings.append(f"Missing required car part: {part}")

        for role, names in assignments.items():
            if len(names) > 1:
                warnings.append(f"Duplicate car part role {role}: {', '.join(names)}")

    def execute(self, context):
        warnings = []
        try:
            output_file = open(self.filepath, "wb")
            try:
                settings = read_settings(self.filepath)

                car_parts = read_car_parts_from_settings(settings)
                if car_parts:
                    apply_car_parts_to_objects(context, car_parts)

                root_name = self.root_node_name
                if not root_name:
                    if self._has_car_parts(context):
                        root_name = os.path.splitext(os.path.basename(self.filepath))[0]
                    else:
                        root_name = "BlenderFile"

                if self._has_car_parts(context):
                    self._validate_car_parts(context, warnings)

                kn5_writer = KN5FileWriter(output_file, context, settings, warnings,
                                           root_node_name=root_name,
                                           even_split=self.even_split_oversized,
                                           forward_axis=self.model_forward_axis)
                kn5_writer.write()
                bpy.ops.kn5.report_message(
                    'INVOKE_DEFAULT',
                    is_error=False,
                    title="Exported successfully",
                    message=os.linesep.join(warnings)
                )
            finally:
                if not output_file is None:
                    output_file.close()
        except: # pylint: disable=bare-except
            error = traceback.format_exc()
            try:
                os.remove(self.filepath)
            except: # pylint: disable=bare-except
                pass
            warnings.append(error)
            bpy.ops.kn5.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title="Export failed",
                message=os.linesep.join(warnings)
            )
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ExportKN5.bl_idname, text="Assetto Corsa (.kn5)")


REGISTER_CLASSES = (
    ReportOperator,
    CopyClipboardButtonOperator,
    ExportKN5,
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
