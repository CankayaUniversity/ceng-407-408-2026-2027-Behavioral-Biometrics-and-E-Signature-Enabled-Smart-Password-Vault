import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from collections import deque
from statistics import median

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QMessageBox,
)


class TimingTextEdit(QTextEdit):
    sample_ready = Signal(dict)
    measurement_interrupted = Signal()

    MAX_HOLD_NS = 2_000_000_000
    MAX_GAP_NS = 2_000_000_000

    def __init__(self):
        super().__init__()

        self.measuring = False

        # Henüz bırakılmamış tuşlar.
        self.pressed_keys = {}

        # Örnekleri basılma sırasıyla tamamlamak için kullanılır.
        self.pending_samples = deque()

        # Bir önceki fiziksel basışın kaydı.
        self.previous_sample = None

        self.setPlaceholderText(
            "Ölçümü başlattıktan sonra burada normal hızında yaz."
        )

    def reset_timing(self):
        self.pressed_keys.clear()
        self.pending_samples.clear()
        self.previous_sample = None

    def set_measuring(self, enabled):
        self.measuring = enabled
        self.reset_timing()

    def keyPressEvent(self, event):
        if self.measuring and not event.isAutoRepeat():
            now = time.perf_counter_ns()
            key = event.key()

            modifiers = event.modifiers()

            shortcut = bool(
                modifiers
                & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier
                    | Qt.KeyboardModifier.MetaModifier
                )
            )

            printable = (
                bool(event.text())
                and event.text().isprintable()
            )

            # Shift, büyük harf yazarken ölçüm dizisini bozmasın.
            shift_only = key == Qt.Key.Key_Shift

            if printable and not shortcut:
                # Uzun mola veya kaybolmuş bırakma olayı varsa
                # önceki diziyi devam ettirmiyoruz.
                long_gap = (
                    self.previous_sample is not None
                    and now - self.previous_sample["press_ns"]
                    > self.MAX_GAP_NS
                )

                stale_press = any(
                    now - sample["press_ns"] > self.MAX_HOLD_NS
                    for sample in self.pressed_keys.values()
                )

                if long_gap or stale_press:
                    self.reset_timing()

                if key not in self.pressed_keys:
                    sample = {
                        "press_ns": now,
                        "release_ns": None,
                        "previous": self.previous_sample,
                    }

                    self.pressed_keys[key] = sample
                    self.pending_samples.append(sample)
                    self.previous_sample = sample

            elif not shift_only:
                # Kısayol, silme, yön tuşu gibi girişler
                # bu ilk ölçüm sürümünün dışında.
                self.reset_timing()

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.measuring and not event.isAutoRepeat():
            now = time.perf_counter_ns()
            key = event.key()

            sample = self.pressed_keys.pop(key, None)

            if sample is not None:
                sample["release_ns"] = now
                self.emit_completed_samples()

        super().keyReleaseEvent(event)

    def emit_completed_samples(self):
        while self.pending_samples:
            sample = self.pending_samples[0]
            previous = sample["previous"]

            # Kendi bırakılma zamanı henüz bilinmiyor.
            if sample["release_ns"] is None:
                break

            # Geçiş süresi için önceki tuşun da bırakılmış
            # olması gerekiyor.
            if (
                previous is not None
                and previous["release_ns"] is None
            ):
                break

            self.pending_samples.popleft()

            dwell_ns = (
                sample["release_ns"] - sample["press_ns"]
            )

            down_down_ms = None
            flight_ms = None

            if previous is not None:
                previous_dwell_ns = (
                    previous["release_ns"]
                    - previous["press_ns"]
                )

                # Önceki basış geçerliyse geçiş özelliklerini ekle.
                if 0 < previous_dwell_ns <= self.MAX_HOLD_NS:
                    down_down_ms = (
                        sample["press_ns"]
                        - previous["press_ns"]
                    ) / 1_000_000

                    flight_ms = (
                        sample["press_ns"]
                        - previous["release_ns"]
                    ) / 1_000_000

            # Eski kayıtların bağlantı zincirini bellekte tutma.
            sample["previous"] = None

            if 0 < dwell_ns <= self.MAX_HOLD_NS:
                self.sample_ready.emit(
                    {
                        "dwell_ms": dwell_ns / 1_000_000,
                        "down_down_ms": down_down_ms,
                        "flight_ms": flight_ms,
                    }
                )

    def focusOutEvent(self, event):
        self.reset_timing()

        if self.measuring:
            self.measurement_interrupted.emit()

        super().focusOutEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Keystroke Lab — İlk Ölçüm")
        self.resize(850, 620)

        self.samples = deque(maxlen=100)
        self.total_samples = 0
        self.session_samples = []
        self.session_id = None
        self.session_started_at = None
        self.session_participant = None
        self.session_saved = False

        title = QLabel("Klavye davranışı laboratuvarı")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        description = QLabel(
            "Geliştirme modu • Kutu ve parmak izi bağlantısı yok.\n"
            "Yalnızca aşağıdaki yazım alanındaki zamanlamalar ölçülür.\n"
            "Oturumu kaydet düğmesi zamanlamaları kaydeder; "
            "yazılan metin ve tuş kimlikleri kaydedilmez."
        )
        description.setWordWrap(True)

        self.status = QLabel("Durum: Ölçüm kapalı")
        self.counter = QLabel("Geçerli basış: 0")
        self.metrics = QLabel("İstatistikler için yazmaya başla.")
        self.metrics.setWordWrap(True)

        self.participant_input = QLineEdit()
        self.participant_input.setPlaceholderText(
            "Takma kullanıcı kodu - örnek user01"
        )
        self.participant_input.setMaxLength(40)

        self.editor = TimingTextEdit()
        self.editor.sample_ready.connect(self.on_sample)
        self.editor.measurement_interrupted.connect(
            self.on_focus_lost
        )

        self.start_button = QPushButton("Ölçümü başlat")
        self.stop_button = QPushButton("Durdur")
        self.reset_button = QPushButton("Temizle")
        self.save_button = QPushButton("Oturumu kaydet")
        self.save_button.clicked.connect(self.save_session)

        self.stop_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_measurement)
        self.stop_button.clicked.connect(self.stop_measurement)
        self.reset_button.clicked.connect(self.reset_measurement)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        layout.addWidget(self.participant_input)
        layout.addWidget(self.editor)
        layout.addWidget(self.counter)
        layout.addWidget(self.metrics)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_measurement(self):
        if self.session_saved:
            QMessageBox.information(
                self,
                "Yeni Oturum",
                "Bu oturum kaydedildi Yeni oturum için Temizle'ye bas."
            )
            return

        participant = self.participant_input.text().strip()

        if not participant:
            QMessageBox.warning(
                self,
                "Kullanıcı kodu gerekli",
                "Önce user01 gibi bir takma kullanıcı kodu gir.",
            )
            return

        if self.session_id is None:
            self.session_id = str(uuid.uuid4())
            self.session_started_at = datetime.now(
                timezone.utc
            ).isoformat()
            self.session_participant = participant
            self.participant_input.setEnabled(False)

        self.editor.set_measuring(True)
        self.status.setText("Durum: Ölçüm aktif - yazım alanında yaz")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.editor.setFocus()

    def stop_measurement(self):
        self.editor.set_measuring(False)
        self.status.setText("Durum: Ölçüm durduruldu")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def reset_measurement(self):
        self.stop_measurement()

        if self.session_samples and not self.session_saved:
            answer = QMessageBox.question(
                self,
                "Kaydedilmemiş oturum",
                "Bu oturum kaydedilmedi. Verileri silmek istiyor musun?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        self.samples.clear()
        self.session_samples.clear()

        self.total_samples = 0
        self.session_id = None
        self.session_started_at = None
        self.session_participant = None
        self.session_saved = False

        self.participant_input.setEnabled(True)
        self.editor.clear()

        self.counter.setText("Geçerli basış: 0")
        self.metrics.setText("İstatistikler için yazmaya başla.")

    def on_focus_lost(self):
        self.stop_measurement()
        self.status.setText(
            "Durum: Yazım alanı odağı kaybetti. "
            "Devam etmek için ölçümü yeniden başlat."
        )

    def on_sample(self, sample):
        self.session_samples.append(dict(sample))
        self.samples.append(sample)
        self.total_samples += 1

        self.counter.setText(
            f"Geçerli basış: {self.total_samples} "
            f"• İstatistik penceresi: {len(self.samples)}/100"
        )

        lines = []

        for field, label in [
            ("dwell_ms", "Basılı tutma"),
            ("down_down_ms", "Ardışık basış"),
            ("flight_ms", "Tuş geçişi"),
        ]:
            values = [
                item[field]
                for item in self.samples
                if item[field] is not None
            ]

            if values:
                lines.append(
                    f"{label} medyanı: {median(values):.1f} ms"
                )
            else:
                lines.append(f"{label}: henüz yeterli örnek yok")

        self.metrics.setText("\n".join(lines))

    def save_session(self):
        self.stop_measurement()

        if not self.session_samples:
            QMessageBox.warning(
                self,
                "Veri yok",
                "Önce ölçümü başlatıp biraz yaz.",
            )
            return

        if self.session_saved:
            QMessageBox.information(
                self,
                "Zaten kaydedildi",
                "Yeni oturum için Temizle'ye bas.",
            )
            return

        data = {
            "schema_version": 1,
            "collector_version": "in-app-v1",
            "session_id": self.session_id,
            "participant_id": self.session_participant,
            "started_at_utc": self.session_started_at,
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "capture_scope": "application_text_area",
            "identity_verified": False,
            "sample_count": len(self.session_samples),
            "samples": self.session_samples,
        }

        folder = Path(__file__).resolve().parent / "data" / "sessions"
        file_path = folder / f"{self.session_id}.json"

        try:
            folder.mkdir(parents=True, exist_ok=True)

            # Dosya zaten varsa üzerine yazma.
            with file_path.open("x", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )

        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Kayıt başarısız",
                f"Oturum kaydedilemedi:\n{error}",
            )
            return

        self.session_saved = True
        self.start_button.setEnabled(False)
        self.status.setText(
            "Durum: Oturum kaydedildi — yeni oturum için Temizle"
        )

        QMessageBox.information(
            self,
            "Oturum kaydedildi",
            f"{len(self.session_samples)} örnek kaydedildi.\n\n"
            f"Dosya:\n{file_path}",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())