import bootstrap,unittest,json
import numpy as np
from backend.text_patterns import load,predict,normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.special import softmax
from unittest.mock import patch

class TextChecks(unittest.TestCase):
 def test_export_inference_matches_library_tfidf(self):
  meta,vocab,idf,coef,intercept=load();text='你好，我是XX市公安局民警，你涉嫌洗钱案件，需要配合调查，案情保密。'
  vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(2,4),vocabulary=vocab,sublinear_tf=True);vectorizer.idf_=idf
  x=vectorizer.transform([normalize(text)]);p=softmax((x@coef.T+intercept)/meta['temperature'],axis=1)[0]
  result=predict(text)
  for item in result['patterns']:self.assertAlmostEqual(item['score'],p[meta['labels'].index(item['label'])],places=3)
 def test_empty_ocr_abstains(self):
  self.assertEqual(predict('16:00')['status'],'insufficient')
 def test_never_calls_normal_safe(self):
  result=predict('你好，我是客户经理，想询问一下您是否有意愿了解保险业务。')
  self.assertNotIn('安全',result['title']);self.assertNotIn('fraud_probability',result)
 def test_quote_engine_failure_preserves_trained_result(self):
  from backend.chat_analysis import analyze
  with patch('backend.chat_analysis._analyze',side_effect=RuntimeError('test unavailable')):
   result=analyze('你好，我是公安局民警，你涉嫌洗钱案件，配合调查，不能告诉任何人。')
  self.assertEqual(result['extraction_status'],'rules_only');self.assertEqual(result['pattern']['status'],'completed')
  self.assertTrue(all(s.get('extraction')=='explicit_request_guard' for s in result['signals']))
  self.assertEqual(result['signals'][0]['quote'],'不能告诉任何人。')
  self.assertIn('语言模型暂不可用',result['note'])
 def test_no_audio_transcription_dependency(self):
  import inspect,backend.text_patterns as module
  self.assertNotIn('transcribe',inspect.getsource(module))
if __name__=='__main__':unittest.main()
