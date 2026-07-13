import json

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
