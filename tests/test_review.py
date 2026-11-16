import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reverse_check.casebook import create_case, read_evidence
from reverse_check.forum_content import normalize_thread
from tests.fixtures import target


def sample():
    c=normalize_thread('nowcoder','https://www.nowcoder.com/discuss/42','标题','我是示例科技员工，搜索平台部最近每晚十点下班。',[],comment_status='visible_only',published_at_raw=None,retrieved_at='2026-11-16')
    c['scan_id']='scan1'
    p={'id':'p1','scan_id':'scan1','candidate_id':c['candidate_id'],'segment_id':'body','quote':'最近每晚十点下班','observation':'作者自述近期晚十点下班','kind':'experience','source_type':'employee_account','dimension':'workload','direction':'risk','scope':{'company':'示例科技','business_unit':None,'department':'搜索平台部','city':None,'role':None},'observed_at':None,'published_at':None,'basis':[{'field':'source_type','segment_id':'body','part':'text','quote':'我是示例科技员工'},{'field':'scope.company','segment_id':'body','part':'text','quote':'示例科技'},{'field':'scope.department','segment_id':'body','part':'text','quote':'搜索平台部'}]}
    return c,p


def setup_case(path,c):
    create_case(path,**target());d=path/'scans'/'scan1';d.mkdir(parents=True)
    (d/'run.json').write_text(json.dumps({'schema_version':2,'candidates':[c],'channels':[],'leads':[]},ensure_ascii=False))


class ReviewTests(unittest.TestCase):
    def test_grounded_evidence_and_stable_id(self):
        from reverse_check.review import prepare_evidence
        c,p=sample();e=prepare_evidence(c,p)
        self.assertEqual(e['quote'],p['quote']);self.assertEqual(e['origin_id'],c['thread_key'])
        self.assertIsNone(e['scope']['city']);self.assertEqual(e,prepare_evidence(c,p))

    def test_rejects_forged_quotes_basis_and_snapshot(self):
        from reverse_check.review import prepare_evidence
        c,p=sample()
        for change in ('quote','basis','kind','snapshot','scan_id'):
            candidate=copy.deepcopy(c);proposal=copy.deepcopy(p)
            if change=='quote':proposal['quote']='不存在'
            if change=='basis':proposal['basis']=[]
            if change=='kind':proposal['kind']='question'
            if change=='snapshot':candidate['segments'][0]['text']+='篡改'
            if change=='scan_id':proposal['scan_id']='../else'
            with self.subTest(change=change),self.assertRaises(ValueError):prepare_evidence(candidate,proposal)

    def test_batch_atomic_and_idempotent(self):
        from reverse_check.review import approve_proposals
        c,p=sample()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            bad={**p,'id':'p2','quote':'错误'};batch={'schema_version':1,'proposals':[p,bad]}
            with self.assertRaises(ValueError):approve_proposals(path,batch,['p1','p2'])
            self.assertEqual(read_evidence(path),[])
            self.assertEqual(approve_proposals(path,batch,['p1'])['inserted'],1)
            self.assertEqual(approve_proposals(path,batch,['p1'])['inserted'],0)
            self.assertEqual(len(read_evidence(path)),1)
