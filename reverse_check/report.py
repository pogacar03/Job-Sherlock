"""Portable reports rendered from the same machine-readable analysis."""

from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote

from .analysis import analyze
from .casebook import _write_json, read_case, read_evidence
from .collection import STATUS_LABELS, collection_summary


STATUS = {'unknown':'待核实', 'observed':'有可追溯观察', 'conflicting':'存在分歧'}
SOURCE = {'employee_account':'员工自述（身份未认证）', 'user_interview':'用户提供访谈', 'official':'官方材料', 'secondary':'二手材料'}
DIRECTION = {'risk':'风险观察', 'positive':'正向观察', 'neutral':'中性观察'}


def _e(value):
    return escape(str(value or ''), quote=True)


def _md(value):
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', escape(str(value or '')))


def _source_html(row):
    ref = row['source_ref']
    if ref.startswith('user-provided:'):
        return f'<span class="source-ref">{_e(ref)}</span>'
    return f'<a href="{_e(ref)}" target="_blank" rel="noopener noreferrer">打开原始来源 ↗</a>'


def _source_md(row):
    ref = row['source_ref']
    if ref.startswith('user-provided:'):
        return _md(ref)
    return '[原始来源](' + quote(ref, safe=':/?=&%#@+;,$!-_.~') + ')'


def markdown_report(data):
    case = data['target']
    lines = [f'# {_md(case["company"])} · 反向背调报告', '']
    if case['demo']:
        lines.extend(['**演示报告：全部材料为虚构，不对应真实公司。**',''])
    lines.extend([f'基准日：{case["as_of"]}；观察窗口：{case["lookback_days"]}天。',
                  '范围：' + ' / '.join(_md(case[k] or '未明确') for k in ('business_unit','department','city','role')), '',
                  f'共保存 {data["summary"]["total_count"]} 条材料；{data["summary"]["eligible_count"]} 条符合分析条件。来源簇数表示材料覆盖，不代表统计置信度。', ''])
    all_rows = {r['id']:r for r in [*data['evidence'],*data['background']]}
    collection=data.get('collection',{})
    if collection.get('runs'):
        lines.extend(['## 来源采集记录','',f'{collection["runs"]} 次采集，累计 {collection["total_urls"]} 条URL任务，{collection["fetch_attempts"]} 次自动读取尝试。',
                      '以下是采集状态，不是已审阅证据；重复URL跨批次按次保留。',''])
        for row in collection['results']:
            lines.append(f'- {_md(row["status"])}：{_md(row["requested_url"])} — {_md(row["reason"])}')
        lines.append('')
    for dim in data['dimensions'].values():
        lines.extend([f'## {dim["label"]} · {STATUS[dim["status"]]}', '', dim['note'],
                      f'材料覆盖：{dim["source_clusters"]} 个来源簇。', ''])
        for identifier in dim['evidence_ids']:
            row = all_rows[identifier]
            lines.extend([f'- [{_md(identifier)}] {_md(row["observation"])}（{DIRECTION[row["direction"]]}）',
                          f'  - 原文：{_md(row["quote"])}',
                          f'  - {_source_md(row)}；观察日期：{row["observed_at"]}；来源簇：{row["source_cluster"]}'])
        lines.extend(['', '面试核实：' + dim['question'], ''])
    lines.extend(['## 背景与待核线索', ''])
    if not data['background']:
        lines.append('尚无背景材料。')
    for row in data['background']:
        lines.extend([f'- [{_md(row["id"])}] {_md(row["title"])}：' + '；'.join(row['reasons']),
                      f'  - 原文或摘要：{_md(row["quote"])}', f'  - {_source_md(row)}'])
    lines.extend(['', '## 方法与适用范围', ''])
    lines.extend('- ' + item for item in data['methodology'])
    return '\n'.join(lines) + '\n'


