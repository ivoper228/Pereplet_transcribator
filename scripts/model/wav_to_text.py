# ---------------------------------------------- БИБЛИОТЕКИ ------------------------------------------------------------
from vosk import Model, KaldiRecognizer
import wave, json, time, nltk, os
DEFAULT_LANG = "russian"
# ----------------------------------------------------------------------------------------------------------------------



def _ensure_punkt():
    # пункт может отсутствовать на «чистых» ПК
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    # в новых версиях NLTK таблицы вынесены отдельно
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        try:
            nltk.download("punkt_tab", quiet=True)
        except Exception:
            pass

def transcribe_audio(file_path):                                              # транскрибация аудио файда
    model_path = "../model/vosk-model-small-ru-0.22"  # малая модель

    model = Model(model_path)
    start_time_model = time.perf_counter()   # старт замера времени выполнения работы модели

    # Открытие файла с аудио
    wf = wave.open(file_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    # Чтение данных и распознавание
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            print("Процесс распознавания...")

    # Получение итогового результата
    result = rec.FinalResult()
    result_dict = json.loads(result)
    transcribed_text = result_dict["text"]

    # Конец времени выполнения программы
    end_time_model = time.perf_counter()
    execution_time_model = end_time_model - start_time_model

    # Преобразование времени выполнения в минуты и секунды
    minutes = int(execution_time_model // 60)
    seconds = int(execution_time_model % 60)
    hundredths = int((execution_time_model * 100) % 100)

    print(f"\n Время выполнения транскрибации: {minutes} минут, {seconds} секунд, {hundredths} сотых секунд. \n")

    return transcribed_text

def add_punctuation_and_capitalize(text: str, lang: str = DEFAULT_LANG) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    _ensure_punkt()
    # ВАЖНО: явно задаём язык
    try:
        sentences = nltk.sent_tokenize(text, language=lang)
    except Exception:
        # если что-то пойдёт не так — просто вернём сырой текст, без крэша
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



def start_model(audio_file_path: str) -> str:
    import wave, json, os
    from pathlib import Path
    import time

    t0 = time.perf_counter()

    # --- путь для временного TXT (абсолютный) ---
    # .../scripts/model -> parent -> scripts -> parent -> корень проекта
    project_root = Path(__file__).resolve().parents[2]
    txt_dir = project_root / "test_formats" / "TXT"
    txt_dir.mkdir(parents=True, exist_ok=True)  # ВАЖНО: создаём папку
    transcribed_text_temp_path = txt_dir / "transcribed_text_temp.txt"

    # --- модель и SR из окружения (как ты уже прокидываешь) ---
    mdir = os.environ.get("VOSK_MODEL_DIR")
    sr = int(os.environ.get("VOSK_SR", "16000"))
    model = Model(mdir)
    rec = KaldiRecognizer(model, sr)

    # --- распознавание ---
    wf = wave.open(audio_file_path, "rb")
    assert wf.getnchannels()==1 and wf.getframerate()==sr and wf.getsampwidth()==2, \
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

    # --- пост-обработка пунктуации (без падений, если нет punkt) ---
    try:
        text = add_punctuation_and_capitalize(text)
    except Exception:
        pass

    # --- запись результата ---
    with open(transcribed_text_temp_path, "w", encoding="utf-8") as f:
        f.write(text)

    dt = time.perf_counter() - t0
    print(f"\n Время выполнения транскрибации: {int(dt//60)} минут, {int(dt%60)} секунд.\n")

    return str(transcribed_text_temp_path)