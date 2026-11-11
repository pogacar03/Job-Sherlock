import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import shutil
import subprocess
import unittest

from reverse_check.casebook import create_case, read_evidence
from reverse_check.collection import collection_summary
from reverse_check.http_source import FetchedPage, FetchError
from reverse_check.report import write_report
from tests.fixtures import target


class ForumTests(unittest.TestCase):
    def test_opencli_structured_stdout_auth_error_is_not_generic_failure(self):
        script='import json; print(json.dumps({"ok":False,"error":{"code":"AUTH_REQUIRED","message":"Login needed"}})); raise SystemExit(77)'
        with self.assertRaises(FetchError) as error:
            self.api()._tool([sys.executable,'-c',script],3)
        self.assertEqual(error.exception.status,'login_required')

    def test_opencli_empty_result_error_means_successful_empty_query(self):
        script='import json; print(json.dumps({"ok":False,"error":{"code":"EMPTY_RESULT"}})); raise SystemExit(1)'
        self.assertEqual(self.api()._tool([sys.executable,'-c',script],3),[])

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('reverse_check.forums'), '缺少论坛实际采集模块')
        from reverse_check import forums
        return forums

    def test_native_scan_reads_replies_filters_salary_and_keeps_drafts_unreviewed(self):
        def fetch(url, **kwargs):
            if 'latest' in url:
                data=[{'id':42,'title':'示例科技工作体验','content':'想了解搜索平台部的情况','created':1790000000},
                      {'id':43,'title':'示例科技薪资','content':'工资多少','created':1790000000}]
            else:
                data=[{'id':1,'content':'最近一直加班，周末也需要上线处理项目。团队沟通依赖临时会议。','created':1790000000}]
            return FetchedPage(url,200,'application/json',json.dumps(data).encode())
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['v2ex'],fetch=fetch)
            result=json.loads((run/'run.json').read_text())
            self.assertEqual(result['channels'][0]['status'],'ok')
            self.assertEqual(len(result['documents']),1)
            self.assertIn('周末',result['documents'][0]['text'])
            self.assertEqual(read_evidence(case),[])
            self.assertEqual(collection_summary(case)['statuses'],{'retrieved':1})

    def test_missing_backend_and_manual_platforms_are_not_zero_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['nowcoder','maimai','offershow'],executable=None)
            data=json.loads((run/'run.json').read_text())
            self.assertEqual([c['status'] for c in data['channels']],['not_configured','not_configured','manual_required'])
            self.assertEqual(data['documents'],[])
            out=case/'report';write_report(case,out)
            report=json.loads((out/'report.json').read_text())
            self.assertEqual(report['scans'][0]['channels'][0]['status'],'not_configured')
            self.assertIn('not\\_configured',(out/'report.md').read_text())
            self.assertIn('not_configured',(out/'report.html').read_text())
            self.assertEqual(set(report['dimensions']),{'workload','atmosphere'})
            self.assertNotIn('薪酬兑现',(out/'report.md').read_text())

    def test_fetch_failure_is_distinct_from_successful_empty_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            def failed(*a,**kw):raise FetchError('blocked','403',403)
            run=self.api().scan_forums(case,['v2ex'],fetch=failed)
            self.assertEqual(json.loads((run/'run.json').read_text())['channels'][0]['status'],'blocked')
            run=self.api().scan_forums(case,['v2ex'],fetch=lambda url,**kw:FetchedPage(url,200,'application/json',b'[]'))
            self.assertEqual(json.loads((run/'run.json').read_text())['channels'][0]['status'],'no_results')

    def test_opencli_reads_details_and_rejects_outside_platform_urls(self):
        calls=[]
        def tool(args,timeout):
            calls.append(args)
            if args[2]=='search':return [{'url':'https://www.nowcoder.com/discuss/42','title':'示例科技'}, {'url':'https://evil.example/a','title':'示例科技加班'}]
            return [{'content':'示例科技搜索平台部最近每天加班到晚上十点，周末一般休息。作者说明团队沟通比较直接。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['nowcoder'],executable='/bin/opencli',tool=tool,queries=['示例科技 加班'])
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(len(data['documents']),1)
            self.assertTrue(any(c[2]=='detail' for c in calls))
            self.assertFalse(any('evil.example' in ' '.join(c) for c in calls))

    def test_unknown_channel_and_bad_budget_do_not_create_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            for kw in [{'channels':['bogus']},{'channels':['v2ex'],'limit':0}]:
                with self.assertRaises(ValueError):self.api().scan_forums(case,**kw)
            self.assertFalse((case/'scans').exists())

    def test_xiaohongshu_field_value_body_is_read_instead_of_false_zero_hits(self):
        def tool(args,timeout):
            if args[2]=='search':return [{'url':'https://www.xiaohongshu.com/explore/abc','title':'示例科技'}]
            if args[2]=='comments':return []
            return [{'field':'title','value':'工作体验'}, {'field':'content','value':'示例科技最近经常加班到十点，团队沟通经常有临时变更，周末也要安排上线值班。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['xiaohongshu'],executable='/bin/opencli',tool=tool)
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(data['channels'][0]['status'],'ok')
            self.assertEqual(len(data['documents']),1)

    def test_default_scan_only_checks_three_core_forums(self):
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,executable=None)
            self.assertEqual([c['id'] for c in json.loads((run/'run.json').read_text())['channels']],['xiaohongshu','nowcoder','maimai'])

    def test_reply_can_supply_workload_even_if_question_has_no_workload_words(self):
        def tool(args,timeout):
            if args[1]=='browser':
                if args[2]=='eval':return [{'kind':'page','url':'https://www.nowcoder.com/discuss/42','ready':True}, {'id':'c1','text':'每天加班到十点，周末通常双休。','author':'anonymous','parent_id':None}]
                return [{'url':'https://www.nowcoder.com/discuss/42'}]
            if args[2]=='search':return [{'url':'https://www.nowcoder.com/discuss/42','title':'示例科技搜索平台部怎么样'}]
            return [{'content':'有人了解搜索平台部吗？想问一下实际情况。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['nowcoder'],executable='/bin/opencli',tool=tool,queries=['示例科技 搜索平台部'])
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(len(data['documents']),1)
            self.assertIn('每天加班',data['documents'][0]['text'])
            self.assertEqual(data['documents'][0]['comments'][0]['id'],'c1')
            self.assertEqual(read_evidence(case),[])

    def test_department_question_is_saved_as_lead_without_claiming_work_experience(self):
        def tool(args,timeout):
            if args[1]=='browser':
                if args[2]=='eval':return [{'kind':'page','url':'https://www.nowcoder.com/discuss/42','ready':True}]
                return [{'url':'https://www.nowcoder.com/discuss/42'}]
            if args[2]=='search':return [{'url':'https://www.nowcoder.com/discuss/42','title':'示例科技搜索平台部怎么样'}]
            return [{'content':'有人了解搜索平台部吗？想问一下实际情况。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['nowcoder'],executable='/bin/opencli',tool=tool,queries=['示例科技 搜索平台部'])
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(data['documents'],[])
            self.assertEqual(len(data['leads']),1)
            self.assertEqual(data['channels'][0]['status'],'leads_only')

    def test_maimai_native_feed_search_reports_login_redirect_without_using_talent_search(self):
        calls=[]
        def tool(args,timeout):
            calls.append(args)
            if args[2]=='eval':return [{'kind':'page','url':'https://maimai.cn/platform/login?to=search','empty':False}]
            return [{'url':'https://maimai.cn/platform/login'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['maimai'],executable='/bin/opencli',tool=tool)
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(data['channels'][0]['status'],'login_required')
            self.assertEqual(data['documents'],[])
            self.assertFalse(any('search-talents' in c for c in calls))

    def test_xhs_timeout_falls_back_to_real_search_page_and_then_reads_comments(self):
        def tool(args,timeout):
            if args[1]=='browser':
                if args[2]=='eval':return [{'kind':'page','url':'https://www.xiaohongshu.com/search_result?keyword=示例科技','status':'ready'}, {'title':'示例科技部门怎么样','url':'https://www.xiaohongshu.com/explore/abc?xsec_token=fixture'}]
                return [{'url':'https://www.xiaohongshu.com/search_result?keyword=示例科技'}]
            if args[2]=='search':raise FetchError('timeout','上游站内跳转超时')
            if args[2]=='comments':return [{'text':'每周两次晚上开会，团队氛围比较直接。','is_reply':True,'reply_to':'user-a'}]
            return [{'field':'content','value':'示例科技部门有人了解吗？想了解近期的实际情况。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['xiaohongshu'],queries=['示例科技'],executable='/bin/opencli',tool=tool)
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(data['channels'][0]['status'],'ok')
            self.assertIn('晚上开会',data['documents'][0]['text'])
            self.assertTrue(data['documents'][0]['comments'][0]['is_reply'])

    def test_xhs_chooses_signed_note_link_over_earlier_unsigned_link_or_author(self):
        from reverse_check.browser_forums import signed_note_url
        self.assertEqual(signed_note_url({'urls':['https://www.xiaohongshu.com/explore/abc','https://www.xiaohongshu.com/user/profile/abc?xsec_token=author','https://www.xiaohongshu.com/search_result/abc?xsec_token=note']}),'https://www.xiaohongshu.com/search_result/abc?xsec_token=note')
        self.assertIsNone(signed_note_url({'urls':['https://evil.example/explore/abc?xsec_token=x','https://www.xiaohongshu.com/explore/abc']}))

    def test_maimai_waits_for_card_navigation_before_reading_url_and_closes_only_created_tab(self):
        from reverse_check.browser_forums import maimai_search
        url='https://maimai.cn/web/search_center?query=example&type=gossip'
        post='https://maimai.cn/community/gossip-detail/123?egid=fixture'
        calls=0;removed=[]
        def tool(args,timeout):
            nonlocal calls
            if args[2]=='eval':return [{'kind':'page','url':url,'empty':False,'cards':[{'index':0,'title':'工作体验'}]}]
            if 'tabs.query' in args:
                calls+=1
                parent={'id':10,'url':url,'lastAccessed':1}
                return [parent] if calls==1 else [parent,{'id':11,'url':'' if calls==2 else post,'openerTabId':10}]
            if 'tabs.remove' in args:removed.extend(json.loads(args[-1]))
            return []
        rows=maimai_search('/bin/opencli','example',1,3,tool)
        self.assertEqual(rows[0]['url'],post)
        self.assertEqual(removed,[11])

    def test_maimai_refocuses_search_for_each_card_and_releases_session_before_cleanup(self):
        from reverse_check.browser_forums import maimai_search
        url='https://maimai.cn/web/search_center?query=example&type=gossip'
        tabs=[{'id':10,'url':url,'lastAccessed':1}];visible=True;released=False;removed=[]
        def tool(args,timeout):
            nonlocal visible,released
            if args[2]=='open':return [{'page':'search-page'}]
            if args[2]=='eval':return [{'kind':'page','url':url,'cards':[{'index':0},{'index':1}]}]
            if args[2]=='tab':
                self.assertEqual(args[4],'search-page');visible=True
            if args[2]=='click':
                self.assertTrue(visible,'新标签页打开后必须重新选择搜索页')
                visible=False;tid=10+len(tabs)
                tabs.append({'id':tid,'url':f'https://maimai.cn/community/gossip-detail/{tid}','openerTabId':10})
            if 'tabs.query' in args:return list(tabs)
            if args[2]=='close':released=True
            if 'tabs.remove' in args:
                self.assertTrue(released);removed.extend(json.loads(args[-1]))
            return []
        self.assertEqual(len(maimai_search('/bin/opencli','example',2,3,tool)),2)
        self.assertEqual(removed,[11,12])

    @unittest.skipUnless(shutil.which('node'),'DOM readiness check needs optional Node runtime')
    def test_nowcoder_waits_past_static_comment_heading_for_delayed_comments(self):
        from reverse_check.browser_forums import nowcoder_comments
        fixture=r'''let ticks=0;global.location={href:'https://www.nowcoder.com/discuss/42'};
        const e={parentElement:{closest:()=>null},getAttribute:()=> 'reply-1',querySelector:s=>s.includes('comment-rich-text')?{innerText:'每晚加班到十点'}:null};
        global.document={body:{innerText:'全部评论'},querySelector:()=>++ticks>=3?e:null,querySelectorAll:()=>ticks>=3?[e]:[]};'''
        def tool(args,timeout):
            if args[2]!='eval':return []
            code=fixture+';Promise.resolve('+args[3]+').then(r=>process.stdout.write(JSON.stringify(r)));'
            result=subprocess.run(['node','-e',code],capture_output=True,text=True,check=True,timeout=3)
            return json.loads(result.stdout)
        comments=nowcoder_comments('/bin/opencli','https://www.nowcoder.com/discuss/42',3,tool)
        self.assertEqual([c['text'] for c in comments],['每晚加班到十点'])

    def test_external_redirect_cannot_be_labeled_as_v2ex_material(self):
        def fetch(url,**kw):return FetchedPage('https://external.example/a',200,'application/json',b'[]')
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['v2ex'],fetch=fetch)
            self.assertEqual(json.loads((run/'run.json').read_text())['channels'][0]['status'],'unsupported_source')
