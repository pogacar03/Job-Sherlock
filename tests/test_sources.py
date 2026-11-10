import json
from pathlib import Path
import tempfile
import unittest

from reverse_check.sources import load_sources, source_for_url, source_queries
from reverse_check.casebook import validate_case
from tests.fixtures import target


class SourceTests(unittest.TestCase):
    def test_registry_routes_subdomains_without_matching_impostor_domains(self):
        registry = load_sources()
        self.assertEqual(source_for_url(registry,'https://www.nowcoder.com/discuss/1')['id'],'nowcoder')
        self.assertEqual(source_for_url(registry,'https://evilnowcoder.com/')['id'],'public-web')
        self.assertEqual(source_for_url(registry,'https://maimai.cn/a')['mode'],'manual')
        self.assertEqual(source_for_url(registry,'https://maimai.cn./a')['mode'],'manual')
        self.assertEqual(source_for_url(registry,'https://ｍａｉｍａｉ.cn/a')['mode'],'manual')

    def test_source_queries_keep_target_and_source_separate(self):
        queries = source_queries(validate_case(target()),load_sources(),['nowcoder'])
        self.assertEqual(len(queries),1)
        self.assertIn('site:nowcoder.com',queries[0]['query'])
        self.assertIn('"示例科技"',queries[0]['query'])
        self.assertIn('"搜索平台部"',queries[0]['query'])
        with self.assertRaises(ValueError):
            source_queries(validate_case(target()),load_sources(),['not-a-source'])

    def test_custom_registry_rejects_unknown_templates_modes_and_duplicate_ids(self):
        base={'id':'test','name':'Test','domains':['example.com'],'mode':'public','query':'site:example.com {company}'}
        invalid=[{**base,'query':'{company.__class__}'},{**base,'query':'{company!r}'},
                 {**base,'mode':'execute'},{**base,'domains':['example.com/path']},
                 {**base,'domains':['']},{**base,'surprise':True}]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sources.json'
            for row in invalid:
                path.write_text(json.dumps({'schema_version':1,'sources':[row]}))
                with self.subTest(row=row),self.assertRaises(ValueError):load_sources(path)
            path.write_text(json.dumps({'schema_version':1,'sources':[base,base]}))
            with self.assertRaises(ValueError):load_sources(path)

    def test_conflicting_domain_policies_cannot_depend_on_registry_order(self):
        public={'id':'a','name':'Public','domains':['example.com'],'mode':'public','query':None}
        manual={**public,'id':'b','name':'Manual','mode':'manual'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sources.json'
            for rows in ([public,manual],[manual,public]):
                path.write_text(json.dumps({'schema_version':1,'sources':rows}))
                with self.assertRaises(ValueError):load_sources(path)
