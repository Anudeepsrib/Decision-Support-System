import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

os.environ["COMPASS_DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "compass-backend-test.sqlite3")

from backend import app as backend


class CompassBackendTest(unittest.TestCase):
    def setUp(self):
        backend.DATABASE_PATH.unlink(missing_ok=True)
        self.client = TestClient(backend.app)
        self.decision = {"id": 1, "title": "Choose a tool", "summary": "Compare viable tools", "criteria": [{"id": "fit", "name": "Fit", "weight": 100}], "evidence": [], "options": [{"name": "A", "scores": {"fit": 4}}, {"name": "B", "scores": {"fit": None}}]}

    def test_workspace_conflicts_and_graph(self):
        created = self.client.post("/api/workspaces", json={"name": "Team", "decisions": [self.decision]})
        self.assertEqual(created.status_code, 201)
        data = created.json()
        workspace = data["workspace"]
        headers = {"Authorization": f"Bearer {data['token']}"}
        self.assertEqual(self.client.get(f"/api/workspaces/{workspace['id']}", headers=headers).status_code, 200)
        saved = self.client.put(f"/api/workspaces/{workspace['id']}/decisions", headers={**headers, "If-Match": "1"}, json={"decisions": [self.decision]})
        self.assertEqual(saved.json()["workspace"]["revision"], 2)
        conflict = self.client.put(f"/api/workspaces/{workspace['id']}/decisions", headers={**headers, "If-Match": "1"}, json={"decisions": [self.decision]})
        self.assertEqual(conflict.status_code, 409)

        def fake_jev(state):
            self.assertEqual(state["deterministic"]["evaluation_progress"], 50)
            return {"assessment": {"readiness": "needs_work", "human_decision_required": True}}

        result = backend.build_assessment_graph(InMemorySaver(), fake_jev).invoke(
            {"decision": self.decision}, {"configurable": {"thread_id": "test"}}
        )
        self.assertTrue(result["assessment"]["human_decision_required"])


if __name__ == "__main__":
    unittest.main()
