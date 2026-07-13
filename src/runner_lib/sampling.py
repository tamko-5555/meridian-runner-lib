"""MCMC サンプリングのラッパ."""

from __future__ import annotations

import dataclasses

from meridian.model import model


@dataclasses.dataclass
class McmcConfig:
    n_chains: int = 3
    n_adapt: int = 500
    n_burnin: int = 750
    n_keep: int = 1000
    n_prior_draws: int = 500
    seed: int | None = None


def fit(mmm: model.Meridian, config: McmcConfig) -> None:
    mmm.sample_prior(config.n_prior_draws)
    mmm.sample_posterior(
        n_chains=config.n_chains,
        n_adapt=config.n_adapt,
        n_burnin=config.n_burnin,
        n_keep=config.n_keep,
        seed=config.seed,
    )
