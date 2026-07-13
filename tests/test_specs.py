from meridian.schema.processors import budget_optimization_processor, marketing_processor

from runner_lib import specs


def test_nonpaid_grid_counts(unfitted_mmm):
    # organic 1ch × 7倍率 + バイナリ non-media 1ch × [0,1] の2倍率 = 9
    result = specs.build_nonpaid_scenario_specs(unfitted_mmm)
    assert len(result) == 7 + 2
    tags = [s.date_interval_tag for s in result]
    assert "organic_media__organic_ch__100pct" in tags
    assert "non_media__promo__0pct" in tags and "non_media__promo__100pct" in tags


def test_build_analysis_specs_composition(fitted_mmm):
    all_specs = specs.build_analysis_specs(fitted_mmm, cost_rate=0.2)
    # ModelFit 1 + Marketing 1 + nonpaid 9 + 固定予算(1+5+制約1) + mROI(1+制約1) = 20
    assert len(all_specs) == 20

    opt_specs = [
        s for s in all_specs if isinstance(s, budget_optimization_processor.BudgetOptimizationSpec)
    ]
    assert len(opt_specs) == 9
    names = [s.optimization_name for s in opt_specs]
    assert len(names) == len(set(names)), "optimization_name は一意であること"
    assert all(s.start_date is not None and s.end_date is not None for s in opt_specs)

    # cost_rate=0.2 → ideal_mroi = 1.25
    assert any("mroi_1.25" in n for n in names)

    marketing = [s for s in all_specs if isinstance(s, marketing_processor.MarketingAnalysisSpec)]
    assert len(marketing) == 1 + 9  # 全期間 1 + nonpaid 9
