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
        page.screenshot(path=str(path / f'{name}.png'), full_page=True, animations='disabled')

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

def illness(browser):
    context, page, admin, student = trial(browser)
    try:
        bid = book_lin(admin, student)
        admin.evaluate('(id)=>{ACT.bOk(id);render()}', bid)
        wait(student, "S.bk && S.bk.st==='已确认'")
        operations = student.evaluate('JSON.stringify(S.ops)')
        # Include all three active states in the affected-slot fixture.
        admin.evaluate("""(id)=>{
          const base=BOOK.find(b=>b.id===id), others=STU.filter(s=>!Object.values(LY_CORE()).some(c=>c.id===s.id)).slice(0,2);
          others.forEach((s,i)=>{BOOK.push({...base,id:'b1_sick_'+i,sid:s.id,t:i,st:i?'change':'confirm',req:i?{type:'取消'}:null});setSlot('c1',7,i,'bk')});render();
        }""", bid)
        schedule = admin.evaluate("JSON.stringify(SCHM.c1['10/21'])")
        log_count = admin.evaluate('(RULES.schedLog||[]).length')
        admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'计划性关时段',rgd:'7',rga:'all'};ACT.schedRegGo();render()")
        check('这些时段上还有 3 个预约，先改时间或婉拒，再关' in admin.inner_text('#toast'), 'B1-3 planned closure is blocked by active bookings')
        check(admin.evaluate("JSON.stringify(SCHM.c1['10/21'])") == schedule and admin.evaluate('(RULES.schedLog||[]).length') == log_count, 'B1-3 blocked registration leaves schedule and log unchanged')
        page.click('[data-side="机构端"]')
        admin.evaluate("ACT.mo('schedReg:');render()")
        check(admin.locator('[data-bind="form.rgd"]').count() == 0 and admin.locator('[data-act=fset][data-arg="rgd|0"]').count() == 1, 'B1-3 date buttons replace free text and include today')
        admin.locator('[data-act=fset][data-arg="rgc|c1"]').click()
        admin.locator('[data-act=fset][data-arg="rgt|病假停诊"]').click()
        admin.locator('[data-act=fset][data-arg="rgd|7"]').click()
        admin.locator('[data-act=fset][data-arg="rga|all"]').click()
        shot(page, 'B1-3-register')
        admin.locator('[data-act=schedRegGo]').click()
        wait(student, 'S.bk===null')
        check(admin.evaluate('(id)=>{const b=BOOK.find(x=>x.id===id);return b.st==="adjust"&&b.adj.why==="老师病假停诊"&&!!b.adj.at}', bid), 'B1-3 confirmed booking becomes adjust with reason and timestamp')
        check(admin.evaluate("BOOK.filter(b=>b.id.startsWith('b1_sick_')).every(b=>b.st==='adjust')"), 'B1-3 pending and change-request bookings are also adjusted')
        check(admin.evaluate("SCHM.c1['10/21'].every(v=>v==='off')"), 'B1-3 sick leave closes every selected daily slot')
        wait(student, "[0,1,2,3].every(t=>slotState(0,6,t)==='closed')")
        check(student.evaluate("S.bkHist[0].st") == '中心调整' and student.evaluate('JSON.stringify(S.ops)') == operations, 'B1-3 history records center adjustment without using cancellation allowance')
        message = '原定的时间因老师临时有事取消了，老师会尽快重新和你约。'
        check(student.evaluate('S.inbox[0].d[0]') == message and message in student.inner_text('#modal'), 'B1-3 inbox and popup use the exact agreed text')
        check(admin.evaluate("NOTI.some(n=>n.to==='c5'&&n.t.includes('中心调整'))&&NOTI.some(n=>n.to===ivResp(CORE.lin)&&n.t.includes('中心调整'))"), 'B1-3 center lead and responsible teacher are notified')
        check(admin.evaluate('LY_snap().__adj.lin') == 1, 'B1-3 snapshot distinguishes adjustment from decline')
        admin.evaluate("ACT.btab('man');ACT.bsub('adjust');render()")
        check('中心调整 · 待重新安排' in admin.inner_text('#pg') and admin.locator(f'[data-arg="bMove:{bid}"]').count() == 1 and admin.locator(f'[data-arg="bNo:{bid}"]').count() == 1, 'B1-3 center lead sees adjustment row and its two actions')
        shot(page, 'B1-3-center-adjustment')
        page.click('[data-side="学生端"]')
        shot(page, 'B1-3-student-notice')
        admin.evaluate("enter('c1','L2','B1');go('booking');ACT.btab('man');ACT.bsub('adjust');render()")
        check(admin.locator(f'[data-arg="bMove:{bid}"]').count() == 1, 'B1-3 appointment teacher sees the adjustment')
        admin.evaluate("enter('c2','L2','B1');go('booking');ACT.btab('man');ACT.bsub('adjust');render()")
        check(admin.locator(f'[data-arg="bMove:{bid}"]').count() == 0, 'B1-3 another teacher does not see this adjustment row')
        admin.evaluate("enter('c5','L3','B1');go('booking');ACT.btab('sched');render()")
        before = admin.evaluate("SCHM.c1['10/23'].slice()")
        page.click('[data-side="机构端"]')
        admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'计划性关时段',rgd:'9',rga:'part'};render()")
        admin.locator('input[data-act=fArr][data-arg="rgts|2"]').check()
        admin.locator('[data-act=schedRegGo]').click()
        after = admin.evaluate("SCHM.c1['10/23'].slice()")
        check(after[2] == 'off' and all(after[t] == before[t] for t in [0,1,3]), 'B1-3 selected-slot closure changes only the checked time')
        before = admin.evaluate("JSON.stringify(SCHM.c1['10/22'])")
        admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'改班',rgd:'8',rga:'all'};ACT.schedRegGo();render()")
        check(admin.evaluate("JSON.stringify(SCHM.c1['10/22'])") == before, 'B1-3 shift-change registration keeps the existing schedule')
    finally:
        context.close()

