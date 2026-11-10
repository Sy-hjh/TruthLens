import bootstrap,unittest
from unittest.mock import patch
import torch
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import app
from domain_model import views,aggregate
class DomainTests(unittest.TestCase):
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
