"""Run with python3 -m reverse_check; intentionally no runtime dependencies."""

import argparse
from importlib.resources import files
import json
from pathlib import Path
import sys

from .analysis import build_plan
from .casebook import create_case, import_evidence, read_case
from .report import write_report
from .collection import collect_sources
from .sources import load_sources


def main(argv=None):
    parser = argparse.ArgumentParser(description='求职侦探：公司与部门反向背调证据工具')
    subs = parser.add_subparsers(dest='command', required=True)
    init = subs.add_parser('init', help='创建一个调查案例')
    init.add_argument('case_dir',type=Path)
    init.add_argument('--company',required=True)
    for field in ('department','business-unit','city','role'):
        init.add_argument('--'+field)
    init.add_argument('--company-alias',action='append',default=[])
    init.add_argument('--as-of')
    init.add_argument('--lookback-days',type=int,default=365)
    init.add_argument('--demo',action='store_true',help='标记虚构演练案例；所有报告显示演示提示')
    plan = subs.add_parser('plan', help='生成检索计划和面试核实问题')
    plan.add_argument('case_dir',type=Path)
    plan.add_argument('--force',action='store_true')
    plan.add_argument('--sources',type=Path,help='本地来源注册表JSON')
    plan.add_argument('--source',action='append',help='限制来源id，可重复')
    sources = subs.add_parser('sources',help='显示本地来源注册表')
    sources.add_argument('--file',type=Path)
    collector = subs.add_parser('collect',help='并发读取已找到的公开原文URL，保存待审阅草稿')
    collector.add_argument('case_dir',type=Path)
    collector.add_argument('--urls',type=Path,required=True,help='1–100个URL的JSON数组')
    collector.add_argument('--sources',type=Path)
    collector.add_argument('--workers',type=int,default=4)
    collector.add_argument('--timeout',type=float,default=10)
    collector.add_argument('--max-bytes',type=int,default=1000000)
    importer = subs.add_parser('import',help='校验后整批导入证据 JSON 数组')
    importer.add_argument('case_dir',type=Path)
    importer.add_argument('--file',type=Path,required=True)
    report = subs.add_parser('report',help='生成 HTML、Markdown、JSON 报告')
    report.add_argument('case_dir',type=Path)
    report.add_argument('--out',type=Path)
    report.add_argument('--force',action='store_true')
    demo = subs.add_parser('demo', help='运行虚构材料的完整演示')
    demo.add_argument('--out',type=Path,default=Path('reports/demo'))
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            fields = {k:getattr(args,k) for k in ('company','department','business_unit','city','role','lookback_days','demo')}
            fields['company_aliases'] = args.company_alias
            if args.as_of:
                fields['as_of'] = args.as_of
            create_case(args.case_dir, **fields)
            print(f'已创建案例：{args.case_dir.resolve()}')
        elif args.command == 'plan':
            case = read_case(args.case_dir)
            target = args.case_dir / 'queries.md'
            if target.exists() and not args.force:
                raise ValueError('检索计划已存在；使用 --force 可重新生成')
            target.write_text(build_plan(case,load_sources(args.sources),args.source),encoding='utf-8')
            print(f'已生成待执行检索计划：{target.resolve()}')
        elif args.command == 'sources':
            print(json.dumps(load_sources(args.file),ensure_ascii=False,indent=2))
        elif args.command == 'collect':
            urls=json.loads(args.urls.read_text(encoding='utf-8'))
            run=collect_sources(args.case_dir,urls,load_sources(args.sources),args.workers,args.timeout,args.max_bytes)
            rows=json.loads((run/'run.json').read_text(encoding='utf-8'))['results']
            readable=sum(row['status']=='retrieved' for row in rows)
            print(f'已记录 {len(rows)} 条URL任务，其中 {readable} 条保存了可见原文；尚未导入证据。')
            print((run/'run.json').resolve())
            print((run/'evidence-drafts.json').resolve())
        elif args.command == 'import':
            rows = json.loads(args.file.read_text(encoding='utf-8'))
            added = import_evidence(args.case_dir, rows)
            print(f'新增 {added} 条证据；重复记录不重复登记。')
        elif args.command == 'report':
            for path in write_report(args.case_dir,args.out or args.case_dir/'report',args.force):
                print(path.resolve())
        elif args.command == 'demo':
            create_case(args.out/'case',company='示例科技',department='搜索平台部',city='上海',role='后端研发',as_of='2026-11-10',demo=True)
            rows = json.loads(files('reverse_check').joinpath('data/demo-evidence.json').read_text(encoding='utf-8'))
            import_evidence(args.out/'case',rows)
            (args.out/'case'/'queries.md').write_text(build_plan(read_case(args.out/'case')),encoding='utf-8')
            for path in write_report(args.out/'case',args.out):
                print(path.resolve())
    except (ValueError,OSError,UnicodeError) as exc:
        print(f'错误：{exc}',file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
