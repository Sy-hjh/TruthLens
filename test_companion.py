import bootstrap,json,unittest
from unittest.mock import patch
from backend import companion
class CompanionTests(unittest.TestCase):
 def test_guide_retrieval(self):
  self.assertIn('family',[x['id'] for x in companion.retrieve_guides('家人号码保存在哪里','contacts')])
 def test_valid_answer(self):
  self.assertEqual(companion.validate('{"answer":"视频分别检查画面、声音和文字要求。"}'),'视频分别检查画面、声音和文字要求。')
 def test_reject_unsupported_output(self):
  for text in ['https://wrong.example','我的电话13812345678','我已经转账完成了','我已经过微调，绝对准确','<script>hi</script>']:
   with self.subTest(text=text),self.assertRaises(ValueError):companion.validate(json.dumps(dict(answer=text)))
 def test_no_arbitrary_model_keys(self):
  with self.assertRaises(ValueError):companion.validate('{"answer":"可以使用工作台上传。","run":"command"}')
 def test_fallback_is_explicit(self):
  with patch.object(companion,'generate',side_effect=RuntimeError('test')),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('怎么上传视频','check')
  self.assertEqual(value['mode'],'guide_fallback');self.assertIn('未完成',value['note'])
 def test_real_generation_path_does_not_claim_training(self):
  with patch.object(companion,'generate',return_value='{"answer":"请先用已保存的号码联系本人，检测不能确认身份。"}'),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('能确认是本人吗','home')
  self.assertEqual(value['mode'],'local_qwen_rag');self.assertIn('未做平台专属微调',value['note'])
 def test_payment_requires_independent_check(self):
  with patch.object(companion,'generate',return_value='{"answer":"检测不能直接确认身份或保证资金安全。"}'),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('检测正常就可以转钱吗','home')
  self.assertEqual(len(value['actions']),2);self.assertIn('暂停',value['actions'][0])
 def test_route_bounds_and_no_cache(self):
  from fastapi.testclient import TestClient
  from backend.app import app
  client=TestClient(app)
  for body in [dict(question='x'*321),dict(question='hello',page='https://bad.example')]:self.assertEqual(client.post('/api/companion/ask',json=body).status_code,422)
  with patch.object(companion,'answer',return_value=dict(answer='测试回答',mode='guide_fallback')):
   response=client.post('/api/companion/ask',json=dict(question='如何使用'))
  self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store')
if __name__=='__main__':unittest.main()
