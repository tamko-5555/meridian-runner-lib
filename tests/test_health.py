from runner_lib import constants, health


def test_health_detail_table_lists_all_checks(fitted_mmm):
    summary = health.run_review(fitted_mmm)
    df = health.health_detail_table(summary)
    # 総合判定 + 実行対象チェック分の行がある(スキップされたチェックも行として現れる)
    assert len(df) == 1 + len(health.CHECK_LABELS_JA)
    assert df.iloc[0]["チェック"] == "総合判定"
    assert set(df.columns) == {"チェック", "判定", "推奨アクション", "詳細"}
    # 極小MCMCでは未収束→収束以外はスキップされ、理由つきで表示される
    assert (df["判定"] == health.NOT_CONVERGED_MARK).any()
    # 意味のない「未実施」だけの表示はしない
    assert not (df["判定"] == health.SKIPPED_MARK).any()


def test_check_labels_cover_only_executed_battery():
    """run() が実行しないチェック(ImplausibleROI等)を表示対象にしない契約."""
    assert "ImplausibleROICheckResult" not in health.CHECK_LABELS_JA
    assert "HighVarianceCheckResult" not in health.CHECK_LABELS_JA
    assert "PotentialBiasCheckResult" not in health.CHECK_LABELS_JA
    # 条件付きスキップの2チェックには対象外の理由文がある
    assert set(health.NOT_APPLICABLE_MARKS) <= set(health.CHECK_LABELS_JA)


def test_export_health_artifacts(posterior_dir):
    matrix = health.export_health_artifacts(posterior_dir)
    assert not matrix.empty
    assert {"setup", "総合判定", "ヘルススコア"}.issubset(matrix.columns)
    # 全チェックがマトリクスの列に出る
    for label in health.CHECK_LABELS_JA.values():
        assert label in matrix.columns

    out = posterior_dir / constants.CHECKS_DIRNAME / constants.HEALTH_DIRNAME
    files = {p.name for p in out.iterdir()}
    assert "setup_normal_model_health_card.html" in files
    assert "setup_normal_health_checks.csv" in files
    assert "setup_normal_health_checks.png" in files
    assert "health_checks_matrix.csv" in files
    assert "health_checks_matrix.png" in files


def test_export_health_artifacts_empty_dir(tmp_path):
    matrix = health.export_health_artifacts(tmp_path)
    assert matrix.empty
