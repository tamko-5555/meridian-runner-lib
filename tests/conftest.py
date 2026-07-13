import matplotlib

matplotlib.use("Agg")  # ヘッドレス環境での plot テスト用

import pytest  # noqa: E402

from runner_lib import synthetic  # noqa: E402

# テスト用の極小 MCMC 設定(実測: session 全体で fit 1 回 約80秒)
TINY_MCMC = dict(n_chains=2, n_adapt=20, n_burnin=20, n_keep=20)


@pytest.fixture
def synthetic_df():
    return synthetic.make_synthetic_df()


@pytest.fixture
def unfitted_mmm(synthetic_df):
    return synthetic.build_unfitted_model(synthetic_df)


@pytest.fixture(scope="session")
def fitted_mmm():
    mmm = synthetic.build_unfitted_model(synthetic.make_synthetic_df())
    mmm.sample_prior(10)
    mmm.sample_posterior(seed=1, **TINY_MCMC)
    return mmm


@pytest.fixture(scope="session")
def setup_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("setups")
    synthetic.write_setup_binpb(
        synthetic.build_unfitted_model(synthetic.make_synthetic_df()),
        d / "setup_normal.binpb",
    )
    synthetic.write_setup_binpb(
        synthetic.build_unfitted_model(synthetic.make_synthetic_df(duplicate_channels=True)),
        d / "setup_broken.binpb",
    )
    return d


@pytest.fixture(scope="session")
def posterior_dir(tmp_path_factory, fitted_mmm):
    from meridian.schema.serde import meridian_serde

    d = tmp_path_factory.mktemp("posteriors")
    meridian_serde.save_meridian(fitted_mmm, str(d / "posterior_setup_normal.binpb"))
    return d
