"""Render asset previews with Blender, preserving URDF transforms and GLB materials.

    blender -b --factory-startup --python scripts/render_previews.py --
    blender -b --factory-startup --python scripts/render_previews.py -- Dexforce_W1_V3

Only preview PNGs are written; source descriptions and meshes are never modified.
"""

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "Dexforce_W1_V2": "robot_with_ee.urdf",
    "Dexforce_W1_V3": "robot_with_ee.urdf",
    "Engineai_PM01": "urdf/robot.urdf",
    "Marvin_M6_S_CCS_696_V4.0": "robot_with_ee.urdf",
    "Marvin_M6_S_CCS_696_PRO_V2.0": "robot_with_ee.urdf",
    "OpenArm": "robot.urdf",
    "UnitreeG1": "robot.urdf",
    "UnitreeR1": "robot.urdf",
    "UnitreeH1": "robot.urdf",
    "UnitreeGo1": "robot.urdf",
}


def vector(text):
    return Vector(tuple(float(value) for value in text.split()))


def origin(element):
    if element is None:
        return Matrix.Identity(4)
    rotation = Euler(vector(element.get("rpy", "0 0 0")), "XYZ").to_matrix().to_4x4()
    return Matrix.Translation(vector(element.get("xyz", "0 0 0"))) @ rotation


def link_frames(robot):
    """Forward kinematics with independent joints at zero and mimic offsets applied."""
    links = {link.get("name") for link in robot.findall("link")}
    joints = {joint.get("name"): joint for joint in robot.findall("joint")}
    children = [joint.find("child").get("link") for joint in joints.values()]
    roots = links - set(children)
    if len(roots) != 1 or len(children) != len(set(children)):
        raise ValueError("Expected a URDF tree with one root and unique child links")
    values = {}

    def joint_value(name, visiting=()):
        if name in visiting:
            raise ValueError(f"Cyclic mimic joint: {name}")
        if name not in values:
            mimic = joints[name].find("mimic")
            values[name] = (
                0.0
                if mimic is None
                else float(mimic.get("multiplier", "1"))
                * joint_value(mimic.get("joint"), (*visiting, name))
                + float(mimic.get("offset", "0"))
            )
        return values[name]

    frames = {roots.pop(): Matrix.Identity(4)}
    pending = list(joints.values())
    while pending:
        ready = [j for j in pending if j.find("parent").get("link") in frames]
        if not ready:
            raise ValueError("Disconnected or cyclic URDF joints")
        for joint in ready:
            parent = joint.find("parent").get("link")
            child = joint.find("child").get("link")
            if child not in links:
                raise ValueError(f"Unknown child link: {child}")
            motion = Matrix.Identity(4)
            kind = joint.get("type")
            if kind in {"revolute", "continuous", "prismatic"}:
                axis_element = joint.find("axis")
                axis = vector(
                    axis_element.get("xyz", "1 0 0")
                    if axis_element is not None
                    else "1 0 0"
                )
                if axis.length == 0:
                    raise ValueError(f"Zero joint axis: {joint.get('name')}")
                axis.normalize()
                value = joint_value(joint.get("name"))
                motion = (
                    Matrix.Translation(axis * value)
                    if kind == "prismatic"
                    else Matrix.Rotation(value, 4, axis)
                )
            elif kind != "fixed":
                raise ValueError(f"Unsupported joint type: {kind}")
            frames[child] = frames[parent] @ origin(joint.find("origin")) @ motion
            pending.remove(joint)
    if set(frames) != links:
        raise ValueError("Disconnected URDF links")
    return frames


def smooth_missing_normals(mesh):
    """Reconstruct shading for STL-derived meshes; retain authored split normals."""
    if mesh.has_custom_normals:
        return
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # STL exports can contain a separate vertex for every triangle corner.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        edge.smooth = edge.is_manifold and edge.calc_face_angle() < math.radians(35)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def import_mesh(path):
    before = set(bpy.data.objects)
    suffix = path.suffix.lower()
    if suffix == ".glb":
        bpy.ops.import_scene.gltf(filepath=str(path))
        # Blender maps glTF's Y-up coordinates to Z-up. URDF mesh coordinates
        # already use the numbers stored in the GLB, so undo that conversion.
        basis = Matrix.Rotation(-math.pi / 2, 4, "X")
    elif suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
        basis = Matrix.Identity(4)
    else:
        raise ValueError(f"Unsupported visual mesh: {path}")
    imported = set(bpy.data.objects) - before
    parts = [(obj, basis @ obj.matrix_world) for obj in imported if obj.type == "MESH"]
    for obj, matrix in parts:
        obj.parent = None
        obj.matrix_world = matrix
        smooth_missing_normals(obj.data)
    for obj in imported:
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    if not parts:
        raise ValueError(f"Empty mesh: {path}")
    return [obj for obj, _ in parts]


def material(name, color, roughness=0.5):
    result = bpy.data.materials.new(name)
    if result.node_tree is None:
        result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Alpha"].default_value = color[3]
    return result


def visual_geometry(geometry, directory):
    mesh = geometry.find("mesh")
    if mesh is not None:
        path = (directory / mesh.get("filename")).resolve(strict=True)
        scale = vector(mesh.get("scale", "1 1 1"))
        parts = import_mesh(path)
        for obj in parts:
            obj.matrix_world = Matrix.Diagonal((*scale, 1)) @ obj.matrix_world
        return parts
    if (box := geometry.find("box")) is not None:
        bpy.ops.mesh.primitive_cube_add(size=1)
        bpy.context.object.scale = vector(box.get("size"))
    elif (sphere := geometry.find("sphere")) is not None:
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=64, ring_count=32, radius=float(sphere.get("radius"))
        )
    elif (cylinder := geometry.find("cylinder")) is not None:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=float(cylinder.get("radius")),
            depth=float(cylinder.get("length")),
        )
    else:
        raise ValueError(f"Unsupported visual geometry: {ET.tostring(geometry)}")
    obj = bpy.context.object
    smooth_missing_normals(obj.data)
    bpy.context.view_layer.update()
    return [obj]


