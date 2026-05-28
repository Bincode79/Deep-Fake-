"""PySide6 UI for Deep-Live-Cam.

Public API kept stable for the rest of the codebase:
    init(start, destroy, lang) -> _Window
        Returned object has .mainloop() that core.py calls.
    update_status(text)
        Thread-safe; routed through Qt signal when called off-UI.
    check_and_ignore_nsfw(target, destroy=None) -> bool
"""

from __future__ import annotations

import os
import platform
import queue
import sys
import tempfile
import threading
import time
import webbrowser
from typing import Callable, List, Optional, Tuple

import cv2
import numpy as np
import requests
from PIL import Image, ImageOps
from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

import modules.core
import modules.globals
import modules.metadata
from modules.face_analyser import (
    add_blank_map,
    detect_one_face_fast,
    ensure_landmarks,
    get_one_face,
    has_valid_map,
    simplify_maps,
)
from modules.gettext import LanguageManager
from modules.gpu_processing import gpu_cvt_color, gpu_flip, gpu_resize
from modules.processors.frame.core import get_frame_processors_modules
from modules.utilities import (
    has_image_extension,
    is_image,
)
from modules.video_capture import VideoCapturer

if platform.system() == "Windows":
    from pygrabber.dshow_graph import FilterGraph

import json


# ─── constants ────────────────────────────────────────────────────────────

ROOT_HEIGHT = 960
ROOT_WIDTH = 640

PREVIEW_DEFAULT_WIDTH = 640
PREVIEW_DEFAULT_HEIGHT = 360

POPUP_LIVE_WIDTH = 900
POPUP_LIVE_HEIGHT = 820
POPUP_LIVE_SCROLL_WIDTH = 870
POPUP_LIVE_SCROLL_HEIGHT = 700

MAPPER_PREVIEW_SIZE = 100


# ─── light theme stylesheet ──────────────────────────────────────────────

LIGHT_QSS = """
QMainWindow, QDialog { background-color: #f5f5f5; color: #1e1e1e; }
QWidget { color: #1e1e1e; font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif; font-size: 11pt; }

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #1a5bbf;
}

QPushButton {
    background-color: #2d6cdf;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover  { background-color: #3a7af0; }
QPushButton:pressed{ background-color: #1d57c2; }
QPushButton:disabled { background-color: #cccccc; color: #888888; }
QPushButton#secondary {
    background-color: #e0e0e0;
    color: #1e1e1e;
}
QPushButton#secondary:hover { background-color: #d0d0d0; }
QPushButton#danger { background-color: #c2412d; }
QPushButton#danger:hover  { background-color: #d8523c; }

QComboBox {
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
    color: #1e1e1e;
}
QComboBox:hover { border-color: #2d6cdf; }
QComboBox QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #2d6cdf;
    selection-color: white;
    border: 1px solid #c0c0c0;
}

QCheckBox {
    spacing: 8px;
    padding: 4px 0;
    color: #1e1e1e;
}
QCheckBox::indicator {
    width: 36px; height: 18px;
    border-radius: 9px;
    background-color: #c0c0c0;
}
QCheckBox::indicator:checked {
    background-color: #2d6cdf;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #d0d0d0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 16px; height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 1px solid #888888;
}
QSlider::sub-page:horizontal {
    background: #2d6cdf;
    border-radius: 3px;
}

QLabel#imageDrop {
    background-color: #fafafa;
    border: 2px dashed #bbbbbb;
    border-radius: 8px;
    color: #666666;
}
QLabel#statusLabel {
    color: #666666;
    font-size: 10pt;
    font-style: italic;
}
QLabel#linkLabel {
    color: #1a5bbf;
    text-decoration: underline;
}

QScrollArea { border: none; background: transparent; }

QFrame#card {
    background-color: #ffffff;
    border-radius: 10px;
}
"""


# ─── modern dark stylesheet ───────────────────────────────────────────────

QSS = """
QMainWindow, QDialog { background-color: #1e1e1e; color: #e6e6e6; }
QWidget { color: #e6e6e6; font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif; font-size: 11pt; }

QGroupBox {
    background-color: #262626;
    border: 1px solid #333333;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #9ec5ff;
}

QPushButton {
    background-color: #2d6cdf;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover  { background-color: #3a7af0; }
QPushButton:pressed{ background-color: #1d57c2; }
QPushButton:disabled { background-color: #444; color: #888; }
QPushButton#secondary {
    background-color: #3a3a3a;
}
QPushButton#secondary:hover { background-color: #4a4a4a; }
QPushButton#danger { background-color: #c2412d; }
QPushButton#danger:hover  { background-color: #d8523c; }

QComboBox {
    background-color: #2a2a2a;
    border: 1px solid #404040;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}
QComboBox:hover { border-color: #2d6cdf; }
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    selection-background-color: #2d6cdf;
    border: 1px solid #404040;
}

QCheckBox {
    spacing: 8px;
    padding: 4px 0;
}
QCheckBox::indicator {
    width: 36px; height: 18px;
    border-radius: 9px;
    background-color: #3a3a3a;
}
QCheckBox::indicator:checked {
    background-color: #2d6cdf;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #3a3a3a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 16px; height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 1px solid #cccccc;
}
QSlider::sub-page:horizontal {
    background: #2d6cdf;
    border-radius: 3px;
}

QLabel#imageDrop {
    background-color: #2a2a2a;
    border: 2px dashed #444;
    border-radius: 8px;
}
QLabel#statusLabel {
    color: #b9b9b9;
    font-size: 10pt;
    font-style: italic;
}
QLabel#linkLabel {
    color: #6ea8ff;
    text-decoration: underline;
}

QScrollArea { border: none; background: transparent; }

QFrame#card {
    background-color: #262626;
    border-radius: 10px;
}
"""


# ─── module-level state ───────────────────────────────────────────────────

_APP: Optional[QApplication] = None
_MAIN: Optional["MainWindow"] = None
_WEBCAM_PREVIEW: Optional["WebcamPreviewWindow"] = None
_LIVE_MAPPER: Optional["LiveMapperDialog"] = None
_LANG: Optional[LanguageManager] = None
_BRIDGE: Optional["_UIBridge"] = None


def _(text: str) -> str:
    """Translate via LanguageManager; falls back to identity."""
    if _LANG is None:
        return text
    return _LANG._(text)


# Preserve original cwd state for file dialogs.
_RECENT_SOURCE_DIR: Optional[str] = None


# ─── image utilities ─────────────────────────────────────────────────────


