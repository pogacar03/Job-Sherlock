"""Concurrent collection of known URLs, kept separate from reviewed evidence."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.message import Message
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import time
import uuid

from .casebook import SCOPE_FIELDS, _write_json, read_case
from .http_source import FetchError, parse_url, public_fetch
from .sources import canonical_url, load_sources, source_for_url


STATUS_LABELS = {
    'retrieved':'原文已保存，待审阅','manual_required':'需要宿主或用户读取',
    'blocked':'访问被拦截','login_required':'需要登录','rate_limited':'请求被限流',
    'not_found':'原文页面不存在或已删除','http_error':'HTTP错误','timeout':'请求超时',
    'network_error':'网络错误','unsupported_content':'不支持的正文格式',
    'empty':'没有足够可见文本','too_large':'正文超过上限','unsafe_url':'URL或地址不适合公开采集',
    'redirect_limit':'重定向次数超限','unsupported_source':'注册表未包含该来源',
}


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=[];self.in_title=False;self.title=[];self.parts=[]

    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','noscript','template','svg'}:self.skip.append(tag)
        if tag=='title':self.in_title=True
        if tag in {'p','div','section','article','br','li','h1','h2','h3','tr'} and not self.skip:self.parts.append('\n')

    def handle_endtag(self,tag):
        if self.skip and tag==self.skip[-1]:self.skip.pop()
        if tag=='title':self.in_title=False
        if tag in {'p','div','article','li','h1','h2','h3'} and not self.skip:self.parts.append('\n')

    def handle_data(self,data):
        if self.skip:return
        if self.in_title:self.title.append(data)
        else:self.parts.append(data)


def _extract(page):
    header=Message();header['content-type']=page.content_type
    mime=header.get_content_type()
    if mime not in {'text/html','application/xhtml+xml','text/plain'}:
        return '', '', 'unsupported_content'
    try:text=page.body.decode(header.get_content_charset() or 'utf-8')
    except (LookupError,UnicodeError):return '', '', 'unsupported_content'
    if mime=='text/plain':return '',text.strip(),None
    parser=_VisibleText()
    try:parser.feed(text)
    except (ValueError,RecursionError):return '', '', 'unsupported_content'
    title=' '.join(''.join(parser.title).split())
    visible='\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip())
    return title,visible,None


def _classify(page,source,title,text,error):
    code=page.status_code
    if code==401:return 'login_required'
    if code==403:return 'blocked'
    if code==429:return 'rate_limited'
    if code in {404,410}:return 'not_found'
    if not 200<=code<300:return 'http_error'
    if error:return error
    for key,status in [('blocked_titles','blocked'),('login_titles','login_required'),('missing_titles','not_found')]:
        if any(marker.casefold() in title.casefold() for marker in source[key]):return status
    if len(text.strip())<30:return 'empty'
    return 'retrieved'


def collect_sources(case_dir,urls,registry=None,workers=4,timeout=10,max_bytes=1000000,fetch=None):
    case=read_case(case_dir)
    if type(workers) is not int or not 1<=workers<=16:raise ValueError('workers需要1–16的整数')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 0<timeout<=120:
        raise ValueError('timeout需要大于0且不超过120秒')
    if type(max_bytes) is not int or not 1<=max_bytes<=10000000:raise ValueError('max_bytes需要1–10000000')
    if not isinstance(urls,list) or not 1<=len(urls)<=100 or not all(isinstance(u,str) and u for u in urls):
        raise ValueError('urls需要1–100个原文URL的JSON数组')
    # Reject malformed/credential URLs before creating logs or making requests.
    try:
        for url in urls:parse_url(url)
    except FetchError as exc:raise ValueError('URL输入无效：'+str(exc)) from exc
    by_key={}
    for url in urls:by_key.setdefault(canonical_url(url),url)
    unique=list(by_key.values())
    registry=registry or load_sources()
    def allow_url(url):
        source=source_for_url(registry,url)
        if not source:raise FetchError('unsupported_source','跳转目标不在来源注册表中',final_url=url)
        if source['mode']=='manual':raise FetchError('manual_required','跳转目标需要宿主或用户读取',final_url=url)
    if fetch is None:
        def fetch(url,timeout,max_bytes):
            return public_fetch(url,timeout,max_bytes,allow_url=allow_url)
    stamp=datetime.now(timezone.utc)
    run_id=stamp.strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
    retrieved_at=stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()

    def task(index,url):
        start=time.monotonic();source=source_for_url(registry,url)
        result={'id':'c-'+hashlib.sha256(url.encode()).hexdigest()[:20],
                'requested_url':url,'final_url':url,'source_id':source['id'] if source else None,'requested_source_id':source['id'] if source else None,
                'status':'unsupported_source','http_status':None,'reason':'', 'title':'','source_text':'',
                'retrieved_at':retrieved_at,'content_sha256':None,'snapshot':None,'mentions':{},'fetch_attempted':False}
        body=None
        if source and source['mode']=='manual':result['status']='manual_required'
        elif source:
            result['fetch_attempted']=True
            try:
                page=fetch(url,timeout=timeout,max_bytes=max_bytes)
                body=page.body
                result['final_url']=page.final_url;result['http_status']=page.status_code
                result['content_type']=page.content_type
                title,text,error=_extract(page)
                final_source=source_for_url(registry,page.final_url)
                result['source_id']=final_source['id'] if final_source else None
                status='unsupported_source' if not final_source else 'manual_required' if final_source['mode']=='manual' else _classify(page,final_source,title,text,error)
                result.update(title=title,source_text=text,status=status)
                result['content_sha256']=hashlib.sha256(body).hexdigest()
                # Mentions are text matches only, never assignments of department scope.
                result['mentions']={field:bool(case.get(field) and case[field].casefold() in text.casefold()) for field in SCOPE_FIELDS}
            except FetchError as exc:
                result.update(status=exc.status,http_status=exc.http_status,final_url=exc.final_url or url,reason=str(exc))
                if exc.http_status in {401,403,404,410,429}:
                    result['status']={401:'login_required',403:'blocked',404:'not_found',410:'not_found',429:'rate_limited'}[exc.http_status]
                elif exc.http_status is not None and not 200<=exc.http_status<300 and exc.status not in {'redirect_limit','unsafe_url','manual_required','unsupported_source'}:
                    result['status']='http_error'
            except (OSError,UnicodeError,ValueError) as exc:
                result.update(status='network_error',reason=str(exc)[:400])
        result['reason']=result['reason'] or STATUS_LABELS[result['status']]
        result['elapsed_ms']=round((time.monotonic()-start)*1000)
        return index,result,body

    completed=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(task,i,url) for i,url in enumerate(unique)]
        for future in as_completed(futures):completed.append(future.result())
    completed.sort(key=lambda item:item[0])
    run=Path(case_dir)/'collections'/run_id
    run.mkdir(parents=True,exist_ok=False)
    (run/'snapshots').mkdir()
    rows=[];drafts=[]
    for _,row,body in completed:
        if body is not None:
            row['snapshot']='snapshots/'+row['id']+'.body'
            (run/row['snapshot']).write_bytes(body)
        rows.append(row)
        if row['status']=='retrieved':
            identifier='c-'+hashlib.sha256((row['final_url']+'\0'+row['content_sha256']).encode()).hexdigest()[:20]
            drafts.append({'id':identifier,'source_ref':row['final_url'],'title':row['title'] or row['final_url'],
                           'source_type':None,'access':'full_text','source_text':row['source_text'],
                           'quote':None,'observation':None,'dimension':None,'direction':None,
                           'scope':{field:None for field in SCOPE_FIELDS},'observed_at':None,
                           'published_at':None,'retrieved_at':retrieved_at,'origin_id':None})
    _write_json(run/'sources.json',registry)
    _write_json(run/'evidence-drafts.json',drafts)
    _write_json(run/'run.json',{'schema_version':1,'run_id':run_id,'started_at':stamp.isoformat(),
                              'case_as_of':case['as_of'],'input_count':len(urls),'input_urls':urls,'unique_count':len(unique),
                              'registry_sha256':hashlib.sha256((run/'sources.json').read_bytes()).hexdigest(),
                              'options':{'workers':workers,'timeout':timeout,'max_bytes':max_bytes},'results':rows})
    return run


def collection_summary(case_dir):
    result={'runs':0,'total_urls':0,'fetch_attempts':0,'statuses':{},'results':[]}
    for path in sorted((Path(case_dir)/'collections').glob('*/run.json')):
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('results'),list):
            raise ValueError('采集记录格式无效：'+str(path))
        result['runs']+=1
        for row in data['results']:
            if not isinstance(row,dict) or row.get('status') not in STATUS_LABELS or not all(isinstance(row.get(k),str) for k in ('requested_url','final_url','reason','retrieved_at','title')) or not {'source_id','http_status','fetch_attempted'}<=row.keys() or type(row['fetch_attempted']) is not bool:
                raise ValueError('采集结果字段无效：'+str(path))
            result['statuses'][row['status']]=result['statuses'].get(row['status'],0)+1
            result['results'].append({**{k:row[k] for k in ('requested_url','final_url','status','reason','retrieved_at','title','http_status','source_id')},'requested_source_id':row.get('requested_source_id',row['source_id'])})
            result['total_urls']+=1
            result['fetch_attempts']+=int(row['fetch_attempted'])
    return result
