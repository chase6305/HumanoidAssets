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
├── Dexforce_W1_V2/
│   ├── robot.urdf
│   ├── robot_with_ee.urdf
│   ├── chassis.urdf
│   ├── torso.urdf
│   ├── head.urdf
│   ├── left_arm.urdf / right_arm.urdf
│   ├── left_hand.urdf / right_hand.urdf
│   ├── visual/
│   └── collision/
├── Dexforce_W1_V3/
│   ├── robot.urdf
│   ├── robot_with_ee.urdf
│   ├── chassis.urdf / torso.urdf / head.urdf
│   ├── left_arm.urdf / right_arm.urdf
│   ├── visual/
│   └── collision/
├── Engineai_PM01/
│   ├── urdf/robot.urdf
│   ├── xml/
│   ├── meshes/
│   └── usd/
├── Marvin_M6_S_CCS_696_V4.0/
│   ├── robot.urdf
│   ├── torso.urdf
│   ├── left_arm.urdf
│   ├── right_arm.urdf
│   ├── left_hand.urdf
│   ├── right_hand.urdf
│   ├── robot_with_ee.urdf
│   ├── visual/
│   └── collision/
├── Marvin_M6_S_CCS_696_PRO_V2.0/
│   ├── robot.urdf
│   ├── robot_with_ee.urdf
│   ├── torso.urdf
│   ├── left_arm.urdf
│   ├── right_arm.urdf
│   ├── left_hand.urdf
│   ├── right_hand.urdf
│   ├── visual/
│   └── collision/
└── OpenArm/
    ├── robot.urdf
    ├── torso.urdf
    ├── left_arm.urdf / right_arm.urdf
    ├── visual/
    └── collision/
```

## Model previews

These diagrams are generated from the checked-in robot assets and show the zero-pose visual geometry used by each main URDF.

| Model | Preview |
| --- | --- |
| Dexforce W1 V2 | ![Dexforce W1 V2 preview](Dexforce_W1_V2/preview.png) |
| Dexforce W1 V3 | ![Dexforce W1 V3 preview](Dexforce_W1_V3/preview.png) |
| EngineAI PM01 | ![EngineAI PM01 preview](Engineai_PM01/preview.png) |
| Marvin M6 S CCS 696 V4.0 | ![Marvin M6 V4.0 preview](Marvin_M6_S_CCS_696_V4.0/preview.png) |
| Marvin M6 S CCS 696 Pro V2.0 | ![Marvin M6 Pro V2.0 preview](Marvin_M6_S_CCS_696_PRO_V2.0/preview.png) |
| OpenArm | ![OpenArm preview](OpenArm/preview.png) |

## Asset Conventions

- Visual meshes use `.glb` in most models.
- Collision meshes use `.stl` or `.obj`, according to the model family.
- Mesh file paths in URDF are relative to each robot folder.
- Part URDF files are extracted subsets and are intended for modular loading.

## Usage Notes

- Load full robots from each `robot.urdf`.
- For Marvin with the two-finger hands attached, load
	`Marvin_M6_S_CCS_696_V4.0/robot_with_ee.urdf`.
- Load Marvin Pro M6 V2.0 from
	`Marvin_M6_S_CCS_696_PRO_V2.0/robot.urdf`, or use `robot_with_ee.urdf`
	for the complete model with the V4.0 two-finger grippers attached.
- Load EngineAI PM01 from `Engineai_PM01/urdf/robot.urdf`; its MuJoCo XML
	entry point is `Engineai_PM01/xml/serial_pm01.xml`.
- Load sub-assemblies from `torso.urdf`, `left_arm.urdf`, or `right_arm.urdf`
	when testing isolated components.
- Load Marvin hands independently from `left_hand.urdf` or `right_hand.urdf`;
	their root links are `left_ee` and `right_ee`, respectively.
- Keep directory structure unchanged so relative mesh references remain valid.

## Maintenance Notes

- Avoid renaming mesh files unless all corresponding URDF references are updated.
- Preserve inertia, mass, and joint axis data unless values are re-validated.
- If assets are regenerated from CAD/export tools, keep this README and URDF
	comments synchronized with the new layout.
