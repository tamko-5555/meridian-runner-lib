# meridian-runner-lib

Batch-estimate and analyze multiple [Google Meridian](https://github.com/google/meridian) MMM setups.

- Flexible binpb loading (`Mmm` / `MmmKernel`)
- Meridian 1.7 EDA gate (skip setups with ERROR findings)
- Subprocess-per-model MCMC (frees GPU memory between models)
- Comparison checks (rhat / R² / MAPE / ModelReviewer health score)
- Full-analysis binpb + geo JSON generation

## Install

    pip install "meridian-runner-lib[colab] @ git+https://github.com/tamko-5555/meridian-runner-lib.git@v0.1.2"

## Usage (from a notebook)

    from runner_lib import orchestrator, checks
    orchestrator.setup_table(INPUT_DIR, OUTPUT_DIR)
    orchestrator.run_all_mcmc(INPUT_DIR, OUTPUT_DIR, n_chains=3, n_adapt=500, n_burnin=750, n_keep=1000)
    checks.summary_table(OUTPUT_DIR)
    orchestrator.run_full_generation("all", OUTPUT_DIR, cost_rate=0.0)

CLI (used internally via subprocess):

    python -m runner_lib.run_mcmc --input setup.binpb --output-dir out/ --setup-name s1 \
        --n-chains 3 --n-adapt 500 --n-burnin 750 --n-keep 1000
    python -m runner_lib.run_full --setup-name s1 --output-dir out/ --cost-rate 0.0
