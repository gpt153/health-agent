"""
Tracker entry validation utilities.
Validates tracker entries against their field definitions at runtime.
"""
import re
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, time as time_type, date as date_type

from src.models.tracking import (
    TrackerDefinition,
    FieldType,
    FieldConfig,
    NumberFieldConfig,
    RatingFieldConfig,
    TextFieldConfig,
    BooleanFieldConfig,
    DateFieldConfig,
    TimeFieldConfig,
    DurationFieldConfig,
    MultiselectFieldConfig,
    SingleSelectFieldConfig
)


class TrackerValidator:
    """Validates tracker entries against their definition"""

    @staticmethod
    def validate_entry(
        definition: TrackerDefinition,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, str]]]:
        """
        Validate entry data against tracker definition.

        Args:
            definition: TrackerDefinition with field schemas
            data: Dictionary of field_name -> value pairs

        Returns:
            Tuple of (is_valid, error_message, validation_details)
            - is_valid: True if all validations pass
            - error_message: Summary error message if invalid
            - validation_details: Dict of field_name -> error_message for each invalid field
        """
        errors: Dict[str, str] = {}

        # Check required fields
        for field_name, field_config in definition.fields.items():
            if field_config.required and field_name not in data:
                errors[field_name] = "Required field missing"

        # Validate each provided field
        for field_name, value in data.items():
            if field_name not in definition.fields:
                errors[field_name] = "Unknown field (not in tracker definition)"
                continue

            field_config = definition.fields[field_name]

            # Validate based on field type
            error = TrackerValidator._validate_field_value(field_config, value)
            if error:
                errors[field_name] = error

        # Determine overall status
        is_valid = len(errors) == 0
        error_msg = None if is_valid else f"Validation failed for {len(errors)} field(s)"

        return is_valid, error_msg, errors if not is_valid else None

    @staticmethod
    def _validate_field_value(field_config: FieldConfig, value: Any) -> Optional[str]:
        """
        Validate a single field value against its configuration.

        Returns:
            Error message if invalid, None if valid
        """
        # None values are only valid for optional fields
        if value is None:
            if field_config.required:
                return "Value is required"
            return None

        # Type-specific validation
        if isinstance(field_config, NumberFieldConfig):
            return TrackerValidator._validate_number(field_config, value)
        elif isinstance(field_config, RatingFieldConfig):
            return TrackerValidator._validate_rating(field_config, value)
        elif isinstance(field_config, TextFieldConfig):
            return TrackerValidator._validate_text(field_config, value)
        elif isinstance(field_config, BooleanFieldConfig):
            return TrackerValidator._validate_boolean(field_config, value)
        elif isinstance(field_config, DateFieldConfig):
            return TrackerValidator._validate_date(field_config, value)
        elif isinstance(field_config, TimeFieldConfig):
            return TrackerValidator._validate_time(field_config, value)
        elif isinstance(field_config, DurationFieldConfig):
            return TrackerValidator._validate_duration(field_config, value)
        elif isinstance(field_config, MultiselectFieldConfig):
            return TrackerValidator._validate_multiselect(field_config, value)
        elif isinstance(field_config, SingleSelectFieldConfig):
            return TrackerValidator._validate_single_select(field_config, value)

        return "Unknown field type"

    @staticmethod
    def _validate_number(config: NumberFieldConfig, value: Any) -> Optional[str]:
        """Validate number field"""
        if not isinstance(value, (int, float)):
            return f"Must be a number, got {type(value).__name__}"

        if config.min_value is not None and value < config.min_value:
            return f"Must be >= {config.min_value}"

        if config.max_value is not None and value > config.max_value:
            return f"Must be <= {config.max_value}"

        return None

    @staticmethod
    def _validate_rating(config: RatingFieldConfig, value: Any) -> Optional[str]:
        """Validate rating field"""
        if not isinstance(value, int):
            return f"Must be an integer, got {type(value).__name__}"

        if value < config.min_value:
            return f"Must be >= {config.min_value}"

        if value > config.max_value:
            return f"Must be <= {config.max_value}"

        return None

    @staticmethod
    def _validate_text(config: TextFieldConfig, value: Any) -> Optional[str]:
        """Validate text field"""
        if not isinstance(value, str):
            return f"Must be text, got {type(value).__name__}"

        if config.max_length and len(value) > config.max_length:
            return f"Must be <= {config.max_length} characters (got {len(value)})"

        return None

    @staticmethod
    def _validate_boolean(config: BooleanFieldConfig, value: Any) -> Optional[str]:
        """Validate boolean field"""
        if not isinstance(value, bool):
            return f"Must be true/false, got {type(value).__name__}"
        return None

    @staticmethod
    def _validate_date(config: DateFieldConfig, value: Any) -> Optional[str]:
        """Validate date field"""
        # Accept datetime.date, datetime.datetime, or ISO string
        if isinstance(value, date_type):
            return None

        if isinstance(value, datetime):
            return None

        if isinstance(value, str):
            try:
                # Try parsing ISO format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return None
            except ValueError:
                return "Must be a valid ISO date (YYYY-MM-DD)"

        return f"Must be a date, got {type(value).__name__}"

    @staticmethod
    def _validate_time(config: TimeFieldConfig, value: Any) -> Optional[str]:
        """Validate time field"""
        # Accept time, datetime, or HH:MM string
        if isinstance(value, time_type):
            return None

        if isinstance(value, datetime):
            return None

        if isinstance(value, str):
            # Validate HH:MM format
            if re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', value):
                return None
            return "Must be in HH:MM format (e.g., '14:30')"

        return f"Must be a time, got {type(value).__name__}"

    @staticmethod
    def _validate_duration(config: DurationFieldConfig, value: Any) -> Optional[str]:
        """Validate duration field (e.g., '30min', '2h', '1.5h')"""
        if not isinstance(value, str):
            return f"Must be a duration string, got {type(value).__name__}"

        # Validate duration format: number + unit (min, h, hr, hour, hours, etc.)
        pattern = r'^(\d+(?:\.\d+)?)\s*(min|mins|minute|minutes|h|hr|hrs|hour|hours)$'
        if not re.match(pattern, value.lower()):
            return "Must be a duration (e.g., '30min', '2h', '1.5 hours')"

        return None

    @staticmethod
    def _validate_multiselect(config: MultiselectFieldConfig, value: Any) -> Optional[str]:
        """Validate multiselect field"""
        if not isinstance(value, list):
            return f"Must be a list, got {type(value).__name__}"

        # All values must be strings from the options
        for item in value:
            if not isinstance(item, str):
                return f"All items must be strings, got {type(item).__name__}"
            if item not in config.options:
                return f"Invalid option '{item}'. Must be one of: {', '.join(config.options)}"

        return None

    @staticmethod
    def _validate_single_select(config: SingleSelectFieldConfig, value: Any) -> Optional[str]:
        """Validate single select field"""
        if not isinstance(value, str):
            return f"Must be a string, got {type(value).__name__}"

        if value not in config.options:
            return f"Invalid option '{value}'. Must be one of: {', '.join(config.options)}"

        return None


# Helper functions for common validation scenarios

def validate_and_create_entry(
    definition: TrackerDefinition,
    user_id: str,
    data: Dict[str, Any],
    notes: Optional[str] = None
) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Validate data and create a TrackerEntry if valid.

    Returns:
        Tuple of (success, entry_or_none, error_message)
    """
    from src.models.tracking import TrackerEntry

    # Validate
    is_valid, error_msg, validation_errors = TrackerValidator.validate_entry(definition, data)

    if not is_valid:
        # Create entry with error status for logging
        entry = TrackerEntry(
            user_id=user_id,
            category_id=definition.id,
            data=data,
            notes=notes,
            validation_status="error",
            validation_errors=validation_errors
        )
        return False, entry, error_msg

    # Valid - create entry
    entry = TrackerEntry(
        user_id=user_id,
        category_id=definition.id,
        data=data,
        notes=notes,
        validation_status="valid",
        validation_errors=None
    )

    return True, entry, None
