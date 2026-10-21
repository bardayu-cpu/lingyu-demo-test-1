"""Batch 3: real clicks for risk-word deltas, upgrades and auxiliary signals."""
import argparse
from playwright.sync_api import sync_playwright
from qa_support import Case, launch


def fill(c, selector, value):
    c.side('机构端')
    c.a.locator(selector).fill(value)
    c.steps.append({'操作': '填写 ' + selector, '内容': value})


def talk(c, text, role='u1|L1'):
    c.select(c.a, '#roleSel', role)
    c.select(c.a, '#jump', 'talk')
    c.click(c.a, '[data-act=tktab][data-arg=recs]')
    c.click(c.a, '[data-act=tkNew]')
    fill(c, '[data-rb=pick]', '林晓')
    sid = c.a.evaluate('LY_CORE().lin.id')
    c.click(c.a, f'[data-act=rcAdd][data-arg="{sid}"]')
    for arg in ['mode|面对面', 'result|已谈', 'types|心理健康']:
        c.click(c.a, f'[data-act=rcT][data-arg="{arg}"]')
    fill(c, '[data-rb=situ]', text)
    c.click(c.a, '[data-act=recSave][data-arg=""]')
    return c.a.evaluate('TALKS[TALKS.length-1].id')


def close_crisis(c, kid):
    c.login()
    c.select(c.a, '#jump', 'crisis')
    c.click(c.a, f'[data-act=crisisOpen][data-arg="{kid}"]')
    c.click(c.a, f'[data-act=recv][data-arg="{kid}"]')
    c.click(c.a, f'[data-arg="step:{kid}|contact"]')
    for arg in ['to|本人', 'res|已接通']:
        c.click(c.a, f'[data-act=fset][data-arg="{arg}"]')
    c.click(c.a, '[data-act=stepOk]')
    c.click(c.a, f'[data-arg="close:{kid}"]')
    for arg in ['state|安全，在校', 'plan|已签署', 'parent|已知情', 'lv|3 重点关注', 'who|朱静']:
        c.click(c.a, f'[data-act=fset][data-arg="{arg}"]')
    fill(c, '[data-bind="form.note"]', '已联系本人并确认安全，安全计划已签署，家长知情，安排后续随访。')
    for arg in c.a.locator('[data-act=fzSet]').evaluate_all('(els)=>els.filter(e=>e.dataset.arg.endsWith("|恢复")).map(e=>e.dataset.arg)'):
        c.click(c.a, f'[data-act=fzSet][data-arg="{arg}"]')
    c.click(c.a, '[data-act=closeOk]')
    c.check(c.a.evaluate('(id)=>CRISES.find(k=>k.id===id).st', kid) == 'closed', '经接收、联系、冻结事项处理后正式结案')


def new_words(browser):
    c = Case(browser, 'B3-1-仅新增风险词报告')
    try:
        tid = talk(c, '我感到绝望，希望老师一起商量下一步。')
        kid = c.a.evaluate('(id)=>CRISES.find(k=>k.fromRec===id).id', tid)
        c.check(not c.a.evaluate('(id)=>CRISES.find(k=>k.id===id).urgent', kid), '初次二级词按一般危机处理')
        c.click(c.a, '[data-act=moClose]')
        close_crisis(c, kid)
        c.select(c.a, '#roleSel', 'u1|L1')
        c.select(c.a, '#jump', 'talk')
        c.click(c.a, '[data-act=tktab][data-arg=recs]')
        c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
        c.click(c.a, f'[data-act=tkEdit][data-arg="{tid}"]')
        fill(c, '[data-rb=situ]', '我感到绝望，希望老师一起商量下一步。今天又说我想死。')
        c.click(c.a, '[data-act=recSave][data-arg=""]')
        c.check(c.a.evaluate('(id)=>CRISES.filter(k=>k.fromRec===id).length', tid) == 2, '旧记录新增一级词，结案后重新报告')
        c.check(c.a.evaluate('(id)=>CRISES.filter(k=>k.fromRec===id).at(-1).urgent', tid), '新危机按新增一级词判定紧急')
        c.check('30 分钟' in c.a.inner_text('#modal'), '新紧急报告弹窗显示30分钟')
        c.shot('新增一级词重新报告紧急')
        c.click(c.a, '[data-act=moClose]')
        count = c.a.evaluate('CRISES.length')
        notices = c.a.evaluate('NOTI.length')
        c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
        c.click(c.a, f'[data-act=tkEdit][data-arg="{tid}"]')
        fill(c, '[data-rb=situ]', '我感到绝望，希望老师一起商量下一步。今天又说我想死。补充了本周课程安排。')
        c.click(c.a, '[data-act=recSave][data-arg=""]')
        c.check(c.a.evaluate('CRISES.length') == count and c.a.evaluate('NOTI.length') == notices, '只改其他文字，不新增报告或通知')
        c.check(c.a.evaluate("cwLv12('我没有想死。最近很累').length") == 0, '否定说法与三级词不进入新增一二级词集合')
    finally:
        c.close()
    return c.checks


