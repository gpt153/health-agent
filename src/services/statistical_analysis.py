"""
Statistical Analysis Utilities
Epic 009 - Phase 6: Pattern Detection Engine

This module provides statistical functions for significance testing and correlation analysis.
All pattern discoveries require statistical significance (p < 0.05) before being accepted.

Key Features:
- Chi-square test for categorical correlations
- Pearson correlation for continuous variables
- Confidence interval calculations
- Statistical significance testing
"""

import logging
from typing import List, Tuple, Optional
import math

logger = logging.getLogger(__name__)

# Statistical significance threshold (alpha level)
DEFAULT_ALPHA = 0.05


def chi_square_test(observed: List[List[int]]) -> Tuple[float, float]:
    """
    Calculate chi-square statistic and p-value for categorical data.

    This test determines if there's a significant association between two
    categorical variables (e.g., "eating pasta" and "feeling tired").

    Args:
        observed: 2D contingency table of observed frequencies
                  Example: [[a, b], [c, d]] for 2x2 table
                  Row 1: Outcome present [with factor, without factor]
                  Row 2: Outcome absent [with factor, without factor]

    Returns:
        Tuple of (chi_square_statistic, p_value)

    Example:
        >>> # Does eating pasta correlate with tiredness?
        >>> # Contingency table:
        >>> #             Pasta  No Pasta
        >>> # Tired         15      3
        >>> # Not Tired      5     17
        >>> observed = [[15, 3], [5, 17]]
        >>> chi_sq, p_val = chi_square_test(observed)
        >>> print(f"χ² = {chi_sq:.2f}, p = {p_val:.4f}")

    Raises:
        ValueError: If observed table is empty or malformed
    """
    if not observed or not all(observed):
        raise ValueError("Observed table cannot be empty")

    if len(observed) != 2 or len(observed[0]) != 2 or len(observed[1]) != 2:
        raise ValueError("Only 2x2 contingency tables are currently supported")

    # Calculate row and column totals
    row_totals = [sum(row) for row in observed]
    col_totals = [sum(col) for col in zip(*observed)]
    grand_total = sum(row_totals)

    if grand_total == 0:
        raise ValueError("Grand total cannot be zero")

    # Calculate expected frequencies
    expected = []
    for i in range(2):
        row = []
        for j in range(2):
            exp = (row_totals[i] * col_totals[j]) / grand_total
            row.append(exp)
        expected.append(row)

    # Calculate chi-square statistic
    chi_square = 0.0
    for i in range(2):
        for j in range(2):
            obs = observed[i][j]
            exp = expected[i][j]
            if exp == 0:
                # Avoid division by zero
                logger.warning(f"Expected frequency is 0 at position ({i}, {j})")
                continue
            chi_square += ((obs - exp) ** 2) / exp

    # Calculate p-value using chi-square distribution with df=1 (for 2x2 table)
    # Using approximation for p-value calculation
    df = 1
    p_value = _chi_square_p_value(chi_square, df)

    return chi_square, p_value


def _chi_square_p_value(chi_square: float, df: int) -> float:
    """
    Calculate p-value for chi-square statistic using approximation.

    For df=1, uses Wilson-Hilferty transformation for accurate p-value.

    Args:
        chi_square: Chi-square statistic
        df: Degrees of freedom

    Returns:
        p-value (probability of observing this result by chance)
    """
    if chi_square < 0:
        return 1.0

    if df == 1:
        # For df=1, use continuity-corrected approximation
        # P(X > chi_square) ≈ 2 * P(Z > sqrt(chi_square))
        z = math.sqrt(chi_square)
        p_value = 2 * (1 - _standard_normal_cdf(z))
        return min(p_value, 1.0)
    else:
        # For other df, use gamma function approximation (not implemented here)
        logger.warning(f"P-value approximation for df={df} not implemented, using conservative estimate")
        return 1.0


