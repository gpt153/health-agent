"""Unit tests for authentication utilities"""
import pytest
from src.utils.auth import is_admin


class TestIsAdmin:
    """Test suite for is_admin function"""

    def test_is_admin_with_correct_string_id(self):
        """Test admin check with correct string ID"""
        assert is_admin("7376426503") is True

    def test_is_admin_with_correct_integer_id(self):
        """Test admin check with correct integer ID (type normalization)"""
        assert is_admin(7376426503) is True

    def test_is_admin_with_whitespace(self):
        """Test admin check handles leading/trailing whitespace"""
        assert is_admin(" 7376426503 ") is True
        assert is_admin("\t7376426503\n") is True
        assert is_admin("  7376426503") is True

    def test_is_admin_with_non_admin_string(self):
        """Test admin check returns False for non-admin user"""
        assert is_admin("12345") is False
        assert is_admin("1234567890") is False

    def test_is_admin_with_non_admin_integer(self):
        """Test admin check returns False for non-admin integer"""
        assert is_admin(12345) is False
        assert is_admin(1234567890) is False

    def test_is_admin_with_none(self):
        """Test admin check handles None gracefully"""
        assert is_admin(None) is False

    def test_is_admin_with_empty_string(self):
        """Test admin check handles empty string"""
        assert is_admin("") is False
        assert is_admin("   ") is False

    def test_is_admin_case_sensitivity(self):
        """Test that admin check is case-sensitive (IDs are numeric)"""
        # This ensures we don't accidentally match wrong IDs
        assert is_admin("7376426503") is True
        # These should all be False (wrong IDs)
        assert is_admin("7376426504") is False
        assert is_admin("073764265903") is False


class TestIsAdminEdgeCases:
    """Test edge cases and special scenarios"""

    def test_is_admin_with_float(self):
        """Test admin check with float (should convert to string)"""
        # Floats should work but will have decimal point
        # This is an edge case - telegram IDs are always integers
        result = is_admin(7376426503.0)
        # The string conversion will be "7376426503.0" which won't match
        # This is expected behavior
        assert result is False

    def test_is_admin_with_scientific_notation(self):
        """Test that large numbers in scientific notation don't match"""
        # This ensures we don't accidentally match wrong format
        assert is_admin("7.376426503e9") is False

    def test_is_admin_type_consistency(self):
        """Test that different valid representations all work"""
        # All valid representations of the admin ID
        valid_representations = [
            "7376426503",
            7376426503,
            " 7376426503",
            "7376426503 ",
            "\t7376426503\t",
        ]

        for representation in valid_representations:
            assert is_admin(representation) is True, (
                f"Failed for representation: {representation!r}"
            )