def upgrade(browser):
    total = 0
    for received in [False, True]:
        c = Case(browser, 'B3-2-已接收后追加升级' if received else 'B3-2-未接收修改升级')
        try:
            tid = talk(c, '我感到绝望，希望老师协助。')
            kid = c.a.evaluate('(id)=>CRISES.find(k=>k.fromRec===id).id', tid)
            c.click(c.a, '[data-act=moClose]')
            if received:
                c.login()
                c.select(c.a, '#jump', 'crisis')
                c.click(c.a, f'[data-act=crisisOpen][data-arg="{kid}"]')
                c.click(c.a, f'[data-act=recv][data-arg="{kid}"]')
                c.select(c.a, '#roleSel', 'u1|L1')
            c.side('机构端')
            c.a.locator('#zapT').check()
            for _ in range(6 if received else 1):
                c.click(c.a, '[data-act=zTime]')
            c.select(c.a, '#jump', 'talk')
            c.click(c.a, '[data-act=tktab][data-arg=recs]')
            c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
            before = c.a.evaluate('CRISES.length')
            n0 = c.a.evaluate('NOTI.length')
            if received:
                c.click(c.a, f'[data-arg="tkAdd:{tid}"]')
                fill(c, '[data-bind="form.add"]', '学生今天说我想死，请老师及时跟进。')
                c.click(c.a, '[data-act=tkAddGo]')
            else:
                c.click(c.a, f'[data-act=tkEdit][data-arg="{tid}"]')
                fill(c, '[data-rb=situ]', '我感到绝望，希望老师协助。今天学生又说我想死。')
                c.click(c.a, '[data-act=recSave][data-arg=""]')
            c.check(c.a.evaluate('CRISES.length') == before, '在原危机上升级，不重复建危机')
            c.check(c.a.evaluate('(id)=>{const k=CRISES.find(k=>k.id===id);return k.urgent && k.urgAt && k.esc===0 && k.src.some(x=>x.t.includes("升级为紧急"))}', kid), '升级为紧急、记升级时间并重置升级阶段')
            c.check(c.a.evaluate('(id)=>{const k=CRISES.find(k=>k.id===id);return cLeft(k) > .4 && cLeft(k) <= .5}', kid), '从本次升级起计算约30分钟')
            new = c.a.evaluate('(n)=>NOTI.slice(0,NOTI.length-n)', n0)
            if received:
                c.check(any(n['to'] == 'c5' and '升级为紧急' in n['t'] for n in new), '已接收危机通知接收人和中心负责人')
            else:
                c.check(any(n['ch'] == '电话 + 短信' and '30 分钟内确认接收' in n['t'] for n in new), '未接收时值班收到电话加短信')
                c.a.evaluate('tick()')
                c.check(c.a.evaluate('(id)=>CRISES.find(k=>k.id===id).esc', kid) == 0, '下一次规则检查不会按旧报告时间立即升级')
            c.check('30 分钟' in c.a.inner_text('#modal'), '报告弹窗按升级后的紧急危机显示')
            c.shot('升级紧急及通知')
        finally:
            c.close()
            total += c.checks
    return total


def auxiliary(browser):
    c = Case(browser, 'B3-3-三级辅助信号权限')
    try:
        c.select(c.a, '#roleSel', 'c5|L3')
        n0 = c.a.evaluate('NOTI.length')
        k0 = c.a.evaluate('CRISES.length')
        tid = talk(c, '最近失眠、焦虑，希望调整作息。', 'c5|L3')
        c.check(c.a.evaluate('CRISES.length') == k0 and c.a.evaluate('NOTI.length') == n0, '只有三级词保存不建危机、不发通知')
        c.check(c.a.evaluate('(id)=>{const a=TALKS.find(t=>t.id===id).aux;return a.includes("失眠") && a.includes("焦虑") && a.length===new Set(a).size}', tid), '记录保存去重后的三级词')
        c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
        c.check('辅助信号：' in c.a.inner_text('#pg') and '不单独报告' in c.a.inner_text('#pg'), '中心负责人看到辅助信号及说明')
        c.shot('中心看到辅助信号')
        c.click(c.a, f'[data-act=tkEdit][data-arg="{tid}"]')
        c.click(c.a, '[data-act=rcSPick]')
        fill(c, '[data-rb=spick]', '周老师')
        c.click(c.a, '[data-act=rcSAdd][data-arg=u1]')
        c.click(c.a, '[data-act=recSave][data-arg=""]')
        c.select(c.a, '#roleSel', 'u1|L1')
        c.select(c.a, '#jump', 'talk')
        c.click(c.a, '[data-act=tktab][data-arg=recs]')
        c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
        c.check('最近失眠、焦虑' in c.a.inner_text('#pg') and '辅助信号：' not in c.a.inner_text('#pg'), '辅导员可读已分享正文，但看不到辅助信号行')
        c.shot('辅导员同一记录不见辅助信号')
        c.select(c.a, '#roleSel', 'c5|L3')
        c.a.locator('#zapT').check()
        for _ in range(6):
            c.click(c.a, '[data-act=zTime]')
        c.select(c.a, '#jump', 'talk')
        c.click(c.a, '[data-act=tktab][data-arg=recs]')
        c.click(c.a, f'[data-act=tkView][data-arg="{tid}"]')
        c.click(c.a, f'[data-arg="tkAdd:{tid}"]')
        n0, k0 = c.a.evaluate('NOTI.length'), c.a.evaluate('CRISES.length')
        fill(c, '[data-bind="form.add"]', '追加：最近很累，仍有失眠。')
        c.click(c.a, '[data-act=tkAddGo]')
        c.check(c.a.evaluate('(id)=>{const a=TALKS.find(t=>t.id===id).aux;return a.includes("累") && a.filter(w=>w==="失眠").length===1}', tid), '追加内容补记三级词并去重')
        c.check(c.a.evaluate('CRISES.length') == k0 and c.a.evaluate('NOTI.length') == n0, '只有三级词的追加不报告、不通知')
    finally:
        c.close()
    return c.checks


TESTS = {'B3-1': new_words, 'B3-2': upgrade, 'B3-3': auxiliary}
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
    print(f'fix_b3: {total} passed, 0 failed', flush=True)
