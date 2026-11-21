"""Real Qt signal calls must preserve Python singletons and exit cleanly."""
import os
import subprocess
import sys


def test_repeated_qt_signal_callbacks_preserve_none_and_process_shutdown():
    # A child interpreter makes finalization part of the assertion. PySide 6.12
    # corrupts singleton references on CPython 3.11 even in this isolated Qt
    # probe, without customer images or SolarCheck windows.
    script = '''
import gc
import json
import sys
from PySide6.QtCore import QObject, Signal, Slot
class Probe(QObject):
    fired = Signal()
    @Slot()
    def receive(self):
        pass
probe = Probe()
probe.fired.connect(probe.receive)
for _ in range(50):
    probe.fired.emit()
gc.collect()
before = sys.getrefcount(None)
for _ in range(500):
    probe.fired.emit()
after = sys.getrefcount(None)
print(json.dumps(dict(before=before, after=after)), flush=True)
assert after >= before - 10, 'Qt callbacks lose references to None'
probe.fired.disconnect()
del probe
gc.collect()
'''
    process = subprocess.run([sys.executable, '-c', script], capture_output=True,
        text=True, timeout=30, env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    assert process.returncode == 0, process.stdout + process.stderr
