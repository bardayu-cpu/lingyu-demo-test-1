"""Select a real opening for existing integration-test fixtures."""
def pick_open(frame, cid, start_di=0, preferred_ti=0, only_day=False):
    frame.wait_for_function('typeof LY_SLOTS !== "undefined" && LY_SLOTS !== null')
    slot = frame.evaluate('''([cid,start,preferred,onlyDay])=>{
      const ci=DATA.counsellors.findIndex(c=>c.id===cid);
      const times=[preferred,...DATA.times.map((_,i)=>i).filter(i=>i!==preferred)];
      for(let di=start;di<DAYS.length && (!onlyDay || di===start);di++)
        for(const ti of times) if(slotState(ci,di,ti)==='open')
          return {arg:`${cid}:${di}:${ti}`,cid,di,ti,date:DAYS[di].toISOString()};
      return null;
    }''', [cid, start_di, preferred_ti, only_day])
    assert slot, f'No open fixture time for {cid}, day {start_di}'
    frame.evaluate('(arg)=>ACT.pickSlot(arg)', slot['arg'])
    print(f'PICK open shared slot {slot["arg"]}', flush=True)
    return slot