CSS = '''
:root{color-scheme:light;--ink:#172d2b;--muted:#586864;--line:#d8e1d8;--paper:#f6f7f0;--green:#194f42;--lime:#d7f394;--amber:#875721;--red:#934337}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--green);text-underline-offset:4px;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible{outline:3px solid #477d32;outline-offset:4px}p{margin:0 0 12px}small,.muted{color:var(--muted)}header{padding:24px max(24px,calc((100vw - 1240px)/2));border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:16px}.brand{font-weight:750;letter-spacing:2px}.demo{background:#fff0c9;color:#69440c;padding:13px 24px;text-align:center;font-weight:600}.shell{max-width:1240px;margin:auto;padding:44px 24px 72px}.hero{display:flex;justify-content:space-between;gap:28px;align-items:end;margin-bottom:32px}.eyebrow{color:var(--green);font-size:12px;letter-spacing:3px;font-weight:700}h1{font-size:clamp(30px,4.3vw,54px);line-height:1.2;margin:12px 0 18px;letter-spacing:-1px}h2{font-size:22px;margin:0 0 10px}h3{font-size:19px;margin:0}h4{font-size:16px;margin:0 0 8px}.scope{color:var(--muted);max-width:760px;overflow-wrap:anywhere}.stamp{border-left:3px solid var(--green);padding:8px 0 8px 18px;min-width:180px}.stamp b{font-size:24px;display:block}.layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:30px}.sidebar{align-self:start;position:sticky;top:24px}.brief{background:var(--green);color:white;border-radius:16px;padding:24px}.brief p{color:#e1ede1}.brief strong{font-size:38px;line-height:1.2}.brief small{color:#e1ede1;display:block;margin-bottom:18px}.brief .metric{padding:14px 0;border-top:1px solid #ffffff35}.sidebar nav{margin-top:18px;display:grid;gap:5px}.sidebar nav a{padding:8px 13px;text-decoration:none;border-radius:7px}.sidebar nav a:hover{background:#e7ecdf}.section-title{display:flex;justify-content:space-between;gap:12px;margin:0 0 18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:#fff;border:1px solid var(--line);border-radius:15px;padding:23px;min-width:0;display:flex;flex-direction:column}.card-top{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:17px}.badge{white-space:nowrap;font-size:11px;font-weight:650;padding:4px 9px;border-radius:30px;background:#edf0ea;color:#56615a}.badge.conflicting{background:#fae8df;color:var(--red)}.badge.observed{background:#e8f2d9;color:#335d28}.cover{font-size:12px;color:var(--muted);margin-bottom:12px}.card p{font-size:14px}.refs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}.refs a{font-size:12px;background:#eff3e7;padding:2px 9px;border-radius:5px;text-decoration:none}.question{border-top:1px dashed var(--line);padding-top:12px;margin-top:auto;font-size:13px}.question b{display:block;color:var(--green);font-size:11px;letter-spacing:1px}.block{margin-top:35px;scroll-margin-top:24px}.entry{background:white;border:1px solid var(--line);border-radius:12px;padding:20px 23px;margin-top:13px;scroll-margin-top:24px;overflow-wrap:anywhere}.entry-title{display:flex;justify-content:space-between;gap:16px;align-items:start}.id{font-family:ui-monospace,monospace;font-size:12px;color:var(--green)}blockquote{border-left:3px solid #b6ce88;margin:12px 0;padding:8px 14px;background:#f7f9ef;white-space:pre-wrap}.meta{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.reason{color:var(--amber);font-size:13px}.source-ref{font-size:12px;color:var(--muted)}details{margin-top:12px}summary{cursor:pointer;color:var(--green);font-size:13px}.original{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;background:#f4f5f0;padding:14px;border-radius:7px}.method{padding:25px;background:#eaf0df;border-radius:14px}.method li{margin:7px 0}.empty{padding:20px;background:white;border:1px dashed var(--line);border-radius:10px;color:var(--muted)}footer{margin-top:35px;font-size:12px;color:var(--muted)}
@media(max-width:900px){.layout{grid-template-columns:1fr}.sidebar{position:static}.brief{display:flex;gap:24px;flex-wrap:wrap}.brief .metric{border:0;padding:0}.brief strong{font-size:28px}.brief small{margin:0}.sidebar nav{display:flex;flex-wrap:wrap}.stamp{min-width:150px}.hero{align-items:start}}
@media(max-width:580px){header{font-size:12px;padding:18px}.shell{padding:28px 16px}.grid{grid-template-columns:1fr}.hero{display:block}.stamp{margin-top:20px}.card{padding:20px}.section-title{display:block}.entry{padding:18px}.entry-title{display:block}.brief{gap:20px}.brief p{width:100%}}
@media print{body{background:white}.sidebar nav,details{display:none}.layout{display:block}.sidebar{position:static;margin-bottom:20px}.brief{color:black;background:#eee}.brief p,.brief small{color:black}.card,.entry{break-inside:avoid}a{color:black}.shell{padding:20px}}
'''