def fit_image_to_size(image, width: int, height: int):
    """BGR ndarray → BGR ndarray scaled to fit within (width, height)."""
    if width is None and height is None or width <= 0 or height <= 0:
        return image
    h, w = image.shape[:2]
    ratio_w = width / w
    ratio_h = height / h
    ratio = min(ratio_w, ratio_h)
    new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
    return gpu_resize(image, dsize=new_size)


def _bgr_to_qpixmap(bgr: np.ndarray) -> QPixmap:
    """Zero-copy BGR ndarray → QPixmap."""
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """PIL.Image → QPixmap."""
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


def render_image_preview(image_path: str, size: Tuple[int, int]) -> QPixmap:
    image = Image.open(image_path)
    if size:
        image = ImageOps.fit(image, size, Image.LANCZOS)
    return _pil_to_qpixmap(image)


def render_video_preview(
    video_path: str, size: Tuple[int, int], frame_number: int = 0
) -> Optional[QPixmap]:
    capture = cv2.VideoCapture(video_path)
    try:
        if frame_number:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        has_frame, frame = capture.read()
        if not has_frame:
            return None
        image = Image.fromarray(gpu_cvt_color(frame, cv2.COLOR_BGR2RGB))
        if size:
            image = ImageOps.fit(image, size, Image.LANCZOS)
        return _pil_to_qpixmap(image)
    finally:
        capture.release()


# ─── persistence ─────────────────────────────────────────────────────────


def save_switch_states():
    state = {
        "keep_fps": modules.globals.keep_fps,
        "keep_audio": modules.globals.keep_audio,
        "keep_frames": modules.globals.keep_frames,
        "keep_fps": modules.globals.keep_fps,
        "map_faces": modules.globals.map_faces,
        "poisson_blend": modules.globals.poisson_blend,
        "color_correction": modules.globals.color_correction,
        "nsfw_filter": modules.globals.nsfw_filter,
        "live_mirror": modules.globals.live_mirror,
        "live_resizable": modules.globals.live_resizable,
        "fp_ui": modules.globals.fp_ui,
        "show_fps": modules.globals.show_fps,
        "theme": modules.globals.theme,
    }
    try:
        with open("switch_states.json", "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def load_switch_states():
    try:
        with open("switch_states.json", "r") as f:
            state = json.load(f)
        modules.globals.keep_fps = state.get("keep_fps", True)
        modules.globals.keep_audio = state.get("keep_audio", True)
        modules.globals.keep_frames = state.get("keep_frames", False)
        modules.globals.map_faces = state.get("map_faces", False)
        modules.globals.poisson_blend = state.get("poisson_blend", False)
        modules.globals.color_correction = state.get("color_correction", False)
        modules.globals.nsfw_filter = state.get("nsfw_filter", False)
        modules.globals.live_mirror = state.get("live_mirror", False)
        modules.globals.live_resizable = state.get("live_resizable", False)
        modules.globals.fp_ui = state.get("fp_ui", {"face_enhancer": False})
        modules.globals.show_fps = state.get("show_fps", False)
        modules.globals.theme = state.get("theme", "dark")
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError):
        pass


def apply_theme():
    """Apply the current theme (dark/light) to the application."""
    if _APP is None:
        return
    qss = LIGHT_QSS if modules.globals.theme == "light" else QSS
    _APP.setStyleSheet(qss)
    save_switch_states()


# ─── thread-safe status bridge ───────────────────────────────────────────


class _UIBridge(QObject):
    """Single QObject that owns cross-thread signals."""

    statusChanged = Signal(str)


def _emit_status(text: str) -> None:
    if _BRIDGE is None:
        print(text)
        return
    _BRIDGE.statusChanged.emit(text)


# ─── public API ──────────────────────────────────────────────────────────


