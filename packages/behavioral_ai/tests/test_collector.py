import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import QApplication

from packages.behavioral_ai.legacy import main as collector


@pytest.fixture(scope='module')
def application():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def editor(application, monkeypatch):
    clock = iter([0, 50_000_000, 100_000_000, 150_000_000])
    monkeypatch.setattr(collector.time, 'perf_counter_ns', lambda: next(clock))
    widget = collector.TimingTextEdit()
    widget.set_measuring(True)
    yield widget
    widget.close()
    widget.deleteLater()


def key_event(editor, event_type, key, text, repeat=False):
    event = QKeyEvent(event_type, key, Qt.KeyboardModifier.NoModifier, text, repeat)
    if event_type == QEvent.Type.KeyPress:
        editor.keyPressEvent(event)
    else:
        editor.keyReleaseEvent(event)


def test_reversed_releases_preserve_press_order_and_overlap(editor):
    samples = []
    editor.sample_ready.connect(samples.append)
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_A, 'a')
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_B, 'b')
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_B, 'b')
    assert samples == []
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_A, 'a')
    assert samples == [
        {'dwell_ms': 150, 'down_down_ms': None, 'flight_ms': None},
        {'dwell_ms': 50, 'down_down_ms': 50, 'flight_ms': -100},
    ]


def test_auto_repeat_does_not_create_or_release_samples(editor):
    samples = []
    editor.sample_ready.connect(samples.append)
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_A, 'a')
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_A, 'a', repeat=True)
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_A, 'a', repeat=True)
    assert samples == []
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_A, 'a')
    assert samples == [{'dwell_ms': 50, 'down_down_ms': None, 'flight_ms': None}]


def test_focus_loss_discards_pending_press_and_breaks_transition(editor):
    samples = []
    interruptions = []
    editor.sample_ready.connect(samples.append)
    editor.measurement_interrupted.connect(lambda: interruptions.append(True))
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_A, 'a')
    editor.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert interruptions == [True]
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_A, 'a')
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_B, 'b')
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_B, 'b')
    assert samples == [{'dwell_ms': 50, 'down_down_ms': None, 'flight_ms': None}]


def test_long_gap_discards_missing_release(editor, monkeypatch):
    clock = iter([0, 3_000_000_000, 3_100_000_000, 3_150_000_000])
    monkeypatch.setattr(collector.time, 'perf_counter_ns', lambda: next(clock))
    samples = []
    editor.sample_ready.connect(samples.append)
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_A, 'a')
    # A's release was lost; a later press must start a new timing sequence.
    key_event(editor, QEvent.Type.KeyPress, Qt.Key.Key_B, 'b')
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_A, 'a')
    key_event(editor, QEvent.Type.KeyRelease, Qt.Key.Key_B, 'b')
    assert samples == [{'dwell_ms': 150, 'down_down_ms': None, 'flight_ms': None}]