def risk_limits(browser):
    for urgent, text in [(False, '我感到绝望'), (True, '我想死')]:
        context, page, admin, student = trial(browser)
        try:
            page.click('[data-side="机构端"]')
            admin.evaluate("enter('u1','L1','B1');go('talk');render()")
            sid = admin.evaluate("STU.find(s=>tkScope(s)&&!CRISES.some(k=>k.sid===s.id&&k.st!=='closed')).id")
            admin.evaluate("""([sid,text])=>{cwHits=[];ACT.tkNew(sid);Object.assign(S.rec,{mode:'面对面',place:'办公室',result:'已谈',situ:text,sis:false,types:['心理健康']});ACT.recSave('');render()}""", [sid, text])
            check(admin.evaluate('S.mo && S.mo.startsWith("tkCrisis:")'), f'B1-4 formal record {text} opens the report receipt')
            kid = admin.evaluate('S.mo.split(":")[1]')
            crisis = admin.evaluate('(id)=>{const k=CRISES.find(x=>x.id===id);return {urgent:k.urgent,limit:kLim(k),left:cLeft(k),record:k.fromRec}}', kid)
            check(crisis['urgent'] == urgent, f'B1-4 {text} has the correct urgency')
            limit = 0.5 if urgent else 4
            check(crisis['limit'] == limit and limit - 0.15 < crisis['left'] <= limit, f'B1-4 {text} countdown starts near {limit} hours')
            popup = admin.inner_text('#modal')
            if urgent:
                check('已报告紧急情况' in popup and '30 分钟' in popup and '先留在学生身边' in popup, 'B1-4 urgent popup retains the original 30-minute guidance')
            else:
                check('已报告，按一般时限处理' in popup and '4 小时内确认接收' in popup and '12 小时升级分管领导' in popup, 'B1-4 general popup separates 4-hour confirmation and 12-hour escalation')
                check('先留在学生身边' not in popup and '995' not in popup, 'B1-4 general popup omits emergency-only guidance')
            expected_time = '30 分钟' if urgent else '4 小时'
            check(admin.evaluate('([id,time])=>NOTI.some(n=>n.ref===id&&n.to===dutyNow()&&n.t.includes(time))', [kid, expected_time]), f'B1-4 notification agrees with {expected_time} limit')
            shot(page, 'B1-4-urgent' if urgent else 'B1-4-general')
            admin.evaluate('(id)=>{ACT.tkView(id);render()}', crisis['record'])
            marker = admin.inner_text('.tkrisk')
            check(('已报告紧急情况' if urgent else '已报告（一般时限）') in marker, f'B1-4 {text} record marker follows its associated crisis')
            admin.evaluate('(id)=>{const k=CRISES.find(x=>x.id===id);k.esc=1;render()}', kid)
            progress = admin.evaluate('l1Extras()')
            check(expected_time + '内未确认' in progress, f'B1-4 counsellor progress uses {expected_time}')
            admin.evaluate('(id)=>{CRISES.find(x=>x.id===id).esc=0;enter("c5","L3","B1");go("crisis");S.crisis=id;render()}', kid)
            # Audit actions advance the demo clock by a minute, so urgent time is already below 30.
            expected_countdown = admin.evaluate('(id)=>"剩 "+Math.max(1,Math.round(cLeft(CRISES.find(x=>x.id===id))*60))+" 分钟"', kid) if urgent else '剩 4 小时'
            check(expected_countdown in admin.inner_text('#pg'), f'B1-4 center displays the matching countdown for {text}')
            if not urgent:
                check(admin.evaluate('(id)=>{const k=CRISES.find(x=>x.id===id),old=RULES.esc;RULES.esc=6;const ok=kLim(k)===6;RULES.esc=old;return ok}', kid), 'B1-4 general limit follows configured RULES.esc')
        finally:
            context.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['B1-2', 'B1-1', 'B1-3', 'B1-4'])
    args = parser.parse_args()
    tests = {'B1-2': slots, 'B1-1': conflicts, 'B1-3': illness, 'B1-4': risk_limits}
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