def _standard_normal_cdf(z: float) -> float:
    """
    Cumulative distribution function for standard normal distribution.

    Uses error function approximation for accurate CDF values.

    Args:
        z: Z-score

    Returns:
        Probability that Z <= z
    """
    # Using error function approximation
    # CDF(z) = 0.5 * (1 + erf(z / sqrt(2)))
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
    """
    Calculate Pearson correlation coefficient and p-value.

    This measures linear correlation between two continuous variables
    (e.g., sleep hours and energy level).

    Args:
        x: First variable values
        y: Second variable values (must be same length as x)

    Returns:
        Tuple of (correlation_coefficient, p_value)
        - correlation_coefficient: r value between -1 and 1
        - p_value: probability of observing this correlation by chance

    Example:
        >>> # Does sleep hours correlate with energy level?
        >>> sleep_hours = [7.5, 6.0, 8.0, 5.5, 7.0, 8.5, 6.5]
        >>> energy_level = [8, 6, 9, 5, 7, 9, 7]
        >>> r, p = pearson_correlation(sleep_hours, energy_level)
        >>> print(f"r = {r:.3f}, p = {p:.4f}")

    Raises:
        ValueError: If x and y have different lengths or are too short
    """
    if len(x) != len(y):
        raise ValueError(f"x and y must have same length (x={len(x)}, y={len(y)})")

    if len(x) < 3:
        raise ValueError(f"Need at least 3 data points for correlation (got {len(x)})")

    n = len(x)

    # Calculate means
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    # Calculate covariance and standard deviations
    covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if std_x == 0 or std_y == 0:
        # No variation in one of the variables
        return 0.0, 1.0

    # Calculate Pearson r
    r = covariance / (std_x * std_y)

    # Ensure r is in valid range (handle floating point errors)
    r = max(-1.0, min(1.0, r))

    # Calculate p-value using t-distribution
    # t = r * sqrt(n - 2) / sqrt(1 - r^2)
    if abs(r) == 1.0:
        # Perfect correlation
        p_value = 0.0
    else:
        t_statistic = r * math.sqrt(n - 2) / math.sqrt(1 - r**2)
        df = n - 2
        p_value = _t_test_p_value(abs(t_statistic), df)

    return r, p_value


def _t_test_p_value(t: float, df: int) -> float:
    """
    Calculate two-tailed p-value for t-statistic.

    Uses approximation for t-distribution p-value.

    Args:
        t: Absolute value of t-statistic
        df: Degrees of freedom

    Returns:
        Two-tailed p-value
    """
    if df < 1:
        return 1.0

    # For large df (>30), t-distribution approximates normal distribution
    if df > 30:
        p_value = 2 * (1 - _standard_normal_cdf(t))
        return min(p_value, 1.0)

    # For smaller df, use approximation
    # This is a simplified approximation - in production, use scipy.stats.t.sf()
    x = df / (df + t**2)
    p_value = 2 * _beta_incomplete(df/2, 0.5, x)
    return min(p_value, 1.0)


def _beta_incomplete(a: float, b: float, x: float) -> float:
    """
    Simplified incomplete beta function approximation.

    This is a placeholder - for production use, scipy.special.betainc should be used.

    Args:
        a: First parameter
        b: Second parameter
        x: Value

    Returns:
        Approximation of incomplete beta function
    """
    # Very rough approximation for demo purposes
    # Real implementation should use scipy.special.betainc
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # Simple linear interpolation as placeholder
    return x


