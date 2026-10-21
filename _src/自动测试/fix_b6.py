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
            self.check('demo-v2.0' in self.page.locator('#tb').inner_text(), '线上顶栏版本为 demo-v2.0')

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
            people = c.a.evaluate("""(()=>{const wong=STU.find(s=>s.name==='Wong Jun' && BOOK.some(b=>b.sid===s.id && ikOf(b) && ikOf(b).sum)) || STU.find(s=>s.name==='Wong Jun');
              const ids=[LY_CORE().chen.id,'s8',wong.id,STU.find(s=>s.queue==='down').id,LY_CORE().lin.id];
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
                if student['down']:
                    c.shot(student['name'] + '-筛查页完整降级申请')
                others = c.a.locator('.db .tabs [data-act=dtab]').evaluate_all('(els)=>els.map(e=>e.dataset.arg).filter(k=>!["rep","tl","bk"].includes(k))')
                for tab in others:
                    c.click(c.a, f'.db .tabs [data-act=dtab][data-arg="{tab}"]')
                    c.check(c.a.evaluate('S.dw.tab') == tab and c.a.locator('.db .ikbox').count() == 0, tab + ' 页签正常切换，不重复展开摘要')
                    if student['down']:
                        c.check(c.a.locator('.db .dbox > b').filter(has_text='申请把').count() == 0, tab + ' 页签只保留降级提示')
                c.click(c.a, '.dh [data-act=dwClose]')
            c.check(first_views['Wong Jun'] != first_views['Lim Jun'], 'Wong Jun 与 Lim Jun 首屏档案内容不同')
            # The booking shortcut retains its audit, but cannot mark a hidden summary read.
            c.select(c.a, '#jump', 'booking')
            c.click(c.a, '[data-act=btab][data-arg=man]')
            c.click(c.a, '.bkpin button[data-act=bOpen]')
            c.check(c.a.locator('.db .ikbox').count() == 0, '待确认看学生信息不会在默认页自动展开摘要')
        finally:
            c.close()
        count += c.checks
    return count


def appointment_rows(browser):
    count = 0
    for role in ['c1|L2', 'c5|L3']:
        c = B6Case(browser, 'B6-2-' + role[:2] + '-人工咨询逐行打开档案')
        try:
            c.login(role)
            c.click(c.a, '[data-act=btab][data-arg=man]')
            c.click(c.a, '[data-act=bsub][data-arg=all]')
            table = '#pg .card:not(.bkpin) table.t'
            ids = c.a.locator(table + ' tr[data-act=bOpen]').evaluate_all('(rows)=>rows.map(r=>r.dataset.arg)')
            c.check(len(ids) >= 5, '先逐行检查原始数据的全部列表，至少五条')
            for bid in ids:
                name = c.a.evaluate('id=>nm(SU(BOOK.find(b=>b.id===id).sid))', bid)
                before = c.a.evaluate('AUDIT.filter(a=>a.t.startsWith("查看预约申请")).length')
                c.click(c.a, table + f' tr[data-arg="{bid}"] td:first-child b', '点原始预约学生姓名 ' + name)
                c.check(name in c.a.locator('.dh h2').inner_text(), '抽屉标题对应 ' + name)
                c.check(c.a.evaluate('AUDIT.filter(a=>a.t.startsWith("查看预约申请")).length') == before + 1, '行点击走 bOpen，仅记一次预约查看')
                c.click(c.a, '.dh [data-act=dwClose]')
            # The seeded demo has fewer than two change/record/adjust/pool rows.
            # Add distinct students as explicit display fixtures, then exercise every
            # row and action through clicks. No click is simulated with ACT calls.
            c.a.evaluate("""()=>{let n=0;for(const st of ['ok','change','adjust','record','pool','confirm'])for(let i=0;i<2;i++){
              const base=BOOK.find(b=>b.st===st)||BOOK[0], sid=STU[120+n++].id;
              const b={...base,id:'qa-b6-'+st+'-'+i,sid,cid:'c1',st,intake:null,fresh:false,rec:null};
              delete b.clash; if(st==='change')b.req={type:'改期',day:4,t:2}; BOOK.push(b);
            }render();}""")
            c.steps.append({'测试准备':'为种子数据少于两行的状态补充独立学生夹具；每种状态两行，只检查列表、档案和按钮行为，不改变业务规则'})
            tabs = ['ok', 'change', 'adjust', 'record'] + (['pool'] if role == 'c5|L3' else []) + ['all']
            for tab in tabs:
                c.click(c.a, f'[data-act=bsub][data-arg="{tab}"]')
                rows = c.a.locator(table + ' tr[data-act=bOpen]')
                c.check(rows.count() >= 2, tab + ' 子列表至少点击两行')
                for i in range(2):
                    row = rows.nth(i)
                    bid = row.get_attribute('data-arg')
                    name = c.a.evaluate('id=>nm(SU(BOOK.find(b=>b.id===id).sid))', bid)
                    row.hover()
                    c.check(row.evaluate('e=>getComputedStyle(e).cursor') == 'pointer' and row.locator('td').first.evaluate('e=>getComputedStyle(e).backgroundColor') != 'rgba(0, 0, 0, 0)', '可点击行使用统一手形与悬停底色')
                    selector = table + f' tr[data-arg="{bid}"]'
                    # Cover name, grade and a padded blank area of the date cell.
                    mode = (tabs.index(tab) + i) % 3
                    if mode == 0:
                        c.click(c.a, selector + ' td:first-child b', '点姓名 ' + name)
                    elif mode == 1:
                        c.click(c.a, selector + ' td:nth-child(2)', '点等级 ' + name)
                    else:
                        c.click(c.a, selector + ' td:nth-child(4)', '点行内空白 ' + name, position={'x': 3, 'y': 3})
                    c.check(name in c.a.locator('.dh h2').inner_text(), tab + ' 子列表打开正确学生 ' + name)
                    c.click(c.a, '.dh [data-act=dwClose]')
            for arg in ['bMove:b1', 'bNo:qa-b6-adjust-0', 'rec:qa-b6-record-0', 'intake:b1']:
                c.click(c.a, '[data-act=bsub][data-arg=all]')
                c.click(c.a, '#pg button[data-act=mo][data-arg="' + arg + '"]')
                c.check(c.a.evaluate('S.mo') == arg and c.a.evaluate('S.dw===null'), arg + ' 只打开自己的弹窗，不同时开档案')
                c.click(c.a, '[data-act=moClose]')
            c.check(c.a.locator('.bkpin button[data-act=bOpen]').count() >= 2, '待确认仍保留原来的看学生信息按钮')
            c.shot('人工咨询可点行')
            c.select(c.a, '#roleSel', 'u1|L1')
            c.check(c.a.locator('#jump option[value=booking]').count() == 0, '辅导员仍没有人工咨询页面')
        finally:
            c.close()
        count += c.checks
    return count


def single_line_bars(browser):
    c = B6Case(browser, 'B6-3-四种宽度的全部比例数字')
    try:
        c.login()
        for width in [1280, 1440, 1615, 1913]:
            c.page.set_viewport_size({'width': width, 'height': 1000})
            c.select(c.a, '#jump', 'data')
            for tab in ['dash', 'stu', 'staff', 'report']:
                c.click(c.a, f'[data-act=dtabD][data-arg="{tab}"]')
                cells = c.a.locator('#pg .hb span:last-child').evaluate_all('(els)=>els.map(e=>({text:e.textContent,height:e.getBoundingClientRect().height,whiteSpace:getComputedStyle(e).whiteSpace}))')
                if tab in ['dash', 'stu']:
                    c.check(bool(cells), f'{width}px {tab} 实际覆盖比例数字')
                c.check(all(x['height'] <= 22 and x['whiteSpace'] == 'nowrap' for x in cells), f'{width}px {tab} 的 {len(cells)} 个数字均为单行：{cells}')
                if width == 1440 and tab == 'stu':
                    c.shot('1440学生情况比例单行')
            student = c.a.evaluate('({id:LY_CORE().chen.id,name:LY_CORE().chen.name})')
            c.open_student(student)
            c.click(c.a, '.db .tabs [data-act=dtab][data-arg=score]')
            cells = c.a.locator('.db .hb span:last-child').evaluate_all('(els)=>els.map(e=>({text:e.textContent,height:e.getBoundingClientRect().height}))')
            c.check(len(cells) == 5 and all(x['height'] <= 22 for x in cells), f'{width}px 档案深度访谈评分五项均为单行：{cells}')
            c.click(c.a, '.dh [data-act=dwClose]')
        c.check(c.a.evaluate('LY_VER') == 'demo-v2.0' and 'demo-v2.0' in c.page.locator('#tb').inner_text(), '两端构建与合并版版本号为 demo-v2.0')
    finally:
        c.close()
    return c.checks


TESTS = {'drawers': drawers, 'rows': appointment_rows, 'bars': single_line_bars}
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
