"""Local Chrome cleanup watchdog and UI synchronization.
Business assertions and application state are unchanged. Wait for an existing
admin toast render before filling text; force-stop this test's own driver only
if Browser.close() stalls after test completion.
"""
import runpy
import sys
import threading
from pathlib import Path
from playwright.sync_api import Browser, Locator

close_original = Browser.close

def close_browser(self, *args, **kwargs):
    proc = self._impl_obj._connection._transport._proc
    timed_out = threading.Event()
    def stop_own_driver():
        timed_out.set()
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    watchdog = threading.Timer(12, stop_own_driver)
    watchdog.daemon = True
    watchdog.start()
    try:
        return close_original(self, *args, **kwargs)
    except Exception:
        if not timed_out.is_set():
            raise
        print('HARNESS: recovered a Chrome driver shutdown stall after test completion', flush=True)
    finally:
        watchdog.cancel()

Browser.close = close_browser
# Wait for the admin toast's scheduled render before entering text. This only
# synchronizes UI automation; no application state or assertion is changed.
fill_original = Locator.fill

def stable_fill(self, value, *args, **kwargs):
    self.evaluate("""() => new Promise(resolve => {
      if (!document.querySelector('#roleSel') || typeof S === 'undefined' || !S.toast) return resolve();
      const started = Date.now(), timer = setInterval(() => {
        if (!S.toast || Date.now() - started > 4000) { clearInterval(timer); resolve(); }
      }, 40);
    })""")
    return fill_original(self, value, *args, **kwargs)

Locator.fill = stable_fill
path = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(path.parent))
sys.argv[0] = str(path)
runpy.run_path(str(path), run_name='__main__')
