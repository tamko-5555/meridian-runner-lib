import json

from runner_lib import checks


def test_coefficient_table(fitted_mmm):
    df = checks.coefficient_table(fitted_mmm)
    assert {"parameter", "channel/dim", "mean", "sd", "2.5%", "97.5%", "r_hat"} <= set(df.columns)
    beta_rows = df[df["parameter"] == "beta_m"]
    assert set(beta_rows["channel/dim"]) == {"ch1", "ch2"}


def test_model_config_summary(fitted_mmm):
    cfg = checks.model_config_summary(fitted_mmm)
    assert cfg["paid_channels"] == ["ch1", "ch2"]
    assert cfg["organic_channels"] == ["organic_ch"]
    assert cfg["non_media_treatments"] == ["promo"]
    assert cfg["controls"] == ["temperature"]
    assert cfg["knots"] == 4 and cfg["max_lag"] == 2


def test_review_model(fitted_mmm):
    status, score = checks.review_model(fitted_mmm)
    assert isinstance(status, str) and isinstance(score, float)


def test_summary_table_and_exports(posterior_dir):
    df = checks.summary_table(posterior_dir)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["setup"] == "setup_normal"
    assert row["rhat_max"] > 0
    assert {"R2", "MAPE", "health_score", "review_status"} <= set(df.columns)

    json_path = checks.export_model_summaries_json(posterior_dir)
    payload = json.loads(json_path.read_text())
    assert "setup_normal" in payload
    assert "coefficients" in payload["setup_normal"]
    assert "config" in payload["setup_normal"]

    csv_path = checks.export_coefficients_csv(posterior_dir)
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8-sig")
    assert "beta_m" in text and "setup_normal" in text
