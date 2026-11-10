import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

from reverse_check.casebook import create_case, import_evidence, read_evidence
from reverse_check.collection import collect_sources, collection_summary
from reverse_check.http_source import FetchedPage, FetchError
from reverse_check.sources import load_sources
from tests.fixtures import target


def page(url,title='员工经历',text='示例科技搜索平台部的作者自述近期项目安排与团队沟通情况。这里有足够长的公开文本用于读取与审阅。',code=200):
    body=f'<html><head><title>{title}</title></head><body><p>{text}</p><script>unsafeInstruction()</script></body></html>'.encode()
    return FetchedPage(url,code,'text/html; charset=utf-8',body)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.case=Path(self.tmp.name)/'case';create_case(self.case,**target())

    def test_parallel_fetches_preserve_association_and_cannot_promote_drafts(self):
        barrier=threading.Barrier(2)
        def fetch(url,timeout,max_bytes):
            self.assertEqual(timeout,3);self.assertEqual(max_bytes,5000)
            barrier.wait(timeout=2)
            return page(url,title=url.rsplit('/',1)[-1])
        run=collect_sources(self.case,['https://example.com/first','https://other.example/second'],workers=2,timeout=3,max_bytes=5000,fetch=fetch)
        data=json.loads((run/'run.json').read_text())
        self.assertEqual([r['title'] for r in data['results']],['first','second'])
        self.assertTrue(all(r['status']=='retrieved' for r in data['results']))
        drafts=json.loads((run/'evidence-drafts.json').read_text())
        self.assertIsNone(drafts[0]['scope']['company'])
        self.assertIsNone(drafts[0]['observed_at'])
        self.assertNotIn('unsafeInstruction',drafts[0]['source_text'])
        self.assertEqual(read_evidence(self.case),[])
        with self.assertRaises(ValueError):import_evidence(self.case,drafts)
        for row in data['results']:
            raw=(run/row['snapshot']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['content_sha256'])
        self.assertEqual(collection_summary(self.case)['total_urls'],2)
        self.assertEqual(data['registry_sha256'],hashlib.sha256((run/'sources.json').read_bytes()).hexdigest())

    def test_http_and_soft_failures_are_not_evidence_of_absence(self):
        cases=[(200,'登录 - Example','login_required'),(200,'Just a moment...','blocked'),
               (200,'页面不存在','not_found'),(403,'Forbidden','blocked'),(429,'Too many','rate_limited'),
               (404,'Not found','not_found'),(503,'Down','http_error')]
        for code,title,status in cases:
            with self.subTest(status=status,code=code):
                run=collect_sources(self.case,['https://example.com/a'],fetch=lambda u,timeout,max_bytes:page(u,title=title,code=code))
                row=json.loads((run/'run.json').read_text())['results'][0]
                self.assertEqual(row['status'],status)
                self.assertEqual(json.loads((run/'evidence-drafts.json').read_text()),[])

    def test_timeout_isolated_from_success_and_duplicate_urls_are_one_request(self):
        called=[]
        def fetch(url,timeout,max_bytes):
            called.append(url)
            if url.endswith('/slow'):raise FetchError('timeout','test timeout')
            return page(url)
        run=collect_sources(self.case,['https://example.com/ok?utm_source=a#one','https://example.com/ok?utm_source=b','https://example.com/slow'],fetch=fetch)
        data=json.loads((run/'run.json').read_text())
        self.assertEqual(len(called),2)
        self.assertEqual(data['input_count'],3)
        self.assertEqual([r['status'] for r in data['results']],['retrieved','timeout'])
        self.assertEqual(len(json.loads((run/'evidence-drafts.json').read_text())),1)

    def test_manual_sources_are_recorded_without_fetching_and_runs_never_overwrite(self):
        def fetch(*args,**kwargs):self.fail('manual source must not perform network request')
        a=collect_sources(self.case,['https://maimai.cn/a'],fetch=fetch)
        b=collect_sources(self.case,['https://maimai.cn/a'],fetch=fetch)
        self.assertNotEqual(a,b)
        self.assertEqual(collection_summary(self.case)['statuses'],{'manual_required':2})
        self.assertEqual(collection_summary(self.case)['runs'],2)
        self.assertEqual(collection_summary(self.case)['fetch_attempts'],0)

    def test_invalid_options_fail_before_network_or_writing(self):
        for options in [{'workers':0},{'timeout':float('nan')},{'max_bytes':0}]:
            with self.subTest(options=options),self.assertRaises(ValueError):
                collect_sources(self.case,['https://example.com'],**options)
        self.assertFalse((self.case/'collections').exists())

    def test_empty_and_non_text_pages_are_not_readable_sources(self):
        for result,status in [(page('https://example.com',text=''), 'empty'),
                              (FetchedPage('https://example.com',200,'image/png',b'PNG'),'unsupported_content')]:
            with self.subTest(status=status):
                run=collect_sources(self.case,['https://example.com'],fetch=lambda *a,**kw:result)
                self.assertEqual(json.loads((run/'run.json').read_text())['results'][0]['status'],status)

    def test_known_access_denial_is_preserved_when_body_format_is_unreadable(self):
        def fetch(*args,**kwargs):raise FetchError('unsupported_content','压缩正文未读取',http_status=403)
        run=collect_sources(self.case,['https://example.com/a'],fetch=fetch)
        row=json.loads((run/'run.json').read_text())['results'][0]
        self.assertEqual(row['status'],'blocked')
        self.assertEqual(row['http_status'],403)

    def test_redirect_uses_final_source_rules_and_records_both_sources(self):
        config=Path(self.tmp.name)/'sources.json'
        config.write_text(json.dumps({'schema_version':1,'sources':[
            {'id':'start','name':'Start','domains':['start.example'],'mode':'public','query':None,'login_titles':[]},
            {'id':'destination','name':'Destination','domains':['target.example'],'mode':'public','query':None,'login_titles':['Members only']},
        ]}))
        run=collect_sources(self.case,['https://start.example/a'],registry=load_sources(config),fetch=lambda *a,**kw:page('https://target.example/a',title='Members only'))
        row=json.loads((run/'run.json').read_text())['results'][0]
        self.assertEqual(row['status'],'login_required')
        self.assertEqual(row['source_id'],'destination')
        self.assertEqual(row['requested_source_id'],'start')
        self.assertEqual(json.loads((run/'evidence-drafts.json').read_text()),[])

    def test_business_query_order_and_encoding_are_preserved_during_deduplication(self):
        called=[]
        def fetch(url,**kwargs):called.append(url);return page(url)
        urls=['https://example.com/a?part=2&part=1&token=a%2Fb+z&utm_source=test',
              'https://example.com/a?part=1&part=2&token=a%2fb%20z']
        run=collect_sources(self.case,urls,fetch=fetch)
        self.assertCountEqual(called,urls)
        self.assertEqual(json.loads((run/'run.json').read_text())['unique_count'],2)
