"""完全版 binpb 用の分析 Spec 群(complete_model_geo からの 1.7 移植)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from meridian.analysis import optimizer
from meridian.analysis.tensors import DataTensors
from meridian.model import model
from meridian.schema.processors import (
    budget_optimization_processor,
    common,
    marketing_processor,
    model_fit_processor,
)

from runner_lib import periods

NONPAID_GRID = (0.0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0)
FIXED_BUDGET_RATIOS = (0.5, 0.8, 1.2, 1.5, 2.0)


def _nonpaid_marketing_spec(tag: str, new_data: DataTensors, confidence_level: float):
    return marketing_processor.MarketingAnalysisSpec(
        date_interval_tag=tag,
        media_summary_spec=marketing_processor.MediaSummarySpec(
            aggregate_times=True,
            marginal_roi_by_reach=True,
            include_non_paid_channels=True,
            new_data=new_data,
        ),
        confidence_level=confidence_level,
    )


def build_nonpaid_scenario_specs(
    mmm: model.Meridian,
    grid: tuple[float, ...] = NONPAID_GRID,
    confidence_level: float = 0.9,
) -> list:
    """organic_media / non_media_treatments の各チャネル × 各倍率のシナリオ Spec."""
    input_data = mmm.input_data
    time_values = input_data.time.values
    result = []

    if input_data.organic_media is not None:
        tensor = np.asarray(input_data.organic_media)
        for ch_idx, ch_name in enumerate(input_data.organic_media_channel.values):
            for ratio in grid:
                scaled = tensor.copy()
                scaled[:, :, ch_idx] = tensor[:, :, ch_idx] * ratio
                result.append(
                    _nonpaid_marketing_spec(
                        f"organic_media__{ch_name}__{int(ratio * 100)}pct",
                        DataTensors(organic_media=scaled, time=time_values),
                        confidence_level,
                    )
                )

    if input_data.non_media_treatments is not None:
        tensor = np.asarray(input_data.non_media_treatments)
        for ch_idx, ch_name in enumerate(input_data.non_media_channel.values):
            col = tensor[:, :, ch_idx].ravel()
            unique_vals = np.unique(col[np.isfinite(col)])
            is_binary = unique_vals.size <= 2 and set(np.round(unique_vals, 6)).issubset({0.0, 1.0})
            for ratio in (0.0, 1.0) if is_binary else grid:
                scaled = tensor.copy()
                scaled[:, :, ch_idx] = tensor[:, :, ch_idx] * ratio
                result.append(
                    _nonpaid_marketing_spec(
                        f"non_media__{ch_name}__{int(ratio * 100)}pct",
                        DataTensors(non_media_treatments=scaled, time=time_values),
                        confidence_level,
                    )
                )

    return result


def build_analysis_specs(
    mmm: model.Meridian,
    *,
    cost_rate: float = 0.0,
    confidence_level: float = 0.9,
) -> list:
    """完全版 binpb に含める全 Spec を組み立てる."""
    available_dates = pd.to_datetime(mmm.input_data.time.values)
    start, end = periods.default_analysis_period(available_dates)
    start_d, end_d = start.date(), end.date()
    period_str = f"{start:%Y%m}-{end:%Y%m}"

    input_data = mmm.input_data
    total_budget = periods.total_spend(input_data)
    period_budget = periods.total_spend(input_data, start, end)
    channel_budgets = periods.spend_by_channel(input_data, start, end)
    ideal_mroi = round(1.0 / (1.0 - cost_rate), 4)

    result: list = [model_fit_processor.ModelFitSpec()]

    result.append(
        marketing_processor.MarketingAnalysisSpec(
            date_interval_tag="full_period",
            media_summary_spec=marketing_processor.MediaSummarySpec(
                aggregate_times=True,
                marginal_roi_by_reach=True,
                include_non_paid_channels=True,
            ),
            response_curve_spec=marketing_processor.ResponseCurveSpec(by_reach=True),
            confidence_level=confidence_level,
        )
    )

    result.extend(build_nonpaid_scenario_specs(mmm, confidence_level=confidence_level))

    def _fixed(name_suffix: str, grid_suffix: str, budget: float, constraints=()):
        return budget_optimization_processor.BudgetOptimizationSpec(
            optimization_name=f"fixed_{name_suffix}",
            grid_name=f"grid_fixed_{grid_suffix}",
            start_date=start_d,
            end_date=end_d,
            date_interval_tag=period_str,
            scenario=optimizer.FixedBudgetScenario(total_budget=budget),
            kpi_type=common.KpiType.REVENUE,
            constraints=list(constraints),
            include_response_curves=True,
            confidence_level=confidence_level,
        )

    result.append(_fixed(period_str, period_str, period_budget))
    for ratio in FIXED_BUDGET_RATIOS:
        result.append(
            _fixed(
                f"{int(ratio * 100)}pct_of_{period_str}",
                f"{int(ratio * 100)}pct_of_{period_str}",
                period_budget * ratio,
            )
        )

    conservative = [
        budget_optimization_processor.ChannelConstraintRel(
            channel_name=ch, spend_constraint_lower=0.3, spend_constraint_upper=0.5
        )
        for ch in channel_budgets
    ]
    result.append(
        _fixed(
            f"conservative_constraints_{period_str}",
            "conservative_constraints",
            total_budget,
            conservative,
        )
    )

    def _flexible(name: str, grid_name: str, constraints=()):
        return budget_optimization_processor.BudgetOptimizationSpec(
            optimization_name=name,
            grid_name=grid_name,
            start_date=start_d,
            end_date=end_d,
            date_interval_tag=period_str,
            scenario=optimizer.FlexibleBudgetScenario(
                target_metric="mroi", target_value=ideal_mroi
            ),
            kpi_type=common.KpiType.REVENUE,
            constraints=list(constraints),
            include_response_curves=True,
            confidence_level=confidence_level,
        )

    result.append(
        _flexible(
            f"flexible_target_mroi_{ideal_mroi}_{period_str}",
            f"grid_flexible_mroi_{ideal_mroi}",
        )
    )
    mroi_constraints = [
        budget_optimization_processor.ChannelConstraintRel(
            channel_name=ch, spend_constraint_lower=0.3, spend_constraint_upper=1.0
        )
        for ch in channel_budgets
    ]
    result.append(
        _flexible(
            f"flexible_target_mroi_{ideal_mroi}_constraints_{period_str}",
            f"grid_flexible_mroi_{ideal_mroi}_constraints",
            mroi_constraints,
        )
    )

    return result
