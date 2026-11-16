import unittest

from reverse_check.pilot import evaluate_pilot


def side(origins=None, active=None, setup=None):
    return {'eligible_origins': origins, 'active_seconds': active, 'setup_seconds': setup}


def case(identifier, manual, tool):
    return {'id': identifier, 'stratum': 'rich', 'manual': manual, 'tool': tool,
            'top10': [], 'review_errors': {'wrong_team': None, 'question_as_fact': None, 'untraceable_quote': None}}


class PilotTests(unittest.TestCase):
    def test_empty_is_unknown(self):
        result = evaluate_pilot({'schema_version': 1, 'cases': [], 'read_checks': []})
        self.assertIsNone(result['metrics']['tool_case_coverage']['value'])
        self.assertEqual(result['metrics']['tool_case_coverage']['denominator'], 0)
        self.assertIsNone(result['active_time_reduction']['value'])

    def test_coverage_times_and_unknowns(self):
        data = {'schema_version': 1, 'read_checks': [], 'cases': [
            case('a', side(['x', 'x'], 100), side(['y'], 60)),
            case('b', side(['z'], 200), side([], 100)),
            case('c', side(), side()),
        ]}
        result = evaluate_pilot(data)
        self.assertEqual(result['metrics']['manual_positive_tool_coverage'],
                         {'numerator': 1, 'denominator': 2, 'unknown_count': 1, 'value': .5})
        self.assertAlmostEqual(result['active_time_reduction']['value'], .45)
        self.assertEqual(result['errors']['wrong_team']['unknown_count'], 3)

    def test_invalid_values_rejected(self):
        for invalid in (True, -1, float('nan'), float('inf')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                evaluate_pilot({'schema_version': 1, 'cases': [case('a', side([], invalid), side([]))], 'read_checks': []})

    def test_read_checks_exclude_ineligible_and_count_unknown(self):
        checks = [dict(id='a', channel='nowcoder', manual_readable=True, body_ok=True, comments_expected=True, comments_ok=False),
                  dict(id='b', channel='nowcoder', manual_readable=False, body_ok=None, comments_expected=True, comments_ok=None),
                  dict(id='c', channel='maimai', manual_readable=None, body_ok=None, comments_expected=False, comments_ok=None)]
        r = evaluate_pilot({'schema_version': 1, 'cases': [], 'read_checks': checks})
        self.assertEqual(r['metrics']['body_read_rate']['value'], 1)
        self.assertEqual(r['metrics']['body_read_rate']['unknown_count'], 1)
        self.assertEqual(r['metrics']['comment_read_rate']['value'], 0)

    def test_duplicate_ids_and_overlong_results_rejected(self):
        item = case('a', side([]), side([]))
        with self.assertRaises(ValueError):
            evaluate_pilot({'schema_version': 1, 'cases': [item, item], 'read_checks': []})
        item['top10'] = [{'ref': str(i), 'team_relevant': None, 'experience': None} for i in range(11)]
        with self.assertRaises(ValueError):
            evaluate_pilot({'schema_version': 1, 'cases': [item], 'read_checks': []})

    def test_manual_negative_is_excluded_from_positive_denominator(self):
        item = case('a', side([]), side())
        result = evaluate_pilot({'schema_version': 1, 'cases': [item], 'read_checks': []})
        metric = result['metrics']['manual_positive_tool_coverage']
        self.assertEqual(metric['denominator'], 0)
        self.assertEqual(metric['unknown_count'], 0)
        self.assertIsNone(metric['value'])


if __name__ == '__main__':
    unittest.main()
