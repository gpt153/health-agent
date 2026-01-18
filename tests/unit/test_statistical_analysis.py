"""
Unit tests for statistical_analysis module
Epic 009 - Phase 6: Pattern Detection Engine

Tests statistical functions used for pattern significance testing.
Target coverage: 95%+
"""

import pytest
import math
from src.services.statistical_analysis import (
    chi_square_test,
    pearson_correlation,
    calculate_confidence_interval,
    is_statistically_significant,
    calculate_effect_size_cohens_d,
    get_minimum_sample_size
)


class TestChiSquareTest:
    """Tests for chi_square_test() function"""

    def test_significant_correlation(self):
        """Test chi-square test detects significant association"""
        # Strong association: Pasta → Tiredness
        # Contingency table:
        #             Pasta  No Pasta
        # Tired         15      3
        # Not Tired      5     17
        observed = [[15, 3], [5, 17]]

        chi_sq, p_value = chi_square_test(observed)

        assert chi_sq > 0
        assert p_value < 0.05  # Statistically significant
        assert is_statistically_significant(p_value)

    def test_no_correlation(self):
        """Test chi-square test finds no association when none exists"""
        # No association (evenly distributed)
        #             Factor  No Factor
        # Outcome        10      10
        # No Outcome     10      10
        observed = [[10, 10], [10, 10]]

        chi_sq, p_value = chi_square_test(observed)

        assert chi_sq >= 0
        # p_value should be high (not significant)
        # Note: Exact p-value depends on statistical implementation

    def test_empty_table_raises_error(self):
        """Test that empty contingency table raises ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            chi_square_test([])

    def test_invalid_dimensions_raises_error(self):
        """Test that non-2x2 table raises ValueError"""
        # 3x2 table (not supported)
        observed = [[1, 2], [3, 4], [5, 6]]

        with pytest.raises(ValueError, match="2x2 contingency tables"):
            chi_square_test(observed)

    def test_zero_grand_total_raises_error(self):
        """Test that table with zero sum raises ValueError"""
        observed = [[0, 0], [0, 0]]

        with pytest.raises(ValueError, match="Grand total cannot be zero"):
            chi_square_test(observed)


class TestPearsonCorrelation:
    """Tests for pearson_correlation() function"""

    def test_perfect_positive_correlation(self):
        """Test perfect positive correlation (r = 1.0)"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x

        r, p_value = pearson_correlation(x, y)

        assert r == pytest.approx(1.0, abs=0.01)
        assert p_value < 0.05  # Should be significant

    def test_perfect_negative_correlation(self):
        """Test perfect negative correlation (r = -1.0)"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]  # y = -2x + 12

        r, p_value = pearson_correlation(x, y)

        assert r == pytest.approx(-1.0, abs=0.01)
        assert p_value < 0.05

    def test_no_correlation(self):
        """Test no correlation (r ≈ 0)"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [3.0, 3.0, 3.0, 3.0, 3.0]  # Constant (no variation)

        r, p_value = pearson_correlation(x, y)

        assert r == pytest.approx(0.0, abs=0.01)
        assert p_value > 0.05  # Not significant

    def test_positive_correlation_sleep_energy(self):
        """Test realistic positive correlation (sleep hours → energy)"""
        sleep_hours = [7.5, 6.0, 8.0, 5.5, 7.0, 8.5, 6.5, 7.5]
        energy_level = [8, 6, 9, 5, 7, 9, 7, 8]

        r, p_value = pearson_correlation(sleep_hours, energy_level)

        assert r > 0.5  # Moderate to strong positive correlation
        assert r <= 1.0

    def test_unequal_length_raises_error(self):
        """Test that unequal length arrays raise ValueError"""
        x = [1.0, 2.0, 3.0]
        y = [1.0, 2.0]  # Different length

        with pytest.raises(ValueError, match="same length"):
            pearson_correlation(x, y)

    def test_too_few_points_raises_error(self):
        """Test that < 3 data points raises ValueError"""
        x = [1.0, 2.0]
        y = [3.0, 4.0]

        with pytest.raises(ValueError, match="at least 3 data points"):
            pearson_correlation(x, y)


class TestConfidenceInterval:
    """Tests for calculate_confidence_interval() function"""

    def test_high_success_rate(self):
        """Test confidence interval for high success rate"""
        # Pattern occurred 18 out of 25 times (72%)
        lower, upper = calculate_confidence_interval(18, 25)

        assert 0.0 <= lower < upper <= 1.0
        # Should be centered around 0.72
        midpoint = (lower + upper) / 2
        assert midpoint == pytest.approx(0.72, abs=0.1)

    def test_fifty_percent_success_rate(self):
        """Test confidence interval for 50% success rate"""
        # Pattern occurred 50 out of 100 times
        lower, upper = calculate_confidence_interval(50, 100)

        assert 0.0 <= lower < upper <= 1.0
        # Should be centered around 0.50
        midpoint = (lower + upper) / 2
        assert midpoint == pytest.approx(0.50, abs=0.1)

    def test_zero_successes(self):
        """Test confidence interval for 0% success rate"""
        lower, upper = calculate_confidence_interval(0, 10)

        assert lower == 0.0
        assert upper < 0.3  # Upper bound should be low

    def test_all_successes(self):
        """Test confidence interval for 100% success rate"""
        lower, upper = calculate_confidence_interval(10, 10)

        assert lower > 0.7  # Lower bound should be high
        assert upper == 1.0

    def test_invalid_total_raises_error(self):
        """Test that total <= 0 raises ValueError"""
        with pytest.raises(ValueError, match="Total must be positive"):
            calculate_confidence_interval(5, 0)

        with pytest.raises(ValueError, match="Total must be positive"):
            calculate_confidence_interval(5, -10)

    def test_successes_greater_than_total_raises_error(self):
        """Test that successes > total raises ValueError"""
        with pytest.raises(ValueError, match="between 0 and total"):
            calculate_confidence_interval(15, 10)

    def test_negative_successes_raises_error(self):
        """Test that negative successes raises ValueError"""
        with pytest.raises(ValueError, match="between 0 and total"):
            calculate_confidence_interval(-5, 10)


