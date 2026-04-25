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
    def __init__(self,
                 username: str | None = None,
                 password: str | None = None,
                 host: str | None = None):
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
        if self._token is None:
            return headers
        return {**headers, "Authorization": f"Bearer {self._token}"}


    def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        new_headers = self._apply_token(headers)
        req = self._client.request(method, path, headers=new_headers, **kwargs)
        req.raise_for_status()
        return req


    # TODO: set operator here (see if server returns is_admin - if not, modify it!)
    def _login(self, username, password):
        req_json = {"username": username, "password": password}
        login_request = self._request("POST", "/token/",
                                      data=req_json,
                                      headers={"Content-Type": "application/x-www-form-urlencoded"})
        login_response = login_request.json()
        self._token = login_response["access_token"]

        return self._token


    def create_member(self, username: str, email: str | None = None):
        req_json = { "name": username }

        if email is not None:
            req_json["email"] = email

        create_request = self._request("POST", "/members/", json=req_json)
        return create_request.json()


    # TODO: fix request params
    def get_member_list(self, skip: int | None = None, limit: int | None = None):
        req_params = {}
        if skip is not None: req_params["skip"] = skip
        if limit is not None: req_params["limit"] = limit
        get_request = self._request("GET", "/members/", params=req_params)
        return get_request.json()


    def get_member(self, name: str):
        get_request = self._request("GET", f"/members/{name}")
        return get_request.json()


    # TODO: use pydantic for cleaner queries
    def update_member(self, name: str,
                      new_name: str | None = None,
                      new_email: str | None = None,
                      new_password: str | None = None,
                      is_active: bool | None = None
                      ):
        req_json = {}
        if new_name is not None: req_json["name"] = new_name
        if new_email is not None: req_json["email"] = new_email
        if new_password is not None: req_json["password"] = new_password
        if is_active is not None: req_json["is_active"] = is_active
        patch_request = self._request("PATCH", f"/members/{name}", json=req_json)
        # TODO: decide: do we need to log in again?
        return patch_request.json()


    def delete_member(self, name: str):
        delete_request = self._request("DELETE", f"/members/{name}")
        return delete_request.json()


    def update_member_perms(self, name: str,
                            is_admin: bool | None = None,
                            is_operator: bool | None = None,
                            is_suspended: bool | None = None
                            ):
        req_json = {}
        if is_admin is not None: req_json["is_admin"] = is_admin
        if is_operator is not None: req_json["is_operator"] = is_operator
        if is_suspended is not None: req_json["is_suspended"] = is_suspended
        patch_request = self._request("PATCH", f"/members/{name}/role/", json=req_json)
        return patch_request.json()


    def _validate_job(self, queue_name: str, job_input: dict):
        if "queue_name" not in job_input.keys():
            job_input.update({"queue_name": queue_name})
        else:
            if job_input["queue_name"] != queue_name:
                raise ValueError(f"queue_name in job_input must match queue_name provided in submit_job arguments.")


    # TODO: update job_input type?
    def submit_job(self, queue_name: str, job_input: dict):
        self._validate_job(queue_name, job_input)

        req_json = {
                "queue_name": queue_name,
                "input": job_input
                }
        post_resp = self._request("POST", "/job/", json=req_json)
        return post_resp.json()


    def _embed_qiskit(self, qc: typing.List[qiskit.QuantumCircuit]):
        try:
            import qiskit
            import qiskit.qpy
        except ImportError:
            raise ImportError("qiskit is required for this method. Please run 'pip install qiskit' or install aqdrop[qiskit].")

        with tempfile.NamedTemporaryFile(delete_on_close=False) as tf:
            qiskit.qpy.dump(qc, tf)
            tf.close()
            with open(tf.name, 'rb') as tfr:
                qc_embedded = base64.b64encode(tfr.read())
        return qc_embedded.decode()


    def extract_qiskit(self, b: str) -> typing.List[qiskit.QuantumCircuit]:
        try:
            import qiskit
            import qiskit.qpy
        except ImportError:
            raise ImportError("qiskit is required for this method. Please run 'pip install qiskit' or install aqdrop[qiskit].")

        embedded_qpy = base64.b64decode(b)
        circuits = qiskit.qpy.load(io.BytesIO(embedded_qpy))

        if not isinstance(circuits, list):
            raise TypeError("Embedded QPY must contain a list of Qiskit circuits.")
        if all(isinstance(qc, qiskit.QuantumCircuit) for qc in circuits):
            return circuits

        raise TypeError("Embedded QPY list must contain only Qiskit circuits.")


    def _validate_qiskit(self, queue_name: str, qc: typing.List[qiskit.QuantumCircuit], meta: dict):
        try:
            import qiskit
            import qiskit.qpy
        except ImportError:
            raise ImportError("qiskit is required for this method. Please run 'pip install qiskit' or install aqdrop[qiskit].")

        # ensure job submission specifies shots
        if 'shots' not in meta.keys():
            raise ValueError("argument 'meta' must contain an entry 'shots'")

        # ensure shots are specified for each circuit
        num_circs = len(qc)
        if len(meta['shots']) != num_circs:
            raise ValueError(f"argument 'meta' must specify {num_circs} shots, but has only specified {len(meta['shots'])}")


    def submit_qiskit(self, queue_name: str, qc: typing.List[qiskit.QuantumCircuit], meta: dict):
        # raise exceptions if the job submission is badly formatted
        self._validate_qiskit(queue_name, qc, meta)

        qc_embedded = self._embed_qiskit(qc)
        job_dd = dict(**meta, qpy=qc_embedded)
        submitted = self.submit_job(queue_name, job_dd)

        return submitted


    def get_job(self, job_id: int, extract_qpy: bool = False):
        get_request = self._request("GET", f"/job/?job_id={job_id}")
        job_dd: dict = get_request.json()

        if extract_qpy:
            qc = self.extract_qiskit(job_dd["qpy"])
            job_dd.update({"qc": qc})

        return job_dd


    def check_job(self, job_id: int):
        get_request = self._request("GET", f"/job/check/?job_id={job_id}")
        return get_request.json()


    def cancel_job(self, job_id: int):
        r = self._request("PATCH", "/job/cancel/", json={"id": job_id})
        return r.json()


    def dispatch_job(self, job_id: int,
                     status: defs.JobStatus,
                     output: dict | None = None):
        req_json = {
                "id": job_id,
                "status": status.value,
                "output": output
                }
        r = self._request("PATCH", "/job/dispatch/", json=req_json)
        return r.json()


    def add_queue(self, queue_name: str, default_access: bool, limit: int, queue_type: defs.QueueType, max_qubits: int, description: str = ""):
        req_json = {
                "name": queue_name,
                "default_access": default_access,
                "limit_per_member": limit, 
                "description": description,
                "type": queue_type,
                "max_qubits": max_qubits
                }
        r = self._request("POST", "/queue/", json=req_json)
        return r.json()


    def get_queue(self, queue_name: str):
        return self._request("GET", f"/queue/{queue_name}").json()


    def list_queues(self, state: defs.QueueState | None = None):
        req_params = {}
        if state is not None:
            req_params["state"] = state.value
        return self._request("GET", "/queues/", params=req_params).json()


    # TODO: use pydantic for cleaner queries
    def update_queue(self, queue_name: str,
                     new_name: str | None = None,
                     new_default_access: bool | None = None,
                     new_limit: int | None = None,
                     new_state: defs.QueueState | None = None):
        req_json = {}
        if new_name is not None: req_json["name"] = new_name
        if new_default_access is not None: req_json["default_access"] = new_default_access
        if new_limit is not None: req_json["limit"] = new_limit
        if new_state is not None: req_json["state"] = new_state.value
        r = self._request("PATCH", f"/queue/{queue_name}", json=req_json)
        return r.json()


    # TODO: use pydantic for cleaner queries
    def query_jobs(self,
                   id: int | None = None,
                   queue_name: str | None = None,
                   queue_id: int | None = None,
                   owner_name: str | None = None,
                   owner_id: int | None = None,
                   status: defs.JobStatus | None = None):
        req_params = {}
        if id is not None: req_params["id"] = id
        if queue_name is not None: req_params["queue_name"] = queue_name
        if queue_id is not None: req_params["queue_id"] = queue_id
        if owner_name is not None: req_params["owner_name"] = owner_name
        if owner_id is not None: req_params["owner_id"] = owner_id
        if status is not None: req_params["status"] = status.value
        r = self._request("GET", "/jobs/", params=req_params)
        return r.json()


    def list_members(self,
                     limit: int | None = None,
                     skip: int | None = None):
        req_params = {}
        if limit is not None: req_params["limit"] = limit
        if skip is not None: req_params["skip"] = skip
        r = self._request("GET", "/members/", params=req_params)
        return r.json()
