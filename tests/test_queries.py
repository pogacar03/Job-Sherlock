import unittest

from reverse_check.queries import build_forum_queries, match_hint


class QueryTests(unittest.TestCase):
    def test_platform_use_warning_does_not_assert_employer(self):
        from reverse_check.queries import platform_usage_hint
        case = {'company':'BOSS直聘','company_aliases':['BOSS 直聘']}
        def c(text): return {'title':'','segments':[{'text':text}]}
        self.assertTrue(platform_usage_hint(case,c('一家公司的HR在BOSS 直聘上回复了我')))
        self.assertTrue(platform_usage_hint(case,c('从Boss直聘上找到其他公司的工作')))
        self.assertFalse(platform_usage_hint(case,c('我在BOSS直聘上班，每天写Java')))
        self.assertFalse(platform_usage_hint(case,c('BOSS直聘研发部门工作时间')))
    def test_full_department_and_hints(self):
        case = {'company':'示例科技','department':'国际化广告 CRM 与交易','company_aliases':[]}
        queries = build_forum_queries(case, ['CRM平台', 'CRM平台'])
        self.assertEqual(queries[0], '示例科技 国际化广告 CRM 与交易')
        self.assertEqual(len(queries), 4)
        self.assertEqual(queries[-1], '示例科技 CRM平台')
        with self.assertRaises(ValueError): build_forum_queries(case, ['a','b','c','d'])

    def test_hint_is_not_a_team_assignment(self):
        case = {'company':'示例科技','department':'国际化广告 CRM 与交易','company_aliases':['Example']}
        def candidate(text): return {'title':'', 'segments':[{'text':text}]}
        self.assertEqual(match_hint(case, candidate('示例科技 国际化广告ＣＲＭ与交易')), 'department_mention')
        self.assertEqual(match_hint(case, candidate('example CRM平台'), ['CRM平台']), 'search_hint')
        self.assertEqual(match_hint(case, candidate('示例科技 CRM')), 'company_only')
        self.assertEqual(match_hint(case, candidate('其他公司 CRM平台'), ['CRM平台']), 'unrelated')
        self.assertEqual(match_hint({**case,'department':None}, candidate('示例科技其他部门')), 'company_only')
