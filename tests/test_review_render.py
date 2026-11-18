import json
from pathlib import Path
import tempfile
import unittest

from reverse_check.casebook import read_evidence
from tests.test_review import sample, setup_case


class ReviewRenderTests(unittest.TestCase):
    def test_existing_candidates_flag_platform_use_without_discarding(self):
        from reverse_check.review_render import write_review_cards
        from reverse_check.forum_content import candidate_id_for
        c,_=sample();c['segments'][0]['text']='在示例科技上找其他公司的工作'
        c['candidate_id']=candidate_id_for(c['thread_key'],c['title'],c['segments'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            html=write_review_cards(path,Path(tmp)/'cards').read_text()
            self.assertIn('可能是在使用该平台',html)
            self.assertIn('在示例科技上找其他公司的工作',html)

    def test_interactive_review_also_warns_platform_use(self):
        from reverse_check.review import review_interactive
        from reverse_check.forum_content import candidate_id_for
        c,p=sample();c['segments'][0]['text']+='，也在示例科技上找其他公司的工作。'
        c['candidate_id']=candidate_id_for(c['thread_key'],c['title'],c['segments']);p['candidate_id']=c['candidate_id']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c);output=[]
            review_interactive(path,{'schema_version':1,'proposals':[p]},input_fn=lambda _:'s',output_fn=output.append)
            self.assertTrue(any('可能是在使用该平台' in text for text in output))
            self.assertEqual(read_evidence(path),[])
    def test_card_escapes_html_and_does_not_create_evidence(self):
        from reverse_check.review_render import write_review_cards
        c,p=sample();c['title']='<script>alert(1)</script>'
        from reverse_check.forum_content import candidate_id_for
        c['candidate_id']=candidate_id_for(c['thread_key'],c['title'],c['segments'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            out=Path(tmp)/'cards';html=write_review_cards(path,out).read_text()
            self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
            self.assertIn('body',html);self.assertEqual(read_evidence(path),[])
            with self.assertRaises(ValueError):write_review_cards(path,out)

    def test_interactive_accepts_only_selected(self):
        from reverse_check.review import review_interactive
        c,p=sample();p2={**p,'id':'p2','kind':'question'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'case';setup_case(path,c)
            answers=iter(['a','q'])
            result=review_interactive(path,{'schema_version':1,'proposals':[p,p2]},input_fn=lambda _:next(answers),output_fn=lambda _:None)
            self.assertEqual(result['inserted'],1);self.assertEqual(len(read_evidence(path)),1)
