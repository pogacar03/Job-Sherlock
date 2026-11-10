def record(**changes):
    value = {
        'id': 'e1', 'source_ref': 'https://example.com/post/1',
        'title': '员工自述', 'source_type': 'employee_account', 'access': 'full_text',
        'source_text': '最近一个月基本每晚十点下班，周末通常休息。',
        'quote': '最近一个月基本每晚十点下班',
        'observation': '作者自述最近一个月常在晚十点下班。',
        'dimension': 'workload', 'direction': 'risk',
        'scope': {'company': '示例科技', 'department': '搜索平台部', 'city': '上海', 'role': '后端研发', 'business_unit': None},
        'observed_at': '2026-10-15', 'published_at': '2026-10-20',
        'retrieved_at': '2026-11-10', 'origin_id': 'account-a',
    }
    value.update(changes)
    return value


def target():
    return {'company': '示例科技', 'department': '搜索平台部', 'city': '上海', 'role': '后端研发', 'as_of': '2026-11-10'}
