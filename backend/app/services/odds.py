from __future__ import annotations

from math import exp


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def poisson_pmf(k: int, lam: float) -> float:
    return (lam ** k) * exp(-lam) / _factorial(k)


def _factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def poisson_outcome_probs(home_lambda: float, away_lambda: float, max_goals: int = 5) -> tuple[float, float, float]:
    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for hg in range(0, max_goals + 1):
        p_hg = poisson_pmf(hg, home_lambda)
        for ag in range(0, max_goals + 1):
            p_ag = poisson_pmf(ag, away_lambda)
            p = p_hg * p_ag
            if hg > ag:
                home_win += p
            elif hg < ag:
                away_win += p
            else:
                draw += p

    total = home_win + draw + away_win
    if total == 0:
        return 0.33, 0.34, 0.33
    return home_win / total, draw / total, away_win / total


def form_to_prob(home_ppg: float, away_ppg: float) -> tuple[float, float, float]:
    diff = _clamp((home_ppg - away_ppg) / 3.0, -1.0, 1.0)
    home = 0.5 + 0.3 * diff
    draw = 0.25 - 0.1 * abs(diff)
    away = 1.0 - home - draw
    home = _clamp(home, 0.05, 0.9)
    away = _clamp(away, 0.05, 0.9)
    draw = _clamp(draw, 0.05, 0.5)
    total = home + draw + away
    return home / total, draw / total, away / total


def blend_probs(a: tuple[float, float, float], b: tuple[float, float, float], weight_a: float = 0.6) -> tuple[float, float, float]:
    w = _clamp(weight_a, 0.0, 1.0)
    home = a[0] * w + b[0] * (1 - w)
    draw = a[1] * w + b[1] * (1 - w)
    away = a[2] * w + b[2] * (1 - w)
    total = home + draw + away
    return home / total, draw / total, away / total


def compute_lambdas(
    home_goals_for: float,
    home_goals_against: float,
    away_goals_for: float,
    away_goals_against: float,
    home_ppg: float,
    away_ppg: float,
) -> tuple[float, float]:
    base_home = 1.35
    base_away = 1.05

    home_strength = (home_goals_for + away_goals_against) / 2.0
    away_strength = (away_goals_for + home_goals_against) / 2.0

    form_adjust = _clamp((home_ppg - away_ppg) / 6.0, -0.15, 0.15)

    home_lambda = _clamp(base_home * home_strength * (1.0 + form_adjust), 0.2, 4.0)
    away_lambda = _clamp(base_away * away_strength * (1.0 - form_adjust), 0.2, 4.0)

    return home_lambda, away_lambda


def compute_odds(
    home_goals_for: float,
    home_goals_against: float,
    home_ppg: float,
    away_goals_for: float,
    away_goals_against: float,
    away_ppg: float,
    home_boost: float = 0.0,
    away_boost: float = 0.0,
) -> tuple[float, float, float, float]:
    home_goals_for = _clamp(home_goals_for + home_boost, 0.4, 3.5)
    away_goals_for = _clamp(away_goals_for + away_boost, 0.4, 3.5)
    home_ppg = _clamp(home_ppg + home_boost * 0.4, 0.5, 2.8)
    away_ppg = _clamp(away_ppg + away_boost * 0.4, 0.5, 2.8)

    home_lambda, away_lambda = compute_lambdas(
        home_goals_for,
        home_goals_against,
        away_goals_for,
        away_goals_against,
        home_ppg,
        away_ppg,
    )

    poisson_probs = poisson_outcome_probs(home_lambda, away_lambda)
    form_probs = form_to_prob(home_ppg, away_ppg)
    blended = blend_probs(poisson_probs, form_probs, weight_a=0.7)

    confidence = max(blended)
    return blended[0], blended[1], blended[2], confidence
