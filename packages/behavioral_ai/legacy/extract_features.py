import csv
import json
import math
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent
SESSIONS_DIR = ROOT / "data" / "sessions"
OUTPUT_FILE = ROOT / "data" / "features.csv"

WINDOW_SIZE = 100
FEATURE_VERSION = "timing-summary-v2"


def percentile(values, fraction):
    """Sıralı değerler arasında doğrusal ara değer hesaplar."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    weight = position - lower
    return (
        ordered[lower] * (1 - weight)
        + ordered[upper] * weight
    )


def describe(values, prefix):
    return {
        f"{prefix}_median_ms": median(values),
        f"{prefix}_iqr_ms": (
            percentile(values, 0.75)
            - percentile(values, 0.25)
        ),
        f"{prefix}_p10_ms": percentile(values, 0.10),
        f"{prefix}_p90_ms": percentile(values, 0.90),
    }


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_session(data):
    if data.get("schema_version") != 1:
        raise ValueError("Desteklenmeyen kayıt sürümü.")

    for field in ("session_id", "participant_id"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"Eksik veya geçersiz alan: {field}")

    samples = data.get("samples")

    if not isinstance(samples, list):
        raise ValueError("samples bir liste olmalı.")

    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"Örnek {index}: geçersiz kayıt.")

        dwell = sample.get("dwell_ms")

        if not is_number(dwell) or not 0 < dwell <= 2000:
            raise ValueError(f"Örnek {index}: geçersiz dwell.")

        for field in ("down_down_ms", "flight_ms"):
            if field not in sample:
                raise ValueError(f"Örnek {index}: {field} eksik.")

            value = sample[field]

            if value is not None and not is_number(value):
                raise ValueError(f"Örnek {index}: geçersiz {field}.")

        down_down = sample["down_down_ms"]

        if down_down is not None and not 0 <= down_down <= 2000:
            raise ValueError(f"Örnek {index}: geçersiz down-down.")


def make_features(window):
    dwell = [
        sample["dwell_ms"]
        for sample in window
    ]

    # İlk basışın geçişi pencerenin dışından geliyor olabilir.
    transitions = window[1:]

    # Eksik geçişler sıfır değildir.
    # Her özellik için yalnızca mevcut ölçümleri kullanıyoruz.
    down_down = [
        sample["down_down_ms"]
        for sample in transitions
        if sample["down_down_ms"] is not None
    ]

    flight = [
        sample["flight_ms"]
        for sample in transitions
        if sample["flight_ms"] is not None
    ]

    possible_transitions = len(transitions)

    down_down_coverage = (
        len(down_down) / possible_transitions
    )

    flight_coverage = (
        len(flight) / possible_transitions
    )

    # Başlangıç için deneysel veri yeterliliği koşulu.
    # İleride gerçek verilerle değerlendireceğiz.
    if (
        down_down_coverage < 0.70
        or flight_coverage < 0.70
    ):
        return None

    features = {}
    features.update(describe(dwell, "dwell"))
    features.update(describe(down_down, "down_down"))
    features.update(describe(flight, "flight"))

    features["overlap_ratio"] = (
        sum(value < 0 for value in flight)
        / len(flight)
    )

    # Bunlar veri kalitesi bilgileri.
    # İlk modelde davranış özelliği olarak kullanmayacağız.
    features["down_down_count"] = len(down_down)
    features["flight_count"] = len(flight)
    features["down_down_coverage"] = down_down_coverage
    features["flight_coverage"] = flight_coverage

    return features


def session_rows(data):
    samples = data["samples"]

    full_window_count = len(samples) // WINDOW_SIZE
    remaining = len(samples) % WINDOW_SIZE

    for window_index in range(full_window_count):
        start = window_index * WINDOW_SIZE
        end = start + WINDOW_SIZE

        window = samples[start:end]
        features = make_features(window)

        if features is None:
            print(
                f"  Pencere {window_index}: "
                "geçiş verisi yetersiz, atlandı."
            )
            continue

        row = {
            "feature_version": FEATURE_VERSION,
            "participant_id": data["participant_id"],
            "session_id": data["session_id"],
            "window_index": window_index,
            "sample_count": len(window),
        }

        row.update(features)
        yield row

    if remaining:
        print(
            f"  Son {remaining} basış tam pencere "
            "oluşturmadığı için kullanılmadı."
        )


def main():
    paths = sorted(SESSIONS_DIR.glob("*.json"))

    if not paths:
        print(f"Oturum dosyası bulunamadı: {SESSIONS_DIR}")
        return

    rows = []
    seen_sessions = set()

    for path in paths:
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
            validate_session(data)

            session_id = data["session_id"]

            if session_id in seen_sessions:
                print(
                    f"Tekrarlanan oturum atlandı: {path.name}"
                )
                continue

            seen_sessions.add(session_id)

            extracted = list(session_rows(data))
            rows.extend(extracted)

            print(
                f"{data['participant_id']} | "
                f"{path.name} | "
                f"{len(data['samples'])} basış → "
                f"{len(extracted)} pencere"
            )

        except (OSError, ValueError, TypeError) as error:
            print(
                f"Dosya işlenemedi: {path.name}\n"
                f"Hata: {error}"
            )
            print("CSV güncellenmedi.")
            return

    # Bu bölüm for döngüsünün DIŞINDA olmalı.
    if not rows:
        print(
            "\nKullanılabilir pencere oluşmadı.\n"
            "En az 100 basış ve yeterli geçiş verisi gerekiyor.\n"
            "CSV güncellenmedi."
        )
        return

    try:
        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()),
            )

            writer.writeheader()
            writer.writerows(rows)

    except OSError as error:
        print(f"CSV kaydedilemedi: {error}")
        return

    print(f"\nToplam pencere: {len(rows)}")
    print(f"Özellik tablosu: {OUTPUT_FILE.resolve()}")
    print("JSON kayıtları değiştirilmedi.")


if __name__ == "__main__":
    main()
