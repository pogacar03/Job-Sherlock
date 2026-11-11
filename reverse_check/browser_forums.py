"""Read visible forum DOM through the user's connected OpenCLI browser."""
import json
from urllib.parse import quote, urlsplit, parse_qs
import re
import uuid

from .http_source import FetchError, parse_url


def _same_page(actual,expected):
    try:
        a,host=parse_url(actual); b,wanted=parse_url(expected)
        return host==wanted and a.path.rstrip('/')==b.path.rstrip('/')
    except FetchError:return False


def signed_note_url(row):
    for url in row.get('urls',[]) + ([row['url']] if isinstance(row.get('url'),str) else []):
        try:
            parts,host=parse_url(url)
            if host=='www.xiaohongshu.com' and re.fullmatch(r'/(?:explore|search_result|note)/[a-fA-F0-9]+',parts.path) and parse_qs(parts.query).get('xsec_token'):
                return url
        except (FetchError,TypeError):continue
    return None


def nowcoder_comments(executable,url,timeout,tool):
    session='job-sherlock-comments-'+uuid.uuid4().hex[:10]
    script=r'''(async () => {
      const ready=()=>document.querySelector('.comment-box') || (/暂无评论/.test(document.body?.innerText||'') && !/加载中/.test(document.body?.innerText||''));
      for(let i=0;i<20&&!ready();i++) await new Promise(r=>setTimeout(r,250));
      const rows=[{kind:'page',url:location.href,ready:!!ready(),coverage:'visible_only'}];
      const nodes=Array.from(document.querySelectorAll('.comment-box')).slice(0,40);
      for(const e of nodes) {
        const text=e.querySelector('.comment-rich-text .vue-ellipsis-js-content, .comment-rich-text')?.innerText?.trim();
        if(!text) continue;
        const parent=e.parentElement?.closest('.comment-box');
        rows.push({id:e.getAttribute('data-contentid'),text,
          author:e.querySelector('.user-nickname')?.innerText?.trim()||null,
          author_url:e.querySelector('.user-nickname a')?.href||null,
          parent_id:parent?.getAttribute('data-contentid')||null,
          time:e.querySelector('time, .comment-time, .create-time')?.innerText?.trim()||null});
      }
      return rows;
    })()'''
    try:
        tool([executable,'browser','open',url,'--session',session],timeout)
        rows=tool([executable,'browser','eval',script,'--session',session],timeout)
        if not rows or rows[0].get('kind')!='page':raise FetchError('invalid_response','评论页没有返回来源信息')
        if not _same_page(rows[0].get('url',''),url):raise FetchError('unsupported_source','评论页跳转后与原帖不一致')
        if not rows[0].get('ready'):raise FetchError('timeout','牛客评论尚未加载；不能视为没有评论')
        return [r for r in rows[1:] if isinstance(r.get('text'),str) and r['text'].strip()][:40]
    finally:
        try:tool([executable,'browser','close','--session',session],min(timeout,5))
        except FetchError:pass


def xhs_search(executable,query,limit,timeout,tool):
    session='job-sherlock-search-'+uuid.uuid4().hex[:10]
    url='https://www.xiaohongshu.com/search_result?keyword='+quote(query)+'&source=web_explore_feed'
    script=r'''(async () => {
      const state=()=>{
        const t=document.body?.innerText||'';
        if(/登录后查看搜索结果/.test(t)||document.querySelector('#login-btn')) return 'login_required';
        if(/请求太频繁|访问频次异常|安全限制/.test(t)||location.pathname.includes('/website-login/')) return 'blocked';
        return document.querySelector('section.note-item')?'ready':null;
      };
      for(let i=0;i<40&&!state();i++) await new Promise(r=>setTimeout(r,250));
      const rows=[{kind:'page',url:location.href,status:state()||'timeout'}];
      for(const e of Array.from(document.querySelectorAll('section.note-item')).slice(0,MAX_ROWS)) {
        const title=e.querySelector('.title')?.innerText?.trim();
        if(title) rows.push({title,urls:Array.from(e.querySelectorAll('a[href]')).map(a=>a.href)});
      }
      return rows;
    })()'''.replace('MAX_ROWS',str(limit))
    try:
        tool([executable,'browser','open',url,'--session',session],timeout)
        rows=tool([executable,'browser','eval',script,'--session',session],timeout)
        if not rows or rows[0].get('kind')!='page':raise FetchError('invalid_response','小红书搜索页没有返回来源信息')
        actual=rows[0].get('url','')
        if not _same_page(actual,url) or urlsplit(actual).query.find('keyword=')<0:
            raise FetchError('unsupported_source','小红书搜索跳转到其他页面')
        from urllib.parse import parse_qs
        if parse_qs(urlsplit(actual).query).get('keyword')!=[query]:raise FetchError('invalid_response','搜索页面关键词与目标不一致')
        status=rows[0].get('status')
        if status!='ready':raise FetchError(status if status in {'login_required','blocked','timeout'} else 'invalid_response','小红书搜索页尚不可读取')
        results=[{'title':row.get('title',''),'url':signed_note_url(row)} for row in rows[1:]]
        results=[row for row in results if row['url']]
        if len(rows)>1 and not results:raise FetchError('invalid_response','结果卡片尚未返回可读取的笔记链接')
        return results
    finally:
        try:tool([executable,'browser','close','--session',session],min(timeout,5))
        except FetchError:pass


