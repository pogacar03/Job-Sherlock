"""Read forum threads and preserve separately attributable text segments."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from urllib.parse import parse_qs

from .browser_forums import maimai_post, nowcoder_comments
from .http_source import FetchError, parse_url


def thread_key(channel: str, url: str) -> str:
    parts, host = parse_url(url)
    routes = {
        'nowcoder': (('nowcoder.com',), r'/(?:feed/main/detail|discuss)/([a-zA-Z0-9]+)'),
        'xiaohongshu': (('xiaohongshu.com',), r'/(?:explore|search_result|note)/([a-fA-F0-9]+)'),
        'maimai': (('maimai.cn',), r'/community/gossip-detail/([0-9]+)'),
    }
    if channel not in routes:
        raise FetchError('unsupported_source', '不支持的论坛渠道')
    domains, pattern = routes[channel]
    match = re.fullmatch(pattern, parts.path.rstrip('/'))
    if not match or not any(host == d or host.endswith('.'+d) for d in domains):
        raise FetchError('unsupported_source', '不支持的论坛原帖链接')
    return channel + ':' + match.group(1)


def candidate_id_for(thread_key: str, title: str, segments: list[dict]) -> str:
    payload = json.dumps({'title': title, 'segments': segments}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return 'c-' + hashlib.sha256((thread_key+'\0'+payload).encode()).hexdigest()[:20]


def normalize_thread(channel: str, url: str, title: str, body_text: str, comments: list[dict], *, comment_status: str, published_at_raw: str | None, retrieved_at: str) -> dict:
    key = thread_key(channel, url)
    segments = [{'id':'body','kind':'body','text':body_text,'author':None,'author_url':None,'platform_id':None,'parent_id':None,'time_raw':published_at_raw}]
    for comment in comments:
        value = comment.get('text')
        if not isinstance(value, str) or not value.strip(): continue
        segments.append({'id':f'comment-{len(segments):04d}', 'kind':'comment', 'text':value, 'author':comment.get('author'), 'author_url':comment.get('author_url'), 'platform_id':comment.get('id'), 'parent_id':comment.get('parent_id'), 'time_raw':comment.get('time')})
    text = title + '\n' + body_text + ''.join('\n评论：'+s['text'] for s in segments[1:])
    return {'channel':channel,'url':url,'title':title,'text':text,'comments':comments,'comment_status':comment_status,'published_at':published_at_raw,'published_at_raw':published_at_raw,'retrieved_at':retrieved_at,'thread_key':key,'segments':segments,'candidate_id':candidate_id_for(key,title,segments),'errors':[],'scope_note':'正文与有限评论；作者身份、体验时间和部门归属待核实，评论数量不是独立证人数'}


def read_forum_thread(channel: str, url: str, *, executable: str, timeout: float, tool) -> dict:
    thread_key(channel, url)
    command = {'nowcoder':'detail','xiaohongshu':'note','maimai':'post'}[channel]
    details = maimai_post(executable,url,timeout,tool) if channel == 'maimai' else tool([executable,channel,command,url,'-f','json'],timeout)
    if channel == 'xiaohongshu':
        title = next((str(x.get('value') or '') for x in details if x.get('field') == 'title'), '')
        body = '\n'.join(str(x.get('value') or '') for x in details if x.get('field') in {'content','desc'})
    else:
        title = ''
        body = '\n'.join(str(x.get('content') or x.get('desc') or x.get('text') or '') for x in details)
    if not body.strip(): raise FetchError('unsupported_content', '没有识别到正文')
    comments = []; status = 'not_supported'; errors = []
    try:
        if channel == 'nowcoder':
            comments = nowcoder_comments(executable,url,timeout,tool); status = 'visible_only'
        elif channel == 'xiaohongshu':
            comments = tool([executable,channel,'comments',url,'--limit','20','--with-replies','true','-f','json'],timeout); status = 'bounded'
    except FetchError as exc:
        status = exc.status; errors.append({'stage':'comments','status':exc.status,'reason':str(exc)})
    result = normalize_thread(channel,url,title,body,comments,comment_status=status,published_at_raw=None,retrieved_at=datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    result['errors'] = errors
    return result
