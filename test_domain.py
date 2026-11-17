import bootstrap,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import torch
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import app
from backend import app as backend_app
from domain_model import views,aggregate
class DomainTests(unittest.TestCase):
    def test_region_cluster_marks_box_and_ignores_single_pixel(self):
        from backend.tamper import anomaly_regions
        heat = Image.new("L", (100, 100))
        heat.putpixel((5, 5), 255)
        heat.paste(224, (30, 40, 43, 48))
        regions = anomaly_regions(heat)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["box"], [0.30, 0.40, 0.43, 0.48])

    def test_legacy_local_map_adds_warning_without_changing_model_scores(self):
        import base64
        from io import BytesIO
        from backend.tamper import with_saved_regions
        heat = Image.new("L", (20, 20))
        heat.paste(224, (7, 7, 12, 12))
        data = BytesIO()
        heat.save(data, format="PNG")
        uri = "data:image/png;base64," + base64.b64encode(data.getvalue()).decode()
        report = {"summary": "未触发", "modules": {"tamper": {"status": "completed", "score": 0.2, "map_png": uri}}}
        enriched = with_saved_regions(report)
        self.assertIn("局部异常区域", enriched["summary"])
        self.assertEqual(enriched["modules"]["tamper"]["score"], 0.2)
        self.assertNotIn("regions", report["modules"]["tamper"])

    def test_high_local_risk_is_reported_with_low_whole_image_score(self):
        image_result = {"status": "completed", "score": 0.10, "threshold": 0.50}
        tamper_result = {"status": "completed", "score": 0.98, "threshold": 0.95}
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sample.png"
            Image.new("RGB", (20, 20)).save(path)
            with patch.dict(backend_app.jobs, {"test-tamper": {}}, clear=True), \
                patch("backend.resource_budget.prepare", return_value={}), \
                patch("backend.detector.classify", return_value=image_result), \
                patch("backend.tamper.available", return_value=True), \
                patch("backend.tamper.predict", return_value=tamper_result), \
                patch("backend.storage.save") as save:
                backend_app.process("test-tamper", path, path.name, "", "", folder)
                self.assertEqual(backend_app.jobs["test-tamper"]["status"], "completed")
                saved = save.call_args.args[0]
                self.assertIn("局部篡改风险", saved["summary"])
                self.assertEqual(saved["modules"]["image"], image_result)
                self.assertEqual(saved["modules"]["tamper"], tamper_result)

    def test_portrait_landscape_and_jpeg_keep_five_views(self):
        for size in ((120,400),(400,120),(224,224)):
            for quality in (None,60,85):
                tensor=views(Image.new('RGB',size,(130,70,40)),quality)
                self.assertEqual(tuple(tensor.shape),(5,3,224,224));self.assertTrue(torch.isfinite(tensor).all())
    def test_local_view_permutation_does_not_change_aggregation(self):
        x=torch.tensor([[2.,1.,3.,5.,7.]])
        self.assertTrue(torch.equal(aggregate(x),aggregate(x[:,[0,4,2,3,1]])))
    def test_missing_product_model_does_not_return_generic_score(self):
        with patch('backend.product.available',return_value=False):
            response=TestClient(app).post('/api/analyze',files={'file':('test.jpg',b'not-used')},data={'scene':'product'})
        self.assertEqual(response.status_code,503)
    def test_unknown_scene_rejected(self):
        response=TestClient(app).post('/api/analyze',files={'file':('test.jpg',b'not-used')},data={'scene':'made-up'})
        self.assertEqual(response.status_code,422)
if __name__=='__main__':unittest.main()
