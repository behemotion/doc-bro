"""Contract tests for ConfigurationState model validation."""

import pytest
from datetime import datetime
from typing import Optional

# Import will fail until model is implemented - this is expected for TDD
try:
    from src.models.configuration_state import ConfigurationState
    MODEL_EXISTS = True
except ImportError:
    MODEL_EXISTS = False


@pytest.mark.contract
class TestConfigurationStateModel:
    """Test ConfigurationState model contracts."""

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_creation_configured(self):
        """Test ConfigurationState creation for configured entity."""
        setup_time = datetime.utcnow()

        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=setup_time,
            needs_migration=False
        )

        assert config_state.is_configured is True
        assert config_state.has_content is True
        assert config_state.configuration_version == "1.0"
        assert config_state.setup_completed_at == setup_time
        assert config_state.needs_migration is False

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_creation_unconfigured(self):
        """Test ConfigurationState creation for unconfigured entity."""
        config_state = ConfigurationState(
            is_configured=False,
            has_content=False,
            configuration_version="1.0",
            setup_completed_at=None,
            needs_migration=False
        )

        assert config_state.is_configured is False
        assert config_state.has_content is False
        assert config_state.configuration_version == "1.0"
        assert config_state.setup_completed_at is None
        assert config_state.needs_migration is False

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_version_validation(self):
        """Test configuration_version validation."""
        # Valid versions
        valid_versions = ["1.0", "2.1", "3.0.0", "1.2.3-beta", "2.0-rc1"]
        for version in valid_versions:
            config_state = ConfigurationState(
                is_configured=True,
                has_content=False,
                configuration_version=version,
                setup_completed_at=datetime.utcnow(),
                needs_migration=False
            )
            assert config_state.configuration_version == version

        # Invalid versions should raise validation error
        invalid_versions = ["", "v1.0", "1", "invalid", "1.0.0.0.0"]
        for version in invalid_versions:
            with pytest.raises(ValueError, match="configuration_version must match supported versions"):
                ConfigurationState(
                    is_configured=True,
                    has_content=False,
                    configuration_version=version,
                    setup_completed_at=datetime.utcnow(),
                    needs_migration=False
                )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_setup_completed_logic(self):
        """Test setup_completed_at logic validation."""
        setup_time = datetime.utcnow()

        # When is_configured=True, setup_completed_at should be set
        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=setup_time,
            needs_migration=False
        )
        assert config_state.setup_completed_at == setup_time

        # When is_configured=False, setup_completed_at should be None
        config_state = ConfigurationState(
            is_configured=False,
            has_content=False,
            configuration_version="1.0",
            setup_completed_at=None,
            needs_migration=False
        )
        assert config_state.setup_completed_at is None

        # When is_configured=True but setup_completed_at is None, should raise validation error
        with pytest.raises(ValueError, match="setup_completed_at only set when is_configured=True"):
            ConfigurationState(
                is_configured=True,
                has_content=False,
                configuration_version="1.0",
                setup_completed_at=None,
                needs_migration=False
            )

        # When is_configured=False but setup_completed_at is set, should raise validation error
        with pytest.raises(ValueError, match="setup_completed_at only set when is_configured=True"):
            ConfigurationState(
                is_configured=False,
                has_content=False,
                configuration_version="1.0",
                setup_completed_at=setup_time,
                needs_migration=False
            )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_migration_scenarios(self):
        """Test various migration scenarios."""
        # New entity - no migration needed
        config_state = ConfigurationState(
            is_configured=False,
            has_content=False,
            configuration_version="2.0",
            setup_completed_at=None,
            needs_migration=False
        )
        assert not config_state.needs_migration

        # Old version - migration needed
        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=datetime.utcnow(),
            needs_migration=True
        )
        assert config_state.needs_migration

        # After migration - up to date
        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="2.0",
            setup_completed_at=datetime.utcnow(),
            needs_migration=False
        )
        assert not config_state.needs_migration

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_status_properties(self):
        """Test computed status properties."""
        # Fully configured and populated
        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=datetime.utcnow(),
            needs_migration=False
        )
        assert config_state.is_ready()
        assert not config_state.needs_setup()

        # Configured but empty
        config_state = ConfigurationState(
            is_configured=True,
            has_content=False,
            configuration_version="1.0",
            setup_completed_at=datetime.utcnow(),
            needs_migration=False
        )
        assert config_state.is_ready()
        assert not config_state.needs_setup()

        # Not configured
        config_state = ConfigurationState(
            is_configured=False,
            has_content=False,
            configuration_version="1.0",
            setup_completed_at=None,
            needs_migration=False
        )
        assert not config_state.is_ready()
        assert config_state.needs_setup()

        # Needs migration
        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=datetime.utcnow(),
            needs_migration=True
        )
        assert not config_state.is_ready()
        assert config_state.needs_setup()

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_serialization(self):
        """Test ConfigurationState serialization to dict."""
        setup_time = datetime.utcnow()

        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=setup_time,
            needs_migration=False
        )

        # Should be able to serialize to dict
        state_dict = config_state.model_dump()
        assert isinstance(state_dict, dict)
        assert state_dict["is_configured"] is True
        assert state_dict["has_content"] is True
        assert state_dict["configuration_version"] == "1.0"
        assert state_dict["setup_completed_at"] == setup_time
        assert state_dict["needs_migration"] is False

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_deserialization(self):
        """Test ConfigurationState deserialization from dict."""
        setup_time = datetime.utcnow()

        state_data = {
            "is_configured": True,
            "has_content": False,
            "configuration_version": "2.0",
            "setup_completed_at": setup_time,
            "needs_migration": False
        }

        config_state = ConfigurationState.model_validate(state_data)
        assert config_state.is_configured is True
        assert config_state.has_content is False
        assert config_state.configuration_version == "2.0"
        assert config_state.setup_completed_at == setup_time
        assert config_state.needs_migration is False

    @pytest.mark.skipif(not MODEL_EXISTS, reason="ConfigurationState model not yet implemented")
    def test_configuration_state_json_serialization(self):
        """Test ConfigurationState JSON serialization for database storage."""
        setup_time = datetime.utcnow()

        config_state = ConfigurationState(
            is_configured=True,
            has_content=True,
            configuration_version="1.0",
            setup_completed_at=setup_time,
            needs_migration=False
        )

        # Should be able to serialize to JSON string
        json_str = config_state.model_dump_json()
        assert isinstance(json_str, str)

        # Should be able to deserialize from JSON string
        config_state_restored = ConfigurationState.model_validate_json(json_str)
        assert config_state_restored.is_configured == config_state.is_configured
        assert config_state_restored.has_content == config_state.has_content
        assert config_state_restored.configuration_version == config_state.configuration_version
        assert config_state_restored.needs_migration == config_state.needs_migration


if not MODEL_EXISTS:
    def test_configuration_state_model_not_implemented():
        """Test that fails until ConfigurationState model is implemented."""
        assert False, "ConfigurationState model not yet implemented - this test should fail until T025 is completed"