def load_robot(path):
    robot = ET.parse(path).getroot()
    frames = link_frames(robot)
    materials = {item.get("name"): item for item in robot.findall("material")}
    objects = []
    for link in robot.findall("link"):
        for visual in link.findall("visual"):
            transform = frames[link.get("name")] @ origin(visual.find("origin"))
            parts = visual_geometry(visual.find("geometry"), path.parent)
            override = visual.find("material")
            rgba = None
            if override is not None:
                rgba = override.find("color")
                if rgba is None and override.get("name") in materials:
                    rgba = materials[override.get("name")].find("color")
            for obj in parts:
                obj.name = f"{link.get('name')}/{obj.name}"
                obj.matrix_world = transform @ obj.matrix_world
                if rgba is not None or not obj.data.materials:
                    color = (
                        tuple(float(v) for v in rgba.get("rgba").split())
                        if rgba is not None
                        else (0.65, 0.68, 0.72, 1)
                    )
                    obj.data.materials.clear()
                    obj.data.materials.append(material(obj.name, color))
                objects.append(obj)
    if not objects:
        raise ValueError(f"No visual geometry: {path}")
    bpy.context.view_layer.update()
    return objects


def look_at(obj, target):
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def setup_studio(objects, model):
    corners = [
        obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box
    ]
    lower = Vector(tuple(min(p[i] for p in corners) for i in range(3)))
    upper = Vector(tuple(max(p[i] for p in corners) for i in range(3)))
    # A rotated object's bounding-box corners can lie below its actual surface.
    # Use vertices for ground contact so the robot does not appear to float.
    floor = float("inf")
    for obj in objects:
        coordinates = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get("co", coordinates)
        row = np.array(obj.matrix_world)[2]
        heights = coordinates.reshape(-1, 3) @ row[:3] + row[3]
        floor = min(floor, float(heights.min()))
    factor = 2.0 / max(upper - lower)
    center = Vector(((lower.x + upper.x) / 2, (lower.y + upper.y) / 2, lower.z))
    normalization = Matrix.Scale(factor, 4) @ Matrix.Translation(-center)
    for obj in objects:
        obj.matrix_world = normalization @ obj.matrix_world
    corners = [normalization @ p for p in corners]
    height = (upper.z - lower.z) * factor
    target = Vector((0, 0, height / 2))
    direction = Vector((6, -1.5, 1.05))
    if model == "UnitreeGo1":
        direction = Vector((4.5, -6, 3.0))
    bpy.ops.object.camera_add(location=target + direction)
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.dof.use_dof = False
    look_at(camera, target)
    basis = camera.rotation_euler.to_matrix().transposed()
    projected = [basis @ (p - target) for p in corners]
    xmin, xmax = min(p.x for p in projected), max(p.x for p in projected)
    ymin, ymax = min(p.y for p in projected), max(p.y for p in projected)
    camera.location += basis.transposed() @ Vector(
        ((xmin + xmax) / 2, (ymin + ymax) / 2, 0)
    )
    camera.data.ortho_scale = max(xmax - xmin, ymax - ymin) * 1.16
    bpy.context.scene.camera = camera
    # The thin OpenArm mounting plate needs closer contact to read as grounded.
    clearance = 0.0001 if model == "OpenArm" else 0.003
    bpy.ops.mesh.primitive_plane_add(
        size=200, location=(0, 0, (floor - lower.z) * factor - clearance)
    )
    bpy.context.object.data.materials.append(
        material("Studio floor", (0.065, 0.078, 0.10, 1), 0.8)
    )
    for name, location, power, size in [
        ("Key", (3, -4, 5), 650, 3),
        ("Fill", (2, 4, 3), 450, 3),
        ("Rim", (-3, 1, 4), 800, 2.5),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, target)
    world = bpy.context.scene.world
    if world.node_tree is None:
        world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.3, 0.3, 0.3, 1)
    background.inputs["Strength"].default_value = 0.5


def render(model, args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Studio")
    objects = load_robot(ROOT / model / MODELS[model])
    setup_studio(objects, model)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.005
    scene.cycles.adaptive_min_samples = min(32, args.samples)
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.denoising_prefilter = "ACCURATE"
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = args.threads
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 85
    scene.render.film_transparent = False
    scene.render.filter_size = 1.0
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.7
    output = (
        args.output_dir / f"{model}.png"
        if args.output_dir
        else ROOT / model / "preview.png"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output.resolve())
    print(f"Rendering {model}: {len(objects)} mesh objects -> {output}", flush=True)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "models", nargs="*", help="Model directory names; defaults to all"
    )
    parser.add_argument("--resolution", type=int, default=2400)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Write MODEL.png here instead of replacing previews",
    )
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if args.resolution < 1 or args.samples < 1 or not 1 <= args.threads <= 1024:
        parser.error(
            "Resolution/samples must be positive; threads must be in [1, 1024]"
        )
    for model in args.models or MODELS:
        if model not in MODELS:
            parser.error(f"Unknown model: {model}; choose from {', '.join(MODELS)}")
        render(model, args)


if __name__ == "__main__":
    main()
