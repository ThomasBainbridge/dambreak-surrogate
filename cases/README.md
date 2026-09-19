# OpenFOAM case definition

`damBreak_template/` is the base `interFoam` case every database run is
generated from. It began as the OpenFOAM v2312 `damBreak` laminar tutorial,
modified to run for the full 1.5 s impact event, and adds two
`surfaceFieldValue` function objects on the `obstacle` patch
(`obstaclePressureAverage`, `obstaclePressureMaximum`). These write `p_rgh` and
`alpha.water` every 0.005 s.

Its geometry is the reference design point H = 0.292 m, h = 0.048 m,
x = 0.292 m. `scripts/generate_surrogate_database_cases.py` copies it once per
design point and rewrites three files:

| File | What the generator changes |
|---|---|
| `system/blockMeshDict` | domain blocks around the obstacle (height `h`, front position `x`) |
| `system/setFieldsDict` | initial water column (height `H`) |
| `system/controlDict` | `endTime`, field `writeInterval`, function-object `writeInterval` |

To run the template on its own (OpenFOAM v2312 environment sourced):

```bash
cd cases/damBreak_template && ./Allrun
```

Only case definitions live here. Meshes and results are generated locally and
git-ignored.
