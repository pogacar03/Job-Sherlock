import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from reverse_check.casebook import create_case, read_evidence
from reverse_check.collection import collection_summary
from reverse_check.http_source import FetchedPage, FetchError
from reverse_check.report import write_report
from tests.fixtures import target


class ForumTests(unittest.TestCase):
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
            self.assertEqual([c['status'] for c in data['channels']],['not_configured','manual_required','manual_required'])
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
            return [{'field':'title','value':'工作体验'}, {'field':'content','value':'示例科技最近经常加班到十点，团队沟通经常有临时变更，周末也要安排上线值班。'}]
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['xiaohongshu'],executable='/bin/opencli',tool=tool)
            data=json.loads((run/'run.json').read_text())
            self.assertEqual(data['channels'][0]['status'],'ok')
            self.assertEqual(len(data['documents']),1)

    def test_external_redirect_cannot_be_labeled_as_v2ex_material(self):
        def fetch(url,**kw):return FetchedPage('https://external.example/a',200,'application/json',b'[]')
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case';create_case(case,**target())
            run=self.api().scan_forums(case,['v2ex'],fetch=fetch)
            self.assertEqual(json.loads((run/'run.json').read_text())['channels'][0]['status'],'unsupported_source')
