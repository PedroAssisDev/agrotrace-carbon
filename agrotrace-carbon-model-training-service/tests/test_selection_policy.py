from model_training_service.evaluation.selection import (
    REGRESSION_BASELINE,
    TIME_SERIES_BASELINE,
    select_against_baseline,
)


def test_baseline_wins_when_complex_does_not_improve():
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 10.0,
            "linear_regression": 10.5,
            "random_forest": 11.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=0.0,
        family="regression",
    )
    assert decision.selected_candidate == REGRESSION_BASELINE
    assert decision.absolute_improvement == 0.0


def test_complex_wins_when_improves_mae():
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 10.0,
            "linear_regression": 9.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=0.0,
        family="regression",
    )
    assert decision.selected_candidate == "linear_regression"
    assert decision.absolute_improvement == 1.0


def test_complex_wins_when_improves_rmse():
    decision = select_against_baseline(
        candidate_scores={
            TIME_SERIES_BASELINE: 5.0,
            "holt": 4.0,
        },
        baseline_name=TIME_SERIES_BASELINE,
        metric_name="rmse",
        minimum_improvement=0.0,
        family="time_series",
    )
    assert decision.selected_candidate == "holt"
    assert decision.metric_name == "rmse"


def test_tie_prefers_simpler_model():
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 8.0,
            "linear_regression": 7.0,
            "random_forest": 7.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=0.0,
        family="regression",
    )
    assert decision.selected_candidate == "linear_regression"


def test_equal_to_baseline_keeps_baseline():
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 3.0,
            "ridge": 3.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=0.0,
        family="regression",
    )
    assert decision.selected_candidate == REGRESSION_BASELINE


def test_positive_threshold_keeps_baseline_when_not_met():
    # baseline=100, candidate=97, threshold=5 → precisa score < 95
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 100.0,
            "linear_regression": 97.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=5.0,
        family="regression",
    )
    assert decision.selected_candidate == REGRESSION_BASELINE
    assert decision.absolute_improvement == 0.0
    assert decision.minimum_improvement_over_baseline == 5.0
    assert "nenhum candidato complexo" in decision.selection_reason.lower()


def test_positive_threshold_allows_complex_when_met():
    # baseline=100, candidate=94, threshold=5 → 94 < 95
    decision = select_against_baseline(
        candidate_scores={
            REGRESSION_BASELINE: 100.0,
            "linear_regression": 94.0,
        },
        baseline_name=REGRESSION_BASELINE,
        metric_name="mae",
        minimum_improvement=5.0,
        family="regression",
    )
    assert decision.selected_candidate == "linear_regression"
    assert decision.absolute_improvement == 6.0
    assert decision.percent_improvement == 6.0
    assert decision.minimum_improvement_over_baseline == 5.0
    assert decision.winner_metric == 94.0
    assert "linear_regression" in decision.selection_reason
