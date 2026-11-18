"""Render read-only candidate cards without scripts or remote assets."""
from html import escape
from pathlib import Path
from .review import load_candidates
from .casebook import read_case
from .queries import platform_usage_hint


def write_review_cards(case_dir: Path, out: Path, *, force=False) -> Path:
    candidates=load_candidates(case_dir)
    case=read_case(case_dir)
    out=Path(out);path=out/'cards.html'
    if path.exists() and not force: raise ValueError('候选卡片已存在；使用 --force 覆盖')
    e=lambda value:escape(str(value if value is not None else '未知'),quote=True)
    cards=[]
    for c in candidates:
        segments=''.join('<section><h3>'+e(s['kind'])+' · '+e(s['id'])+'</h3><p>作者：'+e(s.get('author'))+'；时间原文：'+e(s.get('time_raw'))+'</p><pre>'+e(s['text'])+'</pre></section>' for s in c['segments'])
        warning='<p>可能是在使用该平台，而非在该公司工作；需核对原文，不能据此认定雇主。</p>' if platform_usage_hint(case,c) else ''
        cards.append('<article><h2>'+e(c['title'] or '无标题')+'</h2><p>扫描 '+e(c['scan_id'])+' · 候选 '+e(c['candidate_id'])+' · 匹配提示 '+e(c.get('match_hint'))+' · 评论范围 '+e(c.get('comment_status'))+'</p><p>'+e(c.get('scope_note'))+'</p>'+warning+'<a rel="noopener noreferrer" href="'+e(c['url'])+'">打开原帖</a>'+segments+'</article>')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>待审阅候选</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}article{border:1px solid #ccc;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{border-top:1px solid #ddd}</style><h1>待审阅候选</h1><p>共 '+str(len(cards))+' 条；这些材料尚未作为证据，匹配提示不代表已确认团队。</p>'+''.join(cards)+'</html>'
    out.mkdir(parents=True,exist_ok=True);path.write_text(page,encoding='utf-8');return path
