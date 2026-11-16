import json
import shutil
import subprocess
import unittest
from reverse_check.http_source import FetchError


class MaimaiCommentTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'DOM test needs optional Node')
    def test_missing_post_body_does_not_use_comment_as_body(self):
        from reverse_check.browser_forums import maimai_post
        fixture=r'''global.location={href:'https://maimai.cn/community/gossip-detail/42',pathname:'/community/gossip-detail/42'};
        global.setTimeout=(fn)=>fn();global.document={querySelector:s=>s.includes('GossipDetailContent')?null:{innerText:'这是一条评论，而不是原帖正文，不能误当成主帖。'}};'''
        def tool(args,timeout):
            if args[2]!='eval':return []
            code=fixture+';Promise.resolve('+args[3]+').then(r=>process.stdout.write(JSON.stringify(r)));'
            return json.loads(subprocess.run(['node','-e',code],capture_output=True,text=True,check=True,timeout=3).stdout)
        with self.assertRaises(FetchError) as err: maimai_post('/bin/opencli','https://maimai.cn/community/gossip-detail/42',3,tool)
        self.assertEqual(err.exception.status,'unsupported_content')
    def test_unrecognized_layout_is_not_empty_comments(self):
        from reverse_check.browser_forums import maimai_comments
        calls=[]
        def tool(args,timeout):
            calls.append(args)
            if args[2]=='eval':return [{'kind':'page','url':'https://maimai.cn/community/gossip-detail/42','status':'unsupported_content'}]
            return []
        with self.assertRaises(FetchError) as err:
            maimai_comments('/bin/opencli','https://maimai.cn/community/gossip-detail/42',2,tool)
        self.assertEqual(err.exception.status,'unsupported_content')
        self.assertTrue(any(args[2]=='close' for args in calls))

    def test_foreign_redirect_is_rejected(self):
        from reverse_check.browser_forums import maimai_comments
        def tool(args,timeout):
            if args[2]=='eval':return [{'kind':'page','url':'https://evil.example/community/gossip-detail/42','status':'visible_only'}]
            return []
        with self.assertRaises(FetchError) as err: maimai_comments('/bin/opencli','https://maimai.cn/community/gossip-detail/42',2,tool)
        self.assertEqual(err.exception.status,'unsupported_source')

    @unittest.skipUnless(shutil.which('node'),'DOM test needs optional Node')
    def test_only_card_own_text_is_read_and_delayed_cards_are_waited_for(self):
        from reverse_check.browser_forums import maimai_comments
        fixture=r'''let ticks=0;
        global.location={href:'https://maimai.cn/community/gossip-detail/42',pathname:'/community/gossip-detail/42'};
        const rich={innerText:'顶层评论'};
        const card={getAttribute:k=>k==='data-sentry-component'?'CommentCard':null,
          querySelectorAll:s=>s.startsWith(':scope > div.ml-8')?[rich]:[rich,{innerText:'折叠回复'}]};
        const list={children:[card]};
        global.document={querySelector:s=>{if(s.includes('CommentList'))return ++ticks>=3?list:null;return null;},body:{innerText:'评论 加载中'}};'''
        def tool(args,timeout):
            if args[2]!='eval':return []
            code=fixture+';Promise.resolve('+args[3]+').then(r=>process.stdout.write(JSON.stringify(r)));'
            result=subprocess.run(['node','-e',code],capture_output=True,text=True,check=True,timeout=4)
            return json.loads(result.stdout)
        rows=maimai_comments('/bin/opencli','https://maimai.cn/community/gossip-detail/42',4,tool)
        self.assertEqual([r['text'] for r in rows],['顶层评论'])
        self.assertIsNone(rows[0]['parent_id']);self.assertIsNone(rows[0]['author'])

    @unittest.skipUnless(shutil.which('node'),'DOM test needs optional Node')
    def test_static_heading_does_not_establish_empty_list(self):
        from reverse_check.browser_forums import maimai_comments
        fixture=r'''global.location={href:'https://maimai.cn/community/gossip-detail/42',pathname:'/community/gossip-detail/42'};
        global.setTimeout=(fn)=>fn();global.document={querySelector:()=>({children:[]}),body:{innerText:'评论 加载中'}};'''
        def tool(args,timeout):
            if args[2]!='eval':return []
            code=fixture+';Promise.resolve('+args[3]+').then(r=>process.stdout.write(JSON.stringify(r)));'
            return json.loads(subprocess.run(['node','-e',code],capture_output=True,text=True,check=True,timeout=3).stdout)
        with self.assertRaises(FetchError) as err:
            maimai_comments('/bin/opencli','https://maimai.cn/community/gossip-detail/42',3,tool)
        self.assertEqual(err.exception.status,'unsupported_content')
