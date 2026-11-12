import bootstrap,unittest,json
from backend.chat_assessment import enrich
from backend.chat_analysis import validate
class AssessmentTests(unittest.TestCase):
 def test_borrow_and_blocked_verification_warn_even_without_classifier(self):
  text='喂妈妈，我现在急需用点钱。你先借我两千，转到这个新账户。别给我打电话，忙完再说。'
  signals,value=enrich(text,[])
  self.assertEqual(value['level'],'alert');self.assertIn('疑似',value['title']);self.assertEqual(value['cases'][0]['publisher'],'汕尾市公安局');self.assertTrue(all(s['quote'] in text for s in signals))
 def test_normal_conversation_does_not_get_borrowing_case(self):
  signals,value=enrich('妈妈，今天晚上吃饺子吗？好呀，下班回家吃。',[])
  self.assertEqual(signals,[]);self.assertEqual(value['cases'],[]);self.assertNotEqual(value['level'],'alert')
 def test_education_and_negative_money_request_not_red(self):
  for text in ['反诈提醒：别给陌生人汇款，也不要透露验证码。','我今天开会，别给我打电话。']:
   _,value=enrich(text,[]);self.assertNotEqual(value['level'],'alert')
 def test_account_transfer_is_not_password_request(self):
  self.assertEqual(validate(json.dumps({'signals':[{'category':'credentials','quote':'转到这个新账户'}]},ensure_ascii=False),'转到这个新账户'),[])
 def test_legitimate_borrowing_alone_not_accused(self):
  _,value=enrich('先借我两千，晚上当面说，可以打我原来的电话确认。',[])
  self.assertNotEqual(value['level'],'alert');self.assertEqual(value['cases'],[])
  _,value=enrich('妈妈，先借我两千，不要转到这个新账户，先电话核实。',[])
  self.assertNotEqual(value['level'],'alert')
if __name__=='__main__':unittest.main()
