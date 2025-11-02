"""GitLab API client."""
from typing import Optional

import httpx

from app.config import GITLAB_HOST
from app.services.gitlab.exceptions import GitLabAPIError, GitLabAuthenticationError


class GitLabClient:
    """Client for interacting with the GitLab API."""

    def __init__(self, base_url: str = GITLAB_HOST):
        """Initialize the GitLab client.

        Args:
            base_url: Base URL of the GitLab instance
        """
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v4"

    async def get_projects(self, token: str, group_id: int) -> list[dict]:
        """Fetch projects from a specific GitLab group.

        Args:
            token: GitLab personal access token
            group_id: GitLab group ID to filter projects

        Returns:
            List of project dictionaries belonging to the specified group and its nested groups

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/groups/{group_id}/projects"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"include_subgroups": True}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=headers, params=params, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

    async def get_project_hooks(self, token: str, project_id: int) -> list[dict]:
        """Fetch hooks for a specific GitLab project.

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID

        Returns:
            List of hook dictionaries for the specified project

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/projects/{project_id}/hooks"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

    async def create_project_hook(
        self,
        token: str,
        project_id: int,
        webhook_url: str,
        webhook_token: str,
        description: Optional[str] = None,
        enable_ssl_verification: bool = True,
        push_events: bool = False,
        merge_requests_events: bool = False,
        note_events: bool = False,
        confidential_issues_events: bool = False,
        issues_events: bool = False,
        tag_push_events: bool = False,
        pipeline_events: bool = False,
        job_events: bool = False,
        wiki_page_events: bool = False,
        deployment_events: bool = False,
        releases_events: bool = False,
    ) -> dict:
        """Create a webhook for a specific GitLab project.

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID
            webhook_url: URL for the webhook
            webhook_token: Secret token for webhook authentication and identification
            description: Optional description/name for the webhook
            enable_ssl_verification: Whether to enable SSL verification
            push_events: Whether to trigger on push events
            merge_requests_events: Whether to trigger on merge request events
            note_events: Whether to trigger on note events
            confidential_issues_events: Whether to trigger on confidential issue events
            issues_events: Whether to trigger on issue events
            tag_push_events: Whether to trigger on tag push events
            pipeline_events: Whether to trigger on pipeline events
            job_events: Whether to trigger on job events
            wiki_page_events: Whether to trigger on wiki page events
            deployment_events: Whether to trigger on deployment events
            releases_events: Whether to trigger on release events

        Returns:
            Dictionary representing the created hook

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/projects/{project_id}/hooks"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "url": webhook_url,
            "token": webhook_token,
            "enable_ssl_verification": enable_ssl_verification,
            "push_events": push_events,
            "merge_requests_events": merge_requests_events,
            "note_events": note_events,
            "confidential_issues_events": confidential_issues_events,
            "issues_events": issues_events,
            "tag_push_events": tag_push_events,
            "pipeline_events": pipeline_events,
            "job_events": job_events,
            "wiki_page_events": wiki_page_events,
            "deployment_events": deployment_events,
            "releases_events": releases_events,
        }
        if description:
            data["description"] = description

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, json=data, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

    async def update_project_hook(
        self,
        token: str,
        project_id: int,
        hook_id: int,
        webhook_url: str,
        webhook_token: str,
        description: Optional[str] = None,
        enable_ssl_verification: bool = True,
        push_events: bool = False,
        merge_requests_events: bool = False,
        note_events: bool = False,
        confidential_issues_events: bool = False,
        issues_events: bool = False,
        tag_push_events: bool = False,
        pipeline_events: bool = False,
        job_events: bool = False,
        wiki_page_events: bool = False,
        deployment_events: bool = False,
        releases_events: bool = False,
    ) -> dict:
        """Update a webhook for a specific GitLab project.

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID
            hook_id: Hook ID to update
            webhook_url: URL for the webhook
            webhook_token: Secret token for webhook authentication and identification
            description: Optional description/name for the webhook
            enable_ssl_verification: Whether to enable SSL verification
            push_events: Whether to trigger on push events
            merge_requests_events: Whether to trigger on merge request events
            note_events: Whether to trigger on note events
            confidential_issues_events: Whether to trigger on confidential issue events
            issues_events: Whether to trigger on issue events
            tag_push_events: Whether to trigger on tag push events
            pipeline_events: Whether to trigger on pipeline events
            job_events: Whether to trigger on job events
            wiki_page_events: Whether to trigger on wiki page events
            deployment_events: Whether to trigger on deployment events
            releases_events: Whether to trigger on release events

        Returns:
            Dictionary representing the updated hook

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/projects/{project_id}/hooks/{hook_id}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "url": webhook_url,
            "token": webhook_token,
            "enable_ssl_verification": enable_ssl_verification,
            "push_events": push_events,
            "merge_requests_events": merge_requests_events,
            "note_events": note_events,
            "confidential_issues_events": confidential_issues_events,
            "issues_events": issues_events,
            "tag_push_events": tag_push_events,
            "pipeline_events": pipeline_events,
            "job_events": job_events,
            "wiki_page_events": wiki_page_events,
            "deployment_events": deployment_events,
            "releases_events": releases_events,
        }
        if description:
            data["description"] = description

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    url, headers=headers, json=data, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

    async def get_project_triggers(self, token: str, project_id: int) -> list[dict]:
        """Fetch pipeline triggers for a specific GitLab project.

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID

        Returns:
            List of trigger dictionaries for the specified project

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/projects/{project_id}/triggers"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

    async def create_project_trigger(
        self,
        token: str,
        project_id: int,
        description: str,
    ) -> dict:
        """Create a pipeline trigger token for a specific GitLab project.

        Args:
            token: GitLab personal access token
            project_id: GitLab project ID
            description: Description/name for the trigger token

        Returns:
            Dictionary representing the created trigger (including the token)

        Raises:
            GitLabAuthenticationError: If authentication fails
            GitLabAPIError: If the API request fails
        """
        url = f"{self.api_base}/projects/{project_id}/triggers"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"description": description}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, json=data, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise GitLabAuthenticationError(
                        "Invalid GitLab personal access token"
                    )
                raise GitLabAPIError(
                    f"GitLab API error: {e.response.text}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise GitLabAPIError(f"Network error: {str(e)}") from e

