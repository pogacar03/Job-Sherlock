"""Build search phrases and label textual matches without asserting scope."""
import re
import unicodedata


def _norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text or '')).casefold()


def build_forum_queries(case: dict, search_terms: list[str] | None = None) -> list[str]:
    if search_terms is not None and (not isinstance(search_terms,list) or len(search_terms)>3 or any(not isinstance(s,str) or not s.strip() or len(s)>80 for s in search_terms)):
        raise ValueError('search-term 最多3条非空文本，每条最多80字符')
    company = ' '.join(case['company'].split())
    department = ' '.join((case.get('department') or '').split())
    seed = ' '.join(x for x in (company,department) if x)
    queries = [seed, seed+' 加班', seed+' 氛围'] + [company+' '+' '.join(term.split()) for term in (search_terms or [])]
    unique = []; seen = set()
    for item in queries:
        key = _norm(item)
        if key not in seen: unique.append(item); seen.add(key)
    return unique


def match_hint(case: dict, candidate: dict, search_terms: list[str] | None = None) -> str:
    text = _norm(candidate.get('title', '') + ' ' + ' '.join(s.get('text','') for s in candidate.get('segments', [])))
    names = [case.get('company'), *case.get('company_aliases', [])]
    if not any(_norm(name) and _norm(name) in text for name in names): return 'unrelated'
    department = _norm(case.get('department'))
    if department and department in text: return 'department_mention'
    if any(_norm(term) and _norm(term) in text for term in (search_terms or [])): return 'search_hint'
    return 'company_only'
