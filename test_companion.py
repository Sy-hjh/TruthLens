import bootstrap,json,unittest
from unittest.mock import Mock, patch
from backend import companion, companion_online
class CompanionTests(unittest.TestCase):
 def setUp(self):
  config=patch.object(companion,'configured_model',return_value=None)
  config.start()
  self.addCleanup(config.stop)
 def test_guide_retrieval(self):
  self.assertIn('family',[x['id'] for x in companion.retrieve_guides('家人号码保存在哪里','contacts')])
 def test_desktop_resolver_selects_a_unique_media_file(self):
  from pathlib import Path
  from tempfile import TemporaryDirectory
  from fastapi import HTTPException
  from backend.app import find_desktop_file
  with TemporaryDirectory() as folder:
   desktop=Path(folder)
   (desktop/'ai.wav').touch()
   (desktop/'ai.txt').touch()
   self.assertEqual(find_desktop_file('AI',desktop).name,'ai.wav')
   (desktop/'ai.mp3').touch()
   with self.assertRaises(HTTPException) as ambiguous:
    find_desktop_file('ai',desktop)
   self.assertEqual(ambiguous.exception.detail['code'],'ambiguous_file')
   self.assertEqual(find_desktop_file('ai.WAV',desktop).name,'ai.wav')
   with self.assertRaises(HTTPException):
    find_desktop_file('../ai.wav',desktop)
 def test_drive_resolver_searches_nested_folders_and_reports_ambiguity(self):
  from pathlib import Path
  from tempfile import TemporaryDirectory
  from fastapi import HTTPException
  from backend.app import find_drive_file
  with TemporaryDirectory() as folder:
   root=Path(folder)
   first=root/'材料'
   first.mkdir()
   (first/'录音 01.m4a').touch()
   self.assertEqual(find_drive_file('录音 01', root),first/'录音 01.m4a')
   (root/'录音 01.m4a').touch()
   with self.assertRaises(HTTPException) as ambiguous:
    find_drive_file('录音 01',root)
   self.assertIn(str(first/'录音 01.m4a'),ambiguous.exception.detail['paths'])
   with self.assertRaises(HTTPException) as timed_out:
    find_drive_file('录音 01',root,timeout=0)
   self.assertEqual(timed_out.exception.status_code,408)
   clock=Mock()
   clock.monotonic.side_effect=[0,0,0,0,2]
   with patch('backend.app.time',clock),self.assertRaises(HTTPException) as partial:
    find_drive_file('录音 01',root,timeout=1)
   self.assertEqual(partial.exception.detail['code'],'incomplete_file_search')
   self.assertEqual(partial.exception.detail['paths'],[str(root/'录音 01.m4a')])
 def test_valid_answer(self):
  self.assertEqual(companion.validate('{"answer":"视频分别检查画面、声音和文字要求。"}'),'视频分别检查画面、声音和文字要求。')
 def test_answer_limit_matches_next_turn_history(self):
  from backend.app import CompanionTurn
  maximum='核'*300
  self.assertEqual(companion.validate(json.dumps({'answer':maximum})),maximum)
  self.assertEqual(CompanionTurn(question='怎么核验',answer=maximum).answer,maximum)
  with self.assertRaises(ValueError):companion.validate(json.dumps({'answer':maximum+'验'}))
 def test_reject_unsupported_output(self):
  for text in ['https://wrong.example','我的电话13812345678','我已经转账完成了','我已经过微调，绝对准确','<script>hi</script>','可以建立验证码口头核对流程。','对方索要银行卡号，属于诈骗行为。','能否提供订单号让我查一下？','这篇论文肯定是AI写的。','有90%的概率是诈骗。']:
   with self.subTest(text=text),self.assertRaises(ValueError):companion.validate(json.dumps(dict(answer=text)))
 def test_no_arbitrary_model_keys(self):
  with self.assertRaises(ValueError):companion.validate('{"answer":"可以使用工作台上传。","run":"command"}')
 def test_fallback_is_explicit(self):
  with patch.object(companion,'generate',side_effect=RuntimeError('test')),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('怎么上传视频','check')
  self.assertEqual(value['mode'],'guide_fallback');self.assertIn('备用',value['note'])
 def test_online_model_selects_material_in_one_call(self):
  online=companion_online.OnlineModel('https://api.siliconflow.cn/v1/chat/completions','XingChenAGI/Xing4.0-29B','test-secret')
  response=Mock(status_code=200)
  response.json.return_value={'choices':[{'message':{'content':'image'}}]}
  history=[dict(question='有人拿商品损坏的图申请售后',answer='你手上有客户发来的照片吗？')]
  with patch.object(companion,'configured_model',return_value=online),patch.object(companion,'generate') as local,patch.object(companion_online.requests,'post',return_value=response) as post,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('有，我怀疑是别人合成的。','home',history)
  self.assertEqual(result['mode'],'material_guidance')
  self.assertEqual(result['material_options'],['image'])
  self.assertIn('添加附件',result['answer'])
  post.assert_called_once()
  self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer test-secret')
  self.assertIn(history[0]['question'],post.call_args.kwargs['json']['messages'][-1]['content'])
  self.assertNotIn('test-secret',str(post.call_args.kwargs['json']))
  local.assert_not_called()
 def test_online_auth_failure_is_visible(self):
  online=companion_online.OnlineModel('https://example.test/v1/chat/completions','test-model','test-secret')
  with patch.object(companion,'configured_model',return_value=online),patch.object(companion_online.requests,'post',return_value=Mock(status_code=401)),patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('怎么核验','home')
  self.assertEqual(result['mode'],'guide_fallback')
  self.assertIn('API Key',result['note'])
  self.assertNotIn('test-secret',str(result))
 def test_numbered_friend_loan_is_a_situation_to_answer(self):
  question='我朋友跟我借500，说手机坏了能帮我看一下是不是真的吗'
  reply='先别转账。用你原来保存的号码联系朋友本人，问是不是他发来借钱的消息。'
  false_capability='上传借条照片，真鉴平台检索是否与银行登记相符。'
  with patch.object(companion,'generate',side_effect=[json.dumps({'answer':false_capability}),json.dumps({'answer':reply})]) as model:
   result=companion.answer(question,'home')
  self.assertEqual(model.call_count,2)
  self.assertEqual(result['answer'],reply+companion.CHECK_OFFER)
  self.assertEqual(result['material_options'],[])
  self.assertEqual(result['actions'],[])
  self.assertTrue({'K1','K2','K9'} & {source['id'] for source in result['sources']})
 def test_numbered_loan_failure_still_explains_how_to_verify(self):
  with patch.object(companion,'generate',side_effect=companion_online.OnlineModelError('模型超时')):
   result=companion.answer('同学说手机坏了，问我借两百块，这事靠谱吗？','home')
  self.assertEqual(result['mode'],'guide_fallback')
  self.assertIn('先别转账',result['answer'])
  self.assertIn('保存的号码',result['answer'])
 def test_unknown_material_asks_one_question(self):
  question='帮我核验一下这个是不是真的'
  with patch.object(companion,'generate',return_value='any') as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer(question,'home')
  model.assert_called_once()
  self.assertEqual(result['mode'],'material_guidance')
  self.assertEqual(result['answer'].count('？'),1)
  self.assertIn('还是',result['answer'])
  self.assertEqual(result['material_options'],[])
 def test_photo_selection_goes_directly_to_attachment(self):
  with patch.object(companion,'configured_model') as model:
   for question in ('照片','我说的是照片','就是照片。','帮我检测一下这张照片是不是AI生成的。'):
    with self.subTest(question=question):
     result=companion.answer(question,'home')
     self.assertEqual(result['material'],'image')
     self.assertIn('截屏',result['answer'])
     self.assertNotIn('？',result['answer'])
   model.assert_not_called()
 def test_airline_procedure_is_answered_before_optional_check(self):
  question='刚刚客服说飞机不飞了，要给我退款，让我给银行卡，我想问问是不是真的正常流程是什么样子得'
  reply='先别把银行卡号告诉对方。自行查航司官方航班状态，再到原购票订单查看退改，退款通常原路退回。'
  with patch.object(companion,'generate',side_effect=['any',json.dumps({'answer':reply})]) as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer(question,'home')
  self.assertEqual(model.call_count,2)
  self.assertEqual(result['answer'],reply+companion.CHECK_OFFER)
  self.assertEqual(result['material_options'],[])
 def test_flight_refund_sources_do_not_appear_in_retail_refund(self):
  from backend.rag import FLIGHT_GUIDANCE_IDS,FLIGHT_REFUND_IDS,retrieve
  retail=retrieve('客服收到货损截图，电商订单退款流程是什么？')
  flight=retrieve('客服说飞机不飞了，要给我退款，让我给银行卡。')
  self.assertTrue(FLIGHT_GUIDANCE_IDS.isdisjoint(doc['id'] for doc in retail))
  self.assertTrue(FLIGHT_REFUND_IDS.issubset(doc['id'] for doc in flight))
 def test_current_flight_notification_uses_notice_source_even_after_refund(self):
  history=[dict(question='刚刚客服打电话要我的银行卡说机票退款，怎么办？',answer='从原购票订单核实。')]
  question='飞机停飞正常通知我们得流程是什么'
  reply='航司会通过官方 App、短信或电话通知，售票平台也会转达。可打开原购票订单核对。'
  with patch.object(companion,'generate',side_effect=['outside',json.dumps({'answer':reply})]) as model:
   result=companion.answer(question,'home',history)
  self.assertEqual(model.call_count,2)
  self.assertEqual(result['answer'],reply)
  self.assertEqual(json.loads(model.call_args.args[0][-1]['content'])['history'],[])
  self.assertEqual([source['id'] for source in result['sources']],['K12'])
  self.assertEqual(result['material_options'],[])
  self.assertEqual(result['actions'],[])
 def test_implicit_followup_keeps_context_and_retries_an_overconfident_answer(self):
  history=[dict(question='航班取消后正常怎么通知乘客？',answer='航司可通过官方 App、短信和电话通知。')]
  reply='索要卡号这一步很可疑，先别给。自己打开原购票订单，或联系航司官方客服确认。'
  with patch.object(companion,'generate',side_effect=['none','{"answer":"对方索要银行卡号，属于诈骗行为。"}',json.dumps({'answer':reply})]) as model:
   result=companion.answer('会否给我打电话要我银行卡号','home',history)
  self.assertEqual(model.call_count,3)
  self.assertIn(history[0]['question'],model.call_args_list[0].args[0][-1]['content'])
  self.assertEqual(result['mode'],'local_qwen_rag')
  self.assertEqual(result['answer'],reply)
  self.assertIn('K10',[source['id'] for source in result['sources']])
 def test_qualitative_impressions_are_allowed(self):
  for reply in ('对方要先交解冻费，我看风险较高，建议先别付。','仅从这一点看，可能是冒充客服。','这篇论文的引文值得核对，但不能确认是AI写的。'):
   with self.subTest(reply=reply):
    self.assertEqual(companion.validate(json.dumps({'answer':reply})),reply)
 def test_writing_consultation_answers_instead_of_asking_for_attachment(self):
  reply='先看课程是否允许 AI，再核对学生的草稿和引用，聊聊他怎样写出这段论证。'
  with patch.object(companion,'generate',side_effect=['any',json.dumps({'answer':reply})]) as model:
   result=companion.answer('我是老师，怀疑学生的论文是AI写的，我怎么核实？','home')
  self.assertIn('没有论文及文档正文的作者检测功能',model.call_args.args[0][0]['content'])
  self.assertEqual(result['answer'],reply)
  self.assertEqual(result['material_options'],[])
  self.assertIn('K13',[source['id'] for source in result['sources']])
 def test_notification_answer_does_not_reuse_refund_details(self):
  reply='航司会短信通知，3-7个工作日内退款。'
  with patch.object(companion,'generate',side_effect=['none',json.dumps({'answer':reply})]),self.assertLogs(level='ERROR'):
   result=companion.answer('航班取消通常怎么通知乘客？','home')
  self.assertIn('短信',result['answer'])
  self.assertNotIn('退款',result['answer'])
 def test_routine_procedure_does_not_offer_material_for_wrong_plan(self):
  question='公司正常变更供应商收款账户时，审批流程是什么？'
  reply='先在内部系统核对供应商信息，再按既定权限复核账户变更申请。'
  with patch.object(companion,'generate',side_effect=['image',json.dumps({'answer':reply})]),patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer(question,'home')
  self.assertEqual(result['answer'],reply)
  self.assertEqual(result['material_options'],[])
 def test_accepting_optional_check_moves_to_attachment_question(self):
  history=[dict(question='航空客服要银行卡，退款正常吗？',answer='从原订单核实。'+companion.CHECK_OFFER)]
  with patch.object(companion,'generate') as model:
   result=companion.answer('可以','home',history)
  model.assert_not_called()
  self.assertEqual(result['mode'],'material_guidance')
 def test_decline_rejects_a_second_flight_verification_offer(self):
  question='不用检测，航班取消退款到哪办？'
  reply='从原购票订单办理。需要我再帮你核验航班状态或订单信息吗？'
  with patch.object(companion,'generate',side_effect=['offer',json.dumps({'answer':reply})]),self.assertLogs(level='ERROR'):
   result=companion.answer(question,'home')
  self.assertIn('原购票渠道',result['answer'])
  self.assertNotIn('需要我再帮你核验',result['answer'])
 def test_decline_keeps_context_and_answers_substantively(self):
  history=[dict(question='客户发了货损截图要求售后退款，流程是什么？',answer='可以先核对原订单。'+companion.CHECK_OFFER)]
  reply='先在原订单里核对售后工单，检查最初上传的凭证是否符合平台规则。'
  with patch.object(companion,'generate',side_effect=['chat',json.dumps({'answer':reply})]) as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('不用检测，先回答退款流程。','home',history)
  self.assertIn(history[0]['question'],model.call_args.args[0][-1]['content'])
  self.assertEqual(result['answer'],reply)
  self.assertEqual(result['material_options'],[])
  continued=[*history,dict(question='不用检测，先回答退款流程。',answer=reply)]
  with patch.object(companion,'generate',side_effect=['offer',json.dumps({'answer':reply})]),patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('如果原订单找不到凭证呢？','home',continued)
  self.assertEqual(result['answer'],reply)
 def test_answer_first_uses_previous_question_instead_of_old_upload_step(self):
  history=[dict(question='财务收到改收款账户的消息，正常审核步骤是什么？',answer='请先添加附件。')]
  reply='先暂停改账户，再用通讯录里原有的渠道联系业务方，复核原审批记录。'
  with patch.object(companion,'generate',side_effect=['outside',json.dumps({'answer':reply})]),patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('先回答问题','home',history)
  self.assertEqual(result['answer'],reply)
 def test_current_scam_help_takes_priority_over_old_photo(self):
  history=[dict(question='帮我看看这张照片',answer='请添加照片。')]
  reply='先停止与对方联系，保留聊天记录。如果已经转账，请马上联系银行尝试止付并报警。你已经付过钱了吗？'
  with patch.object(companion,'generate',return_value=json.dumps({'answer':reply})) as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('我现在遇到诈骗了，我该怎么办？','home',history)
  model.assert_called_once()
  self.assertEqual(result['answer'],reply)
  self.assertEqual(result['material_options'],[])
  self.assertEqual(result['sources'][0]['id'],'incident-safety')
 def test_model_classifies_reported_payment_and_attachment_reply_falls_back(self):
  question='我已经汇款了，他还催我交解冻费，我先做什么？'
  with patch.object(companion,'generate',side_effect=['incident','{"answer":"先上传图片给我看看。"}']) as model,patch('backend.rag.retrieve',return_value=[]),self.assertLogs(level='ERROR'):
   result=companion.answer(question,'home')
  self.assertEqual(model.call_count,2)
  self.assertEqual(result['mode'],'guide_fallback')
  self.assertIn('止付',result['answer'])
  self.assertNotIn('若已经',result['answer'])
  self.assertEqual(result['material_options'],[])
 def test_video_capability_describes_actual_features(self):
  with patch.object(companion,'generate') as model:
   result=companion.answer('视频会检查哪些内容？','home')
  model.assert_not_called()
  self.assertEqual(result['answer'],companion.VIDEO_CAPABILITY_SUMMARY)
 def test_real_generation_path_does_not_claim_training(self):
  with patch.object(companion,'generate',side_effect=['none','{"answer":"请先用已保存的号码联系本人，检测不能确认身份。"}']),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('能确认是本人吗','home')
  self.assertEqual(value['mode'],'local_qwen_rag');self.assertIn('未做平台专属微调',value['note'])
 def test_payment_requires_independent_check(self):
  with patch.object(companion,'generate',side_effect=['none','{"answer":"检测不能直接确认身份或保证资金安全。"}']),patch('backend.rag.retrieve',return_value=[]):
   value=companion.answer('检测正常就可以转钱吗','home')
  self.assertEqual(len(value['actions']),2);self.assertIn('暂停',value['actions'][0])
 def test_unverified_fraud_claim_uses_neutral_guidance(self):
  claim='这是典型的冒充亲友诈骗。请先暂停转账。'
  question='孩子用朋友手机发微信，说手机丢了，让我转点钱。'
  with patch.object(companion,'generate',side_effect=['none',json.dumps({'answer':claim})]),patch('backend.rag.retrieve',return_value=[]),self.assertLogs(level='ERROR'):
   result=companion.answer(question,'home')
  self.assertEqual(result['mode'],'guide_fallback')
  self.assertNotIn('诈骗',result['answer'])
  self.assertIn('保存的号码',result['answer'])
  self.assertEqual(result['actions'],[])
 def test_unrelated_question_stops_after_scope_selection(self):
  with patch.object(companion,'generate',return_value='outside') as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('帮我写个番茄炒蛋的菜谱。','home')
  model.assert_called_once()
  self.assertEqual(result['mode'],'scope_guidance')
  self.assertIn('防骗',result['answer'])
 def test_new_unrelated_question_does_not_inherit_flight_context(self):
  history=[dict(question='航班停飞后正常怎么通知？',answer='航司会通过官方 App 和短信通知。')]
  with patch.object(companion,'generate') as model:
   result=companion.answer('苹果是什么颜色？','home',history)
  model.assert_not_called()
  self.assertEqual(result['mode'],'scope_guidance')
  self.assertNotIn('红色',result['answer'])
 def test_workflow_reply_cannot_invent_an_approval_threshold(self):
  reply='金额≥3万元时必须加一位审批人。'
  with patch.object(companion,'generate',side_effect=['none',json.dumps({'answer':reply})]),patch('backend.rag.retrieve',return_value=[]),self.assertLogs(level='ERROR'):
   result=companion.answer('企业审批付款如何建立防冒充流程？','check')
  self.assertEqual(result['mode'],'guide_fallback')
  self.assertNotIn('3万元',result['answer'])
  self.assertIn('审批流程',result['answer'])
 def test_automatic_report_advice_uses_actual_findings_and_situation(self):
  report={'context':'我是客服，买家用图片要求付款。','summary':'未完成检测','modules':{'image':{'status':'unavailable'}}}
  reply='请到原订单核对最早提交的材料。'
  with patch.object(companion,'generate',return_value=json.dumps({'answer':reply})) as model,patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer(companion.POST_CHECK_QUESTION,'report',report=report)
  model.assert_called_once()
  input_data=json.loads(model.call_args.args[0][-1]['content'])
  self.assertEqual(input_data['user_description'],report['context'])
  self.assertIn('尚未得到有效结果',input_data['report']['findings'][0])
  self.assertIn('尚未得到有效结果',result['answer'])
  self.assertTrue(result['answer'].endswith(reply))
 def test_risk_reply_does_not_repeat_safety_actions(self):
  reply='有冒充风险，先别转钱。请用你原来保存的手机号联系本人核实。'
  with patch.object(companion,'generate',side_effect=['none',json.dumps({'answer':reply})]),patch('backend.rag.retrieve',return_value=[]):
   result=companion.answer('有人说是孩子，让我给他转钱。','home')
  self.assertEqual(result['answer'],reply)
  self.assertEqual(result['actions'],[])
 def test_route_bounds_and_no_cache(self):
  from fastapi.testclient import TestClient
  from backend.app import app
  client=TestClient(app)
  for body in [dict(question='x'*321),dict(question='hello',page='https://bad.example')]:self.assertEqual(client.post('/api/companion/ask',json=body).status_code,422)
  with patch.object(companion,'answer',return_value=dict(answer='测试回答',mode='guide_fallback')):
   response=client.post('/api/companion/ask',json=dict(question='如何使用'))
  self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store')
 def test_companion_request_accepts_five_turns(self):
  from backend.app import CompanionRequest
  from pydantic import ValidationError
  history=[dict(question=f'问题 {i}',answer=f'回答 {i}') for i in range(5)]
  self.assertEqual(len(CompanionRequest(question='那下一步呢？',history=history).history),5)
  with self.assertRaises(ValidationError):
   CompanionRequest(question='那下一步呢？',history=[*history,history[0]])
if __name__=='__main__':unittest.main()
