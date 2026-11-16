"""Validate segment-grounded proposals and record explicit review decisions."""
import hashlib
import json
from pathlib import Path
import re

from .casebook import FOCUS_DIMENSIONS, SCOPE_FIELDS, _write_json, import_evidence, validate_evidence
from .forum_content import candidate_id_for, thread_key
from .http_source import FetchError

PROPOSAL_FIELDS = {'id','scan_id','candidate_id','segment_id','quote','observation','kind','source_type','dimension','direction','scope','observed_at','published_at','basis'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _validate_candidate(candidate):
    try:
        key=thread_key(candidate['channel'],candidate['url'])
        segments=candidate['segments'];title=candidate['title']
        if not isinstance(segments,list) or not segments or any(not isinstance(s,dict) or not isinstance(s.get('text'),str) for s in segments): raise ValueError('候选段落无效')
        if len({s.get('id') for s in segments}) != len(segments): raise ValueError('候选段落 id 重复')
        if key!=candidate['thread_key'] or candidate_id_for(key,title,segments)!=candidate['candidate_id']: raise ValueError('候选快照校验失败')
    except (KeyError, TypeError, FetchError) as exc:
        raise ValueError('候选快照无效') from exc


def load_candidates(case_dir: Path) -> list[dict]:
    root=Path(case_dir)/'scans';rows=[]
    for path in sorted(root.glob('*/run.json')):
        if path.is_symlink() or path.parent.is_symlink(): raise ValueError('扫描目录不可为符号链接')
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version')!=2: continue
        if not isinstance(data.get('candidates'),list): raise ValueError('候选列表无效')
        for item in data['candidates']:
            _validate_candidate(item)
            rows.append({**item,'scan_id':path.parent.name})
    return rows


def prepare_evidence(candidate: dict, proposal: dict) -> dict:
    _validate_candidate(candidate)
    if not isinstance(proposal,dict) or set(proposal)!=PROPOSAL_FIELDS: raise ValueError('建议字段缺失或未知')
    if not isinstance(proposal['id'],str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',proposal['id']): raise ValueError('建议 id 无效')
    if candidate.get('scan_id')!=proposal['scan_id'] or candidate['candidate_id']!=proposal['candidate_id']: raise ValueError('建议与快照不匹配')
    if proposal['kind']!='experience' or proposal['source_type']!='employee_account': raise ValueError('仅员工亲历建议可接收')
    if proposal['dimension'] not in FOCUS_DIMENSIONS: raise ValueError('建议维度无效')
    scope=proposal['scope']
    if not isinstance(scope,dict) or set(scope)!=set(SCOPE_FIELDS): raise ValueError('scope 字段不完整')
    segments={s['id']:s for s in candidate['segments']}
    def check_quote(segment_id, part, quote):
        if segment_id not in segments or part not in ('text','time_raw'): raise ValueError('引用段落无效')
        value=segments[segment_id].get(part)
        if not isinstance(quote,str) or not quote.strip() or not isinstance(value,str) or quote not in value: raise ValueError('引用未出现在指定原文')
    check_quote(proposal['segment_id'],'text',proposal['quote'])
    basis=proposal['basis']
    if not isinstance(basis,list): raise ValueError('basis 必须为数组')
    supported=set()
    allowed={'source_type','observed_at','published_at',*('scope.'+f for f in SCOPE_FIELDS)}
    for entry in basis:
        if not isinstance(entry,dict) or set(entry)!={'field','segment_id','part','quote'} or entry['field'] not in allowed: raise ValueError('依据字段无效')
        if entry['part']!='text' and not (entry['field']=='published_at' and entry['part']=='time_raw'): raise ValueError('依据位置无效')
        check_quote(entry['segment_id'],entry['part'],entry['quote']);supported.add(entry['field'])
    required={'source_type'}|{'scope.'+k for k,v in scope.items() if v is not None and v!=''}|{k for k in ('observed_at','published_at') if proposal[k] is not None}
    if not required<=supported: raise ValueError('非空来源、范围或日期缺少原文依据')
    row={'source_ref':candidate['url'],'title':candidate['title'] or candidate['url'],'source_type':proposal['source_type'],'access':'full_text','source_text':'\n\n'.join(s['text'] for s in candidate['segments']),'quote':proposal['quote'],'observation':proposal['observation'],'dimension':proposal['dimension'],'direction':proposal['direction'],'scope':scope,'observed_at':proposal['observed_at'],'published_at':proposal['published_at'],'retrieved_at':candidate['retrieved_at'],'origin_id':candidate['thread_key']}
    row['id']='r-'+hashlib.sha256(_json(row).encode()).hexdigest()[:20]
    return validate_evidence(row)


def _batch(batch):
    if not isinstance(batch,dict) or set(batch)!={'schema_version','proposals'} or type(batch['schema_version']) is not int or batch['schema_version']!=1 or not isinstance(batch['proposals'],list) or not 1<=len(batch['proposals'])<=100: raise ValueError('建议批次格式无效')
    ids=[p.get('id') if isinstance(p,dict) else None for p in batch['proposals']]
    if any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids): raise ValueError('建议 id 缺失或重复')
    return {p['id']:p for p in batch['proposals']}


def approve_proposals(case_dir: Path, batch: dict, accepted_ids: list[str]) -> dict:
    proposals=_batch(batch)
    if not isinstance(accepted_ids,list) or len(set(accepted_ids))!=len(accepted_ids) or any(i not in proposals for i in accepted_ids): raise ValueError('选中建议无效')
    if not accepted_ids: return {'receipt':None,'inserted':0,'evidence_ids':[]}
    candidates={(c['scan_id'],c['candidate_id']):c for c in load_candidates(case_dir)}
    rows=[]
    for identifier in accepted_ids:
        p=proposals[identifier];c=candidates.get((p.get('scan_id'),p.get('candidate_id')))
        if c is None: raise ValueError('找不到建议对应的扫描候选')
        rows.append(prepare_evidence(c,p))
    digest=hashlib.sha256(_json({'accepted_ids':accepted_ids,'rows':rows}).encode()).hexdigest()[:24]
    folder=Path(case_dir)/'reviews';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(digest+'.json');receipt={'status':'prepared','evidence_ids':[r['id'] for r in rows],'accepted_ids':accepted_ids}
    _write_json(path,receipt)
    count=import_evidence(case_dir,rows)
    try: _write_json(path,{**receipt,'status':'committed'})
    except OSError as exc: raise ValueError('证据已登记，但回执写入失败；请重试同一批次以恢复') from exc
    return {'receipt':str(path),'inserted':count,'evidence_ids':receipt['evidence_ids']}


def review_interactive(case_dir: Path, batch: dict, *, input_fn=input, output_fn=print) -> dict:
    proposals=_batch(batch)
    candidates={(c['scan_id'],c['candidate_id']):c for c in load_candidates(case_dir)}
    selected=[]
    for identifier,p in proposals.items():
        c=candidates.get((p.get('scan_id'),p.get('candidate_id')))
        output_fn('\n建议 '+identifier+'：'+_json(p))
        if c:
            output_fn('原文：'+_json([{'id':s['id'],'text':s['text'],'time_raw':s.get('time_raw')} for s in c['segments']]))
        else: output_fn('无法找到对应原文快照')
        while True:
            choice=input_fn('[a]接收 / [s]跳过 / [q]结束：').strip().lower()
            if choice=='q': return approve_proposals(case_dir,batch,selected)
            if choice=='s': break
            if choice=='a':
                if c is None: output_fn('无法接收：找不到候选');continue
                try: prepare_evidence(c,p)
                except ValueError as exc: output_fn('无法接收：'+str(exc));continue
                selected.append(identifier);break
            output_fn('请输入 a、s 或 q。')
    return approve_proposals(case_dir,batch,selected)
