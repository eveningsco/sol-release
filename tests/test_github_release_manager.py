"""Tests for GitHub Release Manager functionality.

These tests validate the release management, artifact handling,
and workflow orchestration logic.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from github_release_manager import (
    GitHubAPIError,
    GitHubReleaseManager,
    ComponentMetadataFetcher,
    ReleaseWorkflowOrchestrator
)


class TestGitHubAPIError:
    """Tests for the GitHubAPIError exception."""

    def test_exception_message(self):
        """Test that error message is preserved."""
        error = GitHubAPIError("Test API error message")
        assert str(error) == "Test API error message"

    def test_exception_inherits_from_exception(self):
        """Test that GitHubAPIError inherits from Exception."""
        assert isinstance(GitHubAPIError("test"), Exception)


class TestGitHubReleaseManager:
    """Tests for the GitHubReleaseManager class."""

    def test_initialization(self):
        """Test manager initialization with default values."""
        manager = GitHubReleaseManager("test_token")

        assert manager.token == "test_token"
        assert manager.owner == "eveningsco"
        assert manager.repo == "sol-release"
        assert manager.api_base == "https://api.github.com"
        assert "Authorization" in manager.headers
        assert "Accept" in manager.headers

    def test_initialization_with_custom_values(self):
        """Test manager initialization with custom owner and repo."""
        manager = GitHubReleaseManager("test_token", "custom_owner", "custom_repo")

        assert manager.owner == "custom_owner"
        assert manager.repo == "custom_repo"

    @patch('github_release_manager.urlopen')
    def test_list_releases(self, mock_urlopen):
        """Test listing releases from GitHub API."""
        mock_response = Mock()
        mock_response.read.return_value = b'[{"id": 1, "tag_name": "v1.0.0"}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        releases = manager.list_releases(per_page=10, page=1)

        assert len(releases) == 1
        assert releases[0]["id"] == 1
        assert releases[0]["tag_name"] == "v1.0.0"

    @patch('github_release_manager.urlopen')
    def test_get_release(self, mock_urlopen):
        """Test fetching a specific release."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"id": 123, "tag_name": "v2.0.0"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        release = manager.get_release(123)

        assert release["id"] == 123
        assert release["tag_name"] == "v2.0.0"

    @patch('github_release_manager.urlopen')
    def test_get_release_by_tag(self, mock_urlopen):
        """Test fetching release by tag name."""
        mock_response = Mock()
        mock_response.read.return_value = b'[{"id": 456, "tag_name": "v1.5.0"}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        release = manager.get_release_by_tag("v1.5.0")

        assert release is not None
        assert release["id"] == 456
        assert release["tag_name"] == "v1.5.0"

    @patch('github_release_manager.urlopen')
    def test_get_release_by_tag_not_found(self, mock_urlopen):
        """Test fetching non-existent release by tag."""
        mock_response = Mock()
        mock_response.read.return_value = b'[]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        release = manager.get_release_by_tag("nonexistent_tag")

        assert release is None

    @patch('github_release_manager.urlopen')
    def test_delete_release(self, mock_urlopen):
        """Test deleting a release."""
        mock_response = Mock()
        mock_response.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        result = manager.delete_release(789)

        assert result is True

    @patch('github_release_manager.urlopen')
    def test_cleanup_old_releases(self, mock_urlopen):
        """Test cleanup of old releases."""
        mock_response = Mock()
        mock_response.read.return_value = b'[]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        deleted = manager.cleanup_old_releases(keep_count=5)

        assert isinstance(deleted, list)
        mock_urlopen.assert_called()

    @patch('github_release_manager.urlopen')
    def test_get_release_assets(self, mock_urlopen):
        """Test fetching release assets."""
        mock_response = Mock()
        mock_response.read.return_value = b'[{"id": 1, "name": "asset.zip"}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = GitHubReleaseManager("test_token")
        assets = manager.get_release_assets(123)

        assert len(assets) == 1
        assert assets[0]["id"] == 1
        assert assets[0]["name"] == "asset.zip"


