"""
Unit tests for custom tracking system (Epic 006)
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.tracking import (
    TrackerDefinition,
    TrackerEntry,
    FieldType,
    NumberFieldConfig,
    RatingFieldConfig,
    TextFieldConfig,
    BooleanFieldConfig,
    MultiselectFieldConfig,
    SingleSelectFieldConfig,
    TrackingSchedule
)
from src.utils.tracker_validation import TrackerValidator, validate_and_create_entry


class TestTrackerDefinition:
    """Test TrackerDefinition model validation"""

    def test_create_valid_tracker(self):
        """Test creating a valid tracker"""
        tracker = TrackerDefinition(
            user_id="test_user",
            name="Energy Tracker",
            icon="⚡",
            fields={
                "level": NumberFieldConfig(
                    label="Energy Level",
                    min_value=1,
                    max_value=10
                )
            }
        )

        assert tracker.name == "Energy Tracker"
        assert tracker.icon == "⚡"
        assert "level" in tracker.fields
        assert tracker.category_type == "custom"

    def test_tracker_requires_at_least_one_field(self):
        """Test that tracker must have at least one field"""
        with pytest.raises(ValueError, match="at least one field"):
            TrackerDefinition(
                user_id="test_user",
                name="Empty Tracker",
                fields={}
            )

    def test_tracker_name_validation(self):
        """Test tracker name cannot be empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            TrackerDefinition(
                user_id="test_user",
                name="   ",
                fields={"test": TextFieldConfig(label="Test")}
            )

    def test_field_name_must_be_identifier(self):
        """Test field names must be valid Python identifiers"""
        with pytest.raises(ValueError, match="Invalid field name"):
            TrackerDefinition(
                user_id="test_user",
                name="Test",
                fields={
                    "invalid field name": TextFieldConfig(label="Test")
                }
            )

    def test_category_type_validation(self):
        """Test category_type must be valid"""
        with pytest.raises(ValueError, match="category_type must be"):
            TrackerDefinition(
                user_id="test_user",
                name="Test",
                fields={"test": TextFieldConfig(label="Test")},
                category_type="invalid"
            )


class TestFieldConfigs:
    """Test field configuration models"""

    def test_number_field_config(self):
        """Test number field configuration"""
        field = NumberFieldConfig(
            label="Weight",
            min_value=0,
            max_value=500,
            unit="kg"
        )

        assert field.type == FieldType.NUMBER
        assert field.label == "Weight"
        assert field.unit == "kg"

    def test_number_field_range_validation(self):
        """Test number field range must be valid"""
        with pytest.raises(ValueError, match="min_value must be"):
            NumberFieldConfig(
                label="Test",
                min_value=100,
                max_value=50
            )

    def test_rating_field_config(self):
        """Test rating field configuration"""
        field = RatingFieldConfig(
            label="Mood",
            min_value=1,
            max_value=5
        )

        assert field.type == FieldType.RATING
        assert field.min_value == 1
        assert field.max_value == 5

    def test_rating_field_validation(self):
        """Test rating field validation"""
        with pytest.raises(ValueError):
            RatingFieldConfig(
                label="Test",
                min_value=5,
                max_value=5
            )

        with pytest.raises(ValueError):
            RatingFieldConfig(
                label="Test",
                min_value=-1,
                max_value=10
            )

    def test_multiselect_field_config(self):
        """Test multiselect field configuration"""
        field = MultiselectFieldConfig(
            label="Symptoms",
            options=["headache", "nausea", "fatigue"]
        )

        assert field.type == FieldType.MULTISELECT
        assert len(field.options) == 3

    def test_multiselect_options_validation(self):
        """Test multiselect options must be unique and non-empty"""
        with pytest.raises(ValueError, match="cannot be empty"):
            MultiselectFieldConfig(
                label="Test",
                options=[]
            )

        with pytest.raises(ValueError, match="must be unique"):
            MultiselectFieldConfig(
                label="Test",
                options=["option1", "option1"]
            )


class TestTrackerSchedule:
    """Test tracking schedule validation"""

    def test_valid_schedule(self):
        """Test creating a valid schedule"""
        schedule = TrackingSchedule(
            type="daily",
            time="08:00",
            days=[0, 1, 2, 3, 4],
            message="Time to log!"
        )

        assert schedule.time == "08:00"
        assert len(schedule.days) == 5

    def test_time_format_validation(self):
        """Test time must be in HH:MM format"""
        with pytest.raises(ValueError, match="HH:MM format"):
            TrackingSchedule(
                type="daily",
                time="8:00",
                message="Test"
            )

        with pytest.raises(ValueError, match="HH:MM format"):
            TrackingSchedule(
                type="daily",
                time="25:00",
                message="Test"
            )

    def test_days_validation(self):
        """Test days must be 0-6"""
        with pytest.raises(ValueError, match="0-6"):
            TrackingSchedule(
                type="weekly",
                time="09:00",
                days=[0, 7, 8],
                message="Test"
            )


