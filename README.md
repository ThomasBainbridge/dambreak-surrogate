# Automated OpenFOAM VOF Simulation and Surrogate Modelling of Dam-Break Impact Loads on an Obstacle

![CI](https://github.com/ThomasBainbridge/dambreak-surrogate/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

A CFD + surrogate-modelling study that turns the OpenFOAM `interFoam` dam-break
tutorial into a **fully automated 403-case two-phase VOF database**, extracts
**robust impact-load metrics** on a downstream obstacle, and trains
**scalar surrogates** for design-space exploration and a **POD reduced-order
field surrogate** for the free surface. Both are validated on 60 geometries
that were never used in training.

<p align="center">
  <img src="docs/gifs/FINAL_cfd_vs_pod_surrogate_alpha_field.gif" width="90%"
       alt="CFD vs POD surrogate reconstruction of the water volume fraction for an unseen validation geometry">
  <br>
  <em>CFD (left) vs the 200-mode POD field surrogate (centre) for an unseen
  validation geometry, with the absolute error (right): the bulk surge is
  reproduced, while the sharp interface near the obstacle is smoothed.</em>
</p>

> **Two-page summary for a quick read: [REPORT.md](REPORT.md).**
> **Full results write-up with figures: [RESULTS.md](RESULTS.md).**

```
 OpenFOAM damBreak case (interFoam, laminar, VOF)
   -> 403-case design (7x7x7 training grid + 60 off-grid LHS validation cases)
      -> automated case generation + batch CFD (403/403 completed)
         -> robust impact metrics (rolling peaks, impulses, wetting time)
            -> scalar surrogates (10 model families x raw/log targets)
               -> POD field surrogate for alpha.water (200 modes, per-time-slice KNN)
                  -> validation on 60 unseen geometries
```

> This is **not** a replacement for CFD. It quantifies which impact quantities
> a cheap surrogate can predict reliably across the design space, which it
> cannot, and how far a linear reduced-order basis can reproduce a sharp,
> moving free surface.

**Status:** complete end-to-end — design of experiments, automated case
generation, 403 `interFoam` runs (every case completed, every mesh passing
`checkMesh`), metric extraction, scalar surrogate selection across 11
impact targets, and a time-sliced POD field surrogate validated on
3 660 unseen snapshots. Headline numbers in [Results](#results); full
walk-through in [RESULTS.md](RESULTS.md).

---

## Why this project

The load a dam-break surge puts on a structure is expensive to compute: every
design point is a transient two-phase VOF simulation, and the quantities that
matter (peak pressure, impulse, when the structure first gets wet) come from a
violent, short-lived impact. This project asks how much of that behaviour can
be captured by **surrogates trained on a systematically designed CFD
database**. Which load metrics are smooth enough to predict across the design
space? Which are dominated by transient spikes? How well can a **reduced-order
field model** reproduce the evolving free surface on geometries it has never
seen? The answers are reported honestly, including where the surrogates fail.

---

## Problem

A column of water collapses under gravity, surges along the channel floor and
strikes a rectangular obstacle. The transient hydraulic load on the obstacle
depends on the water-column height and on the obstacle's height and position.
The goal is to map that dependence efficiently from high-fidelity CFD, and to
test whether surrogates generalise to unseen geometries.

**Solver:** OpenFOAM v2312 `interFoam`: laminar, 2-D, VOF (`alpha.water`),
adaptive time step (Co ≤ 0.25).
**Domain:** 0.584 m × 0.584 m tank, water column 0.146 m wide, obstacle
0.024 m wide; ~9 000 cells for the reference geometry (3 mm cells around
the obstacle).
**Run:** 1.5 s per case; fields every 0.025 s (61 snapshots), obstacle pressure
every 0.005 s.

## Governing equations

The `interFoam` solver uses a Volume of Fluid (VOF) method to track the
water–air interface.

**Volume fraction transport**

$$\frac{\partial \alpha}{\partial t} + \nabla \cdot (\alpha \mathbf{U}) + \nabla \cdot \left[\alpha(1-\alpha)\mathbf{U}_r\right] = 0$$

The third term is the interface-compression term that keeps the interface
sharp without explicit reconstruction; $\mathbf{U}_r$ is active only where
$\alpha(1-\alpha) \neq 0$.

**Mixture properties**

$$\rho = \alpha\rho_w + (1-\alpha)\rho_a \qquad \mu = \alpha\mu_w + (1-\alpha)\mu_a$$

**Continuity and momentum**

$$\nabla \cdot \mathbf{U} = 0$$

$$\frac{\partial (\rho \mathbf{U})}{\partial t} + \nabla \cdot (\rho \mathbf{U} \otimes \mathbf{U}) = -\nabla p + \nabla \cdot \left[\mu \left(\nabla \mathbf{U} + \nabla \mathbf{U}^T\right)\right] + \rho \mathbf{g} + \mathbf{f}_\sigma$$

**Surface tension** (Continuum Surface Force model, Brackbill et al. 1992) and
the **modified pressure** OpenFOAM solves for:

$$\mathbf{f}_\sigma = \sigma \kappa \nabla \alpha \qquad\qquad p_{rgh} = p - \rho \mathbf{g} \cdot \mathbf{x}$$

$p_{rgh}$ removes the hydrostatic contribution and is the obstacle pressure
reported throughout. $\alpha$: water volume fraction; $\mathbf{U}$: velocity;
$\rho$, $\mu$: mixture density and viscosity; $\sigma = 0.07$ N/m;
$\kappa$: interface curvature; $\mathbf{g}$: gravity.

## Design of experiments

Three geometric parameters are varied; the obstacle width is fixed.

| Parameter | Symbol | Range |
|---|---|---|
| Initial water-column height | H | 0.240 – 0.365 m |
| Obstacle height | h | 0.030 – 0.072 m |
| Obstacle front position | x | 0.220 – 0.380 m |

- **343 training cases** on a 7 × 7 × 7 full-factorial grid.
- **60 validation cases** by Latin hypercube sampling, nudged off the grid and
  held out of all training.

The design is seeded and regenerates exactly (checked by the test suite). The
resulting database is 403 cases, ~27 GB, 24 583 free-surface snapshots.

---

## Repository layout

```
.
├── cases/
│   └── damBreak_template/    # base interFoam case every design point is generated from
├── scripts/                  # the pipeline, in run order (see scripts/run_all.sh)
│   ├── create_surrogate_doe_design.py        # 343 grid + 60 LHS design
│   ├── generate_surrogate_database_cases.py  # one OpenFOAM case per design point
│   ├── run_surrogate_database_all.sh         # batch blockMesh/setFields/interFoam
│   ├── extract_surrogate_database_metrics.py # peaks, impulses, wetting times
│   ├── compute_robust_peak_metrics.py        # rolling-window / top-fraction peaks
│   ├── train_robust_surrogate_models.py      # 10 model families, select per target
│   ├── plot_final_surrogate_response_surfaces.py
│   ├── build_alpha_field_surrogate_dataset.py    # alpha.water -> 96x96 snapshots
│   ├── train_alpha_pod_timeslice_surrogate_200m.py # POD + per-time-slice KNN
│   ├── make_*_gifs.py        # showcase animations
│   └── run_all.sh            # whole pipeline, or one stage at a time
├── results/                  # extracted CFD metrics, surrogate outputs, summaries (committed)
├── docs/figures/, docs/gifs/ # committed showcase figures (README, RESULTS)
├── tests/                    # pytest suite (design, case generation, metrics)
├── parametric_study/         # generated 403-case CFD database (~27 GB, git-ignored)
├── .github/workflows/ci.yml  # pytest on push/PR
├── REPORT.md / RESULTS.md    # summary / full results write-up
├── pyproject.toml            # project metadata + [dev] extra
└── requirements.txt          # (+ requirements-lock.txt: exact tested versions)
```

The CFD database itself is not version-controlled. The metrics extracted from
it are committed, so every surrogate result can be re-trained without
OpenFOAM.

---

## Quickstart

Requires Python ≥ 3.10; the CFD stage additionally needs OpenFOAM v2312
(WSL/Linux; set `OPENFOAM_BASHRC` if it is not at the default path).

```bash
# 1. Python environment + tests (no OpenFOAM needed)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest -q

# 2. Re-train the scalar surrogates from the committed CFD metrics
python scripts/train_robust_surrogate_models.py
python scripts/plot_final_surrogate_response_surfaces.py

# 3. Full pipeline from scratch (OpenFOAM; the CFD stage is long-running)
scripts/run_all.sh                     # design cfd metrics surrogates field media
scripts/run_all.sh design cfd          # or any subset of stages
```

---

## Results

Full walk-through with every figure: **[RESULTS.md](RESULTS.md)**. Headlines,
all on the **60 unseen validation geometries**:

- **Time-windowed and integrated loads are highly predictable**: 0.050 s
  rolling peak of the local maximum pressure R² = **0.997** (1.5 % nRMSE),
  area-average pressure impulse **0.980**, first wetting time **0.974**.
- **Instantaneous-style peaks are not**: the mean of the top 1 % of
  area-average pressure samples reaches only R² = **0.15**. The shorter or
  spikier the peak definition, the worse the best surrogate does.
- **No single model family wins**: polynomial ridge is selected for 6 of the
  11 targets, with KNN, RBF-SVR and a Gaussian process for the rest.
- **The POD field surrogate** (200 modes, 93.6 % variance) reproduces the free
  surface with mean α-RMSE **0.091**, water-region IoU **0.85** and 1.8 %
  volume error. Its error peaks during the obstacle impact (t ≈ 0.6–1.0 s).

![Selected surrogate validation R²](docs/figures/final_selected_surrogate_validation_r2.png)

The honest through-line: **averaging over a time window or integrating over
the impact turns an unpredictable load into a predictable one**. The raw
instantaneous peak is set by short, local splash events that a smooth
surrogate over three geometric inputs cannot resolve.

---

## Future Work

Three directions follow from the results. First, a **nonlinear field
surrogate** (local POD per flow regime, or a convolutional autoencoder), since
the linear POD basis smooths the sharp VOF interface exactly where the impact
happens. Second, **probabilistic surrogates for the spiky peak metrics**:
predict a distribution of peak pressure (for example with Gaussian-process
variance or quantile regression) rather than one number, because the
instantaneous peak behaves like a noisy extreme-value quantity. Third, **3-D
and turbulent impact**, checking whether the robust-metric conclusions survive
once the flow is no longer laminar and two-dimensional.

---

## Limitations

- **2-D, laminar, one mesh.** The flow is quasi-2-D and laminar; no
  mesh-independence study was run on the impact pressures, which are the
  quantities most sensitive to resolution.
- **Model selection uses the validation set.** For each target the best of
  20 model/transform combinations is chosen by validation nRMSE, and that same
  score is reported, so the headline R² values are mildly optimistic. There is
  no separate test set.
- **Three inputs only.** Obstacle width, fluid properties and tank size are
  fixed; the surrogates interpolate within the sampled box and are not
  validated outside it.
- **The POD field surrogate is an approximation.** Error concentrates at the
  moving interface near the obstacle, at wall contact and in thin films. Some
  field-diagnostic figures (error over time, IoU, interface error) are curated
  outputs whose generating script is not in the repository.
- **The database is not redistributed.** Re-running from scratch needs the
  ~27 GB CFD database, which must be regenerated with OpenFOAM.

---

## License

MIT — see [LICENSE](LICENSE). The OpenFOAM case is derived from the OpenFOAM
v2312 `damBreak` tutorial and inherits its GPL where applicable.
