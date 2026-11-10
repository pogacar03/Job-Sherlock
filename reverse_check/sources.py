"""Pinned, local source configuration and source-specific discovery queries."""

from importlib.resources import files
import json
from pathlib import Path
import re
from string import Formatter
from urllib.parse import unquote_plus, urlsplit, urlunsplit


RULES = {
    'blocked_titles':['Just a moment','Attention Required','安全验证','访问验证'],
    'login_titles':['登录','Sign in'],
    'missing_titles':['页面不存在','内容已删除','Page not found'],
}


def canonical_url(url):
    parts=urlsplit(url)
    pairs=[]
    for part in parts.query.split('&'):
        key=unquote_plus(part.partition('=')[0]).lower()
        if not key.startswith('utm_') and key not in {'fbclid','gclid'}:pairs.append(part)
    return urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path or '/','&'.join(pairs),''))


def load_sources(path=None):
    text=Path(path).read_text(encoding='utf-8') if path else files('reverse_check').joinpath('data/sources.json').read_text(encoding='utf-8')
    data=json.loads(text)
    if not isinstance(data,dict) or set(data)!={'schema_version','sources'} or type(data['schema_version']) is not int or data['schema_version']!=1:
        raise ValueError('来源注册表需要 schema_version=1 与 sources 数组')
    rows=data['sources']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:
        raise ValueError('sources 需要1–100个来源')
    result=[]; ids=set(); fallback=0; declared_domains=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)-{'id','name','domains','mode','query',*RULES}:
            raise ValueError('来源配置含未知字段或不是对象')
        identifier=row.get('id'); name=row.get('name')
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',identifier) or identifier in ids:
            raise ValueError('来源id无效或重复')
        if not isinstance(name,str) or not name.strip() or row.get('mode') not in {'public','manual'}:
            raise ValueError('来源名称或mode无效')
        domains=row.get('domains')
        if not isinstance(domains,list) or not all(isinstance(d,str) and re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}',d) for d in domains):
            raise ValueError('domains 需要不含协议、端口或路径的小写域名数组')
        if not domains:fallback+=1
        for domain in domains:
            if domain in declared_domains:raise ValueError('来源域名重复，读取策略不明确：'+domain)
            declared_domains.add(domain)
        query=row.get('query')
        if query is not None:
            if not isinstance(query,str) or not query.strip():raise ValueError('query必须是文本或null')
            try:
                for _,field,spec,conversion in Formatter().parse(query):
                    if field is not None and (field not in {'company','department','business_unit','city','role'} or spec or conversion):
                        raise ValueError('query只接受公司、部门、城市、业务线、岗位占位符')
            except ValueError as exc:raise ValueError('query模板无效：'+str(exc)) from exc
        item={**row,'query':query,'name':name.strip()}
        for key,default in RULES.items():
            markers=row.get(key,default)
            if not isinstance(markers,list) or not all(isinstance(v,str) and v.strip() for v in markers):
                raise ValueError(key+'必须是非空文本数组')
            item[key]=markers
        result.append(item); ids.add(identifier)
    if fallback>1:raise ValueError('最多一个空域名的通用来源')
    return {'schema_version':1,'sources':result}


def source_for_url(registry,url):
    host=(urlsplit(url).hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
    matches=[(len(domain),row) for row in registry['sources'] for domain in row['domains'] if host==domain or host.endswith('.'+domain)]
    if matches:return max(matches,key=lambda item:item[0])[1]
    return next((row for row in registry['sources'] if not row['domains']),None)


def source_queries(case,registry,selected=None):
    selected=set(selected) if selected else None
    known={row['id'] for row in registry['sources']}
    if selected and selected-known:raise ValueError('未知来源：'+', '.join(sorted(selected-known)))
    values={key:('"'+' '.join((case.get(key) or '').replace('"',' ').split())+'"') if case.get(key) else '' for key in ('company','business_unit','department','city','role')}
    return [{'source_id':row['id'],'name':row['name'],'mode':row['mode'],
             'query':' '.join(row['query'].format(**values).split())}
            for row in registry['sources'] if row['query'] and (not selected or row['id'] in selected)]
