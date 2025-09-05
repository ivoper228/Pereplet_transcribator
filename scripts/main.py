# ---------------------------------------------- БИБЛИОТЕКИ ------------------------------------------------------------
import numpy as np
import json, pyaudio, sys, os
from pathlib import Path


from PySide6 import QtGui
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTimer, QTime, QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QMessageBox, QPushButton, QProgressDialog, QFileDialog

from UI.Main_menu_script import Ui_MainWindow
from UI.Info_menu_script import Ui_Dialog_info
from UI.Dictation_audio_menu_script import Ui_Dialog_dict_audio
from UI.Transcrib_text_menu_script import Ui_Dialog_audio_file_to_text

from vosk import Model, KaldiRecognizer

    # Подлкючение функций из других файлов
from model.format_to_audio import continue_process_transcription
from model.wav_to_text import start_model
# ----------------------------------------------------------------------------------------------------------------------

    # Загрузка модели
model_path = "../model/vosk-model-small-ru-0.22"   # малая модель
model = Model(model_path)
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = (BASE_DIR / ".." / "model" / "vosk-model-small-ru-0.22").resolve()
print("[DEBUG] MODEL_DIR:", MODEL_DIR)

# --------------------------------------------- ТРАНСКРИБАЦИЯ ----------------------------------------------------------
class TranscribTextMenu(QDialog):
    """
    Класс TranscribTextMenu представляет собой диалоговое окно для транскрибации аудио и видео файлов в текстовый формат.

    Атрибуты класса:
    ----------------
    last_save_path : str
        Переменная класса для хранения последнего пути сохранения файла.

    Атрибуты экземпляра:
    --------------------
    ui : Ui_Dialog_audio_file_to_text
        Интерфейс пользовательского диалога.

    main_window : QMainWindow
        Главное окно приложения.

    textEdit_field_to_text : QTextEdit
        Поле для отображения текста транскрибации.

    Методы:
    -------
    __init__(self, main_window):
        Инициализирует экземпляр класса, устанавливает заголовок окна и подключает сигналы к соответствующим слотам.

    is_valid_audio_or_video_file(self, file_name):
        Проверяет, является ли файл допустимым аудио или видео форматом.

    show_invalid_file_warning(self):
        Отображает предупреждающее сообщение о неверном формате файла.

    open_file_dialog(self, event, line_edit):
        Открывает диалоговое окно для выбора файла и проверяет его формат.

    continue_transcription_process(self, file_path):
        Отображает диалоговое окно с подтверждением продолжения процесса транскрибации.

    open_file_dialog_with_btn(self, line_edit):
        Открывает диалоговое окно для выбора файла и обрабатывает продолжение процесса транскрибации.

    save_file_dialog(self, line_edit):
        Открывает диалоговое окно для сохранения файла и проверяет наличие текста для сохранения.

    save_text_to_file(self, file_name=None):
        Сохраняет текст транскрибации в указанный файл.

    back_to_main(self):
        Закрывает текущее окно и возвращает к главному окну приложения.
    """

    last_save_path = ""              # Переменная класса для хранения последнего пути сохранения

    def __init__(self, main_window):
        super(TranscribTextMenu, self).__init__()
        self.ui = Ui_Dialog_audio_file_to_text()
        self.ui.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("AudioToText - Файл в текст")

        self.textEdit_field_to_text = self.ui.textEdit_field_to_text

        self.ui.pushButton_back_to_main.clicked.connect(self.back_to_main)
        self.ui.lineEdit_way_open_file.mousePressEvent = lambda event: self.open_file_dialog(event, self.ui.lineEdit_way_open_file)
        self.ui.lineEdit_way_save_file.mousePressEvent = lambda event: self.save_file_dialog(self.ui.lineEdit_way_save_file)
        self.ui.pushButton_choose_file.clicked.connect(lambda: self.open_file_dialog_with_btn(self.ui.lineEdit_way_open_file))
        self.ui.pushButton_save_files.clicked.connect(lambda: self.save_file_dialog(self.ui.lineEdit_way_save_file))

    def is_valid_audio_or_video_file(self, file_name):   # Проверяет входной формат файла
        valid_extensions = ['.wav', '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.flac', '.aac', '.wma', '.wmv', '.alac', '.ogg', '.aiff', '.dsd', '.WebM', '.flv']
        _, ext = os.path.splitext(file_name)
        return ext.lower() in valid_extensions

    def show_invalid_file_warning(self):   # Отображение окна предупреждения о неверном формате
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("Внимание! Выбранный вами файл не является аудио или видео, пожалуйста, выберите другой файл!")
        msg_box.setWindowTitle("Ошибка выбора файла")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def open_file_dialog(self, event, line_edit):         # Открывает окно выбора файла
        if event.button() == Qt.MouseButton.LeftButton:
            file_name, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "All Files (*)")
            if file_name:
                if not self.is_valid_audio_or_video_file(file_name):
                    self.show_invalid_file_warning()
                else:
                    line_edit.setText(file_name)

    def continue_transcription_process(self, file_path):
        print(f"[UI] confirm dialog for: {file_path}")
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Вопрос")
        msg_box.setText("Начать процесс транскрибации?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg_box.exec() == QMessageBox.Yes:
            print("[UI] clicked:", msg_box.clickedButton().text() if msg_box.clickedButton() else "None")
            from model.format_to_audio import continue_process_transcription
            return continue_process_transcription(file_path)
        return None

    def open_file_dialog_with_btn(self, line_edit):       # Обработчик нажатия на кнопку "Выбрать" при выборе файла

        # --- 1) выбор файла ---
        AUDIO_FILTER = "Audio files (*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.wma *.alac);;All files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите аудио", "", AUDIO_FILTER)
        if not file_path:
            return

        # быстрая валидация расширения (если в проекте есть готовый валидатор — можешь заменить)
        valid_exts = {".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".alac"}
        import os
        if os.path.splitext(file_path)[1].lower() not in valid_exts:
            QMessageBox.warning(self, "Неподдерживаемый формат",
                                "Выберите аудио-файл: WAV/MP3/FLAC/AAC/M4A/OGG/WMA/ALAC.")
            return

        # покажем путь в поле выбора (если такое поле есть в UI)
        try:
            self.ui.lineEdit_way_open_file.setText(file_path)
        except Exception:
            pass

        print(f"[UI] Старт транскрибации файла: {file_path}")

        # --- 2) прогресс и «занят» ---
        progress = QProgressDialog("Идет процесс распознавания...", "Отмена", 0, 100, self)
        progress.setWindowTitle("Распознавание")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        # опционально заблокируем основные кнопки/курсор
        try:
            self.setCursor(Qt.BusyCursor)
        except Exception:
            pass

        try:
            # --- 3) конвертация в WAV ---
            # если в твоём классе есть метод-обёртка (с подтверждением) — используем его:
            if hasattr(self, "continue_transcription_process"):
                wav_path = self.continue_transcription_process(file_path)
            else:
                # иначе — импортируем прямую функцию из конвертера
                from model.format_to_audio import continue_process_transcription
                wav_path = continue_process_transcription(file_path)

            if not wav_path:
                print("[UI] Конвертация отменена/неуспешна.")
                progress.close()
                return

            print(f"[FORMAT] WAV готов: {wav_path}")
            progress.setValue(50)

            # --- 4) распознавание Vosk ---
            from model.wav_to_text import start_model
            print("[VOSK] Запускаю распознавание…")
            txt_path = start_model(wav_path)  # функция должна вернуть путь к временному .txt с результатом

            # --- 5) чтение результата и вывод в текстовое поле ---
            text = ""
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"[VOSK] Не удалось прочитать результат: {e}")

            if hasattr(self.ui, "textEdit_field_to_text"):
                self.ui.textEdit_field_to_text.setPlainText(text)
            print(f"[VOSK] Готово. Результат: {txt_path}")

            progress.setValue(100)

        except Exception as e:
            # покажем ошибку пользователю и в консоли
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            progress.close()
            try:
                self.setCursor(Qt.ArrowCursor)
            except Exception:
                pass
    def save_file_dialog(self, line_edit):                     # Вызываем окно сохранения файла
        if not self.ui.textEdit_field_to_text.toPlainText():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText("Поле текста пустое")
            msg.setInformativeText("Хотите сохранить пустой файл перед созданием нового?")
            msg.setWindowTitle("Внимание")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if msg.exec() == QMessageBox.StandardButton.Yes:  # Если нажата "Сохранить"
                self.save_text_to_file()
                return
            else:          # Если отмена сохранения файла
                return

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", self.last_save_path, "Text Files (*.txt)")
        if file_name:
            self.save_text_to_file(file_name)

    def save_text_to_file(self, file_name=None):        # Сохранене файла по указанному пути
        if file_name is None:
            file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", self.last_save_path, "Text Files (*.txt)")
            if not file_name:
                return
        with open(file_name, 'w') as file:
            file.write(self.ui.textEdit_field_to_text.toPlainText())

        # Обновление пути сохраненного файла в GUI приложения
        self.ui.lineEdit_way_save_file.setText(file_name)
        self.last_save_path = file_name  # Обновление последнего пути сохранения

    def back_to_main(self):       # Обработчик кнопки "Назад"
        self.close()
        if self.main_window.isHidden():
            self.main_window.show()
        elif self.main_window.isMinimized():
            self.main_window.showNormal()
