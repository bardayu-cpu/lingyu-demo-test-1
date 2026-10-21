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
        check('这个时间已由 林晓 先申请，请改时间或婉拒' in admin.inner_text('#toast'), 'B1-1 duplicate confirmation names the first applicant')
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
        check(admin.evaluate('LY_snap().lin.st') == 'adjust' and admin.evaluate('!Object.hasOwn(LY_snap(),"__adj")'), 'B1-3 snapshot tracks the actual adjust state without __adj flags')
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
            expected_progress = expected_time + ('内未确认' if urgent else '内没人确认接收')
            check(expected_progress in progress, f'B1-4 counsellor progress uses {expected_time}')
            admin.evaluate('(id)=>{CRISES.find(x=>x.id===id).esc=0;enter("c5","L3","B1");go("crisis");S.crisis=id;render()}', kid)
            # Audit actions advance the demo clock by a minute, so urgent time is already below 30.
            expected_countdown = admin.evaluate('(id)=>"剩 "+Math.max(1,Math.round(cLeft(CRISES.find(x=>x.id===id))*60))+" 分钟"', kid) if urgent else '剩 4 小时'
            check(expected_countdown in admin.inner_text('#pg'), f'B1-4 center displays the matching countdown for {text}')
            if not urgent:
                check(admin.evaluate('(id)=>{const k=CRISES.find(x=>x.id===id),old=RULES.esc;RULES.esc=6;const ok=kLim(k)===6;RULES.esc=old;return ok}', kid), 'B1-4 general limit follows configured RULES.esc')
        finally:
            context.close()

def clash_chen(admin):
    admin.evaluate("LY_in({t:'book',core:'chen',cid:'c1',date:DD(7).toISOString(),ti:2,kind:'预咨询'});render()")
    return admin.evaluate("BOOK.filter(b=>b.sid===CORE.chen.id&&b.st==='confirm').slice(-1)[0].id")

def admin_open(admin):
    return admin.evaluate("""(()=>{
      for(let day=1;day<5;day++) for(let t=0;t<TIMES.length;t++)
        if(slotAt('c1',day,t)==='open') return {day,t,date:DD(day).toISOString()};
      throw new Error('No open fixture slot');
    })()""")

def resync_review(browser):
    context, page, admin, student = trial(browser)
    try:
        first = book_lin(admin, student)
        second = clash_chen(admin)
        admin.evaluate('(id)=>{S.form={why:"时段冲突"};ACT.bNoOk(id);render()}', second)
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'bk', '打回-1 declining the later conflict keeps the first reservation')
        check(admin.evaluate('(id)=>{const b=BOOK.find(x=>x.id===id);return b.st==="confirm"&&!b.clash}', first), '打回-1 first pending request is preserved without a conflict marker')
        student.evaluate("reset('D');prepare('book');S.day=6;render()")
        wait(student, "slotState(0,6,2)==='taken'")
        check(student.evaluate("slotBtn(DATA.counsellors[0],6,2,slotState(0,6,2)).includes('已约满')"), '打回-1 Wang sees the time as full after declining Chen')
        admin.evaluate('(id)=>{S.form={why:"老师临时有安排"};ACT.bNoOk(id);render()}', first)
        wait(student, "slotState(0,6,2)==='open'")
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'open', '打回-1 declining the last application releases the slot')
    finally:
        context.close()
    # Exercise every old-slot mutation path named in the review.
    for action in ['confirmed_decline', 'move', 'agree_cancel', 'agree_reschedule', 'incoming_cancel', 'incoming_book']:
        context, page, admin, student = trial(browser)
        try:
            first = book_lin(admin, student)
            if action != 'confirmed_decline':
                second = clash_chen(admin)
            if action in ['confirmed_decline', 'move', 'agree_cancel', 'agree_reschedule']:
                admin.evaluate('(id)=>{ACT.bOk(id);render()}', first)
            new = admin_open(admin) if action in ['move', 'agree_reschedule', 'incoming_book'] else None
            if action == 'confirmed_decline':
                admin.evaluate('(id)=>{S.form={why:"老师临时有安排"};ACT.bNoOk(id);render()}', first)
                check(admin.evaluate("SCHM.c1['10/21'][2]") == 'open', '打回-1 declining a confirmed booking releases its last held slot')
            elif action == 'move':
                admin.evaluate('([id,p])=>{S.form={slot:p.day+"-"+p.t};ACT.bMoveOk(id);render()}', [first, new])
            elif action in ['agree_cancel', 'agree_reschedule']:
                admin.evaluate('([id,p,cancel])=>{const b=BOOK.find(x=>x.id===id);b.st="change";b.req=cancel?{type:"取消"}:{type:"改期",day:p.day,t:p.t};ACT.bAgree(id);render()}', [first, new, action == 'agree_cancel'])
            elif action == 'incoming_cancel':
                admin.evaluate("LY_in({t:'cancel',core:'lin'});render()")
            else:
                admin.evaluate('(p)=>{LY_in({t:"book",core:"lin",cid:"c1",date:p.date,ti:p.t,kind:"预咨询"});render()}', new)
            if action != 'confirmed_decline':
                check(admin.evaluate("SCHM.c1['10/21'][2]") == 'bk', f'打回-1 {action} preserves the remaining reservation')
                check(admin.evaluate('(id)=>!BOOK.find(x=>x.id===id).clash', second), f'打回-1 {action} clears the sole remaining request conflict')
        finally:
            context.close()
    context, page, admin, student = trial(browser)
    try:
        first = book_lin(admin, student)
        admin.evaluate('(id)=>{RULES.offSlots={"c1|7|2":1};S.form={why:"老师临时有安排"};ACT.bNoOk(id);render()}', first)
        check(admin.evaluate("SCHM.c1['10/21'][2]") == 'off', '打回-1 registered closure takes precedence over release')
    finally:
        context.close()

