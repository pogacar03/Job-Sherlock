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

    def test_author_claim_must_be_in_quoted_segment(self):
        from reverse_check.review import prepare_evidence
        from reverse_check.forum_content import candidate_id_for
        c,p=sample()
        comment={'id':'comment-0001','kind':'comment','text':'最近每晚十点下班','author':'另一人','author_url':None,'platform_id':None,'parent_id':None,'time_raw':None}
        c['segments'].append(comment);c['candidate_id']=candidate_id_for(c['thread_key'],c['title'],c['segments'])
        p.update(candidate_id=c['candidate_id'],segment_id='comment-0001')
        with self.assertRaises(ValueError):prepare_evidence(c,p)

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

    def test_interrupted_receipt_can_be_retried(self):
        from reverse_check.review import approve_proposals
        from reverse_check.casebook import _write_json
        c,p=sample();batch={'schema_version':1,'proposals':[p]}
        calls=[]
        def write(path, data):
            calls.append(data['status'])
            if data['status']=='committed': raise OSError('disk error')
            _write_json(path,data)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            with patch('reverse_check.review._write_json',side_effect=write):
                with self.assertRaisesRegex(ValueError,'证据已登记'):approve_proposals(path,batch,['p1'])
            self.assertEqual(len(read_evidence(path)),1)
            result=approve_proposals(path,batch,['p1'])
            self.assertEqual(result['inserted'],0)
            self.assertEqual(json.loads(Path(result['receipt']).read_text())['status'],'committed')

    def test_keyboard_interrupt_never_imports_selection(self):
        from reverse_check.review import review_interactive
        c,p=sample()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            def interrupted(_): raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                review_interactive(path,{'schema_version':1,'proposals':[p]},input_fn=interrupted,output_fn=lambda _:None)
            self.assertEqual(read_evidence(path),[])

    def test_fictional_experience_question_other_team_and_unknown_date(self):
        from reverse_check.review import approve_proposals, prepare_evidence
        from reverse_check.analysis import analyze
        from reverse_check.casebook import read_case
        from reverse_check.forum_content import candidate_id_for
        c,p=sample()
        c['segments'][0]['text']+=' 其他团队经历发生于2026-11-10。'
        c['candidate_id']=candidate_id_for(c['thread_key'],c['title'],c['segments'])
        p['candidate_id']=c['candidate_id']
        with self.assertRaises(ValueError):prepare_evidence(c,{**p,'kind':'question'})
        other={**p,'id':'p2','scope':{**p['scope'],'department':'其他团队'},'observed_at':'2026-11-10'}
        other['basis']=[entry if entry['field']!='scope.department' else {**entry,'quote':'其他团队'} for entry in p['basis']]+[{'field':'observed_at','segment_id':'body','part':'text','quote':'2026-11-10'}]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            approve_proposals(path,{'schema_version':1,'proposals':[p,other]},['p1','p2'])
            analysis=analyze(read_case(path),read_evidence(path))
            self.assertEqual(analysis['summary']['eligible_count'],0)
            self.assertEqual(len(analysis['background']),2)
            self.assertIn('观察时间不明',analysis['background'][0]['reasons'])
            self.assertIn('部门不匹配',analysis['background'][1]['reasons'])