# ----------------------------------------------------------------------------------------------------------------------


# --------------------------------------------- НАДИКТОВКА -------------------------------------------------------------
class AudioProcessor(QThread):
    """
        Класс AudioProcessor представляет собой поток для обработки аудио в реальном времени, используя модель распознавания речи.

        Атрибуты экземпляра:
        --------------------
        model : object
            Модель для распознавания речи.

        recognition : object
            Объект распознавания речи, используемый для обработки аудио данных.

        stream : object
            Аудио поток для записи и считывания данных.

        ui : object
            Интерфейс пользовательского интерфейса для отображения текста.

        is_recording : bool
            Флаг для управления состоянием записи аудио.

        Методы:
        -------
        __init__(self, model, recognition, stream, ui, parent=None):
            Инициализирует экземпляр класса с заданными параметрами.

        run(self):
            Запускает поток для обработки аудио данных и распознавания речи.

        stop(self):
            Останавливает запись аудио и закрывает аудио поток.
        """

    def __init__(self, model, recognition, stream, ui, parent=None):
        super(AudioProcessor, self).__init__(parent)
        self.model = model
        self.recognition = recognition
        self.stream = stream
        self.ui = ui
        self.is_recording = True

    def run(self):                # Запуск приема аудио-потока
        print(" Говорите: ")
        while self.is_recording:
            data = self.stream.read(4000, exception_on_overflow=False)
            if self.recognition.AcceptWaveform(data) and len(data) > 0:
                answer = json.loads(self.recognition.Result())
                if answer["text"]:
                    self.ui.textEdit_field_to_text_from_audio.append(answer["text"])
                    audio_data = np.frombuffer(data, dtype=np.int16)

    def stop(self):                 # Остановка приема аудио-потока
        self.is_recording = False
        self.stream.stop_stream()
        self.stream.close()

