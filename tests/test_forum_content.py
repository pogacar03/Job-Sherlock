import json
from pathlib import Path
import tempfile
import unittest

from reverse_check.casebook import create_case, read_evidence
from reverse_check.http_source import FetchError
from tests.fixtures import target


class ForumContentTests(unittest.TestCase):
    def test_identity_ignores_signature_and_keeps_platform(self):
        from reverse_check.forum_content import thread_key
        self.assertEqual(thread_key('xiaohongshu', 'https://www.xiaohongshu.com/explore/abc?xsec_token=a'), thread_key('xiaohongshu', 'https://www.xiaohongshu.com/search_result/abc?xsec_token=b'))
        self.assertNotEqual(thread_key('maimai', 'https://maimai.cn/community/gossip-detail/123'), thread_key('nowcoder', 'https://www.nowcoder.com/discuss/123'))
        with self.assertRaises(FetchError): thread_key('nowcoder', 'https://evil.example/discuss/123')

    def test_segments_preserve_comments_and_stable_identity(self):
        from reverse_check.forum_content import normalize_thread
        args = ('nowcoder', 'https://www.nowcoder.com/discuss/42', '标题', '这个团队加班吗？', [{'text': '每周两晚加班', 'author': 'a'}, {'text': '每周两晚加班', 'author': 'b'}])
        kw = {'comment_status': 'visible_only', 'published_at_raw': None, 'retrieved_at': '2026-11-16'}
        record = normalize_thread(*args, **kw)
        self.assertEqual([s['kind'] for s in record['segments']], ['body', 'comment', 'comment'])
        self.assertIsNone(record['segments'][0]['author'])
        self.assertEqual(record['segments'][2]['author'], 'b')
        self.assertEqual(record['candidate_id'], normalize_thread(*args, **kw)['candidate_id'])

    def test_direct_read_keeps_signed_url_and_does_not_search(self):
        from reverse_check.forums import scan_forums
        url = 'https://www.xiaohongshu.com/explore/abc?xsec_token=fixture'
        calls = []
        def tool(args, timeout):
            calls.append(args)
            if args[2] == 'note': return [{'field': 'content', 'value': '内容原文'}]
            if args[2] == 'comments': raise FetchError('login_required', '登录')
            self.fail('unexpected command')
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)/'case'; create_case(case, **target())
            run = scan_forums(case, ['xiaohongshu'], executable='/bin/opencli', tool=tool, source_urls={'xiaohongshu': [url]})
            data = json.loads((run/'run.json').read_text())
            self.assertEqual(data['schema_version'], 2)
            self.assertEqual(data['candidates'][0]['segments'][0]['text'], '内容原文')
            self.assertEqual(data['candidates'][0]['comment_status'], 'login_required')
            self.assertEqual(read_evidence(case), [])
            self.assertTrue(all(url in cmd for cmd in calls))

    def test_invalid_direct_link_fails_before_creating_scan(self):
        from reverse_check.forums import scan_forums
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)/'case'; create_case(case, **target())
            for url in ('https://evil.example/explore/abc?xsec_token=x', 'https://www.xiaohongshu.com/explore/abc'):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    scan_forums(case, ['xiaohongshu'], source_urls={'xiaohongshu': [url]})
            self.assertFalse((case/'scans').exists())
