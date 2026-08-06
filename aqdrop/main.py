from __future__ import annotations

import os
import ssl

import certifi
import httpx

from . import defs, creds


class AqdropClient:
    """Client for interacting with the AQDROP service API."""

    def __init__(self,
                 host: str | None = None,
                 token: str | None = None,
                 client_id: str | None = None,
                 private_key_path: str | None = None,
                 token_url: str | None = None):
        """Initialize an authenticated AQDrop client.

        Args:
            host: The service host. Defaults to AQDROP_HOSTNAME.
            token: An existing SFAPI bearer token.
            client_id: SFAPI client ID used to fetch a bearer token.
            private_key_path: Private key used with the SFAPI client ID.
            token_url: Optional SFAPI token endpoint override.
        """
        self._token = None
        self._sfapi_refresh_credentials = None

        if host is None:
            host = creds.get_network()

        direct_token_configured = token is not None or bool(os.getenv("SFAPI_TOKEN"))
        resolved_client_id = client_id or os.getenv("SFAPI_CLIENT_ID")
        resolved_private_key_path = private_key_path or os.getenv("SFAPI_PRIVATE_KEY_PATH")
        if not direct_token_configured and resolved_client_id and resolved_private_key_path:
            self._sfapi_refresh_credentials = (
                resolved_client_id,
                resolved_private_key_path,
                token_url or creds.get_token_url(),
            )

        token = creds.resolve_token(
            token=token,
            client_id=client_id,
            private_key_path=private_key_path,
            token_url=token_url,
        )

        ctx = ssl.create_default_context(cafile=certifi.where())
        self._client = httpx.Client(base_url=host.rstrip("/"), timeout=10, verify=ctx)
        self._token = token


    def _apply_token(self, headers: dict):
        """Adds the authentication token to the request headers.

        Args:
            headers: The current headers dictionary.

        Returns:
            dict: The updated headers dictionary with Authorization header.
        """
        if self._token is None:
            return headers
        return {**headers, "Authorization": f"Bearer {self._token}"}


    def _request(self, method: str, path: str, **kwargs):
        """Performs an HTTP request with the authentication token.

        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            path: API endpoint path.
            **kwargs: Additional arguments passed to httpx.Client.request.

        Returns:
            httpx.Response: The response from the API.
        """
        headers = kwargs.pop("headers", {})
        new_headers = self._apply_token(headers)
        req = self._client.request(method, path, headers=new_headers, **kwargs)
        if req.status_code == 401 and self._sfapi_refresh_credentials is not None:
            req.close()
            self._token = creds.refresh_sfapi_token(*self._sfapi_refresh_credentials)
            refreshed_headers = self._apply_token(headers)
            req = self._client.request(method, path, headers=refreshed_headers, **kwargs)
        req.raise_for_status()
        return req


    def _validate_job(self, queue_name: str, job_input: dict):
        """Validates that the job input queue name matches the requested queue.

        Args:
            queue_name: The name of the queue.
            job_input: The job input dictionary.

        Raises:
            ValueError: If queue_name in job_input doesn't match provided queue_name.
        """
        if "queue_name" not in job_input.keys():
            job_input.update({"queue_name": queue_name})
        else:
            if job_input["queue_name"] != queue_name:
                raise ValueError(f"queue_name in job_input must match queue_name provided in submit_job arguments.")


    # TODO: update job_input type?
    def submit_job(self, queue_name: str, job_input: dict):
        """Submits a job to a specific queue.

        Args:
            queue_name: The name of the queue.
            job_input: The job parameters dictionary.

        Returns:
            dict: The API response for the submitted job.
        """
        self._validate_job(queue_name, job_input)

        req_json = {
                "queue_name": queue_name,
                "input": job_input
        }
        post_resp = self._request("POST", "/job/", json=req_json)
        return post_resp.json()


    def get_job(self, job_id: int):
        """Retrieves a job by its ID.

        Args:
            job_id: The ID of the job.

        Returns:
            dict: Job details, or an empty dictionary when the job is not found.
        """
        try:
            get_request = self._request("GET", f"/job/?job_id={job_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {}
            raise
        job_dd: dict = get_request.json()

        return job_dd


    def check_job(self, job_id: int):
        """Checks the status of a job.

        Args:
            job_id: The ID of the job.

        Returns:
            dict: Job status information.
        """
        get_request = self._request("GET", f"/job/check/?job_id={job_id}")
        return get_request.json()


    def cancel_job(self, job_id: int):
        """Cancels a pending or running job.

        Args:
            job_id: The ID of the job.

        Returns:
            dict: The API response for the cancelled job.
        """
        r = self._request("PATCH", "/job/cancel/", json={"id": job_id})
        return r.json()


    def reset_job(self, job_id: int, comment: str | None = None):
        """Resets a job's status.

        Args:
            job_id: The ID of the job.
            comment: Optional comment explaining the reset.

        Returns:
            dict: The API response for the reset job.
        """
        req_json = {"id": job_id}
        if comment is not None:
            req_json["comment"] = comment
        r = self._request("PATCH", "/job/reset/", json=req_json)
        return r.json()


    def dispatch_job(self, job_id: int,
                     status: defs.JobStatus,
                     output: dict | None = None):
        """Updates a job's status and output (used by worker nodes).

        Args:
            job_id: The ID of the job.
            status: The new status of the job (from defs.JobStatus).
            output: Optional output data.

        Returns:
            dict: The API response for the dispatched job.
        """
        req_json = {
                "id": job_id,
                "status": status.value,
                "output": output
                }
        r = self._request("PATCH", "/job/dispatch/", json=req_json)
        return r.json()


    def add_queue(self, queue_name: str,  limit: int, queue_type: defs.QueueType, max_qubits: int, description: str = ""):
        """Creates a new queue in the system.

        Args:
            queue_name: The name of the queue.
            limit: Limit per member.
            queue_type: The type of queue (from defs.QueueType).
            max_qubits: Maximum qubits allowed.
            description: Optional description of the queue.

        Returns:
            dict: The API response for the created queue.
        """
        req_json = {
                "name": queue_name,
                "limit_per_member": limit,
                "description": description,
                "type": queue_type,
                "max_qubits": max_qubits
                }
        r = self._request("POST", "/queue/", json=req_json)
        return r.json()


    def get_queue(self, queue_name: str):
        """Retrieves details for a specific queue.

        Args:
            queue_name: The name of the queue.

        Returns:
            dict: Queue details.
        """
        return self._request("GET", f"/queue/{queue_name}").json()


    def list_queues(self, state: defs.QueueState | None = None):
        """Lists all queues, optionally filtered by state.

        Args:
            state: Optional filter for queue state (from defs.QueueState).

        Returns:
            list: A list of queue dictionaries.
        """
        req_params = {}
        if state is not None:
            req_params["state"] = state.value
        return self._request("GET", "/queues/", params=req_params).json()


    def update_queue(self, queue_name: str,
                     new_limit: int | None = None,
                     new_state: defs.QueueState | None = None,
                     new_max_qubits: int | None = None,
                     new_type: defs.QueueType | None = None):
        """Updates a queue's configuration.

        Args:
            queue_name: The name of the queue.
            new_limit: Optional new limit per member.
            new_state: Optional new state (from defs.QueueState).
            new_max_qubits: Optional new maximum qubit count.
            new_type: Optional new queue type.

        Returns:
            dict: The API response for the updated queue.
        """
        req_json = {}
        if new_limit is not None: req_json["limit_per_member"] = new_limit
        if new_state is not None: req_json["state"] = new_state.value
        if new_max_qubits is not None: req_json["max_qubits"] = new_max_qubits
        if new_type is not None: req_json["type"] = new_type.value
        r = self._request("PATCH", f"/queue/{queue_name}", json=req_json)
        return r.json()


    def query_jobs(self,
                   id_min: int | None = None,
                   id_max: int | None = None,
                   queue_name: str | None = None,
                   owner_name: str | None = None,
                   status: defs.JobStatus | None = None,
                   max_jobs: int | None = None,
                   created_min: str | None = None,
                   created_max: str | None = None,
                   reverse: bool = False):
        """Queries jobs based on various filters.

        Args:
            id_min: Minimum job ID.
            id_max: Maximum job ID.
            queue_name: Filter by queue name.
            owner_name: Filter by owner username.
            status: Filter by job status (from defs.JobStatus).
            max_jobs: Maximum number of jobs to return.
            created_min: Minimum creation date.
            created_max: Maximum creation date.
            reverse: Whether to return results in reverse order.

        Returns:
            list: A list of matching job dictionaries.
        """
        req_params = {}
        if id_min is not None: req_params["id_min"] = id_min
        if id_max is not None: req_params["id_max"] = id_max
        if queue_name is not None: req_params["queue_name"] = queue_name
        if owner_name is not None: req_params["owner_name"] = owner_name
        if status is not None: req_params["status"] = status.value
        if max_jobs is not None: req_params["max_jobs"] = max_jobs
        if created_min is not None: req_params["created_min"] = created_min
        if created_max is not None: req_params["created_max"] = created_max
        if reverse: req_params["reverse"] = "true"
        r = self._request("GET", "/jobs/", params=req_params)
        return r.json()