def html_report(data):
    case,summary = data['target'],data['summary']
    collection=data.get('collection',{})
    collection_html=''
    if collection.get('runs'):
        items=''.join(f'<li><strong>{_e(STATUS_LABELS[row["status"]])}</strong> · {_e(row["requested_url"])}<br><span class="meta">{_e(row["reason"])} · 获取 {_e(row["retrieved_at"])}</span></li>' for row in collection['results'])
        collection_html=f'<section class="entry" style="margin:0 0 24px"><h2>来源采集记录</h2><p>{collection["runs"]} 次采集 · {collection["total_urls"]} 条URL任务 · {collection["fetch_attempts"]} 次自动读取尝试</p><p class="meta">采集原文需要审阅后才进入证据账本；登录、验证码、限流与网络失败分别记录。同一URL跨批次按次保留。</p><details><summary>展开每条采集状态</summary><ul>{items}</ul></details></section>'
    cards, navigation = [],[]
    for key,dim in data['dimensions'].items():
        links = ''.join(f'<a href="#evidence-{_e(i)}">{_e(i)}</a>' for i in dim['evidence_ids'])
        navigation.append(f'<a href="#dimension-{key}">{_e(dim["label"])}</a>')
        cards.append(f'''<article class="card" id="dimension-{key}">
<div class="card-top"><h3>{_e(dim['label'])}</h3><span class="badge {dim['status']}">{STATUS[dim['status']]}</span></div>
<div class="cover">{dim['source_clusters']} 个来源簇 · {len(dim['evidence_ids'])} 条符合条件材料</div>
<p>{_e(dim['note'])}</p><div class="refs">{links}</div>
<div class="question"><b>面试时核实</b>{_e(dim['question'])}</div></article>''')
    entries = []
    for row in data['evidence']:
        scope = ' / '.join(row['scope'][k] or '未明确' for k in ('department','city','role'))
        entries.append(f'''<article class="entry" id="evidence-{_e(row['id'])}">
<div class="entry-title"><div><span class="id">{_e(row['id'])} · {_e(row['source_cluster'])}</span><h4>{_e(row['title'])}</h4></div><span class="badge">{DIRECTION[row['direction']]}</span></div>
<p>{_e(row['observation'])}</p><blockquote>{_e(row['quote'])}</blockquote>
<p class="meta">{_e(SOURCE[row['source_type']])} · 观察 {_e(row['observed_at'])} · 发布 {_e(row['published_at'] or '不明')} · 获取 {_e(row['retrieved_at'])}<br>{_e(scope)}</p>
{_source_html(row)}<details><summary>查看保存的原文文本</summary><div class="original">{_e(row['source_text'])}</div></details></article>''')
    backgrounds = []
    for row in data['background']:
        backgrounds.append(f'''<article class="entry" id="evidence-{_e(row['id'])}"><span class="id">{_e(row['id'])}</span><h4>{_e(row['title'])}</h4>
<p class="reason">仅作背景：{_e('；'.join(row['reasons']))}</p><blockquote>{_e(row['quote'])}</blockquote>
<p class="meta">{_e(SOURCE[row['source_type']])} · 观察 {_e(row['observed_at'] or '不明')} · 获取 {_e(row['retrieved_at'])}</p>{_source_html(row)}</article>''')
    demo = '<div class="demo">演示报告 · 全部材料为虚构，不对应真实公司</div>' if case['demo'] else ''
    scope = ' / '.join(case[k] or '未明确' for k in ('business_unit','department','city','role'))
    overview = '当前材料不足以判断目标部门的实际工作体验。' if not summary['eligible_count'] else '先看材料覆盖，再看观察和分歧。'
    methodology = ''.join('<li>'+_e(item)+'</li>' for item in data['methodology'])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{_e(case['company'])} · 反向背调报告</title><style>{CSS}</style></head><body>
<header><span class="brand">求职侦探</span><span>以原文为起点 · 为下一次面试做准备</span></header>{demo}
<main class="shell"><section class="hero"><div><div class="eyebrow">WORKPLACE EVIDENCE BRIEF</div><h1>{_e(case['company'])}</h1><div class="scope">{_e(scope)}</div></div><div class="stamp"><small>调查基准日</small><b>{case['as_of']}</b><small>观察窗口 {case['lookback_days']} 天</small></div></section>
<div class="layout"><aside class="sidebar"><div class="brief"><p>{overview}</p><div class="metric"><strong>{summary['eligible_count']}<span style="font-size:14px"> / {summary['total_count']}</span></strong><small>符合条件 / 已保存材料</small></div><div class="metric"><strong>{summary['source_clusters']}</strong><small>符合条件材料的来源簇</small></div><div class="metric"><strong>{summary['unknown_dimensions']}</strong><small>仍待核实的维度</small></div></div><nav aria-label="报告导航">{''.join(navigation)}<a href="#sources">原文与出处</a><a href="#background">背景与线索</a></nav></aside>
<div>{collection_html}<section><div class="section-title"><h2>部门体验 · 六个维度</h2><small>材料覆盖不是置信概率</small></div><div class="grid">{''.join(cards)}</div></section>
<section class="block" id="sources"><h2>原文与出处</h2><p class="muted">摘录、观察与出处一起保留，便于逐条复查。</p>{''.join(entries) or '<div class="empty">尚无满足范围、时间与原文要求的直接材料。</div>'}</section>
<section class="block" id="background"><h2>背景与待核线索</h2><p class="muted">以下材料没有用于判断目标部门的现状。</p>{''.join(backgrounds) or '<div class="empty">尚无背景材料。</div>'}</section>
<section class="block method"><h2>如何理解这份报告</h2><ul>{methodology}</ul></section>
<footer>本地生成 · 原文内容可能涉及未公开访谈，请在分享前审阅。JSON 与 Markdown 保留同一批分析结果。</footer></div></div></main></body></html>'''


def write_report(case_dir, out, force=False):
    case = read_case(case_dir)
    rows = read_evidence(case_dir)
    data = analyze(case, rows)
    data['collection']=collection_summary(case_dir)
    out = Path(out)
    files = [out / ('report.'+ext) for ext in ('html','md','json')]
    if not force and any(p.exists() for p in files):
        raise ValueError('报告已存在；使用不同输出目录，或显式添加 --force')
    rendered = [html_report(data), markdown_report(data)]
    out.mkdir(parents=True, exist_ok=True)
    for path,content in zip(files[:2],rendered):
        path.write_text(content, encoding='utf-8')
    _write_json(files[2], data)
    return files
