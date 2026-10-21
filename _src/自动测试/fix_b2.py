"""Batch 2 UI and cross-frame acceptance checks."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def moves(browser):
    total = 0
    for adjusted in [False, True]:
        c = Case(browser, 'B2-1-中心调整' if adjusted else 'B2-1-普通申请')
        try:
            c.login('c1|L2')
            bid = c.book()
            if adjusted:
                c.click(c.a, f'[data-act=bOk][data-arg="{bid}"]')
                c.wait(c.s, 'S.bk.st==="已确认"')
                c.click(c.a, '[data-act=btab][data-arg=sched]')
                c.click(c.a, '[data-arg="schedReg:"]')
                for arg in ['rgc|c1', 'rgt|病假停诊', 'rgd|7', 'rga|all']:
                    c.click(c.a, f'[data-act=fset][data-arg="{arg}"]')
                c.click(c.a, '[data-act=schedRegGo]')
                c.wait(c.s, 'S.bk===null')
                c.click(c.a, '[data-act=btab][data-arg=man]')
                c.click(c.a, '[data-act=bsub][data-arg=adjust]')
            c.move(bid, 5, 0)
            c.wait(c.s, 'S.bk && S.bk.st==="已改约"')
            c.check(c.a.evaluate('(id)=>BOOK.find(b=>b.id===id).st', bid) == 'move', '老师提出时间后未提前确认')
            row = c.a.locator('.bkpin tr').filter(has=c.a.locator(f'[data-act=bOpen][data-arg="{bid}"]'))
            c.check(row.locator('button').count() == 1 and '看学生信息' in row.inner_text(), '等待学生确认的行只留学生信息')
            c.side('学生端')
            c.shot('学生收到新时间')
            if adjusted:
                c.check('点「接受新时间」就约好了' in c.s.inner_text('#modal'), '中心调整通知说明接受动作')
                c.click(c.s, '#modal [data-act=movedOk]')
            else:
                c.click(c.s, '#modal .ov', '关闭老师改约通知', position={'x': 2, 'y': 2})
                c.click(c.s, '[data-act=go][data-arg=mybook]', '打开我的预约')
                c.check('不用操作' not in c.s.inner_text('#app'), '预约卡不再提示不用操作')
                c.click(c.s, '[data-act=movedOk]')
            c.wait(c.a, f'BOOK.find(b=>b.id==={bid!r}).st==="ok"')
            c.check(c.s.evaluate('S.bk.st') == '已确认', '学生接受后双端已确认')
            c.check(c.a.evaluate('(id)=>NOTI.some(n=>n.ref===id && n.to==="c1" && n.t.includes("接受了新时间"))', bid), '老师收到接受通知')
            if adjusted:
                c.check(c.a.evaluate("SCHM.c1['10/21'].every(x=>x==='off')"), '接受后原病假日四格仍关闭')
            c.select(c.s, '#jump', 'mybook')
            c.click(c.s, '[data-act=resch]')
            c.click(c.s, '[data-act=reschOk]')
            c.check(c.s.locator('[data-act=pickSlot]').count() == 0, '学生改期也先列日期')
            c.click(c.s, '[data-act=day]')
            c.check(c.s.locator('[data-act=pickSlot]').count() > 0, '选择日期后才显示当天时段')
            c.shot('学生改期按日期选时')
        finally:
            c.close()
            total += c.checks
    return total


TESTS = {'B2-1': moves}
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
    print(f'fix_b2: {total} passed, 0 failed', flush=True)
