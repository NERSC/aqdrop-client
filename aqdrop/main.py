from __future__ import annotations
import httpx
import certifi
import ssl
import base64
import io
import tempfile
import os
import typing

from . import defs, creds


class AqdropClient:
    """Client for interacting with the AQDROP service API."""
    def __init__(self,
                 username: str | None = None,
                 password: str | None = None,
                 host: str | None = None):
        """Initializes the AqdropClient and logs in.

        Args:
            username: The username for authentication. Defaults to AQDROP_USERNAME.
            password: The password for authentication. Defaults to AQDROP_PASSWORD.
            host: The service host. Defaults to AQDROP_HOSTNAME.
        """
        self._token = None

        if username is None:
            username = creds.get_username()

        if password is None:
            password = creds.get_password()

        if host is None:
            host = creds.get_network()

        ctx = ssl.create_default_context(cafile=certifi.where())
        self._client = httpx.Client(base_url=host.rstrip("/"), timeout=10, verify=ctx)

        self._login(username, password)


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
        req.raise_for_status()
        return req


    def _login(self, username, password):
        """Authenticates the client and stores the access token.

        Args:
            username: The username.
            password: The password.

        Returns:
            str: The access token.
        """
        req_json = {"username": username, "password": password}
        login_request = self._request("POST", "/token/",
                                      data=req_json,
                                      headers={"Content-Type": "application/x-www-form-urlencoded"})
        login_response = login_request.json()
        self._token = login_response["access_token"]

        return self._token


    def create_member(self, username: str, email: str | None = None):
        """Creates a new member in the system.

        Args:
            username: The username of the new member.
            email: Optional email address of the new member.

        Returns:
            dict: The API response for the created member.
        """
        req_json = { "name": username }

        if email is not None:
            req_json["email"] = email

        create_request = self._request("POST", "/members/", json=req_json)
        return create_request.json()


    def get_member_list(self):
        """Retrieves a list of all members.

        Returns:
            list: A list of member dictionaries.
        """
        get_request = self._request("GET", "/members/")
        return get_request.json()


    def get_member(self, name: str):
        """Retrieves details for a specific member.

        Args:
            name: The username of the member.

        Returns:
            dict: Member details.
        """
        get_request = self._request("GET", f"/members/{name}")
        return get_request.json()


    # TODO: use pydantic for cleaner queries
    def update_member(self, name: str,
                      new_name: str | None = None,
                      new_email: str | None = None,
                      new_password: str | None = None,
                      is_active: bool | None = None
                      ):
        """Updates a member's profile information.

        Args:
            name: The username of the member to update.
            new_name: Optional new username.
            new_email: Optional new email.
            new_password: Optional new password.
            is_active: Optional activity status.

        Returns:
            dict: The API response for the updated member.
        """
        req_json = {}
        if new_name is not None: req_json["name"] = new_name
        if new_email is not None: req_json["email"] = new_email
        if new_password is not None: req_json["password"] = new_password
        if is_active is not None: req_json["is_active"] = is_active
        patch_request = self._request("PATCH", f"/members/{name}", json=req_json)
        # TODO: decide: do we need to log in again?
        return patch_request.json()


    def delete_member(self, name: str):
        """Deletes a member from the system.

        Args:
            name: The username of the member to delete.

        Returns:
            dict: The API response for the deleted member.
        """
        delete_request = self._request("DELETE", f"/members/{name}")
        return delete_request.json()


    def update_member_perms(self, name: str,
                            is_admin: bool | None = None,
                            is_operator: bool | None = None,
                            is_suspended: bool | None = None
                            ):
        """Updates a member's administrative permissions.

        Args:
            name: The username of the member.
            is_admin: Optional admin status.
            is_operator: Optional operator status.
            is_suspended: Optional suspension status.

        Returns:
            dict: The API response for the updated permissions.
        """
        req_json = {}
        if is_admin is not None: req_json["is_admin"] = is_admin
        if is_operator is not None: req_json["is_operator"] = is_operator
        if is_suspended is not None: req_json["is_suspended"] = is_suspended
        patch_request = self._request("PATCH", f"/members/{name}/role/", json=req_json)
        return patch_request.json()


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
            dict: Job details. Returns an empty dict or {"qc": None} if not found.
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
                     new_state: defs.QueueState | None = None):
        """Updates a queue's configuration.

        Args:
            queue_name: The name of the queue.
            new_limit: Optional new limit per member.
            new_state: Optional new state (from defs.QueueState).

        Returns:
            dict: The API response for the updated queue.
        """
        req_json = {}
        if new_limit is not None: req_json["limit_per_member"] = new_limit
        if new_state is not None: req_json["state"] = new_state.value
        r = self._request("PATCH", f"/queue/{queue_name}", json=req_json)
        return r.json()


    def query_jobs(self,
                   id_min: int | None = None,
                   id_max: int | None = None,
                   queue_name: str | None = None,
                   owner_name: str | None = None,
                   owner_id: int | None = None,
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
            owner_id: Filter by owner ID.
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
        if owner_id is not None: req_params["owner_id"] = owner_id
        if status is not None: req_params["status"] = status.value
        if max_jobs is not None: req_params["max_jobs"] = max_jobs
        if created_min is not None: req_params["created_min"] = created_min
        if created_max is not None: req_params["created_max"] = created_max
        if reverse: req_params["reverse"] = "true"
        r = self._request("GET", "/jobs/", params=req_params)
        return r.json()


    def list_members(self):
        """Retrieves a list of all members.

        Returns:
            list: A list of member dictionaries.
        """
        r = self._request("GET", "/members/")
        return r.json()
