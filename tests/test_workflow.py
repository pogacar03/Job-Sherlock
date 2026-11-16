import json
from pathlib import Path
import tempfile
import unittest
from tests.fixtures import target


class WorkflowTests(unittest.TestCase):
    def test_run_produces_cards_and_report_without_evidence(self):
        from reverse_check.workflow import run_investigation
        def scan(path, **options):
            self.assertEqual(options['total_timeout'],42)
            out=path/'scans'/'fixture';out.mkdir(parents=True)
            (out/'run.json').write_text(json.dumps({'schema_version':2,'status':'completed','channels':[],'candidates':[],'leads':[]}))
            return out
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case'
            result=run_investigation(path,case_fields=target(),scan_options={'total_timeout':42},scan_fn=scan)
            self.assertEqual(result['exit_code'],0)
            self.assertTrue(result['cards_path'].exists());self.assertEqual(len(result['report_paths']),3)
            self.assertEqual(json.loads((path/'evidence.json').read_text()),[])

    def test_invalid_options_or_nonempty_case_do_not_scan(self):
        from reverse_check.workflow import run_investigation
        def scan(*args,**kwargs): self.fail('should not scan')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case'
            with self.assertRaises(ValueError):run_investigation(path,case_fields=target(),scan_options={'total_timeout':0},scan_fn=scan)
            self.assertFalse(path.exists())
            path.mkdir();(path/'existing').write_text('keep')
            with self.assertRaises(ValueError):run_investigation(path,case_fields=target(),scan_options={},scan_fn=scan)
            self.assertEqual((path/'existing').read_text(),'keep')

    def test_partial_and_interrupted_scans_still_render(self):
        from reverse_check.workflow import run_investigation
        for status,code in [('partial',3),('interrupted',130),('budget_exhausted',3)]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                def scan(path,**options):
                    out=path/'scans'/'fixture';out.mkdir(parents=True)
                    (out/'run.json').write_text(json.dumps({'schema_version':2,'status':status,'channels':[],'candidates':[],'leads':[]}))
                    return out
                result=run_investigation(Path(tmp)/'case',case_fields=target(),scan_options={},scan_fn=scan)
                self.assertEqual(result['exit_code'],code)
                self.assertTrue(result['cards_path'].exists())
