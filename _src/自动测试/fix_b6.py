"""B6 acceptance: real clicks in both local builds and the published trial.

QA_URL may point at the published trial for the same browser checks.
Application state is inspected for assertions, never changed to simulate a click.
"""
import argparse
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from qa_support import Case, ROOT, TRIAL, launch


class B6Case(Case):
    def __init__(self, browser, name):
        self.name, self.steps, self.errors, self.checks = name, [], [], 0
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('https://script.google.com/**', lambda r: r.fulfill(status=200, body='ok'))
        self.page.goto(os.environ.get('QA_URL') or TRIAL.as_uri())
        self.page.fill('#nm', name)
        self.page.click('[data-do=nameOk]')
        self.page.wait_for_selector('iframe[title="机构端"]', state='attached')
        self.a = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '机构端')
        self.s = next(f for f in self.page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '学生端')
        self.s.wait_for_function('typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
        self.out = Path(os.environ.get('QA_DIR', ROOT / '自动测试/shots')) / name
        self.out.mkdir(parents=True, exist_ok=True)
        if os.environ.get('QA_URL'):
            self.check('v1.19.4-gpt' in self.page.locator('#tb').inner_text(), '线上顶栏版本为 v1.19.4-gpt')

    def open_student(self, student):
        self.select(self.a, '#jump', 'students')
        self.a.locator('[data-bind=q]').fill(student['name'])
        self.steps.append({'操作': '搜索学生', '内容': student['name']})
        self.click(self.a, f'#pg tr[data-act=open][data-arg="{student["id"]}"]')
        self.check(student['name'] in self.a.locator('.dh h2').inner_text(), '抽屉标题对应 ' + student['name'])


def drawers(browser):
    count = 0
    for role in ['c1|L2', 'c5|L3']:
        c = B6Case(browser, 'B6-1-' + role[:2] + '-逐学生切档案页签')
        try:
            c.login(role)
            people = c.a.evaluate("""(()=>{const ids=[LY_CORE().chen.id,'s8',STU.find(s=>s.name==='Wong Jun').id,STU.find(s=>s.queue==='down').id,LY_CORE().lin.id];
              return [...new Set(ids)].map(id=>SU(id)).map(s=>({id:s.id,name:s.name,down:s.queue==='down'}));})()""")
            c.check(len(people) >= 5, '每位老师至少打开五位学生档案')
            first_views = {}
            for student in people:
                ab = c.a.evaluate("""sid=>{const b=BOOK.find(b=>b.sid===sid && ['confirm','ok','change','record','pool'].includes(b.st) && ikOf(b) && ikOf(b).st==='sent' && ikOf(b).sum && ikMayView(b));return b ? {id:b.id,viewed:!!ikOf(b).viewed,seen:JSON.stringify(ikOf(b).seen||{})}:null;}""", student['id'])
                c.open_student(student)
                first_views[student['name']] = c.a.locator('.db').inner_text()
                c.check(c.a.locator('.db .ikbox').count() == 0, '打开档案时不在筛查页展开摘要：' + student['name'])
                if ab:
                    c.check(c.a.evaluate('id=>JSON.stringify(ikOf(BOOK.find(b=>b.id===id)).seen||{})', ab['id']) == ab['seen'], '仅打开档案不记摘要已查看')
                    c.check(c.a.locator('.db [data-act=dtab][data-arg=bk]').filter(has_text='有 1 份预咨询摘要').count() == 1, '其他页签只留一行摘要入口')
                c.click(c.a, '.db .tabs [data-act=dtab][data-arg=tl]')
                c.check(c.a.locator('.db .ikbox').count() == 0 and c.a.locator('.db h3').filter(has_text='跟进时间线').count() == 1, '时间线显示本页内容，摘要不占首屏')
                if student['down']:
                    c.check(c.a.locator('.db .dbox > b').filter(has_text='申请把').count() == 0, '时间线不显示完整降级申请')
                    c.click(c.a, '.db [data-act=dtab][data-arg=rep]')
                    c.check(c.a.locator('.db .dbox > b').filter(has_text='申请把').count() == 1, '点击降级提示跳回筛查与报告，完整申请只显示一次')
                if ab:
                    c.click(c.a, '.db [data-act=dtab][data-arg=bk]:not(.on)')
                else:
                    c.click(c.a, '.db .tabs [data-act=dtab][data-arg=bk]')
                c.check(c.a.locator('.db .ikbox').count() == (1 if ab else 0), '只有预约与咨询完整显示可见摘要')
                if ab:
                    c.check(c.a.locator('.db .card').filter(has=c.a.locator('h3').filter(has_text='预约与咨询')).locator('.ikbox').count() == 1, '摘要在预约卡内部、表格上方')
                    c.check(c.a.locator('.ikbox').evaluate('(el)=>!!el.nextElementSibling && el.nextElementSibling.matches("table.t")'), '完整摘要紧邻预约表之前')
                    c.check(c.a.evaluate('id=>!!ikOf(BOOK.find(b=>b.id===id)).seen[`${me()}|${ikOf(BOOK.find(b=>b.id===id)).ver}`]', ab['id']), '真正显示完整摘要后才记录当前老师查看')
                    c.shot(student['name'] + '-预约摘要')
                if student['down']:
                    c.check(c.a.locator('.db .dbox > b').filter(has_text='申请把').count() == 0, '预约页不再完整显示降级申请')
                c.click(c.a, '.db .tabs [data-act=dtab][data-arg=rep]')
                c.check(c.a.locator('.db .ikbox').count() == 0, '返回筛查页完整摘要已收起')
                c.click(c.a, '.dh [data-act=dwClose]')
            c.check(first_views['Wong Jun'] != first_views['Lim Jun'], 'Wong Jun 与 Lim Jun 首屏档案内容不同')
            # The booking shortcut retains its audit, but cannot mark a hidden summary read.
            c.select(c.a, '#jump', 'booking')
            c.click(c.a, '[data-act=btab][data-arg=man]')
            c.click(c.a, '.bkpin [data-act=bOpen]')
            c.check(c.a.locator('.db .ikbox').count() == 0, '待确认看学生信息不会在默认页自动展开摘要')
        finally:
            c.close()
        count += c.checks
    return count


TESTS = {'drawers': drawers}
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=list(TESTS))
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = launch(p)
        try:
            total = sum(fn(browser) for name, fn in TESTS.items() if not args.only or name == args.only)
        finally:
            browser.close()
    print(f'fix_b6: {total} passed, 0 failed', flush=True)