def sick_lin(admin, student):
    bid = book_lin(admin, student)
    admin.evaluate('(id)=>{ACT.bOk(id);render()}', bid)
    wait(student, "S.bk && S.bk.st==='已确认'")
    admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'病假停诊',rgd:'7',rga:'all'};ACT.schedRegGo();render()")
    wait(student, 'S.bk===null && S.bkHist[0].st==="中心调整"')
    return bid

def adjustment_review(browser):
    for action in ['move', 'future_move', 'decline', 'student_book', 'reopen']:
        context, page, admin, student = trial(browser)
        try:
            operations = student.evaluate('JSON.stringify(S.ops)')
            first = sick_lin(admin, student)
            check(admin.evaluate("[0,1,2,3].every(t=>RULES.offSlots['c1|7|'+t]&&SCHM.c1['10/21'][t]==='off')"), f'打回-2 {action}: sick leave records every closed time')
            check(admin.evaluate('LY_snap().lin.st') == 'adjust' and admin.evaluate('!Object.hasOwn(LY_snap(),"__adj")'), f'打回-2 {action}: snapshot exposes adjust directly')
            if action in ['move', 'future_move', 'decline']:
                page.click('[data-side="机构端"]')
                admin.evaluate("enter('c1','L2','review');go('booking');ACT.btab('man');ACT.bsub('adjust');render()")
                check(admin.locator('[data-act=bsub][data-arg=adjust] i.r').count() == 1, f'打回-2 {action}: teacher has a red adjustment count')
                if action in ['move', 'future_move']:
                    new = admin_open(admin) if action == 'move' else admin.evaluate("(()=>{for(let day=5;day<10;day++)for(let t=0;t<4;t++)if(slotAt('c1',day,t)==='open')return {day,t,date:DD(day).toISOString()};throw Error('No future opening')})()")
                    admin.locator(f'[data-arg="bMove:{first}"]').click()
                    check(admin.locator('[data-arg^="slot|"]').count() == 0, 'B2-1 rearrangement starts with date choices only')
                    admin.locator(f'[data-act=mvDay][data-arg="{new["day"]}"]').click()
                    target = admin.locator(f'[data-act=fset][data-arg="slot|{new["day"]}-{new["t"]}"]')
                    check(target.count() == 1, '打回-2 next-week rearrangement is selectable after choosing its date')
                    check(admin.locator('[data-act=mvDay][data-arg="7"]').count() == 0, '打回-2 registered sick-leave day is absent from rearrangement choices')
                    target.click()
                    check('等学生确认' in admin.locator('[data-act=bMoveOk]').inner_text(), 'B2-1 rearrangement explicitly waits for the student')
                    admin.locator('[data-act=bMoveOk]').click()
                    wait(student, "S.bk && S.bk.st==='已改约'")
                    check(admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', first) == 'move', 'B2-1 center adjustment is not confirmed before student acceptance')
                    check(student.evaluate('S.inbox[0].d[0].startsWith("老师重新为你安排了时间：")') and '点「接受新时间」就约好了' in student.inner_text('#modal'), '打回-2 rearrangement reaches inbox and popup with acceptance guidance')
                    page.click('[data-side="学生端"]')
                    shot(page, f'打回-2-重新安排通知-{action}')
                    student.locator('#modal [data-act=movedOk]').click()
                    wait(admin, f'BOOK.find(b=>b.id==={first!r}).st==="ok"')
                    wait(student, "S.bk && S.bk.st==='已确认'")
                    booked = student.evaluate('({cid:S.bk.cid,date:DAYS[S.bk.di].toDateString(),ti:S.bk.ti,kind:S.bk.kind})')
                    expected_date = admin.evaluate('(date)=>new Date(date).toDateString()', new['date'])
                    check(booked == {'cid': 'c1', 'date': expected_date, 'ti': new['t'], 'kind': '预咨询'}, '打回-2 teacher rearrangement restores the actual confirmed appointment')
                    check(admin.evaluate('(id)=>{const b=LY_snap().lin;return b.id===id&&b.st==="ok"&&BOOK.filter(x=>x.sid===CORE.lin.id&&LY_ACTIVE.includes(x.st)).length===1}', first), '打回-2 rearrangement keeps the same admin booking and creates no echo request')
                    page.click('[data-side="学生端"]')
                    shot(page, f'打回-2-重新安排通知-{action}')
                    student.evaluate("ACT.close();ACT.go('mybook');render()")
                    check(student.locator('[data-act=resch]').count() == 1, '打回-2 the restored appointment can continue into rescheduling')
                else:
                    admin.locator(f'[data-arg="bNo:{first}"]').click()
                    admin.locator('[data-act=fset][data-arg^="why|"]').first.click()
                    admin.locator('[data-act=bNoOk]').click()
                    wait(student, 'S.info && S.info.body==="老师这次没能重新安排，请重新选一个时间。"')
                    check(student.evaluate('S.bk') is None and student.evaluate('S.inbox[0].d[0]') == '老师这次没能重新安排，请重新选一个时间。', '打回-2 declining adjustment sends the exact new-time invitation')
                    check(student.evaluate('S.info.btn[0]') == 'book', '打回-2 decline notification links to counselling booking')
                    page.click('[data-side="学生端"]')
                    shot(page, '打回-2-婉拒后重新选时间')
            elif action == 'student_book':
                from test_support import pick_open
                student.evaluate("ACT.close();prepare('book');render()")
                picked = pick_open(student, 'c1', 6, 2)
                student.evaluate('ACT.bookSubmit();render()')
                wait(admin, f'BOOK.find(b=>b.id==={first!r}).st==="cancelled"')
                check(admin.evaluate('(id)=>{const b=LY_snap().lin;return b&&b.id!==id&&b.st==="confirm"}', first), '打回-2 student rebooking cancels adjust and creates a new pending request')
                check(admin.evaluate('(date)=>sameDay(new Date(LY_snap().lin.date),new Date(date))', picked['date']), '打回-2 the new pending request uses the student-selected date')
            else:
                page.click('[data-side="机构端"]')
                admin.evaluate("ACT.schPick('c1|10/21');render()")
                admin.locator('[data-act=mslot][data-arg="10/21|2"]').click()
                admin.locator('[data-act=mSave]').click()
                check(admin.evaluate("!RULES.offSlots['c1|7|2']&&[0,1,3].every(t=>RULES.offSlots['c1|7|'+t])"), '打回-2 reopening one saved slot clears only its closure marker')
                admin.evaluate("slotResync('c1',7,2);render()")
                wait(student, "slotState(0,6,2)==='open'")
                check(admin.evaluate("SCHM.c1['10/21'][2]") == 'open', '打回-2 explicit reopening survives later resync')
            if action != 'reopen':
                check(admin.evaluate("SCHM.c1['10/21'].every(v=>v==='off')"), f'打回-2 {action}: all original sick-leave slots stay closed')
                wait(student, "[0,1,2,3].every(t=>slotState(0,6,t)==='closed')")
            check(student.evaluate('JSON.stringify(S.ops)') == operations, f'打回-2 {action}: center actions do not use student operation allowances')
        finally:
            context.close()
    context, page, admin, student = trial(browser)
    try:
        admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'计划性关时段',rgd:'9',rga:'part',rgts:['2']};ACT.schedRegGo();slotResync('c1',9,2);render()")
        check(admin.evaluate("RULES.offSlots['c1|9|2']&&SCHM.c1['10/23'][2]==='off'"), '打回-2 planned closure also persists through resync')
        first = book_lin(admin, student)
        admin.evaluate("ACT.mo('schedReg:');S.form={rgc:'c1',rgt:'计划性关时段',rgd:'7',rga:'all'};ACT.schedRegGo();render()")
        check(admin.evaluate("!RULES.offSlots['c1|7|2']") and admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', first) == 'confirm', '打回-2 blocked planned closure does not record a false closure')
    finally:
        context.close()

def crisis_copy_review(browser):
    for urgent, text in [(False, '我感到绝望'), (True, '我想死')]:
        context, page, admin, student = trial(browser)
        try:
            page.click('[data-side="机构端"]')
            admin.evaluate("enter('u1','L1','review');go('talk');render()")
            sid = admin.evaluate("STU.find(s=>tkScope(s)&&!CRISES.some(k=>k.sid===s.id&&k.st!=='closed')).id")
            admin.evaluate("([sid,text])=>{cwHits=[];ACT.tkNew(sid);Object.assign(S.rec,{mode:'面对面',place:'办公室',result:'已谈',situ:text,sis:false,types:['心理健康']});ACT.recSave('');render()}", [sid, text])
            kid = admin.evaluate('S.mo.split(":")[1]')
            tid = admin.evaluate('(id)=>CRISES.find(k=>k.id===id).fromRec', kid)
            name = admin.evaluate('(id)=>SU(id).name', sid)
            admin.evaluate("ACT.moClose();S.rv=null;S.rec=null;go('talk');S.tabs.talk='recs';render()")
            expected = '已报告紧急情况' if urgent else '已报告（一般时限）'
            row = admin.locator(f'tr:has([data-act=tkView][data-arg="{tid}"]) .tkrisk')
            check(expected in row.inner_text(), f'打回-3 {text}: actual talk list uses the associated urgency')
            shot(page, '打回-3-紧急列表' if urgent else '打回-3-一般时限列表')
            admin.locator(f'[data-act=tkView][data-arg="{tid}"]').click()
            check(expected in admin.inner_text('.tkrisk'), f'打回-3 {text}: detail uses the same urgency wording')
            if urgent:
                admin.evaluate('NOW.setTime(NOW.getTime()+H);tick();render()')
            else:
                admin.evaluate('ACT.zTime();NOW.setTime(NOW.getTime()+H);tick();render()')
            check(admin.evaluate('(id)=>CRISES.find(k=>k.id===id).esc', kid) >= 1, f'打回-3 {text}: the real demo clock triggers escalation')
            admin.evaluate("go('home');S.hv='work';S.full=true;render()")
            progress = admin.locator('#pg .head').filter(has_text='你报告的紧急情况 · ' + name).inner_text()
            if urgent:
                check('30 分钟内未确认，已再次呼叫并通知中心负责人朱静' in progress, '打回-3 urgent escalation retains 30-minute repeat-call wording')
                check(admin.evaluate('(id)=>NOTI.some(n=>n.ref===id&&n.ch.includes("追呼"))', kid), '打回-3 urgent escalation still makes a repeat call')
                check(admin.evaluate('(id)=>NOTI.some(n=>n.ref===id&&n.to===me()&&n.t.includes("已再次呼叫并通知中心负责人"))', kid), '打回-3 urgent notification receipt agrees with the actual repeat call')
            else:
                check('4 小时内没人确认接收，已通知中心负责人朱静' in progress and '再次呼叫' not in progress, '打回-3 general escalation names the lead without claiming a repeat call')
                check(admin.evaluate('(id)=>!NOTI.some(n=>n.ref===id&&n.ch.includes("追呼"))', kid), '打回-3 general escalation makes no repeat duty call')
                check(admin.evaluate('(id)=>NOTI.some(n=>n.ref===id&&n.to===me()&&n.t.includes("已通知中心负责人")&&!n.t.includes("再次呼叫"))', kid), '打回-3 general notification receipt also omits the false repeat-call claim')
            shot(page, '打回-3-紧急升级进度' if urgent else '打回-3-一般升级进度')
        finally:
            context.close()

def conflict_priority_review(browser):
    context, page, admin, student = trial(browser)
    try:
        first = book_lin(admin, student)
        second = clash_chen(admin)
        page.click('[data-side="机构端"]')
        admin.evaluate("enter('c1','L2','review');go('booking');ACT.btab('man');ACT.bsub('ok');render()")
        check(admin.locator(f'[data-act=bOk][data-arg="{second}"]').count() == 0, '打回-4 conflicting request has no confirm button')
        check(admin.locator(f'.bkpin button[data-act=bOpen][data-arg="{second}"]').count() == 1 and admin.locator(f'.bkpin [data-arg="bMove:{second}"]').count() == 1 and admin.locator(f'.bkpin [data-arg="bNo:{second}"]').count() == 1, '打回-4 conflicting row retains student information, move, and decline')
        pill = admin.locator('.bkpin tr').filter(has=admin.locator(f'[data-act=bOpen][data-arg="{second}"]')).locator('.pill.r')
        check(pill.get_attribute('title') == '这个时间已由 林晓 先申请', '打回-4 conflict title identifies the first applicant')
        admin.evaluate('(id)=>{ACT.bOk(id);render()}', second)
        check(admin.evaluate('([a,b])=>[a,b].every(id=>BOOK.find(x=>x.id===id).st==="confirm")', [first, second]), '打回-4 forced confirmation cannot give the later applicant the first hold')
        check('这个时间已由 林晓 先申请，请改时间或婉拒' in admin.inner_text('#toast'), '打回-4 forced confirmation explains the first applicant priority')
        shot(page, '打回-4-冲突行无确认')
        admin.evaluate("ACT.bsub('all');render()")
        check(admin.locator(f'[data-act=bOk][data-arg="{second}"]').count() == 0, '打回-4 the All table cannot offer a second confirmation entry')
        admin.evaluate("ACT.bsub('ok');render()")
        admin.locator(f'[data-arg="bNo:{first}"]').click()
        admin.locator('[data-act=fset][data-arg^="why|"]').first.click()
        admin.locator('[data-act=bNoOk]').click()
        check(admin.evaluate('(id)=>!BOOK.find(b=>b.id===id).clash', second), '打回-4 declining the first request clears the remaining conflict')
        check(admin.locator(f'[data-act=bOk][data-arg="{second}"]').count() == 1, '打回-4 the remaining request regains its confirm button')
        shot(page, '打回-4-首申请释放后恢复确认')
        admin.locator(f'[data-act=bOk][data-arg="{second}"]').click()
        check(admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', second) == 'ok' and admin.evaluate("SCHM.c1['10/21'][2]") == 'bk', '打回-4 remaining request confirms successfully and keeps its hold')
    finally:
        context.close()
    for state in ['ok', 'change']:
        context, page, admin, student = trial(browser)
        try:
            first = book_lin(admin, student)
            admin.evaluate('(id)=>{ACT.bOk(id);render()}', first)
            second = clash_chen(admin)
            admin.evaluate('([a,b,state])=>{const first=BOOK.find(x=>x.id===a);first.st=state;if(state==="change")first.req={type:"取消"};delete BOOK.find(x=>x.id===b).clash;ACT.bOk(b);render()}', [first, second, state])
            check(admin.evaluate('(id)=>BOOK.find(b=>b.id===id).st', second) == 'confirm', f'打回-4 legacy record without clash cannot double-confirm over {state}')
            check('这个时段已经确认给 林晓 了，请改时间或婉拒' in admin.inner_text('#toast'), f'打回-4 original {state} occupancy guard is retained')
        finally:
            context.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['B1-2', 'B1-1', 'B1-3', 'B1-4', '打回-1', '打回-2', '打回-3', '打回-4'])
    args = parser.parse_args()
    tests = {'B1-2': slots, 'B1-1': conflicts, 'B1-3': illness, 'B1-4': risk_limits, '打回-1': resync_review, '打回-2': adjustment_review, '打回-3': crisis_copy_review, '打回-4': conflict_priority_review}
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
