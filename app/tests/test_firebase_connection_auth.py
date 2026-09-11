import os
os.environ.setdefault("SOCIETY_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_society.db"))
import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import init_db, get_db
from app.core.firebase import (
    init_firebase,
    get_firebase_status,
    is_firebase_available,
    create_firebase_custom_token
)

client = TestClient(app)

class TestFirebaseConnectionAndAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db(force=True)
        # Onboard a test society: Dharwad Handloom Weavers
        res = client.post("/api/v1/onboarding/finalize", json={
            "primary_phone": "9988776655",
            "primary_email": "secretary@dharwad.coop",
            "admin_password": "secureDharwad123",
            "admin_full_name": "Secretary Dharwad",
            "legal_name_en": "Dharwad Handloom Weavers Co-operative Society",
            "legal_name_kn": "ಧಾರವಾಡ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ",
            "registration_number": "DR/DWD/2026/089",
            "registration_date": "2026-01-15",
            "district": "Dharwad",
            "taluk": "Hubballi",
            "hobli_village": "Navalgund",
            "pincode": "580020",
            "registered_office_address": "Station Road, Hubballi",
            "members_count": 45,
            "active_looms_count": 35
        })
        assert res.status_code == 200, f"Onboarding failed: {res.text}"
        data = res.json()
        cls.tenant_id = data["tenant_id"]

        # Authenticate to get session token
        login_res = client.post("/api/v1/auth/login", json={
            "identifier": "9988776655",
            "password": "secureDharwad123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        auth_data = login_res.json()
        cls.token = auth_data["access_token"]
        cls.user_id = auth_data["user_id"]


    def test_01_firebase_live_connection_and_status(self):
        """Verify Firebase Admin SDK, Firestore and Auth are active and connected."""
        status_info = get_firebase_status()
        self.assertTrue(status_info["connected"])
        self.assertEqual(status_info["status"], "connected")
        self.assertEqual(status_info["project_id"], "weaver-society")
        self.assertTrue(status_info["firestore_ready"])
        self.assertTrue(status_info["auth_ready"])

        # Check API status endpoint
        res = client.get("/api/v1/system/firebase-status")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["connected"])
        self.assertEqual(body["project_id"], "weaver-society")
        self.assertTrue(body["firestore_ready"])
        self.assertTrue(body["auth_ready"])

    def test_02_firebase_custom_token_minting(self):
        """Verify authenticated tenant user can obtain a Firebase Custom Token with tenant claims."""
        headers = {"Authorization": f"Bearer {self.token}"}
        res = client.get("/api/v1/auth/firebase-token", headers=headers)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("custom_token", body)
        self.assertEqual(body["project_id"], "weaver-society")
        self.assertEqual(body["user_id"], self.user_id)
        self.assertEqual(body["tenant_id"], self.tenant_id)
        self.assertEqual(body["role"], "SECRETARY")
        self.assertTrue(len(body["custom_token"]) > 50)

    def test_03_firebase_login_invalid_token(self):
        """Verify invalid or forged Firebase ID tokens are rejected with 401."""
        res = client.post("/api/v1/auth/firebase-login", json={
            "id_token": "invalid.forged.token",
            "tenant_id": self.tenant_id
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid Firebase ID token", res.json()["detail"])

    def test_04_firebase_login_phone_match_and_uid_linking(self):
        """Verify simulated Firebase verified phone token matches cooperative user and links firebase_uid."""
        mock_decoded = {
            "uid": "firebase_uid_test_9988776655",
            "phone_number": "+919988776655",
            "email": "secretary@dharwad.coop",
            "name": "Secretary Dharwad"
        }

        with patch("app.api.auth_routes.verify_firebase_id_token", return_value=mock_decoded):
            res = client.post("/api/v1/auth/firebase-login", json={
                "id_token": "valid_mock_firebase_id_token_123"
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("access_token", data)
            self.assertEqual(data["tenant_id"], self.tenant_id)
            self.assertEqual(data["role"], "SECRETARY")
            self.assertEqual(data["user_id"], self.user_id)

        # Confirm firebase_uid was linked in DB
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT firebase_uid FROM users WHERE id = ?", (self.user_id,))
            row = c.fetchone()
            self.assertEqual(row["firebase_uid"], "firebase_uid_test_9988776655")

    def test_05_firebase_sync_to_firestore(self):
        """Verify tenant profile and weavers are synced to Firestore."""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Add a sample weaver member
        w_res = client.post("/api/v1/weavers", headers=headers, json={
            "membership_no": "DWD/WVR/001",
            "full_name_en": "Basavaraj Pattar",
            "full_name_kn": "ಬಸವರಾಜ್ ಪತ್ತಾರ್",
            "phone": "9876543210",
            "village": "Navalgund",
            "taluk": "Hubballi",
            "loom_type": "PIT_LOOM",
            "active_looms_count": 2
        })
        self.assertEqual(w_res.status_code, 200)

        # Trigger sync to Firestore
        sync_res = client.post("/api/v1/system/firebase-sync", headers=headers)
        self.assertEqual(sync_res.status_code, 200)
        sync_data = sync_res.json()
        self.assertTrue(sync_data.get("synced", False), f"Sync failed: {sync_data}")
        self.assertEqual(sync_data["tenant_id"], self.tenant_id)
        self.assertGreaterEqual(sync_data["members_synced"], 1)

if __name__ == "__main__":
    unittest.main()
