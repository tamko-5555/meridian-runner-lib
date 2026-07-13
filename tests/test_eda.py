import json

import pytest
from meridian.model.eda import meridian_eda

from runner_lib import eda, io, synthetic


def _rec(sev):
    return eda.FindingRecord(check_type="X", severity=sev, cause="NONE", explanation="e")


def test_has_error_findings_gate_logic():
    assert eda.has_error_findings([_rec("INFO"), _rec("ERROR")]) is True
    assert eda.has_error_findings([_rec("INFO"), _rec("ATTENTION")]) is False
    assert eda.has_error_findings([]) is False


def test_run_eda_normal_model_has_no_error(unfitted_mmm):
    _, result = eda.run_eda(unfitted_mmm, "normal", n_draws_prior=10)
    assert result.has_error is False
    assert len(result.findings) > 0
    assert set(result.severity_counts) <= {"INFO", "ATTENTION", "ERROR"}


def test_run_eda_broken_model_has_error():
    mmm = synthetic.build_unfitted_model(synthetic.make_synthetic_df(duplicate_channels=True))
    _, result = eda.run_eda(mmm, "broken", n_draws_prior=10)
    assert result.has_error is True


def test_run_eda_national_model_skips_geo_checks():
    # n_geos=1 で構築すると meridian は national モデルと判定する
    # (Meridian.is_national は model_context.n_geos == 1)。
    # geo 専用チェック (geo_cost_per_media_unit / geo_pairwise_correlation /
    # geo_stdev) は inapplicable として例外を送出するが、run_eda はクラッシュ
    # せずにそれらをスキップし、他のチェックの findings を返す必要がある。
    mmm = synthetic.build_unfitted_model(synthetic.make_synthetic_df(n_geos=1))
    assert mmm.is_national is True
    _, result = eda.run_eda(mmm, "national", n_draws_prior=10)
    assert result.has_error is False
    assert len(result.findings) > 0


def test_run_eda_propagates_unexpected_check_error(monkeypatch, unfitted_mmm):
    # geo_stdev_check_outcome プロパティが inapplicable 以外の想定外の例外
    # (RuntimeError) を送出した場合、_collect_outcomes はそれを握りつぶさず
    # run_eda 呼び出し元まで伝播させる (fail-closed) ことを確認する。
    def _boom(self):
        raise RuntimeError("unexpected check failure")

    monkeypatch.setattr(meridian_eda.MeridianEDA, "geo_stdev_check_outcome", property(_boom))

    with pytest.raises(RuntimeError, match="unexpected check failure"):
        eda.run_eda(unfitted_mmm, "normal", n_draws_prior=10)


def test_save_eda_artifacts(tmp_path, unfitted_mmm):
    eda_obj, result = eda.run_eda(unfitted_mmm, "normal", n_draws_prior=10)
    json_path, html_path = eda.save_eda_artifacts(eda_obj, result, tmp_path)
    assert json_path == io.eda_json_path(tmp_path, "normal")
    assert html_path == io.eda_html_path(tmp_path, "normal")
    payload = json.loads(json_path.read_text())
    assert payload["setup"] == "normal"
    assert payload["has_error"] is False
    assert isinstance(payload["findings"], list)
    assert html_path.stat().st_size > 0
