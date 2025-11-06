import sys
import os
import re
import threading
import json
import time
import platform # Ditambahkan untuk mendeteksi OS
import subprocess # Ditambahkan untuk menjalankan macan-engine.exe


from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLineEdit, QLabel, QSlider, QMessageBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QDialog, QStackedLayout, QGraphicsView, QGraphicsScene, QGraphicsTextItem
)
from PySide6.QtCore import (
    QUrl, Qt, QTime, QEvent, QSize, QTimer, Signal, QObject,
    QThread, Slot, QRectF
)
from PySide6.QtGui import QIcon, QPixmap, QImage, QFont, QColor
import numpy as np


# --- PUSTAKA INTI YANG DIUBAH ---
# Menggantikan PyQt6 dengan PySide6, pustaka lain tetap sama
try:
    import vlc
except ImportError:
    print("Kesalahan: Pustaka 'python-vlc' diperlukan.")
    print("Silakan install dengan: pip install python-vlc")
    print("PENTING: Anda juga harus menginstal aplikasi VLC Media Player di sistem Anda.")
    sys.exit(1)


# Pustaka untuk thumbnail tetap menggunakan OpenCV
try:
    import cv2
except ImportError:
    print("Kesalahan: Pustaka 'opencv-python-headless' diperlukan untuk thumbnail.")
    print("Silakan install dengan: pip install opencv-python-headless")
    sys.exit(1)


# Pustaka untuk ikon UI dan pengunduhan
try:
    import qtawesome as qta
except ImportError:
    print("Pustaka 'qtawesome' tidak ditemukan. Silakan install dengan 'pip install qtawesome'")
    qta = None

# Fungsi untuk mendapatkan path macan-engine.exe
def get_ytdlp_path():
    """Mencari path macan-engine.exe di direktori aplikasi atau _MEIPASS."""
    exe_name = "macan-engine.exe" if platform.system() == "Windows" else "macan-engine"
    
    # 1. Cek di direktori aplikasi
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, exe_name)
    if os.path.exists(app_path):
        return app_path
        
    # 2. Cek di _MEIPASS (untuk PyInstaller)
    if hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, exe_name)
        if os.path.exists(meipass_path):
            return meipass_path
            
    return None

YTDLP_EXECUTABLE = get_ytdlp_path()
if not YTDLP_EXECUTABLE:
    print("Peringatan: macan-engine.exe tidak ditemukan di direktori aplikasi.")

# --- KELAS-KELAS PEMBANTU ---


class ThumbnailPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.ToolTip)
        self.setLayout(QVBoxLayout())
        self.label = QLabel("Memuat...")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.label)
        self.setFixedSize(160, 120)
        self.setStyleSheet("background-color: black; border: 1px solid white; color: white; border-radius: 4px;")


    def set_thumbnail(self, pixmap):
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.size() - QSize(4, 4), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled_pixmap)
        else:
            self.label.setText("Gagal")


class ThumbnailGenerator(QObject):
    thumbnail_ready = Signal(QPixmap, float)


    @Slot(str, int, float)
    def generate(self, video_path, timestamp_ms, request_time):
        if not video_path or not os.path.exists(video_path) or timestamp_ms < 0:
            self.thumbnail_ready.emit(QPixmap(), request_time)
            return
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.thumbnail_ready.emit(QPixmap(), request_time)
                return
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.thumbnail_ready.emit(pixmap, request_time)
            else:
                self.thumbnail_ready.emit(QPixmap(), request_time)
        except Exception as e:
            print(f"Kesalahan saat generate thumbnail dengan OpenCV: {e}")
            self.thumbnail_ready.emit(QPixmap(), request_time)


class ClickableSlider(QSlider):
    hover_move = Signal(int)
    hover_leave = Signal()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.orientation() == Qt.Horizontal:
                value = self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / self.width()
            else:
                value = self.minimum() + (self.maximum() - self.minimum()) * event.position().y() / self.height()
            self.setValue(int(value))
            self.sliderMoved.emit(int(value))
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        self.hover_move.emit(event.position().x())
        super().mouseMoveEvent(event)


    def leaveEvent(self, event):
        self.hover_leave.emit()
        super().leaveEvent(event)


class SRTParser:
    def __init__(self, srt_file_path):
        self.subtitles = []
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._parse(content)
        except Exception as e:
            print(f"Gagal membaca atau parse file SRT: {e}")


    def _time_to_ms(self, time_str):
        h, m, s, ms = map(int, re.split('[:,]', time_str))
        return (h * 3600 + m * 60 + s) * 1000 + ms


    def _parse(self, content):
        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)\n\n', re.DOTALL)
        matches = pattern.findall(content)
        for match in matches:
            start_time_str, end_time_str, text = match[1], match[2], match[3]
            self.subtitles.append({
                'start_ms': self._time_to_ms(start_time_str),
                'end_ms': self._time_to_ms(end_time_str),
                'text': text.strip()
            })


    def get_subtitle(self, position_ms):
        for sub in self.subtitles:
            if sub['start_ms'] <= position_ms <= sub['end_ms']:
                return sub['text']
        return None


