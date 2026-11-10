import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.fixtures import record


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.case = self.path / 'case'

    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable,'-m','reverse_check',*map(str,args)], cwd=ROOT, capture_output=True, text=True, env=env)

    def init(self):
        result = self.run_cli('init',self.case,'--company','示例科技','--department','搜索平台部','--city','上海','--role','后端研发','--as-of','2026-11-10')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_complete_workflow_outputs_cited_report_and_search_plan(self):
        self.init()
        self.assertEqual(self.run_cli('plan',self.case).returncode,0)
        self.assertIn('过去四周',(self.case/'queries.md').read_text())
        source = self.path/'input.json'
        source.write_text(json.dumps([record()],ensure_ascii=False))
        result = self.run_cli('import',self.case,'--file',source)
        self.assertEqual(result.returncode,0,result.stderr)
        out = self.path/'report'
        result = self.run_cli('report',self.case,'--out',out)
        self.assertEqual(result.returncode,0,result.stderr)
        data = json.loads((out/'report.json').read_text())
        self.assertEqual(data['summary']['eligible_count'],1)
        self.assertIn('https://example.com/post/1',(out/'report.md').read_text())
        html = (out/'report.html').read_text()
        self.assertIn('id="evidence-e1"',html)
        self.assertIn('href="#evidence-e1"',html)

    def test_empty_case_remains_unknown_and_report_does_not_overwrite(self):
        self.init()
        out = self.path/'report'
        self.assertEqual(self.run_cli('report',self.case,'--out',out).returncode,0)
        before = (out/'report.html').read_bytes()
        result = self.run_cli('report',self.case,'--out',out)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((out/'report.html').read_bytes(),before)
        data = json.loads((out/'report.json').read_text())
        self.assertEqual(data['summary']['unknown_dimensions'],6)
        self.assertEqual(self.run_cli('report',self.case,'--out',out,'--force').returncode,0)

    def test_invalid_json_returns_actionable_error_without_traceback(self):
        self.init()
        source = self.path/'bad.json'
        source.write_text('{broken')
        result = self.run_cli('import',self.case,'--file',source)
        self.assertEqual(result.returncode,2)
        self.assertNotIn('Traceback',result.stderr)
        self.assertIn('错误',result.stderr)

    def test_html_input_stays_text(self):
        self.init()
        source = self.path/'input.json'
        source.write_text(json.dumps([record(observation='<img src=x onerror=alert(1)>',title='<script>alert(1)</script>')]))
        self.assertEqual(self.run_cli('import',self.case,'--file',source).returncode,0)
        out = self.path/'report'
        self.assertEqual(self.run_cli('report',self.case,'--out',out).returncode,0)
        html = (out/'report.html').read_text()
        self.assertNotIn('<img src=x',html)
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;img',html)

    def test_demo_is_labelled_fictional_and_contains_conflicts(self):
        out = self.path/'demo'
        result = self.run_cli('demo','--out',out)
        self.assertEqual(result.returncode,0,result.stderr)
        data = json.loads((out/'report.json').read_text())
        self.assertTrue(data['target']['demo'])
        self.assertEqual(data['dimensions']['workload']['status'],'conflicting')
        self.assertIn('全部材料为虚构',(out/'report.html').read_text())

    def test_cli_runs_without_external_timezone_database(self):
        env = {**os.environ, 'PYTHONTZPATH':''}
        commands = [
            ('init',self.path/'fixed','--company','示例公司','--as-of','2026-11-10'),
            ('init',self.path/'default','--company','示例公司'),
            ('demo','--out',self.path/'without-tzdata'),
        ]
        for args in commands:
            with self.subTest(command=args[0]):
                result = self.run_cli(*args,env=env)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_explicit_demo_case_stays_labelled_in_normal_workflow(self):
        result = self.run_cli('init',self.case,'--company','示例科技','--department','搜索平台部','--demo','--as-of','2026-11-10')
        self.assertEqual(result.returncode,0,result.stderr)
        source = ROOT/'reverse_check/data/demo-evidence.json'
        self.assertEqual(self.run_cli('import',self.case,'--file',source).returncode,0)
        out = self.path/'manual-demo'
        self.assertEqual(self.run_cli('report',self.case,'--out',out).returncode,0)
        self.assertTrue(json.loads((out/'report.json').read_text())['target']['demo'])
        self.assertIn('全部材料为虚构',(out/'report.html').read_text())

    def test_source_registry_and_source_specific_plan_are_available_from_cli(self):
        self.init()
        result=self.run_cli('sources')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('nowcoder',{r['id'] for r in json.loads(result.stdout)['sources']})
        result=self.run_cli('plan',self.case,'--source','nowcoder')
        self.assertEqual(result.returncode,0,result.stderr)
        plan=(self.case/'queries.md').read_text()
        self.assertIn('site:nowcoder.com',plan)
        self.assertNotIn('site:maimai.cn',plan)

    def test_collected_manual_sources_are_reported_without_becoming_evidence(self):
        self.init()
        urls=self.path/'urls.json';urls.write_text(json.dumps(['https://maimai.cn/test']))
        result=self.run_cli('collect',self.case,'--urls',urls,'--workers','2','--timeout','2')
        self.assertEqual(result.returncode,0,result.stderr)
        out=self.path/'with-collection'
        result=self.run_cli('report',self.case,'--out',out)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads((out/'report.json').read_text())
        self.assertEqual(data['collection']['statuses'],{'manual_required':1})
        self.assertEqual(data['collection']['fetch_attempts'],0)
        self.assertEqual(data['summary']['eligible_count'],0)
        self.assertEqual(data['summary']['unknown_dimensions'],6)
        self.assertIn('采集记录',(out/'report.html').read_text())
        self.assertIn('需要宿主或用户读取',(out/'report.md').read_text())

    def test_bad_collection_input_fails_without_request_or_traceback(self):
        self.init()
        urls=self.path/'urls.json';urls.write_text(json.dumps(['https://user:secret@example.com']))
        result=self.run_cli('collect',self.case,'--urls',urls)
        self.assertEqual(result.returncode,2)
        self.assertNotIn('Traceback',result.stderr)
        self.assertFalse((self.case/'collections').exists())


if __name__ == '__main__':
    unittest.main()
