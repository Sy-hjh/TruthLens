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
 def test_urgent_borrowing_reports_text_risk_without_image_score(self):
  from backend.fraud_risk import has_fraud_language
  text='我手机丢了，借我点钱，一会买完手机我就还你\n十万火急'
  signals,assessment=enrich(text,[])
  self.assertTrue(has_fraud_language({'signals': signals, 'assessment': assessment}))
  self.assertIn(('pressure','十万火急'),[(item['category'],item['quote']) for item in signals])
  signals,assessment=enrich('借我一点钱，不要急着转账，可以打原号码确认。',[])
  self.assertFalse(has_fraud_language({'signals': signals, 'assessment': assessment}))

 def test_borrowed_phone_and_immediate_transfer_in_saved_report(self):
  from backend.report_summary import update_summary
  text='我手机刚刚摔坏了，你能借我点钱吗现在，2000\n我现在拿别人手机发的消息，然后我买完手机就还你\n现在你给我转就可以'
  report={'ocr':{'text':text},'chat_analysis':{'status':'completed','assessment':{'level':'attention','version':'qinan-chat-evidence-r3-20261112'},'signals':[]},'modules':{'image':{'status':'completed','score':.32},'tamper':{'status':'completed','method':'fused','regions':[]}}}
  updated=update_summary(report)
  self.assertEqual(updated['summary'],'建议核查')
  self.assertEqual(updated['fraud_risk']['language'],'发现需核实的话术')
  self.assertIn('他人的设备',updated['fraud_risk']['language_reason'])
  quotes={(item['category'],item['quote']) for item in updated['chat_analysis']['signals']}
  self.assertIn(('pressure','现在你给我转就可以'),quotes)
  self.assertIn(('contact_channel','我现在拿别人手机发的消息，'),quotes)

 def test_borrowed_phone_and_forwarding_a_message_do_not_trigger_fraud(self):
  from backend.fraud_risk import has_fraud_language
  for text in ('我现在拿别人手机发的消息，现在你给我转发通知。','我现在拿别人手机联系你，先借我点钱，晚上见面再说。'):
   signals,assessment=enrich(text,[])
   self.assertFalse(has_fraud_language({'signals':signals,'assessment':assessment}))
if __name__=='__main__':unittest.main()