class YouTubeDLWorker(QObject):
    finished = Signal(str, str, str)
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    # --- PERUBAHAN FUNGSI run: Menggunakan subprocess untuk macan-engine.exe ---
    def run(self):
        if not YTDLP_EXECUTABLE:
            self.finished.emit(None, None, "File eksekusi macan-engine.exe tidak ditemukan.")
            return
            
        try:
            # Argumen untuk mendapatkan info JSON tanpa mengunduh
            command = [
                YTDLP_EXECUTABLE,
                '--skip-download',
                '--dump-json',
                '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                self.url
            ]
            
            # Jalankan subprocess
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            
            # Parsing output JSON
            info_dict = json.loads(process.stdout)
            
            # Ekstrak URL stream dan Judul
            video_url = info_dict.get('url') # 'url' di info_dict adalah URL stream yang bisa dimainkan
            title = info_dict.get('title', 'Judul tidak diketahui')
            
            if video_url:
                self.finished.emit(video_url, title, None)
            else:
                self.finished.emit(None, None, "Gagal mendapatkan URL stream video dari macan-engine.")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Error dari macan-engine (Code {e.returncode}): {e.stderr.strip()}"
            self.finished.emit(None, None, error_msg)
        except Exception as e:
            self.finished.emit(None, None, f"Error saat menjalankan macan-engine: {str(e)}")


