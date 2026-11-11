import bootstrap
import unittest, tempfile, time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app, phrase_evidence, cleanup_interrupted
from backend import storage


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.override = patch.object(storage, "ROOT", Path(self.tmp.name))
        self.override.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.override.stop()
        self.tmp.cleanup()

    def test_pages(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertIn("models", self.client.get("/api/health").json())

    def test_upload_validation(self):
        self.assertEqual(
            self.client.post(
                "/api/analyze", files={"file": ("bad.exe", b"x")}
            ).status_code,
            415,
        )
        self.assertEqual(
            self.client.post(
                "/api/analyze", files={"file": ("empty.wav", b"")}
            ).status_code,
            422,
        )

    def test_rules_are_evidence_only(self):
        self.assertTrue(phrase_evidence("马上转账，不要告诉家人"))
        self.assertEqual(phrase_evidence("下午和家人吃饭"), [])

    def test_negation_and_traditional_chinese(self):
        self.assertEqual(phrase_evidence("不涉及转账和验证码"), [])
        self.assertEqual(phrase_evidence("请不要转账"), [])
        self.assertTrue(phrase_evidence("馬上轉帳，不要告訴家人"))

    def test_demo_routes_cannot_read_arbitrary_files(self):
        self.assertEqual(
            self.client.get("/api/demo/family-simulation").status_code, 200
        )
        self.assertEqual(self.client.get("/api/demo/requirements.txt").status_code, 404)

    def test_history(self):
        storage.save({"id": "test", "filename": "test"})
        self.assertEqual(len(self.client.get("/api/cases").json()), 1)
        self.client.delete("/api/cases/test")
        self.assertEqual(self.client.get("/api/cases/test").status_code, 404)

    def test_completed_job_recovers_from_database(self):
        storage.save({'id':'resume-check','filename':'example'})
        result=self.client.get('/api/jobs/resume-check')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['status'],'completed')

    def test_deleted_report_is_removed_from_job_cache(self):
        from backend.app import jobs,joblock
        storage.save({'id':'delete-cache','filename':'example'})
        with joblock:jobs['delete-cache']={'status':'completed','result':{'id':'delete-cache'}}
        self.assertEqual(self.client.delete('/api/cases/delete-cache').status_code,200)
        self.assertEqual(self.client.get('/api/jobs/delete-cache').status_code,404)

    def test_retired_transcript_endpoint_cannot_add_word_detection(self):
        storage.save({'id':'edit','modules':{'audio':{'score':.9}},'phrases':[]})
        r=self.client.post('/api/cases/edit/transcript',data={'text':'马上转账，不要告诉家人'})
        self.assertEqual(r.status_code,410)
        self.assertEqual(storage.get('edit')['phrases'],[])
        self.assertEqual(storage.get('edit')['modules']['audio']['score'],.9)

    def test_interrupted_upload_cleanup_is_scoped(self):
        stale = storage.ROOT / "upload-abcdefgh"
        stale.mkdir()
        (stale / "input.png").write_bytes(b"test")
        keep = storage.ROOT / "reports"
        keep.mkdir()
        (keep / "report.json").write_text("{}")
        self.assertEqual(cleanup_interrupted(), 1)
        self.assertFalse(stale.exists())
        self.assertTrue((keep / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
