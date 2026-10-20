"""Batch 1 acceptance checks. Run after both build.py scripts.

CHROMIUM_PATH=/path/to/chrome python 自动测试/fix_b1.py [--only B1-2]
"""
import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TRIAL = Path(os.environ.get('TRIAL_HTML', ROOT.parent / 'index.html')).resolve()
checks = 0
errors = []

def check(condition, label):
    global checks
    assert condition, label
    checks += 1
    print(f'PASS {label}', flush=True)

def wait(frame, expression):
    frame.wait_for_function(expression, timeout=10000)

def trial(browser):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://script.google.com/**', lambda route: route.fulfill(status=200, body='ok'))
    page.goto(TRIAL.as_uri())
    page.fill('#nm', 'B1 自动验证')
    page.click('[data-do=nameOk]')
    page.wait_for_selector('iframe[title="机构端"]', state='attached')
    admin = next(f for f in page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '机构端')
    student = next(f for f in page.frames if f.parent_frame and f.frame_element().get_attribute('title') == '学生端')
    wait(student, 'typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
    admin.evaluate("enter('c5','L3','B1');go('booking');ACT.btab('sched');render()")
    student.evaluate("reset('A');prepare('home');render()")
    return context, page, admin, student

def shot(page, name):
    directory = os.environ.get('B1_QA_DIR')
    if directory:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path / f'{name}.png'), full_page=True)

def book_lin(admin, student):
    student.evaluate("ACT.pickSlot('c1:6:2');ACT.bookSubmit();render()")
    wait(admin, "BOOK.some(b=>b.sid===CORE.lin.id && b.cid==='c1' && b.day===7 && b.t===2 && b.st==='confirm')")
    return admin.evaluate("BOOK.find(b=>b.sid===CORE.lin.id && b.cid==='c1' && b.day===7 && b.t===2 && b.st==='confirm').id")

def slots(browser):
    context, page, admin, student = trial(browser)
    try:
        page.click('[data-side="机构端"]')
        admin.evaluate("ACT.schPick('c1|10/21');render()")
        check(admin.evaluate("SCHM.c1['10/21'][0]") == 'off', 'B1-2 baseline 10/21 09:00 is closed')
        admin.locator('[data-act=mslot][data-arg="10/21|0"]').click()
        admin.locator('[data-act=mSave]').click()
        wait(student, "slotState(0,6,0)==='open'")
        check(student.evaluate('slotState(0,6,0)') == 'open', 'B1-2 saving a next-week slot reaches student')
        check(admin.evaluate("slotAt('c1',7,0)==='open' && slotAt('missing',7,0)==='off' && slotAt('c1',1,1)===SCHED.c1[1][1]"), 'B1-2 shared slot reader and absent-slot fallback')
        check(admin.evaluate("Object.keys(LY_snap().__slots).length===5 && LY_snap().__slots.c1['10/21']!==SCHM.c1['10/21'] && !LY_snap().__slots.c1['10/12']"), 'B1-2 snapshot has five teachers, copied rows, future dates')
        bid = book_lin(admin, student)
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'bk', 'B1-2 next-week application reserves the monthly slot')
        check(admin.locator('.mdetail .sch button.bk').count() >= 1, 'B1-2 weekly detail shows 已预约')
        shot(page, 'B1-2-reserved')
        student.evaluate("reset('B');prepare('book');S.day=6;render()")
        wait(student, "slotState(0,6,2)==='taken'")
        check('已约满' in student.inner_text('#app'), 'B1-2 other student sees 已约满')
        admin.evaluate('(id)=>{S.form={why:"老师临时有安排"};ACT.bNoOk(id);render()}', bid)
        wait(student, "slotState(0,6,2)==='open'")
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'open', 'B1-2 decline releases the same monthly slot')
        check(student.evaluate("(()=>{const old=LY_SLOTS;LY_SLOTS=null;const same=slotState(0,6,0)===_slotStateB1(0,6,0);LY_SLOTS=old;return same})()"), 'B1-2 standalone student retains original formula')
        admin.evaluate("setSlot('c1',1,0,'open');render()")
        wait(student, "slotState(0,0,0)==='early'")
        check(student.evaluate('slotState(0,0,0)') == 'early', 'B1-2 synced opening still enforces 24 hours')
    finally:
        context.close()

