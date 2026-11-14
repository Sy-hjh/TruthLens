import bootstrap,unittest
from fastapi.testclient import TestClient
from backend.app import app
from backend.agent_review import report_facts
class TruthLensDeliveryTests(unittest.TestCase):
 def test_idle_cache_is_released_under_memory_pressure(self):
  from unittest.mock import patch
  from backend.resource_budget import prepare
  with patch('backend.resource_budget.free_memory',side_effect=[1*1024**3,7*1024**3]),patch('backend.acoustic_worker_client.close') as close,patch('backend.text_runtime.drop_cache') as drop:
   self.assertTrue(prepare()['trimmed']);close.assert_called_once();drop.assert_called_once()
 def test_active_inference_is_never_killed_by_memory_policy(self):
  from unittest.mock import patch
  from backend.detector import lock
  from backend.resource_budget import prepare
  with lock,patch('backend.resource_budget.free_memory',return_value=1),patch('backend.acoustic_worker_client.close') as close:
   self.assertEqual(prepare()['reason'],'model_in_use');close.assert_not_called()
 def test_only_selected_video_stack_is_imported(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  from backend.app import video_predictor
  model=SimpleNamespace(configured=lambda:True,predict=lambda path:None)
  with patch('importlib.import_module',return_value=model) as load:
   predict,fusion=video_predictor();self.assertIs(predict,model.predict);self.assertFalse(fusion)
   load.assert_called_once_with('.ordered_video',package='backend')
 def test_failed_detector_is_not_described_as_real(self):
  facts,_=report_facts({'modules':{'audio':{'status':'failed','score':.99}}},'真人吗')
  self.assertIn('尚未得到有效结果',facts[0]);self.assertNotIn('本次未检出',facts[0])
 def test_segment_uses_own_threshold(self):
  facts,_=report_facts({'modules':{'audio':{'status':'completed','segments':[{'score':.6,'threshold':.7}]}}},'')
  self.assertIn('未检出明确合成',facts[0])
 def test_identity_cannot_be_proved_by_low_score(self):
  facts,note=report_facts({'modules':{'image':{'status':'completed','score':.01,'threshold':.9}}},'这是我女儿吗')
  self.assertIn('不能核实',note);self.assertIn('不能据此确认身份',facts[0])
 def test_probability_question_is_not_assigned_fraud_probability(self):
  _,note=report_facts({'modules':{}},'被骗概率多少')
  self.assertIn('不是被骗概率',note)
 def test_qa_reports_are_hidden_but_not_destroyed(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from backend import storage
  with tempfile.TemporaryDirectory() as d,patch.object(storage,'ROOT',Path(d)):
   storage.save({'id':'qa','internal_only':True});storage.save({'id':'customer'})
   self.assertEqual([r['id'] for r in storage.listing()],['customer']);self.assertEqual(len(storage.listing(True)),2);self.assertEqual(storage.get('qa')['id'],'qa')
 def test_frontend_security_and_cache_policy(self):
  c=TestClient(app);r=c.get('/')
  self.assertEqual(r.status_code,200);self.assertIn('TruthLens',r.text);self.assertEqual(r.headers['cache-control'],'no-cache');self.assertEqual(r.headers['x-content-type-options'],'nosniff')
  self.assertEqual(c.get('/api/cases/missing').headers['cache-control'],'no-store')
if __name__=='__main__':unittest.main()