class TestTrackerValidator:
    """Test tracker entry validation"""

    def setup_method(self):
        """Set up test tracker"""
        self.tracker = TrackerDefinition(
            user_id="test_user",
            name="Test Tracker",
            fields={
                "level": NumberFieldConfig(
                    label="Level",
                    min_value=1,
                    max_value=10
                ),
                "mood": RatingFieldConfig(
                    label="Mood",
                    min_value=1,
                    max_value=5
                ),
                "notes": TextFieldConfig(
                    label="Notes",
                    required=False
                ),
                "symptoms": MultiselectFieldConfig(
                    label="Symptoms",
                    options=["headache", "nausea", "fatigue"],
                    required=False
                )
            }
        )

    def test_validate_valid_entry(self):
        """Test validating a valid entry"""
        data = {
            "level": 7,
            "mood": 4,
            "notes": "Feeling good"
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert is_valid
        assert error_msg is None
        assert errors is None

    def test_validate_missing_required_field(self):
        """Test validation fails for missing required field"""
        data = {
            "level": 7
            # Missing required 'mood' field
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert not is_valid
        assert "mood" in errors
        assert "Required field missing" in errors["mood"]

    def test_validate_out_of_range_number(self):
        """Test validation fails for out-of-range number"""
        data = {
            "level": 15,  # Max is 10
            "mood": 3
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert not is_valid
        assert "level" in errors
        assert "Must be <=" in errors["level"]

    def test_validate_wrong_type(self):
        """Test validation fails for wrong type"""
        data = {
            "level": "seven",  # Should be number
            "mood": 3
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert not is_valid
        assert "level" in errors
        assert "Must be a number" in errors["level"]

    def test_validate_unknown_field(self):
        """Test validation fails for unknown field"""
        data = {
            "level": 7,
            "mood": 3,
            "unknown_field": "test"
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert not is_valid
        assert "unknown_field" in errors

    def test_validate_multiselect_valid(self):
        """Test multiselect validation with valid options"""
        data = {
            "level": 5,
            "mood": 3,
            "symptoms": ["headache", "fatigue"]
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert is_valid

    def test_validate_multiselect_invalid_option(self):
        """Test multiselect validation with invalid option"""
        data = {
            "level": 5,
            "mood": 3,
            "symptoms": ["headache", "invalid_symptom"]
        }

        is_valid, error_msg, errors = TrackerValidator.validate_entry(
            self.tracker,
            data
        )

        assert not is_valid
        assert "symptoms" in errors
        assert "Invalid option" in errors["symptoms"]


class TestValidateAndCreateEntry:
    """Test validate_and_create_entry helper function"""

    def test_create_valid_entry(self):
        """Test creating entry from valid data"""
        tracker = TrackerDefinition(
            user_id="test_user",
            name="Energy",
            fields={
                "level": NumberFieldConfig(label="Level", min_value=1, max_value=10)
            }
        )

        success, entry, error = validate_and_create_entry(
            definition=tracker,
            user_id="test_user",
            data={"level": 8}
        )

        assert success
        assert entry is not None
        assert entry.validation_status == "valid"
        assert error is None

    def test_create_entry_with_validation_error(self):
        """Test creating entry with validation errors"""
        tracker = TrackerDefinition(
            user_id="test_user",
            name="Energy",
            fields={
                "level": NumberFieldConfig(label="Level", min_value=1, max_value=10)
            }
        )

        success, entry, error = validate_and_create_entry(
            definition=tracker,
            user_id="test_user",
            data={"level": 15}  # Out of range
        )

        assert not success
        assert entry is not None
        assert entry.validation_status == "error"
        assert entry.validation_errors is not None
        assert error is not None


@pytest.mark.asyncio
class TestTrackerIntegration:
    """Integration tests requiring database (mark with @pytest.mark.integration)"""

    # These tests would require database setup
    # Marked for future implementation when test database is configured

    async def test_create_and_retrieve_tracker(self):
        """Test creating and retrieving a tracker from database"""
        pytest.skip("Requires database setup")

    async def test_save_and_query_entries(self):
        """Test saving and querying tracker entries"""
        pytest.skip("Requires database setup")

    async def test_tracker_aggregates(self):
        """Test tracker aggregate functions"""
        pytest.skip("Requires database setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