def detect_first_face_from_target(target_path: str):
    """Auto-detect the first face from target image/video when no source is selected."""
    from modules.face_analyser import get_one_face
    import cv2
    ext = os.path.splitext(target_path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'):
        frame = cv2.imread(target_path)
        if frame is not None:
            return get_one_face(frame)
    elif ext in ('.mp4', '.avi', '.mov', '.mkv', '.webm'):
        cap = cv2.VideoCapture(target_path)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            return get_one_face(frame)
    return None


def update_status(text: str) -> None:
    """Thread-safe status update — uses signal if called off-UI thread."""
    _emit_status(_(text))
    if _APP is not None and QThread.currentThread() is _APP.thread():
        # On UI thread — flush events so the user sees the update during
        # long synchronous start() runs.
        _APP.processEvents()


def check_and_ignore_nsfw(target, destroy: Optional[Callable] = None) -> bool:
    from numpy import ndarray
    from modules.predicter import predict_frame, predict_image, predict_video

    check_nsfw = None
    if isinstance(target, str):
        check_nsfw = predict_image if has_image_extension(target) else predict_video
    elif isinstance(target, ndarray):
        check_nsfw = predict_frame

    if check_nsfw and check_nsfw(target):
        if destroy:
            destroy(to_quit=False)
        update_status("Processing ignored!")
        return True
    return False


# ─── camera enumeration (unchanged from tk version) ──────────────────────


def get_available_cameras() -> Tuple[List[int], List[str]]:
    if platform.system() == "Windows":
        try:
            graph = FilterGraph()
            devices = graph.get_input_devices()
            if devices:
                return list(range(len(devices))), devices
            return [], ["No cameras found"]
        except Exception as exc:
            print(f"Error detecting cameras: {exc}")
            return [], ["No cameras found"]

    if platform.system() == "Darwin":
        return [0, 1], ["Camera 0", "Camera 1"]

    # Linux probe
    indices: List[int] = []
    names: List[str] = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            indices.append(i)
            names.append(f"Camera {i}")
            cap.release()
    return (indices, names) if names else ([], ["No cameras found"])


# ─── main window ─────────────────────────────────────────────────────────


def _make_image_drop(text: str, size: Tuple[int, int]) -> QLabel:
    label = QLabel(text)
    label.setObjectName("imageDrop")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedSize(size[0], size[1])
    label.setText(text)
    return label


class _Switch(QWidget):
    """Compact toggle switch with label + optional tooltip."""

    toggled = Signal(bool)

    def __init__(self, text: str, initial: bool, tooltip: str = ""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._checkbox = QCheckBox(text)
        self._checkbox.setChecked(initial)
        self._checkbox.toggled.connect(self.toggled.emit)
        if tooltip:
            self._checkbox.setToolTip(tooltip)
        layout.addWidget(self._checkbox)
        layout.addStretch(1)

    def isChecked(self) -> bool:
        return self._checkbox.isChecked()

    def setChecked(self, value: bool) -> None:
        self._checkbox.setChecked(value)


class MainWindow(QMainWindow):
    def __init__(self, destroy_cb: Callable):
        super().__init__()
        load_switch_states()
        self._destroy_cb = destroy_cb

        # Live preview state
        self._cap = None
        self._capture_queue: Optional[queue.Queue] = None
        self._processed_queue: Optional[queue.Queue] = None
        self._stop_event: Optional[threading.Event] = None
        self._capture_worker: Optional[QThread] = None
        self._processing_worker: Optional[QThread] = None
        self._preview_timer: Optional[QTimer] = None
        self._saved_source_pixmap: Optional[QPixmap] = None

        self.setWindowTitle(
            f"{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}"
        )
        self.setMinimumSize(ROOT_WIDTH, ROOT_HEIGHT)
        self.resize(ROOT_WIDTH, ROOT_HEIGHT)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Source face + live preview
        layout.addLayout(self._build_image_row())

        # Status merged into progress table
        layout.addWidget(self._build_progress_table())

        # Options grid
        layout.addWidget(self._build_options_card())

        # Sliders card
        layout.addWidget(self._build_sliders_card())

        # Action buttons
        layout.addLayout(self._build_action_row())

        # Camera selection (ẩn nếu không có camera)
        self._cam_card = self._build_camera_card()
        if self._cam_card is not None:
            layout.addWidget(self._cam_card)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)

        footer = QLabel("Deep Live Cam")
        footer.setObjectName("linkLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.mousePressEvent = lambda _e: webbrowser.open("https://deeplivecam.net")
        footer_row.addWidget(footer, 1)

        # Theme toggle button
        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("secondary")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip(_("Toggle dark/light theme"))
        self._update_theme_btn_icon()
        self._theme_btn.clicked.connect(self._on_toggle_theme)
        footer_row.addWidget(self._theme_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(footer_row)

        # --- keyboard shortcuts ---
        QShortcut(QKeySequence("Return"), self, self._on_start)
        QShortcut(QKeySequence("Space"), self, self._on_start)
        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_select_source)
        QShortcut(QKeySequence("Ctrl+T"), self, self._on_select_target)
        QShortcut(QKeySequence("Ctrl+L"), self, self._on_live)
        QShortcut(QKeySequence("Ctrl+Q"), self, lambda: self._destroy_cb())

    # ── image row ────────────────────────────────────────────────────────

    def _build_image_row(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Source face preview
        self.source_label = _make_image_drop(_("Khuôn mặt nguồn"), (200, 200))
        layout.addWidget(self.source_label, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        self.btn_select_source = QPushButton(_("Chọn ảnh"))
        self.btn_select_source.setToolTip(
            _("Choose the source face image to swap onto the target")
        )
        self.btn_select_source.clicked.connect(self._on_select_source)
        self.btn_random_face = QPushButton("🔄")
        self.btn_random_face.setObjectName("secondary")
        self.btn_random_face.setFixedWidth(40)
        self.btn_random_face.setToolTip(
            _("Get a random face from thispersondoesnotexist.com")
        )
        self.btn_random_face.clicked.connect(self._on_random_face)
        btn_row.addWidget(self.btn_select_source)
        btn_row.addWidget(self.btn_random_face)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return layout

    # ── options card ─────────────────────────────────────────────────────

    def _build_options_card(self) -> QGroupBox:
        card = QGroupBox(_("Tùy chọn"))
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)

        def make(field, label, tip):
            sw = _Switch(_(label), getattr(modules.globals, field), _(tip))
            sw.toggled.connect(
                lambda v, f=field: (
                    setattr(modules.globals, f, v),
                    save_switch_states(),
                )
            )
            return sw

        self.sw_show_fps = make("show_fps", "Show FPS",
                                "Display frames-per-second counter on the live preview")
        self.sw_live_mirror = make("live_mirror", "Live Mirror",
                                   "Mirror the live camera display horizontally")
        self.sw_color_fix = make("color_correction", "Fix Blueish Cam",
                                 "Fix blue/green color cast from some webcams")

        # Map faces is special — closes mapper when toggled off.
        self.sw_map_faces = _Switch(_("Map faces"), modules.globals.map_faces,
                                    _("Manually assign which source face maps to which target face"))
        self.sw_map_faces.toggled.connect(self._on_map_faces_toggled)

        # Face enhancer dropdown
        enhancer_label = QLabel(_("Face Enhancer:"))
        grid.addWidget(enhancer_label, 0, 0)

        self.cb_enhancer = QComboBox()
        items = [_("None"), "GFPGAN", "GPEN-512", "GPEN-256"]
        self.cb_enhancer.addItems(items)
        initial = _("None")
        if modules.globals.fp_ui.get("face_enhancer", False):
            initial = "GFPGAN"
        elif modules.globals.fp_ui.get("face_enhancer_gpen512", False):
            initial = "GPEN-512"
        elif modules.globals.fp_ui.get("face_enhancer_gpen256", False):
            initial = "GPEN-256"
        self.cb_enhancer.setCurrentText(initial)
        self.cb_enhancer.currentTextChanged.connect(self._on_enhancer_change)
        self.cb_enhancer.setToolTip(_("Select a face enhancement model (None = no enhancement)"))
        grid.addWidget(self.cb_enhancer, 0, 1)

        # Layout: 2 columns of toggles
        items = [
            self.sw_show_fps,
            self.sw_live_mirror, self.sw_color_fix,
            self.sw_map_faces,
        ]
        for i, w in enumerate(items):
            grid.addWidget(w, (i // 2) + 1, i % 2)

        return card

    # ── sliders card ─────────────────────────────────────────────────────

    def _build_sliders_card(self) -> QGroupBox:
        card = QGroupBox(_("Tinh chỉnh"))
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        def slider(min_v, max_v, default, denom, on_change):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(int(min_v * denom), int(max_v * denom))
            s.setValue(int(default * denom))
            s.valueChanged.connect(lambda iv: on_change(iv / denom))
            return s

        # Transparency
        grid.addWidget(QLabel(_("Transparency")), 0, 0)
        self.s_transparency = slider(0.0, 1.0, 1.0, 100, self._on_transparency_change)
        self.s_transparency.setToolTip(
            _("Blend between original and swapped face (0% = original, 100% = fully swapped)")
        )
        grid.addWidget(self.s_transparency, 0, 1)

        # Sharpness
        grid.addWidget(QLabel(_("Sharpness")), 1, 0)
        self.s_sharpness = slider(0.0, 5.0, 0.0, 10, self._on_sharpness_change)
        self.s_sharpness.setToolTip(_("Sharpen the enhanced face output"))
        grid.addWidget(self.s_sharpness, 1, 1)

        return card

    # ── progress table (thay thế target card) ──────────────────────────

    def _build_progress_table(self) -> QGroupBox:
        card = QGroupBox(_("Tiến trình xử lý"))
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Dòng trạng thái chính
        status_row = QHBoxLayout()
        self.progress_icon = QLabel("⏳")
        self.progress_icon.setStyleSheet("font-size: 18px;")
        status_row.addWidget(self.progress_icon)
        self.progress_step = QLabel(_("Sẵn sàng"))
        self.progress_step.setStyleSheet("font-size: 13px; font-weight: 600;")
        status_row.addWidget(self.progress_step, 1)
        self.progress_time = QLabel("00:00")
        self.progress_time.setStyleSheet("color: #888; font-size: 11px;")
        status_row.addWidget(self.progress_time)
        layout.addLayout(status_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Nhật ký xử lý (log) + nút xóa
        log_row = QHBoxLayout()
        log_label = QLabel(_("Nhật ký:"))
        log_label.setStyleSheet("font-size: 11px; color: #888;")
        log_row.addWidget(log_label)
        log_row.addStretch(1)
        self.btn_clear_log = QPushButton(_("Xóa"))
        self.btn_clear_log.setObjectName("secondary")
        self.btn_clear_log.setFixedHeight(20)
        self.btn_clear_log.setFixedWidth(50)
        self.btn_clear_log.clicked.connect(self._on_clear_log)
        log_row.addWidget(self.btn_clear_log)
        layout.addLayout(log_row)

        self.progress_log = QListWidget()
        self.progress_log.setMaximumHeight(100)
        self.progress_log.setAlternatingRowColors(True)
        self.progress_log.setStyleSheet("QListWidget { font-size: 11px; } QListWidget::item { padding: 2px 4px; }")
        layout.addWidget(self.progress_log)

        # File info row (thu gọn) — cho phép chọn target/output
        file_row = QHBoxLayout()
        file_row.setSpacing(4)
        self.lbl_target = QLabel(_("Chưa chọn tệp"))
        self.lbl_target.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_target.setToolTip(_("Target file:"))
        file_row.addWidget(QLabel("📁"), 0, Qt.AlignmentFlag.AlignCenter)
        file_row.addWidget(self.lbl_target, 1)
        self.btn_select_target = QPushButton(_("Chọn tệp"))
        self.btn_select_target.setObjectName("secondary")
        self.btn_select_target.setFixedHeight(24)
        self.btn_select_target.clicked.connect(self._on_select_target)
        file_row.addWidget(self.btn_select_target)
        self.lbl_output = QLabel(_("Auto"))
        self.lbl_output.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_output.setToolTip(_("Output:"))
        file_row.addWidget(self.lbl_output)
        self.btn_select_output = QPushButton(_("Đầu ra"))
        self.btn_select_output.setObjectName("secondary")
        self.btn_select_output.setFixedHeight(24)
        self.btn_select_output.clicked.connect(self._on_select_output)
        file_row.addWidget(self.btn_select_output)
        layout.addLayout(file_row)

        # Bộ đếm thời gian chạy
        self._elapsed_seconds = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._on_elapsed_tick)

        # Kết nối tín hiệu cập nhật
        self._progress_log_entries = []
        self._connect_progress()

        return card

    def _connect_progress(self) -> None:
        global _BRIDGE
        if _BRIDGE is None:
            _BRIDGE = _UIBridge()
        _BRIDGE.statusChanged.connect(self._on_progress_status)

    def _on_elapsed_tick(self) -> None:
        self._elapsed_seconds += 1
        m, s = divmod(self._elapsed_seconds, 60)
        self.progress_time.setText(f"{m:02d}:{s:02d}")

    def _on_clear_log(self) -> None:
        self.progress_log.clear()
        self._progress_log_entries.clear()

    def _on_progress_status(self, text: str) -> None:
        """Cập nhật bảng tiến trình khi nhận được status mới."""
        # Cập nhật bước hiện tại
        self.progress_step.setText(text)
        self.progress_icon.setText("🔄")

        # Thêm vào nhật ký
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {text}"
        self._progress_log_entries.append(entry)
        if len(self._progress_log_entries) > 30:
            self._progress_log_entries.pop(0)
            self.progress_log.takeItem(0)
        self.progress_log.addItem(entry)
        self.progress_log.scrollToBottom()

        # Phân tích tiến độ từ text
        if "/" in text and any(c.isdigit() for c in text.split("/")[0].strip()):
            import re
            nums = re.findall(r'(\d+)\s*/\s*(\d+)', text)
            if nums:
                cur, total = int(nums[0][0]), int(nums[0][1])
                if total > 0:
                    pct = min(int(cur / total * 100), 100)
                    self.progress_bar.setValue(pct)

    def _reset_progress(self) -> None:
        """Đặt lại bảng tiến trình về trạng thái sẵn sàng."""
        self.progress_icon.setText("⏳")
        self.progress_step.setText(_("Sẵn sàng"))
        self.progress_bar.setValue(0)
        self._elapsed_seconds = 0
        self.progress_time.setText("00:00")
        self._elapsed_timer.stop()
        self.progress_log.clear()
        self._progress_log_entries.clear()

    # ── action row ───────────────────────────────────────────────────────

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)

        self.btn_start = QPushButton(_("Bắt đầu"))
        self.btn_start.setObjectName("primary")
        self.btn_start.setToolTip(_("Start processing the target image/video with the selected source face"))
        self.btn_start.clicked.connect(self._on_start)
        row.addWidget(self.btn_start)

        self.btn_stop = QPushButton(_("Dừng"))
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setToolTip(_("Dừng xử lý"))
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setVisible(False)
        row.addWidget(self.btn_stop)

        self.btn_destroy = QPushButton(_("Kết thúc"))
        self.btn_destroy.setObjectName("danger")
        self.btn_destroy.setToolTip(_("Stop processing and close the application"))
        self.btn_destroy.clicked.connect(lambda: self._destroy_cb())

        row.addWidget(self.btn_destroy)
        return row

    def _on_stop(self) -> None:
        modules.globals.cancelled = True
        update_status(_("Đã yêu cầu dừng..."))
        self.btn_stop.setEnabled(False)

    # ── camera card ──────────────────────────────────────────────────────

    def _build_camera_card(self) -> QGroupBox:
        self._camera_indices, self._camera_names = get_available_cameras()
        if not self._camera_indices:
            return None
        card = QGroupBox(_("Camera"))
        layout = QHBoxLayout(card)

        layout.addWidget(QLabel(_("Select Camera:")))

        self.cb_camera = QComboBox()
        self.cb_camera.addItems(self._camera_names)
        self.cb_camera.setToolTip(_("Select which camera to use for live mode"))
        layout.addWidget(self.cb_camera, 1)

        self.btn_live = QPushButton(_("Live"))
        self.btn_live.setToolTip(_("Start real-time face swap using webcam"))
        self.btn_live.clicked.connect(self._on_live)
        layout.addWidget(self.btn_live)

        return card

    # ── slot handlers ────────────────────────────────────────────────────

    def _on_select_source(self) -> None:
        global _RECENT_SOURCE_DIR
        path, _filter = QFileDialog.getOpenFileName(
            self, _("select an source image"),
            _RECENT_SOURCE_DIR or "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)",
        )
        if path and is_image(path):
            modules.globals.source_path = path
            _RECENT_SOURCE_DIR = os.path.dirname(path)
            self.source_label.setPixmap(render_image_preview(path, (200, 200)))
            self.source_label.setText("")
        elif not path:
            return
        else:
            modules.globals.source_path = None
            self.source_label.clear()
            self.source_label.setText(_("Khuôn mặt nguồn"))

    def _on_random_face(self) -> None:
        try:
            response = requests.get(
                "https://thispersondoesnotexist.com/",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
            temp_path = os.path.join(tempfile.gettempdir(), "deep_live_cam_random_face.jpg")
            with open(temp_path, "wb") as f:
                f.write(response.content)
            modules.globals.source_path = temp_path
            self.source_label.setPixmap(render_image_preview(temp_path, (200, 200)))
            self.source_label.setText("")
        except Exception as exc:
            print(f"Failed to fetch random face: {exc}")

    def _set_source_from_frame(self, face) -> None:
        """Update source preview with a detected face (insightface object)."""
        try:
            from PIL import Image, ImageOps
            img = face.bbox if hasattr(face, 'bbox') else None
            # Extract face region from the original frame if available
            if hasattr(face, 'detected_frame') and face.detected_frame is not None:
                frame = face.detected_frame
            else:
                return
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = [max(0, int(v)) for v in face.bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            image = ImageOps.fit(image, (200, 200), Image.LANCZOS)
            self.source_label.setPixmap(_pil_to_qpixmap(image))
            self.source_label.setText("")
        except Exception as e:
            print(f"Failed to set source from frame: {e}")

    def _on_select_target(self) -> None:
        global _RECENT_SOURCE_DIR
        path, _filter = QFileDialog.getOpenFileName(
            self, _("select a target image or video"),
            _RECENT_SOURCE_DIR or "",
            "Media (*.png *.jpg *.jpeg *.gif *.bmp *.mp4 *.mkv *.avi *.mov)",
        )
        if path:
            modules.globals.target_path = path
            _RECENT_SOURCE_DIR = os.path.dirname(path)
            self.lbl_target.setText(os.path.basename(path))
            self.lbl_target.setStyleSheet("color: #e6e6e6;")
            if modules.globals.output_path is None:
                from modules.utilities import normalize_output_path
                modules.globals.output_path = normalize_output_path(
                    modules.globals.source_path, path, None
                )
                self.lbl_output.setText(os.path.basename(modules.globals.output_path) if modules.globals.output_path else _("Auto"))

    def _on_select_output(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(
            self, _("select output file"),
            "",
            "Media (*.mp4 *.mkv *.avi *.png *.jpg)",
        )
        if path:
            modules.globals.output_path = path
            self.lbl_output.setText(os.path.basename(path))
            self.lbl_output.setStyleSheet("color: #e6e6e6;")

    def _on_start(self) -> None:
        if self._stop_event is not None and not self._stop_event.is_set():
            update_status("Please stop Live preview first")
            return
        if modules.globals.source_path is None:
            update_status("Please select a source image first")
            return
        if modules.globals.target_path is None:
            update_status("Please select a target image or video")
            return
        if not modules.globals.frame_processors:
            modules.globals.frame_processors = ["face_swapper"]
        modules.globals.cancelled = False
        self._reset_progress()
        self.btn_start.setEnabled(False)
        self.btn_start.setText(_("Đang xử lý..."))
        self.btn_live.setEnabled(False)
        self.btn_stop.setVisible(True)
        self.btn_stop.setEnabled(True)
        self._elapsed_timer.start(1000)
        thread = threading.Thread(target=self._run_start, daemon=True)
        thread.start()

    def _run_start(self) -> None:
        ok = False
        try:
            modules.core.start()
            ok = True
        except Exception as e:
            update_status(f"Processing failed: {e}")
        finally:
            cancelled = bool(getattr(modules.globals, "cancelled", False))
            QTimer.singleShot(
                0,
                lambda c=cancelled, success=ok: self._finish_processing(c, success),
            )

    def _finish_processing(self, cancelled: bool, success: bool) -> None:
        """UI-thread finalization after background processing completes."""
        self._elapsed_timer.stop()
        self.btn_stop.setEnabled(False)
        self.btn_stop.setVisible(False)
        self.btn_start.setText(_("Bắt đầu"))
        self.btn_start.setEnabled(True)
        self.btn_live.setEnabled(True)

        if cancelled:
            self.progress_icon.setText("⏹️")
            self.progress_step.setText(_("Đã hủy"))
        elif success and self.progress_icon.text() not in ("❌",):
            self.progress_icon.setText("✅")
            self.progress_step.setText(_("Hoàn tất"))
        elif self.progress_icon.text() not in ("❌",):
            self.progress_icon.setText("❌")
            self.progress_step.setText(_("Cảnh báo"))

    def _on_map_faces_toggled(self, value: bool) -> None:
        modules.globals.map_faces = value
        save_switch_states()
        if not value:
            close_mapper_window()

    def _on_enhancer_change(self, choice: str) -> None:
        key_map = {
            _("None"): None,
            "GFPGAN": "face_enhancer",
            "GPEN-512": "face_enhancer_gpen512",
            "GPEN-256": "face_enhancer_gpen256",
        }
        for key in ("face_enhancer", "face_enhancer_gpen256", "face_enhancer_gpen512"):
            _update_tumbler(key, False)
        selected = key_map.get(choice)
        if selected:
            _update_tumbler(selected, True)

    def _on_transparency_change(self, value: float) -> None:
        modules.globals.opacity = value
        pct = int(value * 100)
        if pct == 0:
            modules.globals.fp_ui["face_enhancer"] = False
            update_status("Transparency set to 0% - Face swapping disabled.")
        elif pct == 100:
            modules.globals.face_swapper_enabled = True
            update_status("Transparency set to 100%.")
        else:
            modules.globals.face_swapper_enabled = True
            update_status(_("Transparency set to %d%%") % pct)

    def _on_sharpness_change(self, value: float) -> None:
        modules.globals.sharpness = value
        update_status(_("Sharpness set to %.1f") % value)

    def _on_live(self) -> None:
        if not self.btn_start.isEnabled():
            update_status("Please wait for file processing to finish first")
            return
        if self._stop_event is not None and not self._stop_event.is_set():
            self._stop_live_preview()
            return
        idx = self.cb_camera.currentIndex()
        if idx < 0 or idx >= len(self._camera_indices):
            update_status("No camera available")
            return
        camera_index = self._camera_indices[idx]
        if _LIVE_MAPPER is not None and _LIVE_MAPPER.isVisible():
            update_status("Source x Target Mapper is already open.")
            _LIVE_MAPPER.raise_()
            return
        if not modules.globals.map_faces:
            if modules.globals.source_path is None:
                update_status("Please select a source image first")
                return
            from modules.face_analyser import get_face_analyser
            from modules.processors.frame.face_swapper import get_face_swapper
            get_face_analyser()
            get_face_swapper()
            self._start_live_preview(camera_index)
        else:
            modules.globals.source_target_map = []
            _open_live_mapper_dialog(camera_index, modules.globals.source_target_map)

    def _start_live_preview(self, camera_index: int) -> None:
        self._cap = VideoCapturer(camera_index)
        if not self._cap.start(PREVIEW_DEFAULT_WIDTH, PREVIEW_DEFAULT_HEIGHT, 60):
            update_status("Failed to start camera")
            return

        camera_fps = self._cap.actual_fps
        print(
            f"[webcam] Camera running at {self._cap.actual_width}x"
            f"{self._cap.actual_height}@{camera_fps:.0f}fps"
        )

        self._capture_queue = queue.Queue(maxsize=2)
        self._processed_queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

        self._capture_worker = _CaptureWorker(
            self._cap, self._capture_queue, self._stop_event
        )
        self._processing_worker = _ProcessingWorker(
            self._capture_queue, self._processed_queue, self._stop_event, camera_fps
        )
        self._capture_worker.start()
        self._processing_worker.start()

        poll_ms = max(1, min(16, int(500 / max(camera_fps, 1))))
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._tick_preview)
        self._preview_timer.start(poll_ms)

        self._saved_source_pixmap = self.source_label.pixmap()
        self.source_label.setText("")
        self.btn_live.setText(_("Stop"))
        self.btn_live.setToolTip(_("Stop live preview"))
        self.cb_camera.setEnabled(False)
        update_status("Live preview started")

        self._open_live_preview_window()

    def _open_live_preview_window(self) -> None:
        if hasattr(self, '_live_preview_window') and self._live_preview_window is not None:
            try:
                self._live_preview_window.close()
            except Exception:
                pass
        self._live_preview_window = _LivePreviewWindow(self._processed_queue, self._stop_event)
        self._live_preview_window.show()

    def _stop_live_preview(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._preview_timer:
            try:
                self._preview_timer.stop()
            except Exception:
                pass
            self._preview_timer = None
        for worker in (self._capture_worker, self._processing_worker):
            if worker:
                try:
                    worker.wait(2000)
                except Exception:
                    pass
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        if hasattr(self, '_live_preview_window') and self._live_preview_window is not None:
            try:
                self._live_preview_window.close()
            except Exception:
                pass
            self._live_preview_window = None
        self._cap = None
        self._capture_queue = None
        self._processed_queue = None
        self._stop_event = None
        self._capture_worker = None
        self._processing_worker = None

        self.source_label.clear()
        if self._saved_source_pixmap is not None:
            self.source_label.setPixmap(self._saved_source_pixmap)
            self._saved_source_pixmap = None
        else:
            self.source_label.setText(_("Source face"))
        self.btn_live.setText(_("Live"))
        self.btn_live.setToolTip(_("Start real-time face swap using webcam"))
        self.cb_camera.setEnabled(True)
        update_status("Live preview stopped")

    def _tick_preview(self) -> None:
        if self._stop_event and self._stop_event.is_set():
            self._stop_live_preview()
            return
        if not self._processed_queue:
            return
        try:
            bgr_frame = self._processed_queue.get_nowait()
        except queue.Empty:
            return
        bgr_frame = fit_image_to_size(bgr_frame, self.source_label.width(), self.source_label.height())
        self.source_label.setPixmap(_bgr_to_qpixmap(bgr_frame))

    def closeEvent(self, event) -> None:
        self._stop_live_preview()
        self._destroy_cb()
        event.accept()

    def _on_toggle_theme(self) -> None:
        """Switch between dark and light themes."""
        modules.globals.theme = "light" if modules.globals.theme == "dark" else "dark"
        apply_theme()
        self._update_theme_btn_icon()
        theme_name = _("Light") if modules.globals.theme == "light" else _("Dark")
        update_status(_("Switched to %s theme") % theme_name)

    def _update_theme_btn_icon(self) -> None:
        """Set button text based on current theme."""
        if modules.globals.theme == "dark":
            self._theme_btn.setText("☀️")
            self._theme_btn.setToolTip(_("Switch to Light theme"))
        else:
            self._theme_btn.setText("🌙")
            self._theme_btn.setToolTip(_("Switch to Dark theme"))


def _update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value
    save_switch_states()
    # If we're currently in a live preview, refresh frame processors so
    # toggling enhancers takes effect immediately.
    if _WEBCAM_PREVIEW is not None and _WEBCAM_PREVIEW.isVisible():
        get_frame_processors_modules(modules.globals.frame_processors)


# ─── webcam preview window ───────────────────────────────────────────────


class _CaptureWorker(QThread):
    """Reads frames from the camera into a bounded queue. Drops on overflow."""

    def __init__(self, cap, capture_queue: queue.Queue, stop_event: threading.Event):
        super().__init__()
        self._cap = cap
        self._queue = capture_queue
        self._stop = stop_event

    def run(self) -> None:
        while not self._stop.is_set():
            ret, frame = self._cap.read()
            if not ret:
                self._stop.set()
                break
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(frame)
                except queue.Full:
                    pass


class _ProcessingWorker(QThread):
    """Pulls raw frames, runs detect/swap/enhance, pushes processed frames."""

    def __init__(self, capture_queue, processed_queue, stop_event, camera_fps: float):
        super().__init__()
        self._cq = capture_queue
        self._pq = processed_queue
        self._stop = stop_event
        self._fps = camera_fps

    def run(self) -> None:
        frame_processors = get_frame_processors_modules(modules.globals.frame_processors)
        source_image = None
        last_source_path = None
        prev_time = time.time()
        fps_update_interval = 0.5
        frame_count = 0
        fps = 0.0
        det_count = 0
        cached_target_face = None
        det_interval = max(1, round(self._fps * 0.08))

        while not self._stop.is_set():
            try:
                frame = self._cq.get(timeout=0.05)
            except queue.Empty:
                continue

            temp_frame = frame
            if modules.globals.live_mirror:
                temp_frame = gpu_flip(temp_frame, 1)

            if not modules.globals.map_faces:
                if (
                    modules.globals.source_path
                    and modules.globals.source_path != last_source_path
                ):
                    last_source_path = modules.globals.source_path
                    source_image = get_one_face(cv2.imread(modules.globals.source_path))

                det_count += 1
                if det_count % det_interval == 0:
                    cached_target_face = detect_one_face_fast(temp_frame)

                cached_faces = [cached_target_face] if cached_target_face is not None else None

                # Fast detection skips the 2d106 landmark model, but the mouth
                # mask needs it. Attach landmarks on demand (computed once per
                # detection cycle — the helper no-ops if already present).
                if modules.globals.mouth_mask and cached_faces:
                    ensure_landmarks(temp_frame, cached_faces)

                for fp in frame_processors:
                    if fp.NAME == "DLC.FACE-ENHANCER":
                        if modules.globals.fp_ui["face_enhancer"]:
                            temp_frame = fp.process_frame(
                                None, temp_frame, detected_faces=cached_faces
                            )
                    elif fp.NAME == "DLC.FACE-ENHANCER-GPEN256":
                        if modules.globals.fp_ui.get("face_enhancer_gpen256", False):
                            temp_frame = fp.process_frame(
                                None, temp_frame, detected_faces=cached_faces
                            )
                    elif fp.NAME == "DLC.FACE-ENHANCER-GPEN512":
                        if modules.globals.fp_ui.get("face_enhancer_gpen512", False):
                            temp_frame = fp.process_frame(
                                None, temp_frame, detected_faces=cached_faces
                            )
                    elif fp.NAME == "DLC.FACE-SWAPPER":
                        swapped_bboxes = []
                        if cached_target_face is not None:
                            temp_frame = fp.swap_face(
                                source_image, cached_target_face, temp_frame
                            )
                            if (
                                hasattr(cached_target_face, "bbox")
                                and cached_target_face.bbox is not None
                            ):
                                swapped_bboxes.append(cached_target_face.bbox.astype(int))
                        temp_frame = fp.apply_post_processing(temp_frame, swapped_bboxes)
                    else:
                        temp_frame = fp.process_frame(source_image, temp_frame)
            else:
                modules.globals.target_path = None
                for fp in frame_processors:
                    if fp.NAME == "DLC.FACE-ENHANCER":
                        if modules.globals.fp_ui["face_enhancer"]:
                            temp_frame = fp.process_frame_v2(temp_frame)
                    elif fp.NAME in ("DLC.FACE-ENHANCER-GPEN256", "DLC.FACE-ENHANCER-GPEN512"):
                        fp_key = fp.NAME.split(".")[-1].lower().replace("-", "_")
                        if modules.globals.fp_ui.get(fp_key, False):
                            temp_frame = fp.process_frame_v2(temp_frame)
                    else:
                        temp_frame = fp.process_frame_v2(temp_frame)

            current_time = time.time()
            frame_count += 1
            if current_time - prev_time >= fps_update_interval:
                fps = frame_count / (current_time - prev_time)
                frame_count = 0
                prev_time = current_time

            if modules.globals.show_fps:
                cv2.putText(
                    temp_frame, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2,
                )

            try:
                self._pq.put_nowait(temp_frame)
            except queue.Full:
                try:
                    self._pq.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._pq.put_nowait(temp_frame)
                except queue.Full:
                    pass


class _LivePreviewWindow(QWidget):
    """Resizable live preview window that reads from a shared processed queue."""

    def __init__(self, processed_queue: queue.Queue, stop_event: threading.Event):
        super().__init__()
        self._queue = processed_queue
        self._stop = stop_event
        self.setWindowTitle(_("Live Preview"))
        self.resize(PREVIEW_DEFAULT_WIDTH, PREVIEW_DEFAULT_HEIGHT)
        self.setMinimumSize(320, 180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._image_label, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self) -> None:
        if self._stop.is_set():
            self.close()
            return
        try:
            bgr_frame = self._queue.get_nowait()
        except queue.Empty:
            return
        bgr_frame = fit_image_to_size(bgr_frame, self.width(), self.height())
        self._image_label.setPixmap(_bgr_to_qpixmap(bgr_frame))

    def closeEvent(self, event) -> None:
        try:
            self._timer.stop()
        except Exception:
            pass
        event.accept()


class WebcamPreviewWindow(QWidget):
    def __init__(self, camera_index: int):
        super().__init__()
        self.setWindowTitle(_("Live Preview"))
        self.resize(PREVIEW_DEFAULT_WIDTH, PREVIEW_DEFAULT_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._image_label, 1)

        self._cap = VideoCapturer(camera_index)
        if not self._cap.start(PREVIEW_DEFAULT_WIDTH, PREVIEW_DEFAULT_HEIGHT, 60):
            update_status("Failed to start camera")
            QTimer.singleShot(0, self.close)
            return

        camera_fps = self._cap.actual_fps
        print(
            f"[webcam] Camera running at {self._cap.actual_width}x"
            f"{self._cap.actual_height}@{camera_fps:.0f}fps"
        )

        self._capture_queue: queue.Queue = queue.Queue(maxsize=2)
        self._processed_queue: queue.Queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

        self._capture_worker = _CaptureWorker(
            self._cap, self._capture_queue, self._stop_event
        )
        self._processing_worker = _ProcessingWorker(
            self._capture_queue, self._processed_queue, self._stop_event, camera_fps
        )
        self._capture_worker.start()
        self._processing_worker.start()

        # Poll at ~2x camera fps so we never block but also don't burn CPU.
        poll_ms = max(1, min(16, int(500 / max(camera_fps, 1))))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(poll_ms)

    def _tick(self) -> None:
        if self._stop_event.is_set():
            self.close()
            return
        try:
            bgr_frame = self._processed_queue.get_nowait()
        except queue.Empty:
            return
        bgr_frame = fit_image_to_size(bgr_frame, self.width(), self.height())
        self._image_label.setPixmap(_bgr_to_qpixmap(bgr_frame))

    def closeEvent(self, event) -> None:
        self._stop_event.set()
        try:
            self._timer.stop()
        except Exception:
            pass
        for worker in (self._capture_worker, self._processing_worker):
            try:
                worker.wait(2000)
            except Exception:
                pass
        try:
            self._cap.release()
        except Exception:
            pass
        global _WEBCAM_PREVIEW
        if _WEBCAM_PREVIEW is self:
            _WEBCAM_PREVIEW = None
        event.accept()


def _open_webcam_preview(camera_index: int) -> None:
    global _WEBCAM_PREVIEW
    if _WEBCAM_PREVIEW is not None:
        _WEBCAM_PREVIEW.close()
    _WEBCAM_PREVIEW = WebcamPreviewWindow(camera_index)
    _WEBCAM_PREVIEW.show()


# ─── mapper dialogs (image/video + live) ────────────────────────────────


def _make_thumb(cv2_img: np.ndarray) -> QPixmap:
    rgb = gpu_cvt_color(cv2_img, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb).resize(
        (MAPPER_PREVIEW_SIZE, MAPPER_PREVIEW_SIZE), Image.LANCZOS
    )
    return _pil_to_qpixmap(image)


class LiveMapperDialog(QDialog):
    """Source × Target mapper for live webcam mode."""

    def __init__(self, camera_index: int, mapping: list):
        super().__init__(_MAIN)
        self._camera_index = camera_index
        self._map = mapping
        self.setWindowTitle(_("Source x Target Mapper"))
        self.resize(POPUP_LIVE_WIDTH, POPUP_LIVE_HEIGHT)
        layout = QVBoxLayout(self)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        layout.addWidget(self._scroll, 1)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        for text, slot in (
            (_("Add"), self._on_add),
            (_("Clear"), self._on_clear),
            (_("Submit"), self._on_submit),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self._rebuild()

    def set_status(self, text: str) -> None:
        self._status.setText(_(text))

    def _rebuild(self) -> None:
        body = QWidget()
        grid = QGridLayout(body)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for item in self._map:
            row = item["id"]
            btn_s = QPushButton(_("Select source image"))
            btn_s.setFixedWidth(200)
            btn_s.clicked.connect(lambda _c, n=row: self._select_face(n, "source"))
            grid.addWidget(btn_s, row, 0)

            src_label = QLabel(f"S-{row}")
            src_label.setFixedSize(MAPPER_PREVIEW_SIZE, MAPPER_PREVIEW_SIZE)
            src_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            src_label.setStyleSheet("border: 1px dashed #555;")
            grid.addWidget(src_label, row, 1)
            if "source" in item:
                src_label.setPixmap(_make_thumb(item["source"]["cv2"]))
                src_label.setText("")

            x_label = QLabel("×")
            x_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(x_label, row, 2)

            btn_t = QPushButton(_("Select target image"))
            btn_t.setFixedWidth(200)
            btn_t.clicked.connect(lambda _c, n=row: self._select_face(n, "target"))
            grid.addWidget(btn_t, row, 3)

            tgt_label = QLabel(f"T-{row}")
            tgt_label.setFixedSize(MAPPER_PREVIEW_SIZE, MAPPER_PREVIEW_SIZE)
            tgt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tgt_label.setStyleSheet("border: 1px dashed #555;")
            grid.addWidget(tgt_label, row, 4)
            if "target" in item:
                tgt_label.setPixmap(_make_thumb(item["target"]["cv2"]))
                tgt_label.setText("")

        grid.setRowStretch(grid.rowCount(), 1)
        self._scroll.setWidget(body)

    def _select_face(self, row: int, kind: str) -> None:
        path, _f = QFileDialog.getOpenFileName(
            self, _("select an source image"),
            _RECENT_SOURCE_DIR or "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)",
        )
        if not path:
            return
        cv2_img = cv2.imread(path)
        face = get_one_face(cv2_img)
        if face is None:
            self.set_status("Face could not be detected in last upload!")
            return
        x_min, y_min, x_max, y_max = face["bbox"]
        self._map[row][kind] = {
            "cv2": cv2_img[int(y_min):int(y_max), int(x_min):int(x_max)],
            "face": face,
        }
        self._rebuild()

    def _on_add(self) -> None:
        add_blank_map()
        self._rebuild()
        self.set_status("Please provide mapping!")

    def _on_clear(self) -> None:
        for item in self._map:
            item.pop("source", None)
            item.pop("target", None)
        self._rebuild()
        self.set_status("All mappings cleared!")

    def _on_submit(self) -> None:
        if has_valid_map():
            simplify_maps()
            self.set_status("Mappings successfully submitted!")
            self.accept()
            _open_webcam_preview(self._camera_index)
        else:
            self.set_status("At least 1 source with target is required!")


def _open_live_mapper_dialog(camera_index: int, mapping: list) -> None:
    global _LIVE_MAPPER
    close_mapper_window()
    _LIVE_MAPPER = LiveMapperDialog(camera_index, mapping)
    _LIVE_MAPPER.show()


def close_mapper_window() -> None:
    global _LIVE_MAPPER
    if _LIVE_MAPPER is not None:
        _LIVE_MAPPER.close()
        _LIVE_MAPPER = None


# ─── entry point ─────────────────────────────────────────────────────────


class _Window:
    """Thin wrapper exposing .mainloop() for core.py compatibility."""

    def __init__(self, app: QApplication, main_window: MainWindow):
        self._app = app
        self._main = main_window

    def mainloop(self) -> None:
        self._main.show()
        self._app.exec()


def init(
    start: Callable[[], None], destroy: Callable[[], None], lang: str
) -> _Window:
    global _APP, _MAIN, _LANG, _BRIDGE

    _LANG = LanguageManager(lang)
    if QApplication.instance() is None:
        _APP = QApplication(sys.argv)
    else:
        _APP = QApplication.instance()
    _APP.setStyleSheet(QSS)

    _BRIDGE = _UIBridge()
    _MAIN = MainWindow(destroy)

    # Apply the saved theme
    apply_theme()

    return _Window(_APP, _MAIN)
