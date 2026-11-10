import unittest

from reverse_check.analysis import analyze, build_plan
from reverse_check.casebook import validate_case, validate_evidence
from tests.fixtures import record, target


class AnalysisTests(unittest.TestCase):
    def assess(self, *rows, **changes):
        case = validate_case({**target(), **changes})
        return analyze(case, [validate_evidence(row) for row in rows])

    def test_empty_case_reports_unknown_in_all_six_dimensions(self):
        report = self.assess()
        self.assertEqual(len(report['dimensions']), 6)
        self.assertTrue(all(d['status'] == 'unknown' for d in report['dimensions'].values()))
        self.assertEqual(report['summary']['eligible_count'], 0)

    def test_wrong_department_city_and_role_are_only_background(self):
        for key, value in [('department', '销售部'), ('city', '北京'), ('role', '销售'), ('company','同名但不同公司')]:
            r = record()
            r['scope'][key] = value
            with self.subTest(key=key):
                report = self.assess(r)
                self.assertEqual(report['dimensions']['workload']['status'], 'unknown')
                self.assertEqual(len(report['background']), 1)

    def test_company_aliases_are_explicit_and_do_not_guess_subsidiaries(self):
        r = record()
        r['scope']['company'] = 'Example Tech'
        self.assertEqual(self.assess(r)['summary']['eligible_count'], 0)
        self.assertEqual(self.assess(r, company_aliases=['Example Tech'])['summary']['eligible_count'], 1)

    def test_old_unknown_future_dates_and_unread_sources_are_background(self):
        for changes in [
            {'observed_at':'2022-06-01'}, {'observed_at':None}, {'access':'snippet'},
            {'source_type':'official'}, {'source_type':'secondary'},
            {'observed_at':'2026-11-11', 'published_at':'2026-11-12','retrieved_at':'2026-11-13'},
            {'observed_at':'2026-10-15','published_at':'2026-11-12','retrieved_at':'2026-11-13'},
        ]:
            with self.subTest(changes=changes):
                report = self.assess(record(**changes))
                self.assertEqual(report['summary']['eligible_count'], 0)

    def test_missing_target_department_cannot_produce_department_claim(self):
        self.assertEqual(self.assess(record(), department=None)['summary']['eligible_count'], 0)

    def test_transitive_reposts_do_not_create_independent_sources(self):
        a = record()
        b = record(id='b', source_ref='https://other.example/repost', origin_id='other-label')
        c = record(id='c', source_ref='https://other.example/other', origin_id='other-label', source_text='周末偶尔要参加线上值班。', quote='周末偶尔要参加线上值班。')
        report = self.assess(a,b,c)
        self.assertEqual(report['dimensions']['workload']['source_clusters'], 1)
        self.assertEqual(report['summary']['eligible_count'], 3)

    def test_tracking_urls_of_same_post_are_one_source_even_with_different_quotes(self):
        a = record(source_ref='https://example.com/post/1?utm_source=aa#part1', origin_id=None)
        b = record(id='b', source_ref='https://example.com/post/1?utm_source=bb', origin_id=None, quote='周末通常休息')
        self.assertEqual(self.assess(a,b)['dimensions']['workload']['source_clusters'], 1)

    def test_conflicting_independent_observations_stay_visible(self):
        b = record(id='b', origin_id='account-b', source_ref='https://example.com/post/2', direction='positive', source_text='我所在组最近一个月都能六点下班。', quote='最近一个月都能六点下班', observation='另一作者自述近期六点下班。')
        dim = self.assess(record(),b)['dimensions']['workload']
        self.assertEqual(dim['status'], 'conflicting')
        self.assertEqual(dim['source_clusters'], 2)
        self.assertEqual(dim['evidence_ids'], ['e1','b'])

    def test_plan_contains_targeted_search_and_actionable_interview_question(self):
        plan = build_plan(validate_case(target()))
        self.assertIn('"示例科技" "搜索平台部" "上海"', plan)
        self.assertIn('过去四周', plan)
        self.assertIn('原文', plan)

    def test_query_parameter_order_can_identify_distinct_original_pages(self):
        a=record(source_ref='https://example.com/a?part=2&part=1',origin_id=None)
        b=record(id='b',source_ref='https://example.com/a?part=1&part=2',origin_id=None,source_text='另一个页面描述了一次不同的上线经历。',quote='另一个页面描述了一次不同的上线经历。')
        self.assertEqual(self.assess(a,b)['dimensions']['workload']['source_clusters'],2)


if __name__ == '__main__':
    unittest.main()
