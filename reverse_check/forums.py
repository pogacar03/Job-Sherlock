"""Read-only forum discovery. All matches remain unreviewed source material."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
import uuid

from .casebook import read_case, _write_json
from .collection import collect_sources, _VisibleText
from .http_source import public_fetch, FetchError, FetchedPage, parse_url
from .sources import load_sources
from .browser_forums import nowcoder_comments, xhs_search, maimai_search, maimai_post

DEFAULT_CHANNELS = ('xiaohongshu','nowcoder','maimai')

FOCUS = re.compile(r'加班|工时|工作强度|工作氛围|团队氛围|团队沟通|管理风格|领导|下班|周末|双休|单休|大小周|作息|内卷|职场|排期|值班|on.call|overtime|work.life|workload|management|culture|996|955', re.I)
CHANNELS = {
    'v2ex': ('native', '最近主题及首批回复；非全站历史搜索'),
    'nowcoder': ('opencli', '站内搜索、正文与当前可见评论'),
    'zhihu': ('opencli', '站内搜索与回答详情；不读取其他类型正文'),
    'xiaohongshu': ('opencli', '站内搜索、笔记正文及有限评论/楼中楼'),
    'maimai': ('browser', '动态搜索需登录；公开职言正文读取；评论尚未接通'),
    'offershow': ('manual', '仅工作氛围/强度讨论材料导入，不查询薪资'),
    'kanzhun': ('manual', '员工工作体验原文需用户读取'),
}
DOMAINS = {'v2ex':('v2ex.com',), 'nowcoder':('nowcoder.com',), 'zhihu':('zhihu.com',), 'xiaohongshu':('xiaohongshu.com','xhslink.com'), 'maimai':('maimai.cn',)}
_AUTO = object()


def channel_status(executable=_AUTO,all_channels=False):
    executable = shutil.which('opencli') if executable is _AUTO else executable
    keys=CHANNELS if all_channels else DEFAULT_CHANNELS
    return [{'id':key,'primary':key in DEFAULT_CHANNELS,'backend':CHANNELS[key][0],'status': 'available' if CHANNELS[key][0]=='native' else ('installed_unchecked' if executable else 'not_configured') if CHANNELS[key][0] in {'opencli','browser'} else 'manual_required', 'scope':CHANNELS[key][1]} for key in keys]


def _plain(value):
    if not isinstance(value,str):return ''
    parser=_VisibleText();parser.feed(value)
    return ' '.join(''.join(parser.parts).split())


def _rows(value):
    if isinstance(value,dict):
        if value.get('ok') is False or value.get('success') is False:raise FetchError('tool_error','平台命令返回失败')
        value=value.get('data',value.get('items'))
    if not isinstance(value,list) or not all(isinstance(v,dict) for v in value):
        raise FetchError('invalid_response','平台返回的JSON不是记录数组')
    return value


def _tool(args, timeout):
    # No shell, no credential extraction. External output is bounded and never echoed.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:r=subprocess.run(args,stdout=out,stderr=err,timeout=timeout,check=False)
        except subprocess.TimeoutExpired as exc:raise FetchError('timeout','平台命令超时') from exc
        except OSError as exc:raise FetchError('not_configured','无法启动OpenCLI') from exc
        if out.tell()>2000000:raise FetchError('too_large','平台输出超过2MB')
        if r.returncode:
            out.seek(0)
            try:
                failure=json.load(out)
                code=failure.get('error',{}).get('code') if isinstance(failure,dict) else None
            except (ValueError,UnicodeError,AttributeError):code=None
            if code=='EMPTY_RESULT':return []
            states={'AUTH_REQUIRED':'login_required','RATE_LIMITED':'rate_limited','TIMEOUT':'timeout','SECURITY_BLOCK':'blocked','BROWSER_NOT_CONNECTED':'not_configured'}
            if code in states:raise FetchError(states[code],'OpenCLI状态：'+code+'；请检查平台登录或访问限制')
            if isinstance(code,str) and re.fullmatch(r'[A-Z_]{2,60}',code):
                raise FetchError('tool_error','OpenCLI错误代码：'+code)
            err.seek(0);msg=err.read(4000).decode('utf-8',errors='replace').casefold()
            status='login_required' if any(s in msg for s in ('login','auth','登录')) else 'blocked' if any(s in msg for s in ('captcha','risk','验证码','安全限制')) else 'tool_error'
            raise FetchError(status,'OpenCLI读取失败；请在终端运行opencli doctor检查连接和登录')
        out.seek(0)
        try:
            payload=json.load(out)
            if args[1:3] in (['browser','open'],['browser','close'],['browser','click']) or args[1:4]==['browser','tab','select'] or args[1:5]==['browser','chrome','call','tabs.remove']:
                if isinstance(payload,dict) and payload.get('ok') is True:return [payload.get('data')]
            return _rows(payload)
        except (ValueError,UnicodeError) as exc:raise FetchError('invalid_response','OpenCLI未返回可识别的JSON') from exc


def _allowed(channel,url):
    try:_,host=parse_url(url)
    except FetchError:return False
    return any(host==d or host.endswith('.'+d) for d in DOMAINS[channel])


def scan_forums(case_dir,channels=None,queries=None,limit=5,timeout=20,topic_ids=None,fetch=None,executable=_AUTO,tool=None):
    case=read_case(case_dir)
    channels=list(dict.fromkeys(channels or DEFAULT_CHANNELS))
    if any(c not in CHANNELS for c in channels):raise ValueError('未知论坛渠道')
    if type(limit) is not int or not 1<=limit<=20:raise ValueError('limit需要1–20')
    if isinstance(timeout,bool) or not isinstance(timeout,(float,int)) or not math.isfinite(timeout) or not 0<timeout<=120:raise ValueError('timeout需要大于0且不超过120秒')
    topic_ids=topic_ids or []
    if len(topic_ids)>20 or any(not re.fullmatch(r'[1-9][0-9]{0,11}',str(v)) for v in topic_ids):raise ValueError('topic-id需要正整数，最多20个')
    if queries is not None and (not isinstance(queries,list) or not 1<=len(queries)<=6 or any(not isinstance(q,str) or not q.strip() or len(q)>300 for q in queries)):
        raise ValueError('query需要1–6条非空短文本')
    executable=shutil.which('opencli') if executable is _AUTO else executable
    fetch=fetch or public_fetch;tool=tool or _tool
    terms=[case['company'],*case['company_aliases']]
    department=case.get('department') or ''
    acronyms=re.findall(r'\b[A-Z]{2,8}\b',department)
    team=' '.join(acronyms) if acronyms else department
    seed=' '.join(f'{case["company"]} {team}'.split())
    queries=queries or [seed,seed+' 加班',seed+' 氛围']
    root=Path(case_dir)/'scans'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8])
    (root/'raw').mkdir(parents=True)
    documents=[];leads=[];results=[];counter=0
    def save(value):
        nonlocal counter
        counter+=1;_write_json(root/'raw'/f'{counter:04}.json',value)
    def get(url):
        def allow_url(target):
            if not _allowed('v2ex',target):raise FetchError('unsupported_source','跳转离开V2EX，未读取为论坛材料')
        page=fetch(url,timeout=timeout,max_bytes=2000000,allow_url=allow_url)
        allow_url(page.final_url)
        # Retain exact API bytes, including responses which cannot be parsed.
        nonlocal counter
        counter+=1;(root/'raw'/f'{counter:04}.body').write_bytes(page.body)
        _write_json(root/'raw'/f'{counter:04}.meta.json',{'url':url,'final_url':page.final_url,'http_status':page.status_code,'content_type':page.content_type})
        if page.status_code!=200:
            raise FetchError({401:'login_required',403:'blocked',429:'rate_limited'}.get(page.status_code,'http_error'),'论坛接口返回HTTP '+str(page.status_code))
        try:return _rows(json.loads(page.body))
        except (ValueError,UnicodeError) as exc:raise FetchError('invalid_response','论坛接口没有返回有效JSON记录') from exc
    def relevant(text):return any(t.casefold() in text.casefold() for t in terms) and bool(FOCUS.search(text))
    for channel in channels:
        backend,scope=CHANNELS[channel]
        row={'id':channel,'status':'no_results','scope':scope,'queries':queries if backend in {'opencli','browser'} else [],'checked':0,'matched':0,'errors':[]}
        start=len(documents)
        try:
            if backend=='manual':row['status']='manual_required'
            elif backend in {'opencli','browser'} and not executable:row['status']='not_configured'
            elif backend=='native':
                topics=[]
                if topic_ids:
                    for tid in topic_ids:topics.extend(get('https://v2ex.com/api/topics/show.json?id='+str(tid)))
                else:topics=get('https://v2ex.com/api/topics/latest.json')
                candidates=0
                for topic in topics[:100]:
                    text=_plain(topic.get('title',''))+'\n'+_plain(topic.get('content',''))
                    row['checked']+=1
                    if not any(t.casefold() in text.casefold() for t in terms):continue
                    if re.search('薪资|工资|薪水',text) and not FOCUS.search(text):continue
                    tid=topic.get('id')
                    if type(tid) is not int or tid<=0:continue
                    if candidates>=limit:break
                    candidates+=1
                    try:
                        replies=get(f'https://v2ex.com/api/replies/show.json?topic_id={tid}&page=1&page_size=100')
                        for reply in replies[:100]:text+='\n回复 '+str(reply.get('id',''))+'：'+_plain(reply.get('content',''))
                    except FetchError as exc:row['errors'].append({'stage':'replies','status':exc.status,'topic_id':tid})
                    if relevant(text):documents.append({'channel':channel,'url':f'https://www.v2ex.com/t/{tid}','title':topic.get('title',''),'text':text,'published_at':topic.get('created'),'scope_note':'原帖与首批至多100条回复；作者身份和部门归属未验证'})
                    if len(documents)-start>=limit:break
            else:
                seen=set()
                for query in queries:
                    args=[executable,channel,'search',query,'--limit',str(limit),'-f','json']
                    if channel=='zhihu':args.extend(['--type','answer'])
                    try:rows=maimai_search(executable,query,limit,timeout,tool) if channel=='maimai' else tool(args,timeout)
                    except FetchError as exc:
                        if channel!='xiaohongshu' or exc.status!='timeout':raise
                        rows=xhs_search(executable,query,limit,timeout,tool)
                    save(rows)
                    for candidate in rows[:limit]:
                        url=candidate.get('url','')
                        if not isinstance(url,str) or url in seen or not _allowed(channel,url):continue
                        seen.add(url);row['checked']+=1
                        if channel=='zhihu' and not re.search(r'/answer/[0-9]+',url):continue
                        command={'nowcoder':'detail','zhihu':'answer-detail','xiaohongshu':'note','maimai':'post'}[channel]
                        try:
                            details=maimai_post(executable,url,timeout,tool) if channel=='maimai' else tool([executable,channel,command,url,'-f','json'],timeout)
                            save(details)
                            if channel=='xiaohongshu':
                                text='\n'.join(_plain(str(v.get('value') or '')) for v in details if v.get('field') in {'title','content','desc'})
                            else:
                                text='\n'.join(_plain(str(v.get('content') or v.get('desc') or v.get('text') or '')) for v in details)
                            title=str(candidate.get('title') or '')
                            comments=[];comment_status='not_read'
                            if text:
                                try:
                                    if channel=='nowcoder':comments=nowcoder_comments(executable,url,timeout,tool)
                                    elif channel=='xiaohongshu':comments=tool([executable,channel,'comments',url,'--limit','20','--with-replies','true','-f','json'],timeout)
                                    comment_status='visible_only' if channel=='nowcoder' else 'bounded' if channel=='xiaohongshu' else 'not_supported'
                                    save({'stage':'comments','url':url,'coverage':comment_status,'comments':comments})
                                except FetchError as exc:
                                    comment_status=exc.status
                                    row['errors'].append({'stage':'comments','status':exc.status,'reason':str(exc)})
                            thread=title+'\n'+text
                            for comment in comments:
                                body=comment.get('text','')
                                if isinstance(body,str) and body.strip():thread+='\n评论：'+_plain(body)
                            record={'channel':channel,'url':url,'title':title,'text':thread,'comments':comments,'comment_status':comment_status,'published_at':candidate.get('time') or candidate.get('published_at'),'scope_note':'正文与有限评论；作者身份、体验时间和部门归属待核实，评论数量不是独立证人数'}
                            if text and relevant(thread):documents.append(record)
                            elif text and any(t.casefold() in thread.casefold() for t in terms):leads.append(record)
                        except FetchError as exc:row['errors'].append({'stage':'detail','status':exc.status,'reason':str(exc)})
                        if len(documents)-start>=limit:break
                    if len(documents)-start>=limit:break
            row['matched']=len(documents)-start
            if row['matched']:row['status']='partial' if row['errors'] else 'ok'
            elif row['errors']:row['status']='partial'
            elif any(lead['channel']==channel for lead in leads):row['status']='leads_only'
        except FetchError as exc:
            row['matched']=len(documents)-start
            row['status']='partial' if row['matched'] else exc.status
            row['errors'].append({'stage':'discovery','status':exc.status,'reason':str(exc)})
        results.append(row)
        row['leads']=sum(lead['channel']==channel for lead in leads)
    collection=None
    if documents:
        cache={d['url']:d for d in documents}
        registry=load_sources()
        # Only cached, successfully read platform documents are passed through this policy.
        registry={'schema_version':1,'sources':[{**s,'mode':'public'} for s in registry['sources']]}
        def cached(url,**kwargs):return FetchedPage(url,200,'text/plain; charset=utf-8',cache[url]['text'].encode())
        collection=collect_sources(case_dir,list(cache),registry=registry,fetch=cached)
    _write_json(root/'run.json',{'schema_version':1,'focus':['workload','atmosphere'],'channels':results,'documents':documents,'leads':leads,'collection':str(collection.relative_to(case_dir)) if collection else None,'note':'全部材料待审阅；公司命中不代表部门归属；失败或未配置不代表没有问题'})
    return root


def scan_summary(case_dir):
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((Path(case_dir)/'scans').glob('*/run.json'))]
