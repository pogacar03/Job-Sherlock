"""Validate and persist the evidence ledger; no network or model calls."""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit


DIMENSIONS = {
    'workload': '工作强度', 'atmosphere': '团队氛围', 'management': '管理沟通',
    'stability': '岗位稳定性', 'compensation': '薪酬兑现', 'growth': '成长空间',
}
SCOPE_FIELDS = ('company', 'business_unit', 'department', 'city', 'role')
SOURCE_TYPES = {'employee_account', 'user_interview', 'official', 'secondary'}
ACCESS_TYPES = {'full_text', 'user_provided', 'snippet'}
CASE_FIELDS = {'schema_version', 'company', 'company_aliases', 'department', 'business_unit', 'city', 'role', 'as_of', 'lookback_days', 'demo'}
EVIDENCE_FIELDS = {'id', 'source_ref', 'title', 'source_type', 'access', 'source_text', 'quote', 'observation', 'dimension', 'direction', 'scope', 'observed_at', 'published_at', 'retrieved_at', 'origin_id'}


def _text(value, field, optional=False):
    if optional and (value is None or value == ''):
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} 必须是非空文本')
    return value.strip()


def _date(value, field, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'{field} 必须使用 YYYY-MM-DD')
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f'{field} 日期无效') from exc


def _known_fields(value, allowed, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} 必须是对象')
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f'{label} 含未知字段：{", ".join(sorted(unknown))}')


def validate_case(value):
    _known_fields(value, CASE_FIELDS, '案例')
    result = dict(value)
    version = result.get('schema_version', 1)
    if type(version) is not int or version != 1:
        raise ValueError('不支持的 schema_version')
    result['schema_version'] = 1
    result['company'] = _text(result.get('company'), 'company')
    for field in SCOPE_FIELDS[1:]:
        result[field] = _text(result.get(field), field, optional=True)
    aliases = result.get('company_aliases', [])
    if not isinstance(aliases, list):
        raise ValueError('company_aliases 必须是文本数组')
    result['company_aliases'] = [_text(v, 'company_aliases') for v in aliases]
    result['as_of'] = _date(result.get('as_of'), 'as_of')
    window = result.get('lookback_days', 365)
    if type(window) is not int or not 1 <= window <= 3650:
        raise ValueError('lookback_days 必须是 1–3650 的整数')
    result['lookback_days'] = window
    if not isinstance(result.get('demo', False), bool):
        raise ValueError('demo 必须是布尔值')
    result['demo'] = result.get('demo', False)
    return result


def validate_evidence(value):
    _known_fields(value, EVIDENCE_FIELDS, '证据')
    result = dict(value)
    for field in ('source_ref', 'title', 'source_type', 'access', 'source_text', 'quote', 'observation', 'dimension', 'direction'):
        result[field] = _text(result.get(field), field)
    ref = result['source_ref']
    if ref.startswith('user-provided:'):
        _text(ref.removeprefix('user-provided:'), '材料定位')
    else:
        try:
            url = urlsplit(ref)
            valid = url.scheme in {'https', 'http'} and url.hostname and not url.username and not url.password
            _ = url.port
        except ValueError:
            valid = False
        if not valid or any(c.isspace() for c in ref):
            raise ValueError('source_ref 只接受 HTTP(S) URL 或 user-provided:材料定位')
    for field, choices in [('source_type', SOURCE_TYPES), ('access', ACCESS_TYPES), ('dimension', DIMENSIONS), ('direction', {'risk', 'positive', 'neutral'})]:
        if result[field] not in choices:
            raise ValueError(f'{field} 不支持：{result[field]}')
    if result['quote'] not in result['source_text']:
        raise ValueError('quote 必须是 source_text 中可逐字定位的原文')
    scope = result.get('scope')
    _known_fields(scope, set(SCOPE_FIELDS), 'scope')
    result['scope'] = {field: _text(scope.get(field), 'scope.' + field, optional=field != 'company') for field in SCOPE_FIELDS}
    for field in ('observed_at', 'published_at', 'retrieved_at'):
        result[field] = _date(result.get(field), field, optional=field != 'retrieved_at')
    for field in ('observed_at', 'published_at'):
        if result[field] and result[field] > result['retrieved_at']:
            raise ValueError(f'{field} 不能晚于 retrieved_at')
    result['origin_id'] = _text(result.get('origin_id'), 'origin_id', optional=True)
    identifier = result.get('id')
    if identifier is None:
        raw = json.dumps(result, ensure_ascii=False, sort_keys=True).encode()
        identifier = 'e-' + hashlib.sha256(raw).hexdigest()[:16]
    if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', identifier):
        raise ValueError('id 只接受最多80个字母、数字、下划线和连字符')
    result['id'] = identifier
    return result


def _write_json(path, data):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def create_case(path, **fields):
    path = Path(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError(f'案例目录非空，未覆盖：{path}')
    if 'as_of' not in fields:
        # Only today's Shanghai date is needed, not historical timezone rules.
        # Fixed UTC+8 keeps the zero-dependency CLI usable without system tzdata.
        fields['as_of'] = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    result = validate_case(fields)
    path.mkdir(parents=True, exist_ok=True)
    _write_json(path / 'evidence.json', [])
    _write_json(path / 'case.json', result)
    return result


def read_case(path):
    return validate_case(json.loads((Path(path) / 'case.json').read_text(encoding='utf-8')))


def read_evidence(path):
    rows = json.loads((Path(path) / 'evidence.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('evidence.json 必须是数组')
    normalized = [validate_evidence(row) for row in rows]
    if len({row['id'] for row in normalized}) != len(normalized):
        raise ValueError('evidence.json 存在重复 id')
    return normalized


def import_evidence(path, records):
    read_case(path)
    if not isinstance(records, list):
        raise ValueError('导入文件必须是证据数组')
    incoming = [validate_evidence(row) for row in records]
    # Parallel researchers hand results to one registrar; reject concurrent writers.
    lock = Path(path) / '.import-lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError('另一次导入正在进行；请串行登记。异常退出后确认没有写入进程再移除 .import-lock') from exc
    try:
        existing = read_evidence(path)
        by_id = {row['id']: row for row in existing}
        count = 0
        for row in incoming:
            if row['id'] in by_id:
                if by_id[row['id']] != row:
                    raise ValueError(f'证据 id 冲突：{row["id"]}；请保留原记录或使用新 id')
                continue
            by_id[row['id']] = row
            count += 1
        if count:
            _write_json(Path(path) / 'evidence.json', list(by_id.values()))
        return count
    finally:
        lock.rmdir()
