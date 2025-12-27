#!/usr/bin/env python3
"""
Test script to verify the people API endpoints work correctly.
This script tests the actual FastAPI endpoints.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import requests
import time
import subprocess
import socket

# Add server to path
sys.path.insert(0, "server")


def test_people_endpoints():
    """Test the people API endpoints."""

    # Start the server in a separate process
    print("🚀 Starting test server...")

    # Create a temporary directory for test databases
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()

    # Pick a free port to avoid collisions with any existing dev server.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server_log = None
    try:
        # Set environment variable for test database
        os.environ["PHOTOSEARCH_TEST_MODE"] = "1"
        os.environ["PHOTOSEARCH_BASE_DIR"] = temp_dir

        # Write server logs to a file to avoid PIPE buffer deadlocks.
        server_log = tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix="test_uvicorn_",
            suffix=".log",
            dir=temp_dir,
            delete=False,
        )

        env = os.environ.copy()
        # Ensure server-side code paths that guard on pytest are also applied in
        # this subprocess-based integration test.
        env.setdefault("PYTEST_CURRENT_TEST", "test_people_endpoints")

        # Start the server (import as a package so relative imports work)
        repo_root = Path(original_dir)
        server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            stdout=server_log,
            stderr=server_log,
            cwd=str(repo_root),
            env=env,
        )

        # Wait for server to start (health check with timeout)
        base_url = f"http://127.0.0.1:{port}"
        started = False
        for _ in range(200):
            if server_process.poll() is not None:
                break
            try:
                r = requests.get(f"{base_url}/server/config", timeout=0.5)
                if r.status_code == 200:
                    started = True
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not started:
            stderr = b""
            try:
                # Avoid blocking reads: if the server didn't start, stop it and
                # collect a bounded amount of stderr for diagnostics.
                server_process.terminate()
                try:
                    server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server_process.kill()
                    server_process.wait(timeout=3)

                if server_log is not None:
                    server_log.flush()
                    with open(server_log.name, "rb") as f:
                        stderr = f.read()[-800:] or b""
            except Exception:
                pass
            raise RuntimeError(
                "Test server failed to start. "
                f"exit={server_process.poll()} stderr_tail={stderr.decode('utf-8', errors='ignore')[-800:]}"
            )

        # Test photo path for testing (no leading slash to avoid creating a double-slash URL)
        test_photo_path = "test/people/photo.jpg"

        print("🧪 Testing people endpoints...")

        # Test 1: GET /api/photos/{photo_path}/people (should return empty initially)
        print("Test 1: GET people in photo (empty)")
        response = requests.get(f"{base_url}/api/photos/{test_photo_path}/people", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["people"] == []

        # Test 2: POST /api/photos/{photo_path}/people (add a person)
        print("\nTest 2: POST add person to photo")
        person_id = "test_person_123"
        detection_id = "test_face_123"
        response = requests.post(
            f"{base_url}/api/photos/{test_photo_path}/people",
            json={"person_id": person_id, "detection_id": detection_id},
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["success"]

        # Test 3: GET /api/photos/{photo_path}/people (should now return the person)
        print("\nTest 3: GET people in photo (with person)")
        response = requests.get(f"{base_url}/api/photos/{test_photo_path}/people", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert person_id in response.json()["people"]

        # Test 4: DELETE /api/photos/{photo_path}/people/{person_id} (remove the person)
        print("\nTest 4: DELETE remove person from photo")
        response = requests.delete(
            f"{base_url}/api/photos/{test_photo_path}/people/{person_id}",
            timeout=5,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["success"]

        # Test 5: GET /api/photos/{photo_path}/people (should be empty again)
        print("\nTest 5: GET people in photo (empty again)")
        response = requests.get(f"{base_url}/api/photos/{test_photo_path}/people", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["people"] == []

        print("\n✅ All people endpoint tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise e

    finally:
        # Clean up
        os.chdir(original_dir)

        # Stop the server
        if "server_process" in locals():
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait(timeout=5)

        if server_log is not None:
            try:
                server_log.close()
            except Exception:
                pass

        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Clean up environment variables
        os.environ.pop("PHOTOSEARCH_TEST_MODE", None)
        os.environ.pop("PHOTOSEARCH_BASE_DIR", None)


if __name__ == "__main__":
    test_people_endpoints()
    print("🎉 People endpoints test completed successfully!")
