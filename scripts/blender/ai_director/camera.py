from __future__ import annotations
import bpy
import math
from .subject import subject_height

def create_camera(spec: dict, subject: bpy.types.Object) -> bpy.types.Object:
    lens_mm = int(spec["camera"].get("lens_mm", 35))
    height = subject_height(subject)

    if lens_mm >= 70:
        frame_height = 0.7 * height
        target_z = 0.78 * height
    elif lens_mm <= 28:
        frame_height = 3.5 * height
        target_z = 0.5 * height
    else:
        frame_height = 1.6 * height
        target_z = 0.55 * height

    bpy.ops.object.camera_add(location=(0, -5, target_z))
    camera = bpy.context.object
    camera.name = "director_camera"
    camera.data.lens = lens_mm
    bpy.context.scene.camera = camera

    sensor_height = camera.data.sensor_width * (
        bpy.context.scene.render.resolution_y / bpy.context.scene.render.resolution_x
    )
    fov_v = 2 * math.atan(sensor_height / (2 * lens_mm))
    distance = frame_height / (2 * math.tan(fov_v / 2))

    target = bpy.data.objects.new("camera_target", None)
    bpy.context.scene.collection.objects.link(target)
    target.location = (subject.location.x, subject.location.y, target_z)
    bpy.context.view_layer.update()
    target.parent = subject
    target.matrix_parent_inverse = subject.matrix_world.inverted()

    camera["frame_distance"] = distance
    camera["target_z"] = target_z
    camera.location = (0, -distance, target_z + 0.15 * distance)

    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    constraint.target = target
    configure_depth_of_field(camera, target, lens_mm)
    return camera

def configure_depth_of_field(camera: bpy.types.Object, target: bpy.types.Object, lens_mm: int) -> None:
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = target
    if lens_mm >= 70:
        camera.data.dof.aperture_fstop = 2.4
    elif lens_mm <= 28:
        camera.data.dof.aperture_fstop = 5.6
    else:
        camera.data.dof.aperture_fstop = 3.5
