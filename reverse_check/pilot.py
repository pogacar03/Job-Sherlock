"""Offline evaluation of human-reviewed pilot annotations."""
import json
import math
from pathlib import Path
from statistics import median


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} 字段不完整或包含未知字段')


def _string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} 需要非空文本')


def _bool(value, label, nullable=True):
    if not (type(value) is bool or (nullable and value is None)):
        raise ValueError(f'{label} 需要布尔值或 null')


def _number(value, label, integer=False):
    if value is not None and (type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or value < 0):
        raise ValueError(f'{label} 需要非负有限数或 null')


def _ratio(values):
    known = [v for v in values if v is not None]
    numerator = sum(known)
    return {'numerator': numerator, 'denominator': len(known), 'unknown_count': len(values)-len(known),
            'value': numerator/len(known) if known else None}


def _summary(values):
    return {'median': median(values) if values else None, 'count': len(values)}


def evaluate_pilot(data: dict) -> dict:
    _object(data, ('schema_version', 'cases', 'read_checks'), '评测')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('评测 schema_version 必须为 1')
    if not isinstance(data['cases'], list) or not isinstance(data['read_checks'], list):
        raise ValueError('cases 和 read_checks 必须是数组')
    ids = set()
    for row in data['cases']:
        _object(row, ('id', 'stratum', 'manual', 'tool', 'top10', 'review_errors'), 'case')
        _string(row['id'], 'case.id')
        if row['id'] in ids: raise ValueError('case id 重复')
        ids.add(row['id'])
        if row['stratum'] not in ('rich', 'sparse', 'ambiguous'): raise ValueError('stratum 无效')
        for name in ('manual', 'tool'):
            item = row[name]
            _object(item, ('eligible_origins', 'active_seconds', 'setup_seconds'), name)
            origins = item['eligible_origins']
            if origins is not None:
                if not isinstance(origins, list): raise ValueError('eligible_origins 必须为数组或 null')
                for origin in origins: _string(origin, '来源 id')
            for field in ('active_seconds', 'setup_seconds'): _number(item[field], field)
        if not isinstance(row['top10'], list) or len(row['top10']) > 10: raise ValueError('top10 最多10条')
        for item in row['top10']:
            _object(item, ('ref', 'team_relevant', 'experience'), 'top10')
            _string(item['ref'], 'ref')
            _bool(item['team_relevant'], 'team_relevant')
            _bool(item['experience'], 'experience')
        _object(row['review_errors'], ('wrong_team', 'question_as_fact', 'untraceable_quote'), 'review_errors')
        for key, value in row['review_errors'].items(): _number(value, key, integer=True)
    ids = set()
    for row in data['read_checks']:
        _object(row, ('id', 'channel', 'manual_readable', 'body_ok', 'comments_expected', 'comments_ok'), 'read_check')
        _string(row['id'], 'read_check.id')
        _string(row['channel'], 'channel')
        if row['id'] in ids: raise ValueError('read_check id 重复')
        ids.add(row['id'])
        for field in ('manual_readable', 'body_ok', 'comments_ok'): _bool(row[field], field)
        _bool(row['comments_expected'], 'comments_expected', False)
    cases = data['cases']
    checks = data['read_checks']
    def read_values(field, comments=False):
        rows = [r for r in checks if not comments or r['comments_expected']]
        return [None if r['manual_readable'] is None else r[field] for r in rows if r['manual_readable'] is not False]
    def coverage(rows):
        return _ratio([None if r['tool']['eligible_origins'] is None else bool(r['tool']['eligible_origins']) for r in rows])
    positive = []
    for row in cases:
        manual = row['manual']['eligible_origins']
        tool = row['tool']['eligible_origins']
        if manual is None: positive.append(None)
        elif manual: positive.append(None if tool is None else bool(tool))
    reductions = [1-r['tool']['active_seconds']/r['manual']['active_seconds'] for r in cases
                  if r['manual']['active_seconds'] is not None and r['manual']['active_seconds'] > 0 and r['tool']['active_seconds'] is not None]
    errors = {}
    for key in ('wrong_team', 'question_as_fact', 'untraceable_quote'):
        vals = [r['review_errors'][key] for r in cases]
        errors[key] = {'sum': sum(x for x in vals if x is not None), 'reviewed_count': sum(x is not None for x in vals), 'unknown_count': sum(x is None for x in vals)}
    return {'schema_version': 1, 'metrics': {
        'body_read_rate': _ratio(read_values('body_ok')),
        'comment_read_rate': _ratio(read_values('comments_ok', True)),
        'related_rate': _ratio([x['team_relevant'] for r in cases for x in r['top10']]),
        'tool_case_coverage': coverage(cases), 'manual_positive_tool_coverage': _ratio(positive)},
        'strata': {s: {'tool_case_coverage': coverage([r for r in cases if r['stratum'] == s])} for s in ('rich', 'sparse', 'ambiguous')},
        'active_time_reduction': {'value': median(reductions) if reductions else None, 'paired_count': len(reductions)},
        'setup_time': {s: _summary([r[s]['setup_seconds'] for r in cases if r[s]['setup_seconds'] is not None]) for s in ('manual', 'tool')},
        'errors': errors}


def write_pilot_report(data: dict, out: Path, *, force=False) -> list[Path]:
    result = evaluate_pilot(data)
    out = Path(out)
    paths = [out/'evaluation.json', out/'evaluation.md']
    if not force and any(p.exists() for p in paths): raise ValueError('评测报告已存在；使用 --force 覆盖')
    out.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 试点评测', '', '未知表示尚未评测；结果仅反映提供的标注。', '']
    for key, row in result['metrics'].items():
        value = '尚未评测' if row['value'] is None else f"{row['value']:.1%}"
        lines.append(f"- {key}: {value} ({row['numerator']}/{row['denominator']}, 未知 {row['unknown_count']})")
    lines.extend(['', '完整分层、时间与错误统计见 evaluation.json。', ''])
    paths[1].write_text('\n'.join(lines), encoding='utf-8')
    return paths
