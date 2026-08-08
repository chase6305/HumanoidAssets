# HumanoidAssets

Standardized humanoid robot assets repository.

This repository contains reusable URDF models and paired mesh assets for simulation,
planning, and integration work.

## Repository Scope

- Full robot URDFs and modular sub-assemblies (torso, left arm, right arm)
- Visual meshes for rendering
- Collision meshes for physics and planning
- Mass and inertia definitions embedded in URDF links

## Directory Overview

```text
.
├── Marvin_M6_S_CCS_696_V4.0/
│   ├── robot.urdf
│   ├── torso.urdf
│   ├── left_arm.urdf
│   ├── right_arm.urdf
│   ├── visual/
│   └── collision/
└── OpenArm/
		├── robot.urdf
		├── torso.urdf
		├── left_arm.urdf
		├── right_arm.urdf
		├── visual/
		│   ├── torso/
		│   ├── left_arm/
		│   ├── right_arm/
		│   └── hand/
		└── collision/
				├── torso/
				├── left_arm/
				├── right_arm/
				└── hand/
```

## Asset Conventions

- Visual meshes use `.glb` in most models.
- Collision meshes use `.stl`.
- Mesh file paths in URDF are relative to each robot folder.
- Part URDF files are extracted subsets and are intended for modular loading.

## Usage Notes

- Load full robots from each `robot.urdf`.
- Load sub-assemblies from `torso.urdf`, `left_arm.urdf`, or `right_arm.urdf`
	when testing isolated components.
- Keep directory structure unchanged so relative mesh references remain valid.

## Maintenance Notes

- Avoid renaming mesh files unless all corresponding URDF references are updated.
- Preserve inertia, mass, and joint axis data unless values are re-validated.
- If assets are regenerated from CAD/export tools, keep this README and URDF
	comments synchronized with the new layout.