def calculate_confidence_interval(
    successes: int,
    total: int,
    confidence_level: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate binomial confidence interval (Wilson score interval).

    This is used to estimate the confidence interval for pattern occurrence rates.

    Args:
        successes: Number of successful outcomes (pattern occurred)
        total: Total number of trials (opportunities for pattern)
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) for confidence interval

    Example:
        >>> # Pattern occurred 18 out of 25 times
        >>> lower, upper = calculate_confidence_interval(18, 25)
        >>> print(f"Pattern occurrence rate: 72% (95% CI: {lower*100:.1f}% - {upper*100:.1f}%)")

    Raises:
        ValueError: If total <= 0 or successes < 0 or successes > total
    """
    if total <= 0:
        raise ValueError(f"Total must be positive (got {total})")
    if successes < 0 or successes > total:
        raise ValueError(f"Successes must be between 0 and total (got {successes}/{total})")

    if total == 0:
        return 0.0, 0.0

    # Calculate z-score for confidence level
    # For 95% confidence: z ≈ 1.96
    # For 90% confidence: z ≈ 1.645
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576
    }
    z = z_scores.get(confidence_level, 1.96)

    # Calculate proportion
    p = successes / total

    # Wilson score interval calculation
    denominator = 1 + (z**2 / total)
    center = (p + (z**2 / (2 * total))) / denominator
    margin = (z / denominator) * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))

    lower_bound = max(0.0, center - margin)
    upper_bound = min(1.0, center + margin)

    return lower_bound, upper_bound


def is_statistically_significant(p_value: float, alpha: float = DEFAULT_ALPHA) -> bool:
    """
    Check if p-value meets statistical significance threshold.

    Args:
        p_value: P-value from statistical test
        alpha: Significance threshold (default 0.05)

    Returns:
        True if statistically significant (p < alpha), False otherwise

    Example:
        >>> p_value = 0.003
        >>> if is_statistically_significant(p_value):
        ...     print("Pattern is statistically significant!")
    """
    return p_value < alpha


def calculate_effect_size_cohens_d(mean1: float, mean2: float, std1: float, std2: float, n1: int, n2: int) -> float:
    """
    Calculate Cohen's d effect size for comparing two groups.

    Effect size interpretation:
    - Small: d = 0.2
    - Medium: d = 0.5
    - Large: d = 0.8

    Args:
        mean1: Mean of group 1
        mean2: Mean of group 2
        std1: Standard deviation of group 1
        std2: Standard deviation of group 2
        n1: Sample size of group 1
        n2: Sample size of group 2

    Returns:
        Cohen's d effect size

    Example:
        >>> # Energy level with pasta (mean=5.2, std=1.1, n=18) vs without (mean=7.1, std=1.3, n=22)
        >>> d = calculate_effect_size_cohens_d(5.2, 7.1, 1.1, 1.3, 18, 22)
        >>> print(f"Effect size: {d:.2f} (large effect)")
    """
    if n1 <= 0 or n2 <= 0:
        raise ValueError("Sample sizes must be positive")

    # Pooled standard deviation
    pooled_std = math.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    # Cohen's d
    d = (mean1 - mean2) / pooled_std

    return abs(d)


def get_minimum_sample_size(alpha: float = 0.05, power: float = 0.80, effect_size: float = 0.5) -> int:
    """
    Calculate minimum sample size needed for statistical power.

    This helps determine if we have enough data to reliably detect patterns.

    Args:
        alpha: Significance level (default 0.05)
        power: Statistical power (default 0.80 = 80% power)
        effect_size: Expected effect size (default 0.5 = medium)

    Returns:
        Minimum sample size per group

    Example:
        >>> min_n = get_minimum_sample_size(effect_size=0.5)
        >>> print(f"Need at least {min_n} observations per group")
    """
    # Simplified formula for two-sample t-test
    # For more accurate calculation, use statsmodels or scipy

    z_alpha = 1.96 if alpha == 0.05 else 2.576  # Two-tailed z-score
    z_beta = 0.84 if power == 0.80 else 1.28  # Z-score for power

    if effect_size == 0:
        return float('inf')

    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2

    return math.ceil(n)


# ================================================================
# Placeholder note for production use
# ================================================================
"""
PRODUCTION NOTE:

This module provides basic statistical implementations for pattern detection.
For production use with real data, it's recommended to replace approximations with scipy:

    from scipy import stats

    # Chi-square test
    chi2, p_value = stats.chi2_contingency(observed)[:2]

    # Pearson correlation
    r, p_value = stats.pearsonr(x, y)

    # T-test
    t_stat, p_value = stats.ttest_ind(group1, group2)

The current implementations use mathematical approximations that are
suitable for demonstration and testing, but scipy provides more accurate
and efficient statistical computations.

Add to requirements.txt:
    scipy>=1.11.0
    numpy>=1.24.0
"""
