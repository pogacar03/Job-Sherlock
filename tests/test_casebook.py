import json
from pathlib import Path
import tempfile
import unittest

from reverse_check.casebook import create_case, import_evidence, read_case, read_evidence
from tests.fixtures import record, target


class CasebookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '公司案例'
        create_case(self.path, **target())

    def test_creation_preserves_existing_case(self):
        with self.assertRaises(ValueError):
            create_case(self.path, company='其他公司')
        self.assertEqual(read_case(self.path)['company'], '示例科技')

    def test_import_is_idempotent_and_keeps_source_text(self):
        self.assertEqual(import_evidence(self.path, [record()]), 1)
        self.assertEqual(import_evidence(self.path, [record()]), 0)
        self.assertEqual(read_evidence(self.path)[0]['source_text'], '最近一个月基本每晚十点下班，周末通常休息。')

    def test_batch_with_untraceable_quote_does_not_write_partial_data(self):
        invalid = record(id='e2', quote='领导强制每天加班')
        with self.assertRaises(ValueError):
            import_evidence(self.path, [record(), invalid])
        self.assertEqual(read_evidence(self.path), [])

    def test_rejects_unsafe_sources_invalid_dates_and_unknown_fields(self):
        for changes in [
            {'source_ref': 'javascript:alert(1)'}, {'retrieved_at': '2026-99-10'},
            {'observed_at': '2026-12-01'}, {'dimension': 'worklaod'},
            {'surprise': True}, {'scope': {'company': '示例科技', 'departmant': '搜索平台部'}},
            {'source_ref': 'https://user:secret@example.com/a'},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                import_evidence(self.path, [record(**changes)])

    def test_rejects_changed_record_with_same_id(self):
        import_evidence(self.path, [record()])
        with self.assertRaises(ValueError):
            import_evidence(self.path, [record(observation='另一种描述')])
        self.assertEqual(read_evidence(self.path)[0]['observation'], '作者自述最近一个月常在晚十点下班。')

    def test_user_provided_interviews_can_be_traced_without_a_public_url(self):
        r = record(source_ref='user-provided:匿名访谈笔记', source_type='user_interview')
        import_evidence(self.path, [r])
        self.assertEqual(read_evidence(self.path)[0]['source_ref'], 'user-provided:匿名访谈笔记')

    def test_rejects_empty_target_and_invalid_window(self):
        for fields in [{'company': '  '}, {'company': '公司', 'lookback_days': 0}, {'company':'公司','lookback_days':True}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                create_case(Path(self.tmp.name) / 'invalid', **fields)

    def test_read_revalidates_manually_edited_data(self):
        import_evidence(self.path, [record()])
        path = self.path / 'evidence.json'
        rows = json.loads(path.read_text())
        rows[0]['quote'] = '原文没有这句话'
        path.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            read_evidence(self.path)


if __name__ == '__main__':
    unittest.main()