class PlaylistWidget(QWidget):
    play_requested = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Macan Player - Playlist")
        self.setGeometry(1100, 100, 300, 400)
        icon_path = "player.ico"
        if hasattr(sys, "_MEIPASS"): icon_path = os.path.join(sys._MEIPASS, icon_path)
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
        self.playlist = []
        self._setup_ui()
        self._connect_signals()
        self.setAcceptDrops(True)
    def _setup_ui(self):
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet("background-color: #34495e;")
        self.btn_add_file = QPushButton(" Tambah File")
        if qta: self.btn_add_file.setIcon(qta.icon('fa5s.plus'))
        self.btn_remove = QPushButton(" Hapus")
        if qta: self.btn_remove.setIcon(qta.icon('fa5s.trash'))
        self.btn_clear = QPushButton(" Hapus Semua")
        if qta: self.btn_clear.setIcon(qta.icon('fa5s.times-circle'))
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.btn_add_file)
        controls_layout.addWidget(self.btn_remove)
        controls_layout.addWidget(self.btn_clear)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(controls_layout)
        self.setLayout(main_layout)
    def _connect_signals(self):
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.btn_add_file.clicked.connect(self._add_to_playlist)
        self.btn_remove.clicked.connect(self._remove_from_playlist)
        self.btn_clear.clicked.connect(self._clear_playlist)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path) and os.path.splitext(file_path)[1].lower() in ['.mp4', '.mkv', '.webm', '.avi']:
                self.playlist.append({'path': file_path, 'title': os.path.basename(file_path)})
                self._update_ui()
                self._save_playlist()
        event.acceptProposedAction()
    def _on_item_double_clicked(self, item):
        index = self.list_widget.row(item)
        if 0 <= index < len(self.playlist):
            self.play_requested.emit(self.playlist[index]['path'])
            self._update_selection(index)
    def _add_to_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Tambahkan ke Playlist", "", "Video Files (*.mp4 *.mkv *.webm *.avi)")
        if file_path:
            self.playlist.append({'path': file_path, 'title': os.path.basename(file_path)})
            self._update_ui()
            self._save_playlist()
    def _remove_from_playlist(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        index = self.list_widget.row(selected_items[0])
        del self.playlist[index]
        self._update_ui()
        self._save_playlist()
    def _clear_playlist(self):
        self.playlist.clear()
        self._update_ui()
        self._save_playlist()
    def _update_ui(self):
        self.list_widget.clear()
        for item in self.playlist: self.list_widget.addItem(item['title'])
    def _update_selection(self, index):
        if 0 <= index < self.list_widget.count(): self.list_widget.setCurrentRow(index)
    def get_current_index(self): return self.list_widget.currentRow()
    def get_playlist_data(self): return self.playlist
    def set_playlist_data(self, data):
        self.playlist = data
        self._update_ui()
    def _save_playlist(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_config.json")
        try:
            with open(config_path, "r") as f: config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): config = {}
        config['playlist'] = self.playlist
        with open(config_path, "w") as f: json.dump(config, f, indent=4)


class HistoryWindow(QDialog):
    history_item_selected = Signal(dict)
    delete_selected_requested = Signal(int)
    clear_all_requested = Signal()
    def __init__(self, history_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Riwayat Tontonan")
        self.setGeometry(1100, 550, 300, 400)
        self.history_data = history_data
        self._setup_ui()
        self._connect_signals()
        self.populate_list()
    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.btn_remove_selected = QPushButton(" Hapus Pilihan")
        if qta: self.btn_remove_selected.setIcon(qta.icon('fa5s.trash-alt'))
        self.btn_clear_all = QPushButton(" Hapus Semua")
        if qta: self.btn_clear_all.setIcon(qta.icon('fa5s.times'))
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_remove_selected)
        button_layout.addWidget(self.btn_clear_all)
        self.main_layout.addWidget(self.list_widget)
        self.main_layout.addLayout(button_layout)
    def _connect_signals(self):
        self.list_widget.itemDoubleClicked.connect(self._on_item_selected)
        self.btn_remove_selected.clicked.connect(self._remove_selected)
        self.btn_clear_all.clicked.connect(self._clear_all)
    def populate_list(self):
        self.list_widget.clear()
        for item in reversed(self.history_data):
            list_item = QListWidgetItem(item.get('title', 'Judul Tidak Diketahui'))
            list_item.setData(Qt.UserRole, item)
            self.list_widget.addItem(list_item)
    def _on_item_selected(self, item):
        self.history_item_selected.emit(item.data(Qt.UserRole))
        self.accept()
    def _remove_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Pilih item yang ingin dihapus.")
            return
        original_index = len(self.history_data) - 1 - self.list_widget.row(selected_items[0])
        self.delete_selected_requested.emit(original_index)
    def _clear_all(self):
        if QMessageBox.question(self, "Konfirmasi", "Yakin hapus SEMUA riwayat?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.clear_all_requested.emit()


# --- KELAS UTAMA PLAYER DENGAN IMPLEMENTASI VLC ---


class ModernVideoPlayer(QWidget):
    # --- SINYAL KUSTOM UNTUK MENJEMBATANI EVENT VLC KE QT ---
    request_thumbnail = Signal(str, int, float)
    playback_state_changed = Signal(bool)
    position_updated = Signal(int)
    duration_updated = Signal(int)
    volume_level_changed = Signal(int, bool)
    media_ended = Signal()



    def __init__(self):
        super().__init__()
        self.is_loading_media = False
        self.is_fullscreen = False
        self.normal_geometry = None
        self.last_volume = 50
        self.SKIP_INTERVAL = 10000
        self.playback_speeds = [0.5, 1.0, 1.5, 2.0]
        self.current_speed_index = 1
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_config.json")
        self.themes = {}
        self.theme_names = []
        self.current_theme_index = 0
        self.history = []
        self.current_media_info = {}
        self.srt_parser = None
        self.current_subtitle_text = ""


        self.playlist_widget = PlaylistWidget()
        self.history_window = HistoryWindow(self.history, self)
        self.controls_hide_timer = QTimer(self)
        self.controls_hide_timer.setInterval(2500)
        self.controls_hide_timer.setSingleShot(True)


        self._setup_player()


        self._setup_thumbnail_feature()
        self._setup_themes()
        self._load_config()
        self._setup_ui()
        self._connect_signals()
        self._apply_theme(self.theme_names[self.current_theme_index])


        self.setAcceptDrops(True)
        self.video_frame.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.video_frame.setMouseTracking(True)
        self.controls_container.setMouseTracking(True)
        
        # Arahkan output video VLC ke frame utama
        self._set_video_output(self.video_frame)


    def _setup_thumbnail_feature(self):
        self.last_thumbnail_request_time = 0.0
        self.thumbnail_preview = ThumbnailPreviewWidget()
        self.thumbnail_thread = QThread()
        self.thumbnail_generator = ThumbnailGenerator()
        self.thumbnail_generator.moveToThread(self.thumbnail_thread)
        self.thumbnail_generator.thumbnail_ready.connect(self._update_thumbnail) # Pindahkan koneksi sinyal ke sini
        self.thumbnail_thread.start()


    def _setup_player(self):
        # Inisialisasi instance dan media player VLC
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()


    def _setup_themes(self):
        self.themes = {
            "Dark": """
                QWidget { background-color: #1c1c1c; color: #ecf0f1; font-family: 'Segoe UI', Arial, sans-serif; }
                QPushButton { background-color: transparent; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #3a3a3a; } QPushButton:pressed { background-color: #4a4a4a; }
                QLineEdit { background-color: #2c2c2c; border: 1px solid #444; padding: 5px; border-radius: 4px; }
                QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
                QSlider::handle:horizontal { background: #3498db; width: 12px; margin: -4px 0; border-radius: 6px; }
                QSlider::sub-page:horizontal { background: #3498db; border-radius: 2px; }
                QLabel { font-size: 12px; }
                QListWidget { background-color: #2c3e50; }
            """,
            "Light": """
                QWidget { background-color: #f0f0f0; color: #2c3e50; font-family: 'Segoe UI', Arial, sans-serif; }
                QPushButton { background-color: transparent; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #dcdcdc; } QPushButton:pressed { background-color: #c0c0c0; }
                QLineEdit { background-color: #ffffff; border: 1px solid #bdc3c7; padding: 5px; border-radius: 4px; }
                QSlider::groove:horizontal { height: 4px; background: #bdc3c7; border-radius: 2px; }
                QSlider::handle:horizontal { background: #e74c3c; width: 12px; margin: -4px 0; border-radius: 6px; }
                QSlider::sub-page:horizontal { background: #e74c3c; border-radius: 2px; }
                QLabel { font-size: 12px; }
                QListWidget { background-color: #ffffff; }
            """,
            "Neon Blue": """
                QWidget { background-color: #0d0221; color: #b4f1f1; font-family: 'Segoe UI', Arial, sans-serif; }
                QPushButton { background-color: transparent; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #261a3b; } QPushButton:pressed { background-color: #4d3375; }
                QLineEdit { background-color: #261a3b; border: 1px solid #00aaff; padding: 5px; border-radius: 4px; color: #ffffff; }
                QSlider::groove:horizontal { height: 4px; background: #261a3b; border-radius: 2px; }
                QSlider::handle:horizontal { background: #00aaff; width: 12px; margin: -4px 0; border-radius: 6px; }
                QSlider::sub-page:horizontal { background: #00aaff; border-radius: 2px; }
                QLabel { font-size: 12px; }
                QListWidget { background-color: #261a3b; }
            """,
            "Dark Blue": """
                QWidget { background-color: #0d1b2a; color: #e0e1dd; font-family: 'Segoe UI', Arial, sans-serif; }
                QPushButton { background-color: transparent; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #1b263b; } QPushButton:pressed { background-color: #415a77; }
                QLineEdit { background-color: #1b263b; border: 1px solid #415a77; padding: 5px; border-radius: 4px; }
                QSlider::groove:horizontal { height: 4px; background: #415a77; border-radius: 2px; }
                QSlider::handle:horizontal { background: #778da9; width: 12px; margin: -4px 0; border-radius: 6px; }
                QSlider::sub-page:horizontal { background: #778da9; border-radius: 2px; }
                QLabel { font-size: 12px; }
                QListWidget { background-color: #1b263b; }
            """,
            "Soft Pink": """
                QWidget { background-color: #fce4ec; color: #444; font-family: 'Segoe UI', Arial, sans-serif; }
                QPushButton { background-color: transparent; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #f8bbd0; } QPushButton:pressed { background-color: #f48fb1; }
                QLineEdit { background-color: #ffffff; border: 1px solid #f48fb1; padding: 5px; border-radius: 4px; }
                QSlider::groove:horizontal { height: 4px; background: #f8bbd0; border-radius: 2px; }
                QSlider::handle:horizontal { background: #ec407a; width: 12px; margin: -4px 0; border-radius: 6px; }
                QSlider::sub-page:horizontal { background: #ec407a; border-radius: 2px; }
                QLabel { font-size: 12px; }
                QListWidget { background-color: #fff8f9; }
            """
        }
        self.theme_names = list(self.themes.keys())


    def _apply_theme(self, theme_name):
        if theme_name in self.themes:
            self.setStyleSheet(self.themes[theme_name])
            self.playlist_widget.setStyleSheet(self.themes[theme_name])
            self.history_window.setStyleSheet(self.themes[theme_name])


    def _change_theme(self):
        self.current_theme_index = (self.current_theme_index + 1) % len(self.theme_names)
        new_theme_name = self.theme_names[self.current_theme_index]
        self._apply_theme(new_theme_name)
        self.btn_change_theme.setToolTip(f"Ganti Tema (Sekarang: {new_theme_name})")


    def _load_config(self):
        try:
            with open(self.config_path, "r") as f: config = json.load(f)
            self.last_volume = config.get('last_volume', 50)
            self.vlc_player.audio_set_volume(self.last_volume)
            self.playlist_widget.set_playlist_data(config.get('playlist', []))
            saved_theme = config.get('theme', 'Dark')
            if saved_theme in self.theme_names:
                self.current_theme_index = self.theme_names.index(saved_theme)
            self.history = config.get('history', [])
            self.history_window.history_data = self.history
            self.history_window.populate_list()
        except (FileNotFoundError, json.JSONDecodeError): pass


    def _save_config(self):
        config = {
            'last_volume': self.vlc_player.audio_get_volume(),
            'playlist': self.playlist_widget.get_playlist_data(),
            'theme': self.theme_names[self.current_theme_index],
            'history': self.history
        }
        try:
            with open(self.config_path, "w") as f: json.dump(config, f, indent=4)
        except Exception as e: print(f"Gagal menyimpan konfigurasi: {e}")


    def _setup_ui(self):
        self.setWindowTitle("Macan Video Player")
        self.setGeometry(100, 100, 700, 550)
        icon_path = "player.ico"
        if hasattr(sys, "_MEIPASS"): icon_path = os.path.join(sys._MEIPASS, icon_path)
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))


        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.installEventFilter(self)


        self.subtitle_scene = QGraphicsScene()
        self.subtitle_view = QGraphicsView(self.subtitle_scene, self)
        self.subtitle_view.setStyleSheet("background: transparent; border: none;")
        self.subtitle_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.subtitle_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.subtitle_view.setAttribute(Qt.WA_TransparentForMouseEvents)


        self.subtitle_text_item = QGraphicsTextItem()
        font = QFont("Arial", 20, QFont.Bold)
        self.subtitle_text_item.setFont(font)
        self.subtitle_text_item.setDefaultTextColor(QColor("white"))
        self.subtitle_scene.addItem(self.subtitle_text_item)


        self.video_container = QWidget()
        self.video_stack_layout = QStackedLayout(self.video_container)
        self.video_stack_layout.setStackingMode(QStackedLayout.StackAll)
        
        self.splash_label = QLabel()
        splash_path = "splash.png"
        if hasattr(sys, "_MEIPASS"): splash_path = os.path.join(sys._MEIPASS, splash_path)
        if os.path.exists(splash_path):
            pixmap = QPixmap(splash_path)
            self.splash_label.setPixmap(pixmap.scaled(QSize(480, 480), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.splash_label.setText("Macan Video Player")
        self.splash_label.setAlignment(Qt.AlignCenter)
        self.splash_label.setStyleSheet("background-color: black; color: white; font-size: 30px; font-weight: bold;")
        
        self.video_stack_layout.addWidget(self.video_frame)
        self.video_stack_layout.addWidget(self.splash_label)
        self.video_stack_layout.addWidget(self.subtitle_view)
        
        self.btn_open = QPushButton()
        if qta: self.btn_open.setIcon(qta.icon('fa5s.folder-open'))
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URL video (YouTube, dll)...")
        self.btn_load_url = QPushButton()
        if qta: self.btn_load_url.setIcon(qta.icon('fa5s.link'))
        self.btn_toggle_url_bar = QPushButton()
        if qta: self.btn_toggle_url_bar.setIcon(qta.icon('fa5s.globe'))
        self.btn_show_playlist = QPushButton()
        if qta: self.btn_show_playlist.setIcon(qta.icon('fa5s.list'))
        self.btn_show_history = QPushButton()
        if qta: self.btn_show_history.setIcon(qta.icon('fa5s.history'))


        self.position_slider = ClickableSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.time_label = QLabel("00:00 / 00:00")


        self.btn_prev_playlist = QPushButton()
        if qta: self.btn_prev_playlist.setIcon(qta.icon('fa5s.step-backward'))
        self.btn_next_playlist = QPushButton()
        if qta: self.btn_next_playlist.setIcon(qta.icon('fa5s.step-forward'))
        self.btn_play_pause = QPushButton()
        if qta: self.btn_play_pause.setIcon(qta.icon('fa5s.play'))
        self.btn_stop = QPushButton()
        if qta: self.btn_stop.setIcon(qta.icon('fa5s.stop'))
        self.btn_speed = QPushButton(f"{self.playback_speeds[self.current_speed_index]}x")
        self.btn_mute = QPushButton()
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100) # Volume VLC 0-100
        self.volume_slider.setValue(self.last_volume)
        self.volume_slider.setFixedWidth(120)
        if qta: self._update_volume_icon()


        self.btn_fullscreen = QPushButton()
        if qta: self.btn_fullscreen.setIcon(qta.icon('fa5s.expand'))
        self.btn_change_theme = QPushButton()
        if qta: self.btn_change_theme.setIcon(qta.icon('fa5s.palette'))


        self.controls_container = QWidget()
        self.url_bar_widget = QWidget()
        url_bar_layout = QHBoxLayout()
        url_bar_layout.setContentsMargins(10, 0, 10, 5)
        url_bar_layout.addWidget(self.url_input)
        url_bar_layout.addWidget(self.btn_load_url)
        self.url_bar_widget.setLayout(url_bar_layout)
        self.url_bar_widget.setVisible(False)
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(10, 0, 10, 0)
        slider_layout.addWidget(self.position_slider)
        bottom_controls_layout = QHBoxLayout()
        bottom_controls_layout.setContentsMargins(10, 0, 10, 5)
        bottom_controls_layout.addWidget(self.btn_play_pause)
        bottom_controls_layout.addWidget(self.btn_stop)
        bottom_controls_layout.addWidget(self.btn_prev_playlist)
        bottom_controls_layout.addWidget(self.btn_next_playlist)
        bottom_controls_layout.addWidget(self.time_label)
        bottom_controls_layout.addStretch(1)
        bottom_controls_layout.addWidget(self.btn_open)
        bottom_controls_layout.addWidget(self.btn_toggle_url_bar)
        bottom_controls_layout.addWidget(self.btn_speed)
        bottom_controls_layout.addWidget(self.btn_show_playlist)
        bottom_controls_layout.addWidget(self.btn_show_history)
        bottom_controls_layout.addWidget(self.btn_mute)
        bottom_controls_layout.addWidget(self.volume_slider)
        bottom_controls_layout.addWidget(self.btn_fullscreen)
        bottom_controls_layout.addWidget(self.btn_change_theme)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 5, 0, 0)
        container_layout.setSpacing(5)
        container_layout.addWidget(self.url_bar_widget)
        container_layout.addLayout(slider_layout)
        container_layout.addLayout(bottom_controls_layout)
        self.controls_container.setLayout(container_layout)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.video_container, 1)
        main_layout.addWidget(self.controls_container)
        self.setLayout(main_layout)


        self.video_frame.hide()
        self.splash_label.show()


    def _connect_signals(self):
        # --- KONEKSI SINYAL DARI UI KE FUNGSI KONTROL ---
        self.btn_open.clicked.connect(self._open_file)
        self.url_input.returnPressed.connect(self._load_from_url)
        self.btn_load_url.clicked.connect(self._load_from_url)
        self.btn_toggle_url_bar.clicked.connect(self._toggle_url_bar)
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        self.btn_stop.clicked.connect(self._stop_video)
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        self.btn_mute.clicked.connect(self._toggle_mute)
        self.btn_speed.clicked.connect(self._change_playback_speed)
        self.btn_show_playlist.clicked.connect(self._toggle_playlist_window)
        self.btn_prev_playlist.clicked.connect(self._play_previous_video)
        self.btn_next_playlist.clicked.connect(self._play_next_video)
        self.btn_change_theme.clicked.connect(self._change_theme)
        self.btn_show_history.clicked.connect(self._show_history_window)
        self.history_window.history_item_selected.connect(self._play_from_history)
        self.history_window.delete_selected_requested.connect(self._delete_history_item)
        self.history_window.clear_all_requested.connect(self._clear_all_history_data)


        self.volume_slider.valueChanged.connect(self._set_volume)
        self.position_slider.sliderMoved.connect(self._set_position)


        # --- KONEKSI DARI SINYAL KUSTOM (JEMBATAN VLC) KE UI ---
        self.playback_state_changed.connect(self._update_play_pause_icon)
        self.position_updated.connect(self._update_position)
        self.duration_updated.connect(self._update_duration)
        self.volume_level_changed.connect(self._sync_main_volume_slider)
        self.media_ended.connect(self._handle_media_status_changed)
        
        # Sinyal lain-lain
        self.playlist_widget.play_requested.connect(self._load_and_play_from_playlist)
        self.controls_hide_timer.timeout.connect(self._hide_controls)
        self.position_slider.hover_move.connect(self._show_thumbnail_preview)
        self.position_slider.hover_leave.connect(self.thumbnail_preview.hide)
        self.request_thumbnail.connect(self.thumbnail_generator.generate, Qt.QueuedConnection)


        # --- KONEKSI EVENT MANAGER VLC ---
        event_manager = self.vlc_player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_vlc_position_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_vlc_duration_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_vlc_state_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_vlc_state_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_vlc_state_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_state_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerAudioVolume, self._on_vlc_volume_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerMuted, self._on_vlc_volume_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerUnmuted, self._on_vlc_volume_changed)


    # --- HANDLER UNTUK EVENT DARI VLC ---
    
    def _on_vlc_position_changed(self, event):
        if self.is_loading_media:
            return
        self.position_updated.emit(event.u.new_time)


    def _on_vlc_duration_changed(self, event):
        if self.is_loading_media:
            return
        self.duration_updated.emit(event.u.new_length)


    def _on_vlc_state_changed(self, event):
        state = self.vlc_player.get_state()
        if state == vlc.State.Playing:
            self.playback_state_changed.emit(True)
        elif state in [vlc.State.Paused, vlc.State.Stopped]:
            self.playback_state_changed.emit(False)
        elif state == vlc.State.Ended:
            self.playback_state_changed.emit(False)
            self.media_ended.emit()


    def _on_vlc_volume_changed(self, event):
        if self.is_loading_media:
            return
        self.volume_level_changed.emit(self.vlc_player.audio_get_volume(), self.vlc_player.audio_get_mute())


    # --- FUNGSI-FUNGSI UTAMA YANG DIUBAH UNTUK VLC ---


    def _set_video_output(self, widget):
        """Mengatur output video VLC ke widget tertentu."""
        if platform.system() == "Windows":
            self.vlc_player.set_hwnd(widget.winId())
        else: # Linux, MacOS
            self.vlc_player.set_xwindow(widget.winId())


    def _toggle_play_pause(self):
        if self.vlc_player.is_playing():
            self.vlc_player.pause()
        else:
            self.vlc_player.play()


    def _stop_video(self):
        self.vlc_player.stop()
        self._update_time_label(0, 0)
        self.position_slider.setValue(0)
        self._update_control_states()
        self.subtitle_text_item.setHtml("")
        self.current_subtitle_text = ""


    def _load_video_file(self, file_path_or_url):
        self.setWindowTitle(f"Macan Player - Memuat...")
        self._stop_video()
        
        is_url = "://" in file_path_or_url
        if not is_url:
            self._load_subtitle_file(file_path_or_url)
        
        media = self.vlc_instance.media_new(file_path_or_url)
        self.vlc_player.set_media(media)
        
        self.vlc_player.audio_set_volume(self.volume_slider.value())
        
        # Tambahkan pembaruan title/path ke self.current_media_info di sini
        title = self.current_media_info.get('title', os.path.basename(file_path_or_url))
        self.current_media_info = {'path': file_path_or_url, 'title': title}
        
        self.vlc_player.play()
        QTimer.singleShot(500, self._sync_volume_slider)
        self.setWindowTitle(f"Macan Player - {title}")
        self._update_control_states()
        self._add_to_history(file_path_or_url, title)
        QTimer.singleShot(100, lambda: setattr(self, 'is_loading_media', False))


    def _sync_volume_slider(self):
        vol = self.vlc_player.audio_get_volume()
        vol = max(0, min(100, vol))
        self.volume_slider.setValue(vol)
        self._last_known_volume = vol
        self._update_volume_icon()


    def _set_position(self, position):
        self.vlc_player.set_time(position)


    def _set_volume(self, value):
        self.vlc_player.audio_set_volume(value)


    def _toggle_mute(self):
        self.vlc_player.audio_toggle_mute()


    def _update_position(self, position):
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        
        duration = self.vlc_player.get_length()
        if duration <= 0:
            duration = self.position_slider.maximum()
            
        self._update_time_label(position, duration)


        if self.srt_parser:
            subtitle_text = self.srt_parser.get_subtitle(position)
            display_html = ""
            if subtitle_text:
                subtitle_text = subtitle_text.replace('\n', '<br>')
                style = "color: white; background-color: rgba(0, 0, 0, 0.6); padding: 5px; border-radius: 5px;"
                display_html = f"<div style='{style}'>{subtitle_text}</div>"


            if display_html != self.current_subtitle_text:
                self.current_subtitle_text = display_html
                self.subtitle_text_item.setHtml(f"<center>{display_html}</center>")
                self._reposition_subtitle()


    def _update_duration(self, duration):
        self.position_slider.setRange(0, duration)


    def _change_playback_speed(self):
        self.current_speed_index = (self.current_speed_index + 1) % len(self.playback_speeds)
        new_speed = self.playback_speeds[self.current_speed_index]
        self.vlc_player.set_rate(new_speed)
        self.btn_speed.setText(f"{new_speed}x")
    
    def _update_volume_icon(self):
        if not qta: return
        volume = self.vlc_player.audio_get_volume()
        is_muted = self.vlc_player.audio_get_mute()
        if is_muted or volume == 0: icon = qta.icon('fa5s.volume-mute')
        elif 0 < volume <= 50: icon = qta.icon('fa5s.volume-down')
        else: icon = qta.icon('fa5s.volume-up')
        self.btn_mute.setIcon(icon)


    def _sync_main_volume_slider(self, volume, is_muted):
        if not self.volume_slider.isSliderDown():
            self.volume_slider.setValue(0 if is_muted else volume)
        self._update_volume_icon()


    def _update_control_states(self):
        media = self.vlc_player.get_media()
        is_media_loaded = media is not None
        if is_media_loaded:
            self.splash_label.hide()
            self.video_frame.show()
        else:
            self.video_frame.hide()
            self.splash_label.show()
        
        self.btn_play_pause.setEnabled(is_media_loaded)
        self.btn_stop.setEnabled(is_media_loaded)
        self._update_playlist_nav_buttons()


    def _update_play_pause_icon(self, is_playing):
        if qta:
            icon = qta.icon('fa5s.pause') if is_playing else qta.icon('fa5s.play')
            self.btn_play_pause.setIcon(icon)


    def _handle_media_status_changed(self):
        current_index = self.playlist_widget.get_current_index()
        playlist_data = self.playlist_widget.get_playlist_data()
        if current_index < len(playlist_data) - 1:
            self._play_next_video()
        else:
            self._stop_video()


    def eventFilter(self, source, event):
        if source is self.video_frame:
            if event.type() == QEvent.MouseButtonPress:
                if self.btn_play_pause.isEnabled(): self._toggle_play_pause()
                return True
            elif event.type() == QEvent.MouseButtonDblClick:
                self._toggle_fullscreen()
                return True
        return super().eventFilter(source, event)
        
    # --- FUNGSI-FUNGSI LAINNYA ---
    def _show_thumbnail_preview(self, x_pos):
        video_path = self.current_media_info.get('path', '')
        is_url = "://" in video_path
        media = self.vlc_player.get_media()
        if not media or self.vlc_player.get_length() <= 0 or is_url or not os.path.exists(video_path): return
        value = self.position_slider.minimum() + (self.position_slider.maximum() - self.position_slider.minimum()) * x_pos / self.position_slider.width()
        timestamp_ms = int(value)
        global_slider_pos = self.position_slider.mapToGlobal(self.position_slider.rect().topLeft())
        preview_x = global_slider_pos.x() + x_pos - (self.thumbnail_preview.width() / 2)
        preview_y = global_slider_pos.y() - self.thumbnail_preview.height() - 5
        self.thumbnail_preview.move(int(preview_x), int(preview_y))
        if not self.thumbnail_preview.isVisible():
            self.thumbnail_preview.show()
            self.thumbnail_preview.label.setText("Memuat...")
        current_time = time.time()
        if current_time - self.last_thumbnail_request_time > 0.1:
            self.last_thumbnail_request_time = current_time
            self.request_thumbnail.emit(video_path, timestamp_ms, current_time)


    @Slot(QPixmap, float)
    def _update_thumbnail(self, pixmap, request_time):
        if request_time == self.last_thumbnail_request_time and self.thumbnail_preview.isVisible():
            self.thumbnail_preview.set_thumbnail(pixmap)


    def _show_history_window(self):
        self.history_window.populate_list()
        self.history_window.exec()
    def _add_to_history(self, path, title):
        self.history = [item for item in self.history if item.get('path') != path]
        self.history.append({'path': path, 'title': title})
        if len(self.history) > 50: self.history = self.history[-50:]
    def _play_from_history(self, item):
        path = item.get('path')
        if not path: return
        self._load_video_file(path)
    def _load_subtitle_file(self, video_path):
        self.srt_parser = None
        self.subtitle_text_item.setHtml("")
        base_name, _ = os.path.splitext(video_path)
        srt_path = base_name + ".srt"
        if os.path.exists(srt_path):
            print(f"File subtitle ditemukan: {srt_path}")
            self.srt_parser = SRTParser(srt_path)
        else:
            print("Tidak ada file subtitle (.srt) yang cocok.")
    def _delete_history_item(self, index):
        if 0 <= index < len(self.history):
            del self.history[index]
            self.history_window.populate_list()
            self._save_config()
    def _clear_all_history_data(self):
        self.history.clear()
        self.history_window.populate_list()
        self._save_config()


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path) and os.path.splitext(file_path)[1].lower() in ['.mp4', '.mkv', '.webm', '.avi']:
                self._load_video_file(file_path)
                break
        event.acceptProposedAction()


    def _hide_controls(self):
        if self.is_fullscreen and self.vlc_player.is_playing():
            self.setCursor(Qt.BlankCursor)
            self.controls_container.setVisible(False)


    def open_file_from_path(self, file_path):
        if file_path and os.path.exists(file_path) and any(file_path.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.webm', '.avi']):
            self._load_video_file(file_path)
        else:
            QMessageBox.warning(self, "Tipe File Tidak Didukung", "File bukan video yang didukung.")


    def _toggle_url_bar(self):
        self.url_bar_widget.setVisible(not self.url_bar_widget.isVisible())


    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Video", "", "Video Files (*.mp4 *.mkv *.webm *.avi)")
        if file_path: self._load_video_file(file_path)


    def _load_and_play_from_playlist(self, file_path):
        self._load_video_file(file_path)
        self._update_playlist_nav_buttons()


    def _play_next_video(self):
        current_index = self.playlist_widget.get_current_index()
        playlist_data = self.playlist_widget.get_playlist_data()
        new_index = current_index + 1
        if 0 <= new_index < len(playlist_data):
            self._load_and_play_from_playlist(playlist_data[new_index]['path'])
            self.playlist_widget._update_selection(new_index)


    def _play_previous_video(self):
        current_index = self.playlist_widget.get_current_index()
        playlist_data = self.playlist_widget.get_playlist_data()
        new_index = current_index - 1
        if 0 <= new_index < len(playlist_data):
            self._load_and_play_from_playlist(playlist_data[new_index]['path'])
            self.playlist_widget._update_selection(new_index)


    def _update_playlist_nav_buttons(self):
        playlist_data = self.playlist_widget.get_playlist_data()
        current_index = self.playlist_widget.get_current_index()
        self.btn_prev_playlist.setEnabled(current_index > 0)
        self.btn_next_playlist.setEnabled(current_index < len(playlist_data) - 1)


    def _toggle_playlist_window(self):
        if self.playlist_widget.isVisible(): self.playlist_widget.hide()
        else: self.playlist_widget.show()


    def _load_from_url(self):
        url = self.url_input.text().strip()
        if not url: return
        
        if not YTDLP_EXECUTABLE:
            QMessageBox.critical(self, "Error", "File eksekusi macan-engine.exe tidak ditemukan. Tidak dapat memuat URL.")
            return

        self.setWindowTitle("Macan Player - Mengambil info video...")
        
        # Menggunakan QThread untuk Worker
        self._youtube_dl_thread = QThread()
        self.worker = YouTubeDLWorker(url)
        self.worker.moveToThread(self._youtube_dl_thread)
        self.worker.finished.connect(self._on_youtube_dl_finished)
        self._youtube_dl_thread.started.connect(self.worker.run)
        self._youtube_dl_thread.start()
        
        # Pastikan thread dihentikan setelah selesai
        self.worker.finished.connect(self._youtube_dl_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self._youtube_dl_thread.finished.connect(self._youtube_dl_thread.deleteLater)


    def _on_youtube_dl_finished(self, video_url, title, error):
        if error or not video_url:
            QMessageBox.critical(self, "Error URL", error or "URL tidak valid atau gagal mendapatkan URL stream.")
            self.setWindowTitle("Macan Player")
            return
        self.current_media_info = {'path': video_url, 'title': title}
        self._load_video_file(video_url)
        
    def _skip_forward(self):
        self._set_position(self.vlc_player.get_time() + self.SKIP_INTERVAL)


    def _skip_backward(self):
        self._set_position(max(0, self.vlc_player.get_time() - self.SKIP_INTERVAL))
    
    def _reposition_subtitle(self):
        if not self.subtitle_text_item.toPlainText():
            return
        self.subtitle_scene.setSceneRect(QRectF(self.subtitle_view.rect()))
        text_rect = self.subtitle_text_item.boundingRect()
        view_rect = self.subtitle_view.viewport().rect()
        x = (view_rect.width() - text_rect.width()) / 2
        y = view_rect.height() - text_rect.height() - 20
        self.subtitle_text_item.setPos(x, y)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_subtitle()


    def _update_time_label(self, position, duration):
        if duration > 0:
            pos_time = QTime(0, 0, 0).addMSecs(position)
            dur_time = QTime(0, 0, 0).addMSecs(duration)
            fmt = 'hh:mm:ss' if duration >= 3600000 else 'mm:ss'
            self.time_label.setText(f"{pos_time.toString(fmt)} / {dur_time.toString(fmt)}")
        else:
            self.time_label.setText("00:00 / 00:00")


    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.normal_geometry = self.geometry()
            self.showFullScreen()
        else:
            self.showNormal()
            if self.normal_geometry: self.setGeometry(self.normal_geometry)
            self.controls_container.setVisible(True)
            self.setCursor(Qt.ArrowCursor)


    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F11 or (key == Qt.Key_Escape and self.is_fullscreen):
            self._toggle_fullscreen()
        elif key == Qt.Key_Space:
            if self.is_fullscreen:
                self.controls_container.setVisible(True)
                self.setCursor(Qt.ArrowCursor)
                self.controls_hide_timer.start()
            else:
                self._toggle_play_pause()
        elif key == Qt.Key_Right: self._skip_forward()
        elif key == Qt.Key_Left: self._skip_backward()
        else: super().keyPressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_fullscreen:
            self.controls_container.setVisible(True)
            self.setCursor(Qt.ArrowCursor)
            self.controls_hide_timer.start()
        super().mouseMoveEvent(event)


    def closeEvent(self, event):
        self._save_config()
        self.playlist_widget.close()
        self.history_window.close()
        # Perbaiki penghapusan thread thumbnail
        if self.thumbnail_thread.isRunning():
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()
        self.vlc_player.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = ModernVideoPlayer()
    if len(sys.argv) > 1:
        QTimer.singleShot(0, lambda: player.open_file_from_path(sys.argv[1]))
    player.show()

    sys.exit(app.exec())
