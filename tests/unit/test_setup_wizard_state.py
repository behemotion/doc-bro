"""Unit tests for SetupWizardState model."""

import pytest
from datetime import datetime
from typing import Any, Dict, List
from pydantic import ValidationError

from src.models.installation import SetupWizardState


class TestSetupWizardState:
    """Test cases for SetupWizardState model validation and behavior."""

    def test_valid_setup_wizard_state_creation(self):
        """Test creating a valid SetupWizardState instance."""
        state = SetupWizardState(
            current_step="service_check",
            completed_steps=["welcome", "python_check"],
            services_to_install=["docker", "ollama"],
            user_preferences={"skip_docker": False, "port": 8000},
            skip_services=["qdrant"],
            setup_start_time=datetime.now()
        )

        assert state.current_step == "service_check"
        assert len(state.completed_steps) == 2
        assert "docker" in state.services_to_install
        assert state.user_preferences["port"] == 8000

    def test_current_step_validation(self):
        """Test that current_step must be a valid step name."""
        valid_steps = [
            "welcome", "python_check", "service_check", "service_install",
            "config_setup", "complete"
        ]

        for step in valid_steps:
            state = SetupWizardState(
                current_step=step,
                completed_steps=[],
                services_to_install=[],
                user_preferences={},
                skip_services=[],
                setup_start_time=datetime.now()
            )
            assert state.current_step == step

        # Test invalid step
        with pytest.raises(ValidationError):
            SetupWizardState(
                current_step="invalid_step",
                completed_steps=[],
                services_to_install=[],
                user_preferences={},
                skip_services=[],
                setup_start_time=datetime.now()
            )

    def test_completed_steps_append_only(self):
        """Test that completed_steps maintains order and uniqueness."""
        state = SetupWizardState(
            current_step="service_check",
            completed_steps=["welcome", "python_check"],
            services_to_install=[],
            user_preferences={},
            skip_services=[],
            setup_start_time=datetime.now()
        )

        assert state.completed_steps == ["welcome", "python_check"]

        # Test that order is preserved
        state.completed_steps.append("service_check")
        assert state.completed_steps[-1] == "service_check"

    def test_services_to_install_validation(self):
        """Test that services_to_install contains only valid service names."""
        valid_services = ["docker", "ollama", "qdrant"]

        state = SetupWizardState(
            current_step="service_install",
            completed_steps=["welcome"],
            services_to_install=valid_services,
            user_preferences={},
            skip_services=[],
            setup_start_time=datetime.now()
        )

        assert all(service in valid_services for service in state.services_to_install)

        # Test invalid service name should be caught at validation level
        with pytest.raises(ValidationError):
            SetupWizardState(
                current_step="service_install",
                completed_steps=["welcome"],
                services_to_install=["invalid_service"],
                user_preferences={},
                skip_services=[],
                setup_start_time=datetime.now()
            )

    def test_user_preferences_dict(self):
        """Test user_preferences dictionary handling."""
        preferences = {
            "skip_docker": True,
            "ollama_port": 11434,
            "data_dir": "/custom/path",
            "use_gpu": False
        }

        state = SetupWizardState(
            current_step="config_setup",
            completed_steps=["welcome", "service_check"],
            services_to_install=["ollama"],
            user_preferences=preferences,
            skip_services=["docker"],
            setup_start_time=datetime.now()
        )

        assert state.user_preferences == preferences
        assert state.user_preferences["skip_docker"] is True
        assert state.user_preferences["ollama_port"] == 11434

    def test_skip_services_list(self):
        """Test skip_services list validation."""
        skip_list = ["docker", "qdrant"]

        state = SetupWizardState(
            current_step="service_install",
            completed_steps=["welcome", "service_check"],
            services_to_install=["docker", "ollama"],
            user_preferences={},
            skip_services=skip_list,
            setup_start_time=datetime.now()
        )

        assert state.skip_services == skip_list
        assert "docker" in state.skip_services
        assert "docker" not in state.skip_services

    def test_setup_start_time_tracking(self):
        """Test setup start time tracking."""
        start_time = datetime.now()

        state = SetupWizardState(
            current_step="welcome",
            completed_steps=[],
            services_to_install=[],
            user_preferences={},
            skip_services=[],
            setup_start_time=start_time
        )

        assert state.setup_start_time == start_time

        # Test time difference calculation
        time_diff = (datetime.now() - state.setup_start_time).total_seconds()
        assert time_diff >= 0  # Should not be negative

    def test_json_serialization(self):
        """Test that SetupWizardState can be serialized to/from JSON."""
        original = SetupWizardState(
            current_step="service_install",
            completed_steps=["welcome", "python_check", "service_check"],
            services_to_install=["docker", "ollama"],
            user_preferences={"port": 8000, "skip_ollama": True},
            skip_services=["qdrant"],
            setup_start_time=datetime(2025, 1, 25, 10, 30, 0)
        )

        # Serialize to JSON
        json_data = original.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data["current_step"] == "service_install"
        assert len(json_data["completed_steps"]) == 3
        assert json_data["user_preferences"]["port"] == 8000

        # Deserialize from JSON
        restored = SetupWizardState.model_validate(json_data)
        assert restored.current_step == original.current_step
        assert restored.completed_steps == original.completed_steps
        assert restored.user_preferences == original.user_preferences

    def test_empty_lists_allowed(self):
        """Test that empty lists are allowed for list fields."""
        state = SetupWizardState(
            current_step="welcome",
            completed_steps=[],  # Empty list should be valid
            services_to_install=[],  # Empty list should be valid
            user_preferences={},  # Empty dict should be valid
            skip_services=[],  # Empty list should be valid
            setup_start_time=datetime.now()
        )

        assert len(state.completed_steps) == 0
        assert len(state.services_to_install) == 0
        assert len(state.user_preferences) == 0
        assert len(state.skip_services) == 0

    def test_step_progression_logic(self):
        """Test logical step progression validation."""
        # Test that you can't complete a step before starting it
        with pytest.raises(ValidationError):
            SetupWizardState(
                current_step="welcome",
                completed_steps=["service_check"],  # Can't complete service_check before welcome
                services_to_install=[],
                user_preferences={},
                skip_services=[],
                setup_start_time=datetime.now()
            )

    def test_service_install_skip_consistency(self):
        """Test that services can't be in both install and skip lists."""
        with pytest.raises(ValidationError):
            SetupWizardState(
                current_step="service_install",
                completed_steps=["welcome"],
                services_to_install=["docker"],
                user_preferences={},
                skip_services=["docker"],  # Same service in both lists
                setup_start_time=datetime.now()
            )