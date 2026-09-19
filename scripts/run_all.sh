#!/usr/bin/env bash
#
# Full pipeline, in order. The CFD stage needs OpenFOAM v2312 and writes the
# ~27 GB database; every later stage reads that database. Run a single stage
# with e.g.  scripts/run_all.sh surrogates
#
#   design      design of experiments + OpenFOAM case generation
#   cfd         run all 403 interFoam cases (long)
#   metrics     obstacle pressure / wetting metrics from every case
#   surrogates  scalar surrogate training + response-surface plots
#   field       alpha.water snapshot dataset + POD field surrogate
#   media       showcase GIFs
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python3}"
STAGES=("${@:-design cfd metrics surrogates field media}")

run() { echo; echo ">>> $*"; "$@"; }

for stage in ${STAGES[@]}; do
    case "$stage" in
        design)
            run "$PYTHON" scripts/create_surrogate_doe_design.py
            run "$PYTHON" scripts/generate_surrogate_database_cases.py ;;
        cfd)
            run bash scripts/run_surrogate_database_all.sh ;;
        metrics)
            run "$PYTHON" scripts/extract_surrogate_database_metrics.py
            run "$PYTHON" scripts/compute_robust_peak_metrics.py ;;
        surrogates)
            run "$PYTHON" scripts/train_robust_surrogate_models.py
            run "$PYTHON" scripts/plot_final_surrogate_response_surfaces.py ;;
        field)
            run "$PYTHON" scripts/build_alpha_field_surrogate_dataset.py
            run "$PYTHON" scripts/train_alpha_pod_timeslice_surrogate_200m.py ;;
        media)
            run "$PYTHON" scripts/make_final_showcase_alpha_surrogate_gif_200m.py
            run "$PYTHON" scripts/make_response_surface_gifs.py
            run "$PYTHON" scripts/make_best_design_explorer_gifs.py ;;
        *)
            echo "unknown stage: $stage" >&2; exit 1 ;;
    esac
done
