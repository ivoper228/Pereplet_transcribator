# ---------------------------------------------- БИБЛИОТЕКИ ------------------------------------------------------------
from pydub import AudioSegment
import os
# ----------------------------------------------------------------------------------------------------------------------

SR = int(os.environ.get("VOSK_SR", "16000"))  # берём SR модели, по умолчанию 16000

def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def extract_audio_from_video(video_filepath, output_audio_filepath):  # Извлечение аудио из видео (через ffmpeg/pydub)
    _ensure_parent(output_audio_filepath)
    audio = AudioSegment.from_file(video_filepath)
    audio = audio.set_channels(1).set_frame_rate(SR).set_sample_width(2)
    audio.export(output_audio_filepath, format="wav")
    print(" Видео успешно переконвертировано!")

def convert_audio_to_wav(input_audio_filepath, output_wav_audio_filepath):  # Любой аудио → WAV/mono/SR
    _ensure_parent(output_wav_audio_filepath)
    audio = AudioSegment.from_file(input_audio_filepath)
    audio = audio.set_channels(1).set_frame_rate(SR).set_sample_width(2)
    audio.export(output_wav_audio_filepath, format="wav")
    print(" Аудио успешно переконвертировано!")

def continue_process_transcription(audio_filepath):  # Определяем формат и перегоняем
    # сохраняем в тестовую папку, делаем абсолютный путь от текущего файла
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_audio_filepath = os.path.join(base, "test_formats", "WAV", "output_audio_NEW.wav")
    _ensure_parent(output_audio_filepath)

    ext = os.path.splitext(audio_filepath)[1].lower()
    video_exts = {'.mp4', '.mov', '.ts', '.mkv', '.avi', '.wmv', '.webm', '.flv'}

    if ext == '.wav':
        convert_audio_to_wav(audio_filepath, output_audio_filepath)
    elif ext in video_exts:
        extract_audio_from_video(audio_filepath, output_audio_filepath)
    else:
        convert_audio_to_wav(audio_filepath, output_audio_filepath)

    return output_audio_filepath
