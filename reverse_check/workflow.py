"""Coordinate one local investigation without approving evidence."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from .casebook import create_case, validate_case
from .forums import scan_forums, validate_scan_options
from .report import write_report
from .review_render import write_review_cards


def run_investigation(case_dir: Path, *, case_fields: dict, scan_options: dict, scan_fn=scan_forums) -> dict:
    path=Path(case_dir)
    validate_scan_options(**scan_options)
    fields=dict(case_fields)
    fields.setdefault('as_of',datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    validate_case(fields)
    if path.exists() and (not path.is_dir() or any(path.iterdir())): raise ValueError('案例目录非空；请使用已有案例的 scan/read')
    create_case(path,**fields)
    try:
        scan_dir=scan_fn(path,**scan_options)
    except KeyboardInterrupt:
        return {'case_dir':path,'scan_dir':None,'cards_path':None,'report_paths':[],'exit_code':130}
    scan=json.loads((scan_dir/'run.json').read_text(encoding='utf-8'))
    cards=write_review_cards(path,path/'review')
    reports=write_report(path,path/'report')
    status=scan.get('status')
    code=130 if status=='interrupted' else 0 if status=='completed' else 3
    return {'case_dir':path,'scan_dir':scan_dir,'cards_path':cards,'report_paths':reports,'exit_code':code}
