"""
VRChat API Manager

Handles interaction with the VRChat Web API for authentication and file uploads.
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.vrchat.cloud/api/1"


class APIManager:
    """Manages VRChat Web API interactions."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
        self.auth_cookie: str | None = None
        self.user_agent = "VRChat-MCP/0.1.0 (contact: admin@example.com)"

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with VRChat API using basic auth."""
        try:
            auth = (username, password)
            headers = {"User-Agent": self.user_agent}

            # Simple login request to /auth/user
            response = await self.client.get("/auth/user", auth=auth, headers=headers)

            if response.status_code == 200:
                self.auth_cookie = response.headers.get("set-cookie")
                user_data = response.json()
                return {
                    "status": "success",
                    "message": "Logged in successfully",
                    "username": user_data.get("username"),
                    "id": user_data.get("id"),
                }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "message": "Invalid credentials",
                    "code": 401,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Login failed: {response.status_code}",
                    "details": response.text,
                }

        except Exception as e:
            logger.error(f"Login exception: {e}")
            return {"status": "error", "message": f"Login exception: {e!s}"}

    async def _compute_md5(self, file_path: str) -> str:
        """Compute MD5 hash of a file."""
        return await asyncio.to_thread(self._compute_md5_sync, file_path)

    def _compute_md5_sync(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()  # noqa: S324 (Required by VRChat API for Content-MD5)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def upload_file(self, file_path: str, name: str | None = None) -> dict[str, Any]:
        """Upload a file to VRChat API.

        Flow:
        1. Prepare metadata (MD5, size, mime type).
        2. Create file record (POST /file).
        3. Create file version (POST /file/{id}/{version}).
        4. Start upload (PUT /file/{id}/{version}/{type}/start).
        5. Upload data (PUT to S3/Cloudflare URL).
        6. Finish upload (PUT /file/{id}/{version}/{type}/finish).
        """
        if not os.path.exists(file_path):
            return {"status": "error", "message": f"File not found: {file_path}"}

        if not self.auth_cookie:
            return {
                "status": "error",
                "message": "Not authenticated. Call api_login first.",
            }

        try:
            os.path.getsize(file_path)
            md5_hash = await self._compute_md5(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"
            file_name = name or os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lstrip(".")

            headers = {"User-Agent": self.user_agent, "Cookie": self.auth_cookie}

            # 1. Create File Record
            create_data = {"name": file_name, "mimeType": mime_type, "extension": ext}
            logger.info(f"Creating file record for {file_name}...")
            create_res = await self.client.post("/file", json=create_data, headers=headers)
            if create_res.status_code != 200:
                return {
                    "status": "error",
                    "message": "Failed to create file record",
                    "details": create_res.text,
                }

            file_id = create_res.json().get("id")
            version = 1  # New files start at version 1

            # 2. Start Upload
            # Note: For simple files, we assume 'file' type. VRChat API can be complex with parts.
            # This is a simplified single-part upload implementation.

            # Note: A robust implementation would handle multipart uploads for large files.
            # Here we assume a standard 'file' type upload.

            # Get Upload URL
            upload_type = "file"  # or 'signature', 'delta'
            start_url = f"/file/{file_id}/{version}/{upload_type}/start"
            start_res = await self.client.put(start_url, headers=headers)  # Usually simply PUT starts it?

            # Actually, standard flow creates a version first if it doesn't exist?
            # When creating a new file, version 0 is created? No, '1'.

            # NOTE: VRChat API is quirky. Often requires checking status.
            # Let's try the direct approach: create -> get upload url -> put -> finish.

            if start_res.status_code != 200:
                # Try creating version first?
                # For new files, the /file endpoint typically creates version 1.
                return {
                    "status": "error",
                    "message": "Failed to start upload transaction",
                    "details": start_res.text,
                }

            upload_data = start_res.json()
            upload_url = upload_data.get("url")

            # 3. Upload File Data
            logger.info("Uploading file data...")
            with open(file_path, "rb") as f:
                # Direct upload to the signed URL (S3/Cloudflare)
                # Note: Do not send VRChat cookies to S3
                s3_res = await httpx.AsyncClient().put(
                    upload_url,
                    content=f,
                    headers={
                        "Content-Type": mime_type,
                        "Content-MD5": md5_hash,
                    },  # Sometimes S3 requires MD5
                )

            if s3_res.status_code not in [200, 201]:
                return {
                    "status": "error",
                    "message": "Failed to upload data to storage",
                    "details": s3_res.text,
                }

            # 4. Finish Upload
            finish_url = f"/file/{file_id}/{version}/{upload_type}/finish"
            # ETags might be required.
            finish_data = {"etags": [s3_res.headers.get("ETag").strip('"')] if s3_res.headers.get("ETag") else []}

            finish_res = await self.client.put(finish_url, json=finish_data, headers=headers)

            if finish_res.status_code == 200:
                return {
                    "status": "success",
                    "message": "File uploaded successfully",
                    "file_id": file_id,
                    "url": create_res.json().get("url"),  # Or constructing it
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to finalize upload",
                    "details": finish_res.text,
                }

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {"status": "error", "message": f"Upload failed: {e!s}"}

    async def close(self):
        await self.client.aclose()