def maimai_search(executable,query,limit,timeout,tool):
    """Read the native 职言交流 results and follow actual card navigation."""
    import time
    session='job-sherlock-maimai-search-'+uuid.uuid4().hex[:10]
    url='https://maimai.cn/web/search_center?highlight=true&query='+quote(query)+'&type=gossip'
    script=r'''(async () => {
      for(let i=0;i<40&&!document.querySelector('.list-group-item')&&!location.pathname.includes('login');i++)await new Promise(r=>setTimeout(r,250));
      return [{kind:'page',url:location.href,empty:/暂无相关|没有找到相关|无搜索结果/.test(document.body?.innerText||''),
        cards:Array.from(document.querySelectorAll('li.list-group-item')).slice(0,MAX_ROWS).map((e,index)=>({index,title:e.querySelector('.m-b-5')?.innerText?.trim()||'',summary:e.innerText.slice(0,1000)}))}];
    })()'''.replace('MAX_ROWS',str(limit))
    tab_args=['browser','chrome','call','tabs.query',json.dumps([{'url':'https://maimai.cn/*'}])]
    created=[]
    try:
        opened_page=tool([executable,'browser','open',url,'--session',session],timeout)
        target_page=opened_page[0].get('page') if opened_page and isinstance(opened_page[0],dict) else None
        rows=tool([executable,'browser','eval',script,'--session',session],timeout)
        if not rows or rows[0].get('kind')!='page':raise FetchError('invalid_response','脉脉搜索没有返回来源信息')
        actual=rows[0].get('url','');parts,host=parse_url(actual)
        if host=='maimai.cn' and 'login' in parts.path:raise FetchError('login_required','脉脉职言搜索需要登录')
        if not _same_page(actual,url):raise FetchError('unsupported_source','脉脉职言搜索跳转到其他页面')
        if parse_qs(parts.query).get('query')!=[query] or parse_qs(parts.query).get('type')!=['gossip']:raise FetchError('invalid_response','脉脉搜索词或职言标签不一致')
        cards=rows[0].get('cards',[])
        if not cards and not rows[0].get('empty'):raise FetchError('unsupported_content','尚未识别脉脉职言结果布局，不能当作没有结果')
        before=tool([executable,*tab_args],timeout)
        parents=[t for t in before if _same_page(t.get('url',''),url) and parse_qs(urlsplit(t.get('url','')).query).get('query')==[query]]
        parents.sort(key=lambda t:t.get('lastAccessed',0),reverse=True)
        if not parents or (len(parents)>1 and parents[0].get('lastAccessed',0)==parents[1].get('lastAccessed',0)):
            raise FetchError('unsupported_content','不能唯一识别本次职言搜索标签页')
        parent_ids={parents[0]['id']}
        known={t['id'] for t in before}
        results=[]
        for card in cards[:limit]:
            index=card.get('index')
            if type(index) is not int or not 0<=index<20:continue
            if target_page:tool([executable,'browser','tab','select',target_page,'--session',session],timeout)
            tool([executable,'browser','click',f'li.list-group-item:nth-child({index+1})','--session',session,'--window','foreground'],timeout)
            found=[]
            for attempt in range(8):
                tabs=tool([executable,*tab_args],timeout)
                opened=[t for t in tabs if t.get('id') not in known and t.get('openerTabId') in parent_ids]
                if len(opened)>1:raise FetchError('unsupported_content','卡片打开了多个标签页，未自动选择或关闭')
                found=[t for t in opened if isinstance(t.get('url'),str) and t['url'].startswith('https://maimai.cn/community/gossip-detail/')]
                for t in opened:
                    if t['id'] not in created:created.append(t['id'])
                if found:break
                time.sleep(.2)
            if len(found)!=1:raise FetchError('unsupported_content','没有唯一确认职言卡片打开的原帖，保留搜索范围未知')
            tab=found[0];known.add(tab['id'])
            ref=tab.get('url','');target,host=parse_url(ref)
            if host!='maimai.cn' or not target.path.startswith('/community/gossip-detail/'):
                raise FetchError('unsupported_source','职言卡片未打开可验证的脉脉原帖')
            results.append({'url':ref,'title':card.get('title',''),'search_summary':card.get('summary','')})
        return results
    finally:
        try:tool([executable,'browser','close','--session',session],min(timeout,5))
        except FetchError:pass
        for tab_id in created:
            try:tool([executable,'browser','chrome','call','tabs.remove',json.dumps([tab_id])],min(timeout,5))
            except FetchError:pass


def maimai_post(executable,url,timeout,tool):
    session='job-sherlock-maimai-post-'+uuid.uuid4().hex[:10]
    script=r'''(async () => {
      const body=()=>document.querySelector('main .line-clamp-none.whitespace-pre-wrap');
      for(let i=0;i<24&&!body()&&!location.pathname.includes('login');i++)await new Promise(r=>setTimeout(r,250));
      return [{kind:'page',url:location.href,content:body()?.innerText?.trim()||''}];
    })()'''
    try:
        tool([executable,'browser','open',url,'--session',session],timeout)
        rows=tool([executable,'browser','eval',script,'--session',session],timeout)
        if not rows:raise FetchError('invalid_response','脉脉帖子没有返回数据')
        actual=rows[0].get('url','')
        parts,host=parse_url(actual)
        if host=='maimai.cn' and 'login' in parts.path:raise FetchError('login_required','脉脉帖子需要登录')
        if not _same_page(actual,url):raise FetchError('unsupported_source','脉脉帖子跳转与原文不一致')
        text=rows[0].get('content','')
        if not isinstance(text,str) or len(text.strip())<20:raise FetchError('unsupported_content','没有识别到脉脉正文，不使用推荐区或页面导航充当原文')
        return [{'content':text}]
    finally:
        try:tool([executable,'browser','close','--session',session],min(timeout,5))
        except FetchError:pass