class TestComponentMetadataFetcher:
    """Tests for the ComponentMetadataFetcher class."""

    def test_initialization(self):
        """Test fetcher initialization."""
        fetcher = ComponentMetadataFetcher("test_token")

        assert "sol-software" in fetcher.COMPONENT_MAP
        assert "sol-server" in fetcher.COMPONENT_MAP
        assert "sol-utils" in fetcher.COMPONENT_MAP
        assert fetcher.api_base == "https://api.github.com"

    @patch('github_release_manager.urlopen')
    def test_fetch_component_metadata_success(self, mock_urlopen):
        """Test successful component metadata fetch."""
        mock_response = Mock()
        mock_response.read.return_value = b'''
        {
            "tag_name": "v1.2.3",
            "target_commitish": "main",
            "html_url": "https://github.com/eveningsco/sol-software/releases/v1.2.3"
        }
        '''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ComponentMetadataFetcher("test_token")
        metadata = fetcher.fetch_component_metadata("sol-software")

        assert metadata is not None
        assert metadata["component"] == "sol-software"
        assert metadata["tag_name"] == "v1.2.3"
        assert metadata["branch"] == "main"

    @patch('github_release_manager.urlopen')
    def test_fetch_component_metadata_failure(self, mock_urlopen):
        """Test component metadata fetch failure."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "https://api.github.com/repos/eveningsco/sol-software/releases/latest",
            404,
            "Not Found",
            {},
            None
        )

        fetcher = ComponentMetadataFetcher("test_token")
        metadata = fetcher.fetch_component_metadata("sol-software")

        assert metadata is None

    @patch('github_release_manager.urlopen')
    def test_fetch_all_component_metadata(self, mock_urlopen):
        """Test fetching metadata for all components."""
        mock_response = Mock()
        mock_response.read.return_value = b'''
        {
            "tag_name": "v1.0.0",
            "target_commitish": "main",
            "html_url": "https://github.com/eveningsco/sol-software/releases/v1.0.0"
        }
        '''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ComponentMetadataFetcher("test_token")
        metadata = fetcher.fetch_all_component_metadata()

        assert "sol-software" in metadata
        assert metadata["sol-software"]["tag_name"] == "v1.0.0"

    def test_invalid_component(self):
        """Test fetching metadata for invalid component."""
        fetcher = ComponentMetadataFetcher("test_token")

        with pytest.raises(ValueError) as exc_info:
            fetcher.fetch_component_metadata("invalid-component")

        assert "Unknown component" in str(exc_info.value)


class TestReleaseWorkflowOrchestrator:
    """Tests for the ReleaseWorkflowOrchestrator class."""

    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ReleaseWorkflowOrchestrator("test_token")

        assert isinstance(orchestrator.release_manager, GitHubReleaseManager)
        assert isinstance(orchestrator.component_fetcher, ComponentMetadataFetcher)
        assert orchestrator.workflow_steps == []

    def test_workflow_steps_logging(self):
        """Test workflow step logging."""
        orchestrator = ReleaseWorkflowOrchestrator("test_token")

        orchestrator.log_step("Step 1")
        orchestrator.log_step("Step 2")

        assert len(orchestrator.workflow_steps) == 2
        assert "Step 1" in orchestrator.workflow_steps

    @patch('github_release_manager.GitHubReleaseManager')
    @patch('github_release_manager.ComponentMetadataFetcher')
    def test_create_release_from_components(self, mock_fetcher, mock_manager):
        """Test creating release from component metadata."""
        mock_manager_instance = Mock()
        mock_manager_instance.create_release.return_value = {
            "id": 123,
            "tag_name": "Release-03272026_14-30-00",
            "html_url": "https://github.com/eveningsco/sol-release/releases/tag/v1.0.0"
        }
        mock_manager.return_value = mock_manager_instance

        mock_fetcher_instance = Mock()
        mock_fetcher_instance.fetch_all_component_metadata.return_value = {
            "sol-software": {
                "component": "sol-software",
                "tag_name": "v1.0.0",
                "branch": "main",
                "commit_sha": "abc123def"
            },
            "sol-server": {
                "component": "sol-server",
                "tag_name": "v2.0.0",
                "branch": "develop",
                "commit_sha": "xyz789"
            }
        }
        mock_fetcher.return_value = mock_fetcher_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")
        result = orchestrator.create_release_from_components()

        assert "release" in result
        assert "components" in result
        assert "steps" in result
        assert len(orchestrator.workflow_steps) > 0
        assert any("release" in step.lower() for step in orchestrator.workflow_steps)

    @patch('github_release_manager.GitHubReleaseManager')
    def test_create_release_no_components(self, mock_manager_class):
        """Test release creation with no components."""
        mock_manager_instance = Mock()
        mock_manager_instance.create_release.return_value = {"id": 123}
        mock_manager_class.return_value = mock_manager_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")

        with pytest.raises(GitHubAPIError) as exc_info:
            orchestrator.create_release_from_components({})

        assert "No component metadata" in str(exc_info.value)

    @patch('github_release_manager.GitHubReleaseManager')
    @patch('github_release_manager.ComponentMetadataFetcher')
    def test_cleanup_old_releases(self, mock_fetcher, mock_manager):
        """Test cleanup of old releases."""
        mock_manager_instance = Mock()
        mock_manager_instance.cleanup_old_releases.return_value = []
        mock_manager.return_value = mock_manager_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")
        deleted = orchestrator.cleanup_old_releases(keep_count=5)

        assert isinstance(deleted, list)
        mock_manager_instance.cleanup_old_releases.assert_called_once_with(5)

    @patch('github_release_manager.GitHubReleaseManager')
    @patch('github_release_manager.ComponentMetadataFetcher')
    def test_get_release_history(self, mock_fetcher, mock_manager):
        """Test getting recent release history."""
        mock_manager_instance = Mock()
        mock_manager_instance.list_releases.return_value = [
            {
                "tag_name": "v1.0.0",
                "name": "Release-01012026",
                "created_at": "2026-01-01T00:00:00Z",
                "html_url": "https://github.com/eveningsco/sol-release/releases/v1.0.0",
                "prerelease": True
            }
        ]
        mock_manager.return_value = mock_manager_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")
        history = orchestrator.get_release_history(limit=5)

        assert len(history) == 1
        assert history[0]["tag"] == "v1.0.0"
        assert history[0]["name"] == "Release-01012026"


class TestIntegration:
    """Integration tests for GitHub release management."""

    @patch('github_release_manager.GitHubReleaseManager')
    @patch('github_release_manager.ComponentMetadataFetcher')
    def test_full_release_workflow(self, mock_fetcher, mock_manager):
        """Test complete release workflow from component fetch to release creation."""
        # Setup mock components
        mock_manager_instance = Mock()
        mock_manager_instance.create_release.return_value = {
            "id": 999,
            "tag_name": "Release-12312025_23-59-59",
            "html_url": "https://github.com/eveningsco/sol-release/releases/tag/v1.0.0"
        }
        mock_manager.return_value = mock_manager_instance

        mock_fetcher_instance = Mock()
        mock_fetcher_instance.fetch_all_component_metadata.return_value = {
            "sol-software": {
                "component": "sol-software",
                "tag_name": "v1.0.0",
                "branch": "main",
                "commit_sha": "abc123def456"
            }
        }
        mock_fetcher.return_value = mock_fetcher_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")

        # Execute workflow
        result = orchestrator.create_release_from_components()

        # Verify results
        assert result["release"]["id"] == 999
        assert "sol-software" in result["components"]
        assert len(orchestrator.workflow_steps) >= 3

        # Verify API was called
        mock_manager_instance.create_release.assert_called_once()

    @patch('github_release_manager.GitHubReleaseManager')
    def test_release_with_custom_components(self, mock_manager):
        """Test release creation with custom component metadata."""
        mock_manager_instance = Mock()
        mock_manager_instance.create_release.return_value = {"id": 1}
        mock_manager.return_value = mock_manager_instance

        orchestrator = ReleaseWorkflowOrchestrator("test_token")
        custom_components = {
            "sol-server": {
                "component": "sol-server",
                "tag_name": "v2.0.0",
                "branch": "release",
                "commit_sha": "xyz789"
            }
        }

        result = orchestrator.create_release_from_components(custom_components)

        assert "sol-server" in result["components"]
        mock_manager_instance.create_release.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch('github_release_manager.urlopen')
    def test_network_error_handling(self, mock_urlopen):
        """Test handling of network errors."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Network unreachable")

        manager = GitHubReleaseManager("test_token")

        with pytest.raises(GitHubAPIError) as exc_info:
            manager.list_releases()

        assert "Network error" in str(exc_info.value)

    @patch('github_release_manager.urlopen')
    def test_http_error_handling(self, mock_urlopen):
        """Test handling of HTTP errors."""
        from urllib.error import HTTPError
        import json
        
        # Create proper empty body for the error response
        mock_response = Mock()
        mock_response.read.return_value = b''
        mock_urlopen.side_effect = HTTPError(
            "https://api.github.com/repos/test/test/releases/latest",
            401,
            "Unauthorized",
            {},
            mock_response
        )

        fetcher = ComponentMetadataFetcher("invalid_token")

        metadata = fetcher.fetch_component_metadata("sol-software")
        assert metadata is None  # Should gracefully handle error

    def test_release_body_generation(self):
        """Test that release body is properly formatted."""
        orchestrator = ReleaseWorkflowOrchestrator("test_token")

        test_components = {
            "sol-software": {
                "component": "sol-software",
                "tag_name": "v1.0.0",
                "branch": "main",
                "commit_sha": "abc123def456"
            }
        }

        body = orchestrator._generate_release_body(test_components)

        assert "Combined SOL release package" in body
        assert "Component Sources" in body
        assert "sol-software" in body
        assert "v1.0.0" in body
        assert "main" in body
        # Commit SHA is truncated to 7 characters
        assert "abc123d" in body

    @patch('github_release_manager.urlopen')
    def test_empty_component_metadata(self, mock_urlopen):
        """Test handling of empty component metadata."""
        mock_response = Mock()
        mock_response.read.return_value = b'[]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ComponentMetadataFetcher("test_token")
        metadata = fetcher.fetch_all_component_metadata()

        # Should return empty dict, not None
        assert metadata == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