class DictationAudioDialog(QDialog):
    """
        Класс DictationAudioDialog представляет собой диалоговое окно для диктовки аудио и его преобразования в текст.

        Атрибуты класса:
        ----------------
        last_save_path : str
            Переменная класса для хранения последнего пути сохранения файла.

        Атрибуты экземпляра:
        --------------------
        ui : Ui_Dialog_dict_audio
            Интерфейс пользовательского диалога.

        main_window : QMainWindow
            Главное окно приложения.

        timer : QTimer
            Таймер для отслеживания времени записи.

        elapsed_time : QTime
            Время, прошедшее с начала записи.

        record_icon_path : str
            Путь к иконке кнопки записи.

        recording_icon_path : str
            Путь к иконке активной кнопки записи.

        recognition : object
            Объект распознавания речи.

        stream : object
            Аудио поток для записи и считывания данных.

        is_recording : bool
            Флаг для управления состоянием записи аудио.

        audio_processor : AudioProcessor
            Объект для обработки аудио в реальном времени.

        Методы:
        -------
        __init__(self, main_window):
            Инициализирует экземпляр класса, устанавливает заголовок окна и подключает сигналы к соответствующим слотам.

        load_model(self):
            Загружает модель распознавания речи и инициализирует аудио поток.

        listen(self):
            Запускает обработку аудио в отдельном потоке.

        save_file_dialog_dict_window(self, line_edit):
            Открывает диалоговое окно для сохранения файла и проверяет наличие текста для сохранения.

        save_text_to_file_dict_window(self, file_name=None):
            Сохраняет текст диктовки в указанный файл.

        toggle_recording(self):
            Переключает состояние записи аудио, запускает или останавливает процесс записи и обновляет интерфейс.

        update_timer(self):
            Обновляет отображаемое время записи каждую секунду.

        show_context_menu(self, position):
            Отображает контекстное меню для прекращения записи при нажатии правой кнопкой мыши на кнопку записи.

        reset_timer(self):
            Сбрасывает таймер записи и обновляет интерфейс.

        back_to_main(self):
            Закрывает текущее окно и возвращает к главному окну приложения.
        """

    last_save_path = ""  # Переменная класса для хранения последнего пути сохранения

    def __init__(self, main_window):
        super(DictationAudioDialog, self).__init__()
        self.ui = Ui_Dialog_dict_audio()
        self.ui.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("AudioToText - Аудио в текст")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_time = QTime(0, 0, 0)

        self.record_icon_path = "../icons/record_btn.svg"
        self.recording_icon_path = "../icons/record_btn_red.svg"

        self.ui.pushButton_back_to_main.clicked.connect(self.back_to_main)
        self.ui.pushButton_record_start.clicked.connect(self.toggle_recording)
        self.ui.pushButton_record_start.setIcon(QIcon(self.record_icon_path))
        self.ui.pushButton_record_start.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.pushButton_record_start.customContextMenuRequested.connect(self.show_context_menu)

        self.ui.lineEdit_way_to_save_file.mousePressEvent = lambda event: self.save_file_dialog_dict_window(self.ui.lineEdit_way_to_save_file)
        self.ui.pushButton_save_as.clicked.connect(lambda: self.save_file_dialog_dict_window(self.ui.lineEdit_way_to_save_file))

        self.recognition = None
        self.stream = None
        self.is_recording = False
        self.audio_processor = None

        # Установить начальный текст для поля с текстовыми подсказками пользователю
        self.ui.lineEdit_words_to_dict_info.setEnabled(False)
        self.ui.lineEdit_words_to_dict_info.setText("   Для начала записи нажмите на кнопку справа")

    def load_model(self):                                         # Загрузка модели распознавания речи
        self.recognition = KaldiRecognizer(model, 16000)
        p = pyaudio.PyAudio()
        self.stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        self.stream.start_stream()

    def listen(self):                                                    # Запускает обработкe аудио в отдельном потоке
        if self.audio_processor and self.audio_processor.isRunning():
            self.audio_processor.is_recording = False
            self.audio_processor.wait()

        self.audio_processor = AudioProcessor(model, self.recognition, self.stream, self.ui)
        self.audio_processor.start()

    def save_file_dialog_dict_window (self, line_edit):                     # Открывает диалоговое окно сохранения файла
        if not self.ui.textEdit_field_to_text_from_audio.toPlainText():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText("Поле текста пустое")
            msg.setInformativeText("Хотите сохранить пустой файл перед созданием нового?")
            msg.setWindowTitle("Внимание")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if msg.exec() == QMessageBox.StandardButton.Yes:  # Если нажата "Сохранить"
                self.save_text_to_file_dict_window()
                return
            else:          # Если отмена сохранения
                return

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", self.last_save_path, "Text Files (*.txt)")
        if file_name:
            self.save_text_to_file_dict_window(file_name)

    def save_text_to_file_dict_window(self, file_name=None):   # Сохраняет файл по выбранному пути
        if file_name is None:
            file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", self.last_save_path,"Text Files (*.txt)")
            if not file_name:
                return
        with open(file_name, 'w') as file:
            file.write(self.ui.textEdit_field_to_text_from_audio.toPlainText())

        # Обновление пути сохраненного файла в GUI приложения
        self.ui.lineEdit_way_to_save_file.setText(file_name)
        self.last_save_path = file_name                         # Обновление последнего пути сохранения

    def toggle_recording(self):      # Управляет запуском / остановкой / прекращением записи и обновляет GUI
        # Запуск надиктовки
        if not self.is_recording:
            self.load_model()

            self.timer.start(1000)
            self.ui.pushButton_record_start.setIcon(QIcon(self.recording_icon_path))
            self.ui.lineEdit_way_to_save_file.setEnabled(False)
            self.ui.pushButton_save_as.setEnabled(False)
            self.is_recording = True
            self.listen()

            # Отображение в тектовом информаторе для пользователя сообщения о начале записи
            self.ui.lineEdit_words_to_dict_info.setText("                                            Говорите...")

        # Пауза надиктовки
        else:
            self.timer.stop()
            self.ui.pushButton_record_start.setIcon(QIcon(self.record_icon_path))
            self.ui.lineEdit_way_to_save_file.setEnabled(True)
            self.ui.pushButton_save_as.setEnabled(True)
            self.is_recording = False
            if self.audio_processor:
                self.audio_processor.stop()

            # Отображение в тектовом информаторе для пользователя сообщения об остановке записи
            self.ui.lineEdit_words_to_dict_info.setText("   Для продолжения записи нажмите на кнопку")


    def update_timer(self):                                  # Обновление таймера по надиктовке
        self.elapsed_time = self.elapsed_time.addSecs(1)
        self.ui.label_time_audio.setText(self.elapsed_time.toString("hh:mm:ss"))


    def show_context_menu(self, position):           # Отображение диалогового окна о прекращении записи
        if self.ui.label_time_audio.text() != "00:00:00" and not self.timer.isActive():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("Прекратить текущую запись?")
            msg.setWindowTitle("Прекратить запись")
            yes_button = msg.addButton("Да", QMessageBox.YesRole)
            no_button = msg.addButton("Нет", QMessageBox.NoRole)
            msg.exec()
            if msg.clickedButton() == yes_button:
                self.reset_timer()


    def reset_timer(self):                    # Сбрасывает таймер и отчищает поле для надиктовки
        self.elapsed_time = QTime(0, 0, 0)
        self.ui.label_time_audio.setText(self.elapsed_time.toString("hh:mm:ss"))
        self.ui.lineEdit_way_to_save_file.setEnabled(True)
        self.ui.pushButton_save_as.setEnabled(True)
        self.ui.textEdit_field_to_text_from_audio.clear()
        self.ui.lineEdit_words_to_dict_info.setText("   Для начала записи нажмите на кнопку справа")

    def back_to_main(self):       # Обработчик кнопки "Назад"
        self.close()
        if self.main_window.isHidden():
            self.main_window.show()
        elif self.main_window.isMinimized():
            self.main_window.showNormal()