def conflicts(browser):
    context, page, admin, student = trial(browser)
    try:
        bid = book_lin(admin, student)
        student.evaluate("reset('B');prepare('book');S.day=6;render()")
        wait(student, "slotState(0,6,2)==='taken'")
        check(student.locator('button.tm.full[disabled]').filter(has_text='14:00').count() >= 1, 'B1-1 occupied time is disabled for another student')
        before = student.evaluate('JSON.stringify(S.bk)')
        student.evaluate("ACT.pickSlot('c1:6:2');ACT.bookSubmit();render()")
        check(student.evaluate('JSON.stringify(S.bk)') == before and student.evaluate('S.modal') is None, 'B1-1 forced pick/submit leaves booking unchanged and closes modal')
        check('这个时间刚被约走了，请换一个' in student.inner_text('#toast'), 'B1-1 forced submission explains the conflict')
        # A time selected while open can also be occupied before Submit is pressed.
        student.evaluate("ACT.pickSlot('c1:6:1');render()")
        check(student.evaluate('S.modal') == 'submit', 'B1-1 open time can be selected before it is occupied')
        admin.evaluate("setSlot('c1',7,1,'bk');render()")
        wait(student, "slotState(0,6,1)==='taken'")
        student.evaluate('ACT.bookSubmit();render()')
        check(student.evaluate('JSON.stringify(S.bk)') == before, 'B1-1 submit rechecks a time occupied after picking')
        result = admin.evaluate("LY_in({t:'book',core:'chen',cid:'c1',date:DD(7).toISOString(),ti:2,kind:'预咨询'})")
        admin.evaluate("ACT.btab('man');render()")
        other = admin.evaluate("BOOK.filter(b=>b.sid===CORE.chen.id&&b.day===7&&b.t===2&&b.st==='confirm').slice(-1)[0]")
        check(other['clash'] == bid and '时段冲突' in result, 'B1-1 admin retains a conflicting application with owner id and message')
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'bk', 'B1-1 conflict does not change the reserved slot')
        check(admin.locator('.bkpin .pill.r').filter(has_text='时段冲突').count() == 1, 'B1-1 pending row shows a red conflict pill')
        admin.evaluate('(id)=>{ACT.bOk(id);render()}', bid)
        admin.evaluate('(id)=>{ACT.bOk(id);render()}', other['id'])
        check(admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', bid) == 'ok' and admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', other['id']) == 'confirm', 'B1-1 second conflicting application cannot be confirmed')
        check('这个时段已经确认给 林晓 了，请改时间或婉拒' in admin.inner_text('#toast'), 'B1-1 duplicate confirmation names the existing student')
        # The exception for the current student's own held appointment remains usable.
        student.evaluate("reset('A');prepare('home');S.bk={cid:'c1',di:6,ti:2,kind:'预咨询',st:'待确认'};render();ACT.pickSlot('c1:6:2');render()")
        check(student.evaluate('S.modal') == 'submit', 'B1-1 current student can reopen their own held time')
        page.click('[data-side="机构端"]')
        shot(page, 'B1-1-conflict')
    finally:
        context.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['B1-2', 'B1-1'])
    args = parser.parse_args()
    tests = {'B1-2': slots, 'B1-1': conflicts}
    with sync_playwright() as p:
        choices = [os.environ.get('CHROMIUM_PATH'), '/opt/pw-browsers/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
        executable = next((c for c in choices if c and Path(c).is_file()), None)
        browser = p.chromium.launch(**({'executable_path': executable} if executable else {}))
        try:
            for name, test in tests.items():
                if not args.only or name == args.only:
                    test(browser)
            check(not errors, f'No browser errors: {errors}')
        finally:
            browser.close()
    print(f'fix_b1: {checks} passed, 0 failed', flush=True)

if __name__ == '__main__':
    main()
