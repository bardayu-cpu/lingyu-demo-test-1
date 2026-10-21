"""Batch 4: click checks for invitation counts, configuration, audit and interface."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def counters(browser):
    c = Case(browser, 'B4-1-八张统计卡与名单')
    try:
        c.login()
        for key in ['sent', 'acc', 'no', 'ik', 'queue', 'entry', 'sub', 'ok']:
            card = c.a.locator(f'[data-act=ivF][data-arg="{key}"]')
            n = int(card.locator('b').inner_text())
            c.click(c.a, f'[data-act=ivF][data-arg="{key}"]')
            table = c.a.locator('.card').filter(has=c.a.locator('h3').filter(has_text='当前筛选')).locator('table')
            c.check(table.locator('tr').filter(has=c.a.locator('td b')).count() == n, key + ' 名单人数等于数字卡')
            c.check(f'· {n} 人' in c.a.locator('h3').filter(has_text='当前筛选').inner_text(), key + ' 标明当前筛选及人数')
        c.check('累计 · 其中待回复' in c.a.inner_text('#pg'), '累计发卡和待回复口径写清')
        c.shot('统计筛选与人数')
    finally:
        c.close()
    return c.checks


def eligibility(browser):
    c = Case(browser, 'B4-2-主动邀约等级')
    try:
        c.login()
        before = c.a.evaluate('ivb().list.map(x=>({sid:x.sid,st:x.st}))')
        student = c.a.evaluate('STU.find(s=>curLv(s)===3 && !ivb().list.some(x=>x.sid===s.id))')
        c.check(bool(student), '使用未在批次的三级学生验证新增门槛')
        c.click(c.a, '[data-act=btab][data-arg=pool]')
        c.select(c.a, '[data-pool=ivLv]', '4')
        c.click(c.a, '[data-act=btab][data-arg=inv]')
        c.click(c.a, '[data-arg="ivAdd:"]')
        c.check(c.a.locator('[data-act=ivPickT]').evaluate_all('(els)=>els.every(e=>curLv(SU(e.dataset.arg))>=4)'), '勾选候选只列四级及以上')
        c.click(c.a, '[data-act=fset][data-arg="ivt|paste"]')
        c.a.locator('[data-bind="form.ivIds"]').fill(student['sid'])
        c.steps.append({'操作':'粘贴三级学生学号','内容':student['sid']})
        c.click(c.a, '[data-act=ivAddGo]')
        c.check('未达主动邀约等级（4 级及以上）' in c.a.inner_text('#modal'), '核对解释等级不够，进入对不上')
        c.check(c.a.evaluate('ivb().list.map(x=>({sid:x.sid,st:x.st}))') == before, '学生未加入且原批次学生与状态不变')
        c.shot('未达等级核对结果')
    finally:
        c.close()
    return c.checks


def piles(browser):
    c = Case(browser, 'B4-3-核对结果留在批次')
    try:
        c.login()
        people = c.a.evaluate("""(()=>{const B=ivb(), crisis=STU.find(s=>curLv(s)>=RULES.pool.ivLv && inCrisis(s.id)), booked=STU.find(s=>curLv(s)>=RULES.pool.ivLv && !inCrisis(s.id) && activeBook(s));
          // Isolate first-time exclusion of these two seeded students; keep all other existing piles.
          B.piles.skip=B.piles.skip.filter(x=>x.sid!==crisis.id); B.piles.has=B.piles.has.filter(x=>x.sid!==booked.id);
          return {crisis,booked,before:Object.fromEntries(Object.entries(B.piles).map(([k,v])=>[k,v.length]))};})()""")
        ids = 'NO-SUCH-STUDENT\n' + people['crisis']['sid'] + '\n' + people['booked']['sid']
        c.steps.append({'测试准备':'将两名种子学生从对应核对堆移出，用于验证首次追加；其他既有条目保留'})
        for repeat in [False, True]:
            c.click(c.a, '[data-arg="ivAdd:"]')
            c.click(c.a, '[data-act=fset][data-arg="ivt|paste"]')
            c.a.locator('[data-bind="form.ivIds"]').fill(ids)
            c.steps.append({'操作':'粘贴不存在、危机中、已有预约的三个学号','内容':ids})
            c.click(c.a, '[data-act=ivAddGo]')
            for label in ['对不上（1）', '不走预约队列（1）', '已有安排（1）']:
                c.check(label in c.a.inner_text('#modal'), '核对弹窗：' + label)
            c.click(c.a, '[data-act=moClose]')
            after = c.a.evaluate('Object.fromEntries(Object.entries(ivb().piles).map(([k,v])=>[k,v.length]))')
            c.check(all(after[k] == people['before'][k] + 1 for k in ['bad','skip','has']), '关闭后各堆加一；再次加入按学号去重' if repeat else '关闭后批次三堆人数各加一')
        c.check(c.a.evaluate('ivb().piles.bad.some(x=>x.id==="NO-SUCH-STUDENT" && x.why==="不在名册")'), '对不上保留学号和具体原因')
        c.shot('关闭弹窗后保留核对人数')
    finally:
        c.close()
    return c.checks


TESTS = {'B4-1': counters, 'B4-2': eligibility, 'B4-3': piles}
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
    print(f'fix_b4: {total} passed, 0 failed', flush=True)
