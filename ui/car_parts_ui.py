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


import bpy
from mathutils import Vector
from ..utils.constants import CAR_PART_ROLES, REQUIRED_CAR_PARTS


def get_car_part_assignments(context):
    assignments = {}
    for obj in context.blend_data.objects:
        role = obj.assettoCorsa.carPartRole
        if role != 'NONE':
            assignments.setdefault(role, []).append(obj)
    return assignments


class KN5_OT_AutoCalculateOrigin(bpy.types.Operator):
    bl_idname = "ac_car.auto_calculate_origin"
    bl_label = "Auto-Calculate Origin"
    bl_description = "Set the object origin to a position appropriate for its car part role"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in ["MESH", "CURVE"]
                and obj.assettoCorsa.carPartRole != 'NONE')

    def execute(self, context):
        obj = context.object
        role = obj.assettoCorsa.carPartRole

        bbox_world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        bb_min = Vector((
            min(v.x for v in bbox_world),
            min(v.y for v in bbox_world),
            min(v.z for v in bbox_world),
        ))
        bb_max = Vector((
            max(v.x for v in bbox_world),
            max(v.y for v in bbox_world),
            max(v.z for v in bbox_world),
        ))
        bb_center = (bb_min + bb_max) / 2

        if role.startswith('SUSP_'):
            target = Vector((bb_center.x, bb_center.y, bb_max.z))
        else:
            target = bb_center

        saved_cursor = context.scene.cursor.location.copy()
        context.scene.cursor.location = target
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        context.scene.cursor.location = saved_cursor

        self.report({'INFO'}, f"Origin set for {role}")
        return {'FINISHED'}


class KN5_OT_ValidateCarParts(bpy.types.Operator):
    bl_idname = "ac_car.validate_car_parts"
    bl_label = "Validate Car Parts"
    bl_description = "Check that all required car parts are assigned and no duplicates exist"

    def execute(self, context):
        assignments = get_car_part_assignments(context)
        errors = []

        missing = REQUIRED_CAR_PARTS - set(assignments.keys())
        for part in sorted(missing):
            errors.append(f"Missing required part: {part}")

        for role, objs in assignments.items():
            if len(objs) > 1:
                names = ', '.join(o.name for o in objs)
                errors.append(f"Duplicate role {role}: {names}")

        if errors:
            for err in errors:
                self.report({'WARNING'}, err)
        else:
            self.report({'INFO'}, "All car part validations passed")
        return {'FINISHED'}


class KN5_PT_CarPartPanel(bpy.types.Panel):
    bl_label = "AC Car Part"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type in ["MESH", "CURVE", "EMPTY"]

    def draw(self, context):
        layout = self.layout
        ac_obj = context.object.assettoCorsa

        layout.prop(ac_obj, "carPartRole")

        if ac_obj.carPartRole != 'NONE':
            if context.object.type in ["MESH", "CURVE"]:
                layout.operator("ac_car.auto_calculate_origin")

            col = layout.column(align=True)
            col.label(text="Export Origin Offset:")
            col.prop(ac_obj, "carPartOriginOffset", text="")

            role = ac_obj.carPartRole
            count = sum(
                1 for obj in context.blend_data.objects
                if obj.assettoCorsa.carPartRole == role
            )
            if count > 1:
                row = layout.row()
                row.alert = True
                row.label(
                    text=f"Warning: {count} objects share role {role}",
                    icon='ERROR'
                )


class KN5_PT_CarPartsSummaryPanel(bpy.types.Panel):
    bl_label = "AC Car Parts Summary"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return any(
            obj.assettoCorsa.carPartRole != 'NONE'
            for obj in context.blend_data.objects
        )

    def draw(self, context):
        layout = self.layout
        assignments = get_car_part_assignments(context)

        if not assignments:
            layout.label(text="No car parts assigned")
            return

        for role_id, display, _desc in CAR_PART_ROLES:
            if role_id == 'NONE':
                continue
            if role_id in assignments:
                objs = assignments[role_id]
                row = layout.row()
                if len(objs) > 1:
                    row.alert = True
                row.label(text=f"{display}: {', '.join(o.name for o in objs)}")

        layout.separator()
        box = layout.box()
        box.label(text="Validation:", icon='CHECKMARK')

        missing = REQUIRED_CAR_PARTS - set(assignments.keys())
        if missing:
            for part in sorted(missing):
                row = box.row()
                row.alert = True
                row.label(text=f"Missing required: {part}", icon='ERROR')
        else:
            box.label(text="All required wheel parts assigned", icon='CHECKMARK')

        for role, objs in assignments.items():
            if len(objs) > 1:
                row = box.row()
                row.alert = True
                names = ', '.join(o.name for o in objs)
                row.label(text=f"Duplicate {role}: {names}", icon='ERROR')

        layout.operator("ac_car.validate_car_parts")


REGISTER_CLASSES = (
    KN5_OT_AutoCalculateOrigin,
    KN5_OT_ValidateCarParts,
    KN5_PT_CarPartPanel,
    KN5_PT_CarPartsSummaryPanel,
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