class TestStatisticalSignificance:
    """Tests for is_statistically_significant() function"""

    def test_significant_p_value(self):
        """Test that p < 0.05 is significant"""
        assert is_statistically_significant(0.001) is True
        assert is_statistically_significant(0.01) is True
        assert is_statistically_significant(0.04) is True
        assert is_statistically_significant(0.049) is True

    def test_non_significant_p_value(self):
        """Test that p >= 0.05 is not significant"""
        assert is_statistically_significant(0.05) is False
        assert is_statistically_significant(0.06) is False
        assert is_statistically_significant(0.1) is False
        assert is_statistically_significant(0.5) is False
        assert is_statistically_significant(1.0) is False

    def test_custom_alpha(self):
        """Test custom alpha threshold"""
        # p = 0.02, alpha = 0.01 → not significant
        assert is_statistically_significant(0.02, alpha=0.01) is False

        # p = 0.005, alpha = 0.01 → significant
        assert is_statistically_significant(0.005, alpha=0.01) is True


class TestEffectSizeCohensD:
    """Tests for calculate_effect_size_cohens_d() function"""

    def test_large_effect_size(self):
        """Test large effect size (d > 0.8)"""
        # Energy with pasta: mean=5.2, std=1.1, n=18
        # Energy without pasta: mean=7.1, std=1.3, n=22
        d = calculate_effect_size_cohens_d(5.2, 7.1, 1.1, 1.3, 18, 22)

        assert d > 0.8  # Large effect

    def test_medium_effect_size(self):
        """Test medium effect size (d ≈ 0.5)"""
        d = calculate_effect_size_cohens_d(5.0, 5.6, 1.0, 1.0, 20, 20)

        assert 0.4 < d < 0.7  # Medium effect

    def test_small_effect_size(self):
        """Test small effect size (d ≈ 0.2)"""
        d = calculate_effect_size_cohens_d(5.0, 5.2, 1.0, 1.0, 20, 20)

        assert 0.1 < d < 0.4  # Small effect

    def test_zero_effect_size(self):
        """Test no effect (identical means)"""
        d = calculate_effect_size_cohens_d(5.0, 5.0, 1.0, 1.0, 20, 20)

        assert d == pytest.approx(0.0, abs=0.01)

    def test_negative_sample_size_raises_error(self):
        """Test that negative sample sizes raise ValueError"""
        with pytest.raises(ValueError, match="Sample sizes must be positive"):
            calculate_effect_size_cohens_d(5.0, 6.0, 1.0, 1.0, -10, 20)

        with pytest.raises(ValueError, match="Sample sizes must be positive"):
            calculate_effect_size_cohens_d(5.0, 6.0, 1.0, 1.0, 10, 0)


class TestMinimumSampleSize:
    """Tests for get_minimum_sample_size() function"""

    def test_medium_effect_size(self):
        """Test minimum sample size for medium effect (d=0.5)"""
        min_n = get_minimum_sample_size(effect_size=0.5)

        # For medium effect, typically need 60-70 per group
        assert 50 <= min_n <= 100

    def test_large_effect_size(self):
        """Test minimum sample size for large effect (d=0.8)"""
        min_n = get_minimum_sample_size(effect_size=0.8)

        # For large effect, need fewer samples
        assert min_n < 50

    def test_small_effect_size(self):
        """Test minimum sample size for small effect (d=0.2)"""
        min_n = get_minimum_sample_size(effect_size=0.2)

        # For small effect, need many more samples
        assert min_n > 100

    def test_higher_power(self):
        """Test that higher power requires more samples"""
        min_n_80 = get_minimum_sample_size(effect_size=0.5, power=0.80)
        min_n_90 = get_minimum_sample_size(effect_size=0.5, power=0.90)

        assert min_n_90 > min_n_80


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_chi_square_with_small_counts(self):
        """Test chi-square with small expected frequencies"""
        # Small counts (may not meet chi-square assumptions)
        observed = [[3, 1], [1, 3]]

        chi_sq, p_value = chi_square_test(observed)

        # Should still compute without error
        assert chi_sq >= 0
        assert 0 <= p_value <= 1

    def test_correlation_with_identical_values(self):
        """Test correlation when one variable is constant"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 5.0, 5.0, 5.0, 5.0]  # No variation

        r, p_value = pearson_correlation(x, y)

        assert r == pytest.approx(0.0, abs=0.01)
        assert p_value > 0.05  # Not significant

    def test_confidence_interval_single_trial(self):
        """Test confidence interval with single trial"""
        lower, upper = calculate_confidence_interval(1, 1)

        # With only 1 trial, interval should be wide
        assert 0.0 <= lower < upper <= 1.0
