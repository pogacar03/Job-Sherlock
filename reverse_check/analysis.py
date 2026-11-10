"""Conservative evidence coverage, never a rating of a company or a person."""

from datetime import date
import re
import unicodedata

from .casebook import DIMENSIONS
from .sources import canonical_url, load_sources, source_queries


QUESTIONS = {
    'workload': '过去四周通常几点下班、最晚几点？周末工作和夜间响应各发生几次，如何安排调休？',
    'atmosphere': '最近一次有人提出不同意见或项目失败后，团队怎样讨论和处理？能举一个具体例子吗？',
    'management': '需求和优先级冲突时谁来取舍？临时插单通常怎样调整原有交付时间？',
    'stability': '这个岗位是新增还是替补？过去半年团队规模、业务目标和汇报关系有哪些变化？',
    'compensation': '固定薪资、绩效和奖金如何约定？最近一个周期实际如何兑现，哪些可写入书面材料？',
    'growth': '入职前三个月的目标、导师支持和反馈安排是什么？最近一次内部晋升依据是什么？',
}


def _norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text or '')).casefold()


def _canonical_ref(ref):
    if ref.startswith('user-provided:'):
        return ref
    return canonical_url(ref)


def _reasons(case, row):
    reasons = []
    company_names = [case['company'], *case['company_aliases']]
    if _norm(row['scope']['company']) not in {_norm(n) for n in company_names}:
        reasons.append('公司主体不匹配')
    if not case['department']:
        reasons.append('目标部门尚未明确')
    for field, label in [('business_unit','业务线'),('department','部门'),('city','城市'),('role','岗位')]:
        if case[field] and _norm(case[field]) != _norm(row['scope'][field]):
            reasons.append(label + ('信息缺失' if not row['scope'][field] else '不匹配'))
    if row['access'] == 'snippet':
        reasons.append('只有摘要，原文未核实')
    if row['source_type'] not in {'employee_account','user_interview'}:
        reasons.append('官方或二手背景，不能证明实际工作体验')
    if not row['observed_at']:
        reasons.append('观察时间不明')
    else:
        age = (date.fromisoformat(case['as_of']) - date.fromisoformat(row['observed_at'])).days
        if age < 0:
            reasons.append('观察发生在基准日之后')
        elif age > case['lookback_days']:
            reasons.append('观察已超出时间窗口')
    if row['published_at'] and row['published_at'] > case['as_of']:
        reasons.append('发布在基准日之后')
    return reasons


def _clusters(rows):
    """Connected components prevent transitive repost chains inflating counts."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i,row in enumerate(rows):
        keys = [('ref', _canonical_ref(row['source_ref'])), ('quote', _norm(row['quote']))]
        if row['origin_id']:
            keys.append(('origin', row['origin_id']))
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    return {row['id']: 'source-' + str(find(i) + 1) for i,row in enumerate(rows)}


def analyze(case, records):
    groups = _clusters(records)
    eligible, background = [], []
    for row in records:
        item = {**row, 'source_cluster':groups[row['id']]}
        reasons = _reasons(case, row)
        if reasons:
            background.append({**item, 'reasons':reasons})
        else:
            eligible.append(item)
    dimensions = {}
    for key,label in DIMENSIONS.items():
        rows = [r for r in eligible if r['dimension'] == key]
        directions = {r['direction'] for r in rows}
        count = len({r['source_cluster'] for r in rows})
        if not rows:
            status, note = 'unknown', '没有满足范围、时间与原文要求的直接材料。'
        elif {'risk','positive'} <= directions:
            status, note = 'conflicting', '存在相反方向的观察；需核实时间段、子团队和工作职责差异。'
        else:
            status, note = 'observed', '保存了符合条件的自述；材料覆盖不等于已确认的部门常态。'
        dimensions[key] = {
            'label':label, 'status':status, 'note':note, 'source_clusters':count,
            'coverage':'none' if count == 0 else 'single_source' if count == 1 else 'multiple_sources',
            'directions': sorted(directions), 'evidence_ids':[r['id'] for r in rows],
            'question': QUESTIONS[key],
        }
    return {
        'schema_version':1, 'target':case, 'dimensions':dimensions,
        'summary':{'total_count':len(records), 'eligible_count':len(eligible),
                   'background_count':len(background), 'source_clusters':len({r['source_cluster'] for r in eligible}),
                   'unknown_dimensions':sum(d['status']=='unknown' for d in dimensions.values()),
                   'conflicting_dimensions':sum(d['status']=='conflicting' for d in dimensions.values())},
        'evidence':eligible, 'background':background,
        'methodology':[
            '观察由材料提供者提取；程序不验证外部网页真实性、匿名身份或观察与摘录的语义一致性。',
            '来源簇按填写的血缘、同一URL及相同摘录保守合并；无法保证不同簇真正独立。',
            '来源簇数仅表示已收集材料的覆盖，不是置信概率或代表性抽样。',
            '官方、二手、过时、范围不匹配和摘要材料保留为背景，不能支持部门现状判断。',
        ],
    }


def build_plan(case,registry=None,selected=None):
    tokens = [case[k] for k in ('company','business_unit','department','city','role') if case[k]]
    scope = ' '.join('"'+t.replace('"',' ')+'"' for t in tokens[:4])
    lines = [f'# {case["company"]} 反向背调检索计划', '',
             f'基准日：{case["as_of"]}；观察窗口：{case["lookback_days"]}天。',
             '', '以下为待执行检索式，不表示已搜索或找到证据。平台访问受限时记录缺口并由用户提供原文材料。',
             '', '## 待查对象', '', f'范围：{scope}；岗位：{case["role"] or "尚未明确"}。',
             '先核对公司主体、部门别称、业务线、岗位和办公地点；别名需要证据后显式登记。',
             '', '## 检索与面试问题', '']
    for key,terms in [('workload','加班 值班 周末'),('atmosphere','氛围 协作 复盘'),('management','管理 需求 优先级'),('stability','调整 招聘 离职'),('compensation','奖金 绩效 兑现'),('growth','导师 晋升 培养')]:
        lines.extend([f'### {DIMENSIONS[key]}', '', f'- 员工线索：`{scope} {terms}`',
                      f'- 背景核对：`"{case["company"]}" "{case["department"] or "部门"}" 招聘 业务`',
                      '- 命中后读取原文，登记观察日期、明确所属范围与转载关系；摘要只作线索。',
                      '- 面试核实：' + QUESTIONS[key], ''])
    lines.extend(['## 按来源检索（尚未执行）',''])
    for row in source_queries(case,registry or load_sources(),selected):
        lines.extend([f'- {row["name"]}：`{row["query"]}`'])
    lines.extend(['','公开原文URL可交给 collect 保存；manual来源由宿主或用户读取，所有材料都需审阅后导入。','',
                  '## 完成与停止', '', '每个高优先级问题最多两轮补充检索；连续一轮没有新增可访问原文时记录未知。',
                  '保留检索式、原始URL、访问限制、正反观察；不要用帖子数估算加班或离职发生率。'])
    return '\n'.join(lines) + '\n'
