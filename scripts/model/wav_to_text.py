# scripts/model/wav_to_text.py
import os, time, wave, json
from typing import Optional
from pathlib import Path
from vosk import Model, KaldiRecognizer

# ---- NLTK-safe punctuation (не упадёт, если ресурсов нет) ----
DEFAULT_LANG = "russian"

def _ensure_punkt():
    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            try:
                nltk.download("punkt_tab", quiet=True)
            except Exception:
                pass
        return nltk
    except Exception:
        return None

def add_punctuation_and_capitalize(text: str, lang: str = DEFAULT_LANG) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    nltk = _ensure_punkt()
    if not nltk:
        return text
    try:
        sentences = nltk.sent_tokenize(text, language=lang)
    except Exception:
        return text
    out = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        s = (s[0].upper() + s[1:]) if len(s) > 1 else s.upper()
        if s[-1] not in ".!?…":
            s += "."
        out.append(s)
    return " ".join(out)

def start_model(audio_file_path: str, model_dir: Optional[str] = None) -> str:
    print("[DEBUG] start_model called with:", audio_file_path)
    t0 = time.perf_counter()

    # Куда писать временный TXT
    project_root = Path(__file__).resolve().parents[2]
    txt_dir = project_root / "test_formats" / "TXT"
    txt_dir.mkdir(parents=True, exist_ok=True)
    transcribed_text_temp_path = txt_dir / "transcribed_text_temp.txt"

    # Путь к модели: из аргумента или из ENV
    model_path = model_dir or os.environ.get("VOSK_MODEL_DIR")
    if not model_path:
        raise RuntimeError("VOSK_MODEL_DIR не установлен и model_dir не передан")
    print("[DEBUG] model_path:", model_path)

    sr = int(os.environ.get("VOSK_SR", "16000"))
    model = Model(model_path)
    rec = KaldiRecognizer(model, sr)

    # Читаем WAV
    wf = wave.open(audio_file_path, "rb")
    assert wf.getnchannels() == 1 and wf.getframerate() == sr and wf.getsampwidth() == 2, \
        f"Нужен WAV mono/PCM16 @ {sr} Гц"

    pieces = []
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            print("Процесс распознавания...")
            pieces.append(json.loads(rec.Result()).get("text", ""))

    final = json.loads(rec.FinalResult()).get("text", "")
    text = (" ".join([*pieces, final])).strip()

    # Пунктуация с безопасным фоллбеком
    try:
        text = add_punctuation_and_capitalize(text, lang=DEFAULT_LANG)
    except Exception:
        pass

    with open(transcribed_text_temp_path, "w", encoding="utf-8") as f:
        f.write(text)
    model_path = model_dir or os.environ.get("VOSK_MODEL_DIR")
    if not model_path:
        raise RuntimeError("VOSK_MODEL_DIR не установлен и model_dir не передан")
    print("[DEBUG] model_path:", model_path)

    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    dt = time.perf_counter() - t0
    print(f"\n⏱ Время выполнения: {int(dt//60)} мин, {int(dt%60)} сек\n")
    return str(transcribed_text_temp_path)