# ----------------------------------------------------------------------------------------------------------------------


# --------------------------------------------- ИНФОРМАЦИЯ -------------------------------------------------------------
class InfoMenu(QDialog):
    """
            Класс InfoMenu представляет собой диалоговое окно с информацией о программе.

            Атрибуты экземпляра:
            --------------------
            ui : Ui_Dialog_info
                Интерфейс пользовательского диалога.

            main_window : QMainWindow
                Главное окно приложения.

            Методы:
            -------
            __init__(self, main_window):
                Инициализирует экземпляр класса, устанавливает заголовок окна и подключает сигнал кнопки к слоту.

            back_to_main(self):
                Закрывает текущее окно и возвращает к главному окну приложения.
            """
    def __init__(self, main_window):
        super(InfoMenu, self).__init__()
        self.ui = Ui_Dialog_info()
        self.ui.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("AudioToText - О программе?")

        self.ui.pushButton_back_to_main.clicked.connect(self.back_to_main)

    def back_to_main(self):    # Обработчик кнопки "Назад"
        self.close()
        if self.main_window.isHidden():
            self.main_window.show()
        elif self.main_window.isMinimized():
            self.main_window.showNormal()
# ----------------------------------------------------------------------------------------------------------------------


# --------------------------------------------- ГЛАВНОЕ ОКНО -----------------------------------------------------------
class MainWindow(QMainWindow):
    """
        Класс MainWindow представляет главное окно приложения AudioToText.

        Атрибуты экземпляра:
        --------------------
        ui : Ui_MainWindow
            Интерфейс пользовательского окна.

        Методы:
        -------
        __init__(self):
            Инициализирует экземпляр класса, устанавливает заголовок окна и подключает сигналы кнопок к соответствующим слотам.

        open_audio_file_to_text_window(self):
            Открывает окно для транскрибации аудио файла в текст.

        open_dictation_audio_dialog(self):
            Открывает окно для транскрибации аудио из прямой речи.

        open_info_menu(self):
            Открывает окно со справочной информацией о программе.
        """

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("AudioToText - Главное меню")

        # Подключение обработчика события нажатия на кнопки
        self.ui.pushButton_choose_file.clicked.connect(self.open_audio_file_to_text_window)
        self.ui.pushButton_record_audio.clicked.connect(self.open_dictation_audio_dialog)
        self.ui.pushButton_about_prog.clicked.connect(self.open_info_menu)

    def open_audio_file_to_text_window(self):                        # Открывает окно транскрибации из готвого файла
        self.audio_file_to_text_window = TranscribTextMenu(self)
        self.audio_file_to_text_window.show()

    def open_dictation_audio_dialog(self):                              # Открывает окно транскрибации из прямой речи
        self.dictation_audio_dialog = DictationAudioDialog(self)
        self.dictation_audio_dialog.show()

    def open_info_menu(self):                                  # Открывает окно со справочной информацией
        self.info_menu = InfoMenu(self)
        self.info_menu.show()
# ----------------------------------------------------------------------------------------------------------------------


# --------------------------------------------- ЗАПУСК ПРИЛОЖЕНИЯ ------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("../icons/icon_prog_mini/micro_16_1.png"))  # Установка иконки приложения
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
# ----------------------------------------------------------------------------------------------------------------------