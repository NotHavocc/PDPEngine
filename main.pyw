# PDPEngine v1.0.0, created in 19.9.2026. by nothavoc

import sys
import os
import json
import shutil
import re
import random
import logging
import zipfile
import platform
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSystemTrayIcon, QMenu, QDialog, QFormLayout, 
                             QSlider, QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QListWidget, QStackedWidget, QLineEdit, QFileDialog, QMessageBox, QComboBox, QScrollArea,
                             QFrame, QGridLayout, QInputDialog, QSizePolicy, QStatusBar)
from PyQt6.QtCore import Qt, QSize, QTimer, QPoint, QUrl, QSettings, QObject, pyqtSignal
from PyQt6.QtGui import QMovie, QPixmap, QImageReader, QIcon, QColor, QCursor, QDesktopServices
from PyQt6.QtMultimedia import QSoundEffect

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).parent
    qt_plugins_path = os.path.join(BASE_DIR, 'PyQt6', 'Qt6', 'plugins')
    if os.path.exists(qt_plugins_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins_path
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugins_path, 'platforms')
else:
    BASE_DIR = Path(__file__).parent.resolve()
    EXE_DIR = BASE_DIR

PETS_DIR = Path.home() / 'Documents' / 'PDPEnginePets'
PETS_DIR.mkdir(parents=True, exist_ok=True)

PET_EXTENSION = ".pdppet"
PET_FILTER = f"PDPEngine Pet Pack (*{PET_EXTENSION})"

_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_WIN_RUN_NAME = "PDPEngine"
_MAC_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.pdpengine.autostart.plist"
_LINUX_DESKTOP = Path.home() / ".config" / "autostart" / "pdpengine.desktop"

def _autostart_command():
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).resolve())]
    exe = sys.executable
    if platform.system() == "Windows" and exe.lower().endswith("python.exe"):
        exe = exe[:-len("python.exe")] + "pythonw.exe"
    return [exe, str(Path(__file__).resolve())]

def _autostart_method_name():
    s = platform.system()
    if s == "Windows": return "Windows Registry (Run key)"
    if s == "Darwin":  return "macOS LaunchAgent"
    return "Linux XDG autostart (.desktop)"

def get_autostart():
    s = platform.system()
    try:
        if s == "Windows":
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_READ)
                try:
                    winreg.QueryValueEx(key, _WIN_RUN_NAME)
                    return True
                except FileNotFoundError:
                    return False
                finally:
                    winreg.CloseKey(key)
            except OSError:
                return False
        elif s == "Darwin":
            return _MAC_PLIST.exists()
        else:
            return _LINUX_DESKTOP.exists()
    except Exception:
        return False

def set_autostart(enabled):
    s = platform.system()
    try:
        if s == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                if enabled:
                    cmd = " ".join(f'"{p}"' for p in _autostart_command())
                    winreg.SetValueEx(key, _WIN_RUN_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try: winreg.DeleteValue(key, _WIN_RUN_NAME)
                    except FileNotFoundError: pass
            finally:
                winreg.CloseKey(key)
        elif s == "Darwin":
            if enabled:
                args = "".join(f"        <string>{a}</string>\n" for a in _autostart_command())
                plist = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0">\n<dict>\n'
                    '    <key>Label</key><string>com.pdpengine.autostart</string>\n'
                    '    <key>ProgramArguments</key>\n    <array>\n' + args + '    </array>\n'
                    '    <key>RunAtLoad</key><true/>\n'
                    '    <key>ProcessType</key><string>Interactive</string>\n'
                    '</dict>\n</plist>\n'
                )
                _MAC_PLIST.parent.mkdir(parents=True, exist_ok=True)
                _MAC_PLIST.write_text(plist, encoding='utf-8')
            else:
                _MAC_PLIST.unlink(missing_ok=True)
        else:
            if enabled:
                cmd = " ".join(f'"{p}"' for p in _autostart_command())
                content = ("[Desktop Entry]\nType=Application\nName=PDPEngine\n"
                           f"Exec={cmd}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n")
                _LINUX_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
                _LINUX_DESKTOP.write_text(content, encoding='utf-8')
            else:
                _LINUX_DESKTOP.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, str(e)

def export_pet_pack(pet_name, dest_path):
    pet_dir = PETS_DIR / pet_name
    if not pet_dir.exists():
        raise FileNotFoundError(f"Pet folder not found: {pet_dir}")
    with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(pet_dir.rglob('*')):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(pet_dir).as_posix())

def import_pet_pack(pack_path):
    try:
        with zipfile.ZipFile(pack_path, 'r') as zf:
            names = zf.namelist()
            
            prefix = ''
            if 'config.json' not in names:
                nested = [n for n in names if n.endswith('/config.json') and n.count('/') == 1]
                if not nested:
                    return False, "Invalid pet pack: no config.json found inside.", None
                prefix = nested[0][: -len('config.json')]
            
            config = json.loads(zf.read(prefix + 'config.json').decode('utf-8'))
            
            raw_name = str(config.get('name', '')).strip()
            base = re.sub(r'[^a-zA-Z0-9_]', '_', raw_name.lower())
            if not base:
                base = re.sub(r'[^a-zA-Z0-9_]', '_', Path(pack_path).stem.lower())
            if not base:
                base = 'imported_pet'
            folder_name = base
            counter = 2
            while (PETS_DIR / folder_name).exists():
                folder_name = f"{base}_{counter}"
                counter += 1
            
            dest_dir = PETS_DIR / folder_name
            
            for member in names:
                if member.endswith('/'):
                    continue
                rel = member[len(prefix):] if (prefix and member.startswith(prefix)) else member
                if not rel:
                    continue
                if '..' in Path(rel).parts or Path(rel).is_absolute():
                    continue
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, 'wb') as out:
                    out.write(src.read())
            
            return True, f"Imported as '{folder_name}'", folder_name
    except zipfile.BadZipFile:
        return False, "That file is not a valid pet pack (corrupted or wrong format).", None
    except Exception as e:
        return False, f"Import failed: {e}", None

class PetLoader:
    def __init__(self, pet_name="default_pink"):
        self.pet_name = pet_name
        self.pet_dir = PETS_DIR / pet_name
        self.config_path = self.pet_dir / 'config.json'
        
        self.name = "Unknown Pet"
        self.author = "Unknown"
        self.default_scale = 1.0
        self.scaling_type = "nearest"
        self.sprites = {}
        self.audio = {}
        self.overlay = {}
        self.features = {}
        self.random_actions = []
        
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            logging.error(f"Config not found for pet: {self.pet_name}")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.name = config.get("name", self.pet_name)
            self.author = config.get("author", "Unknown")
            self.default_scale = config.get("default_scale", 1.0)
            self.scaling_type = config.get("scaling_type", "nearest")
            self.features = config.get("features", {})
            self.random_actions = config.get("random_actions", [])
            
            sprite_dir = self.pet_dir / 'sprites'
            for state, filename in config.get("sprites", {}).items():
                filepath = sprite_dir / filename
                if filepath.exists():
                    self.sprites[state] = str(filepath)
                    
            audio_dir = self.pet_dir / 'audio'
            for sound, filename in config.get("audio", {}).items():
                filepath = audio_dir / filename
                if filepath.exists():
                    self.audio[sound] = str(filepath)
                    
            for effect, filename in config.get("overlay", {}).items():
                filepath = sprite_dir / filename
                if filepath.exists():
                    self.overlay[effect] = str(filepath)
                    
        except Exception as e:
            logging.error(f"Failed to load pet config: {e}")

    def get_sprite(self, state, fallback="idle"):
        return self.sprites.get(state, self.sprites.get(fallback, ""))

    def get_audio(self, sound):
        return self.audio.get(sound, "")

class AppManager(QObject):
    active_window_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.windows = []
        self.active_window = None
        self.settings = QSettings("PDP", "DesktopPet")
        self.setup_tray()
        
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon()
        icon_path = str(BASE_DIR / 'assets' / 'icon.png')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(100, 149, 237))
            self.tray_icon.setIcon(QIcon(pixmap))
            
        self.tray_menu = QMenu()
        self.tray_menu.addAction("Create New Pet...").triggered.connect(self.open_pet_maker)
        self.tray_menu.addAction("Spawn Pet...").triggered.connect(self.spawn_pet_dialog)
        self.tray_menu.addAction("Export Active Pet...").triggered.connect(self.export_active_pet)
        self.tray_menu.addAction("Import Pet Pack...").triggered.connect(self.import_pet_pack_dialog)
        self.tray_menu.addSeparator()
        
        self.active_pets_menu = self.tray_menu.addMenu("Active Pets")
        
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("Settings").triggered.connect(self.open_settings)
        self.tray_menu.addAction("Quit All").triggered.connect(self.quit_all)
        
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.Context):
            self.update_active_pets_menu()
            self.tray_menu.popup(QCursor.pos())

    def update_active_pets_menu(self):
        self.active_pets_menu.clear()
        if not self.windows:
            self.active_pets_menu.addAction("No pets spawned").setEnabled(False)
            return
        
        for i, win in enumerate(self.windows):
            pet_name = win.pet_loader.name if win.pet_loader else "Unknown"
            action = self.active_pets_menu.addAction(f"{pet_name} (#{i+1})")
            action.triggered.connect(lambda checked, w=win: self.focus_pet(w))
            
        self.active_pets_menu.addSeparator()
        close_all = self.active_pets_menu.addAction("Close All Pets")
        close_all.triggered.connect(self.close_all_pets)

    def focus_pet(self, window):
        window.show()
        window.raise_()
        window.activateWindow()
        self.active_window = window
        self.active_window_changed.emit(window)

    def close_all_pets(self):
        for win in self.windows[:]:
            win.close()

    def spawn_pet_dialog(self):
        pets_folder = PETS_DIR
        available_pets = [d.name for d in pets_folder.iterdir() if d.is_dir()] if pets_folder.exists() else []
        if not available_pets:
            QMessageBox.warning(None, "No Pets", "Please create a pet first!")
            return
            
        pet_name, ok = QInputDialog.getItem(None, "Spawn Pet", "Choose a pet to spawn:", available_pets, 0, False)
        if ok and pet_name:
            self.spawn_pet(pet_name)

    def spawn_pet(self, pet_name):
        slot = len(self.windows)
        win = FloatingMediaWindow(pet_name, self, slot)
        self.windows.append(win)
        self.active_window = win
        self.settings.setValue("last_used_pet", pet_name)
        self.save_session()
        win.show()
        self.active_window_changed.emit(win)

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)
        if window == self.active_window:
            self.active_window = self.windows[-1] if self.windows else None
        self.save_session()
        if not self.windows:
            if self.settings.value("quit_when_empty", True, type=bool):
                QApplication.quit()

    def save_session(self):
        names = [w.pet_name for w in self.windows]
        self.settings.setValue("session_pets", ",".join(names))
        self.settings.sync()

    def open_pet_maker(self):
        dialog = PetMakerDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_pet = getattr(dialog, 'new_pet_name', None)
            if new_pet:
                self.spawn_pet(new_pet)

    def open_settings(self):
        dialog = SettingsDialog(self.active_window, manager=self)
        dialog.exec()

    def export_active_pet(self):
        if not self.active_window or not self.active_window.pet_loader:
            QMessageBox.warning(None, "Export", "No active pet to export.")
            return
        pet_name = self.active_window.pet_loader.pet_name
        path, _ = QFileDialog.getSaveFileName(None, "Export Pet", f"{pet_name}{PET_EXTENSION}", PET_FILTER)
        if not path:
            return
        if not path.lower().endswith(PET_EXTENSION):
            path += PET_EXTENSION
        try:
            export_pet_pack(pet_name, path)
            QMessageBox.information(None, "Export Complete", f"Pet exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(None, "Export Failed", str(e))

    def import_pet_pack_dialog(self):
        path, _ = QFileDialog.getOpenFileName(None, "Import Pet Pack", "", PET_FILTER + ";;All Files (*)")
        if not path:
            return
        ok, msg, folder = import_pet_pack(path)
        if ok:
            QMessageBox.information(None, "Import Complete", f"{msg}\nUse 'Spawn Pet...' to bring it out!")
        else:
            QMessageBox.critical(None, "Import Failed", msg)

    def quit_all(self):
        self.close_all_pets()

class FloatingMediaWindow(QWidget):
    def __init__(self, pet_name, app_manager, slot=0):
        super().__init__()
        self.app_manager = app_manager
        self.pet_name = pet_name
        self.uid = f"{pet_name}_{slot}"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        
        self.raise_()
        self.activateWindow()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.label = QLabel(self)
        self.label.setStyleSheet("background: transparent;")
        self.label.setScaledContents(False)
        self.label.setMouseTracking(True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)

        self.overlay_label = QLabel(self)
        self.overlay_label.setStyleSheet("background: transparent;")
        self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.overlay_label.hide()
        self.overlay_movie = None
        self.last_overlay_frame = -1

        self.movie = None
        self.original_size = QSize()
        self.current_native_size = QSize()
        self.size_locked = False
        self.pixel_scale = 1.0
        self.target_w = 0
        self.target_h = 0
        
        self.particle_pixmap = None
        self.particles = []
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self.update_particles)
        self.particle_timer.setInterval(50)

        self.state = 'idle'      
        self.idle_pos = self.pos() 
        self.direction = 'down'
        self.target_pos = self.pos()
        self.wandering = False
        self.is_dragging = False
        self.drag_enabled = True
        self.walk_speed = 2

        self.setMouseTracking(True)
        self.mouse_history = []
        self.is_being_petted = False
        self.petting_cooldown_active = False
        self.base_pos = self.pos()
        self.shake_offset = 0
        
        self.petting_timeout = QTimer(self)
        self.petting_timeout.setSingleShot(True)
        self.petting_timeout.timeout.connect(self.finish_petting)

        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self.check_mouse_hover)
        self.hover_timer.start(50)

        self.sounds = {}

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.decide_next_state)
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.step_toward_target)
        self.pet_loader = None 

        self.settings = QSettings("PDP", "DesktopPet")
        self.wandering_enabled = True
        self.sound_enabled = True

        self.pet_loader = PetLoader(pet_name=pet_name)
        self.pixel_scale = self.pet_loader.default_scale
        
        self.load_settings()
        self.load_pet_assets()

        self.set_media(self.pet_loader.get_sprite('idle'))
        self.apply_scale()
        self.state_timer.start(random.randint(3000, 8000))

    def load_pet_assets(self):
        particle_path = self.pet_loader.overlay.get('pet_effect', "")
        if particle_path and os.path.exists(particle_path):
            self.particle_pixmap = QPixmap(particle_path).scaled(
                18, 18, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.FastTransformation
            )
        else:
            self.particle_pixmap = None

        for key in self.pet_loader.audio.keys():
            path = self.pet_loader.get_audio(key)
            if path:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(path))
                vol = self.settings.value("volume", 50, type=int)
                effect.setVolume((vol / 100.0) if self.sound_enabled else 0.0)
                self.sounds[key] = effect

    def set_media(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return

        if self.movie:
            self.movie.stop()
            try: self.movie.frameChanged.disconnect(self._update_gif_frame)
            except TypeError: pass
            self.movie = None
        self.current_pixmap = None

        if file_path.lower().endswith('.gif'):
            reader = QImageReader(file_path)
            size = reader.size()
            if not size.isEmpty():
                self.current_native_size = size
                if not self.size_locked:
                    self.original_size = size
                    self.size_locked = True

            self.movie = QMovie(file_path)
            if not self.movie.isValid(): return
            self.movie.frameChanged.connect(self._update_gif_frame)
            self.movie.start()
            self._update_gif_frame()
        else:
            pixmap = QPixmap(file_path)
            if pixmap.isNull(): return
            if not pixmap.size().isEmpty():
                self.current_native_size = pixmap.size()
                if not self.size_locked:
                    self.original_size = pixmap.size()
                    self.size_locked = True
            self.current_pixmap = pixmap
            self._apply_static_pixmap()

        self.apply_scale()

    def _update_gif_frame(self):
        if not self.movie: return
        pixmap = self.movie.currentPixmap()
        transform = Qt.TransformationMode.FastTransformation if self.pet_loader.scaling_type == "nearest" else Qt.TransformationMode.SmoothTransformation
        scaled = pixmap.scaled(self.target_w, self.target_h, Qt.AspectRatioMode.KeepAspectRatio, transform)
        self.label.setPixmap(scaled)

    def _apply_static_pixmap(self):
        if self.current_pixmap:
            transform = Qt.TransformationMode.FastTransformation if self.pet_loader.scaling_type == "nearest" else Qt.TransformationMode.SmoothTransformation
            scaled = self.current_pixmap.scaled(self.target_w, self.target_h, Qt.AspectRatioMode.KeepAspectRatio, transform)
            self.label.setPixmap(scaled)

    def apply_scale(self):
        if self.original_size.isEmpty() or self.current_native_size.isEmpty(): return
        fixed_height = self.original_size.height() * self.pixel_scale
        aspect_ratio = self.current_native_size.width() / self.current_native_size.height()
        new_width = aspect_ratio * fixed_height
        self.target_w = max(10, int(round(new_width)))
        self.target_h = max(10, int(round(fixed_height)))
        self.resize(self.target_w, self.target_h)
        if self.movie: self._update_gif_frame()
        else: self._apply_static_pixmap()
    
    def play_sound(self, sound_key):
        if not self.sound_enabled: return
        if sound_key in self.sounds:
            if not self.sounds[sound_key].isPlaying():
                self.sounds[sound_key].play()
        
    def load_settings(self):
        p = self.pet_name
        self.pixel_scale = self.settings.value(f"pixel_scale_{p}", self.pet_loader.default_scale, type=float)
        self.wandering_enabled = self.settings.value(f"wandering_{p}", True, type=bool)
        self.sound_enabled = self.settings.value(f"sound_{p}", True, type=bool)
        self.walk_speed = self.settings.value(f"walk_speed_{p}", 2, type=int)
        self.drag_enabled = self.settings.value(f"drag_{p}", True, type=bool)
        
        vol = self.settings.value("volume", 50, type=int)
        vol_float = (vol / 100.0) if self.sound_enabled else 0.0
        for effect in self.sounds.values():
            effect.setVolume(vol_float)
        
        x = self.settings.value(f"window_x_{self.uid}", 100, type=int)
        y = self.settings.value(f"window_y_{self.uid}", 100, type=int)
        point = QPoint(x, y)
        if QApplication.screenAt(point) is None:
            geo = QApplication.primaryScreen().availableGeometry()
            cascade = (int(self.uid.rsplit('_', 1)[-1] or 0) * 40) % 240
            point = QPoint(geo.x() + 80 + cascade, geo.y() + 80 + cascade)
        self.move(point)

    def save_settings(self):
        p = self.pet_name
        self.settings.setValue(f"pixel_scale_{p}", self.pixel_scale)
        self.settings.setValue(f"wandering_{p}", self.wandering_enabled)
        self.settings.setValue(f"sound_{p}", self.sound_enabled)
        self.settings.setValue(f"walk_speed_{p}", self.walk_speed)
        self.settings.setValue(f"drag_{p}", self.drag_enabled)
        
        vol = int(list(self.sounds.values())[0].volume() * 100) if self.sounds else 50
        self.settings.setValue("volume", vol if vol > 0 else 50)
        
        if QApplication.screenAt(self.pos()) is not None:
            self.settings.setValue(f"window_x_{self.uid}", self.pos().x())
            self.settings.setValue(f"window_y_{self.uid}", self.pos().y())
        self.settings.sync()

    def closeEvent(self, event):
        self.save_settings()
        self.app_manager.remove_window(self)
        event.accept()

    def mousePressEvent(self, event):
        self.app_manager.active_window = self
        self.app_manager.active_window_changed.emit(self)
        
        if not self.drag_enabled: return
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.state_timer.stop()
            if 'grab' in self.pet_loader.audio:
                self.play_sound('grab')
            else:
                grab_sound = random.choice(['gasp', 'trip'])
                self.play_sound(grab_sound)
            self.set_media(self.pet_loader.get_sprite('grab', 'idle'))
            self.move_timer.stop()
            self.wandering = False
            self.state = 'idle'
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if not self.drag_enabled or not self.is_dragging: return
        move = event.globalPosition().toPoint() - self.drag_pos
        self.move(self.pos() + move)
        self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if not self.drag_enabled or not self.is_dragging: return
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False      
            self.base_pos = self.pos()
            self.go_idle(skip_special=True)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def check_mouse_hover(self):
        if not hasattr(self, 'pet_loader') or self.pet_loader is None: 
            return
        if self.is_dragging: return 
        if self.petting_cooldown_active: return
        if self.state == 'walking': return
        if not self.pet_loader.features.get("petting_enabled", True): return

        global_pos = QCursor.pos()
        if self.geometry().contains(global_pos):
            local_y = global_pos.y() - self.pos().y()
            local_x = global_pos.x() - self.pos().x()

            if local_y < self.height() * 0.25:
                self.mouse_history.append(local_x)
                
                if len(self.mouse_history) >= 2:
                    dx = local_x - self.mouse_history[-2]
                    self.shake_offset += int(dx * 0.15) 
                    self.shake_offset = max(-5, min(5, self.shake_offset)) 
                    self.move(self.base_pos.x() + self.shake_offset, self.base_pos.y())

                if len(self.mouse_history) > 20:
                    self.mouse_history.pop(0)

                total_movement = sum(abs(self.mouse_history[i] - self.mouse_history[i-1]) for i in range(1, len(self.mouse_history)))

                if total_movement > 120:
                    self.trigger_petting()
                    self.mouse_history.clear()
            else:
                if self.shake_offset != 0:
                    self.shake_offset = int(self.shake_offset * 0.5)
                    if abs(self.shake_offset) < 1: self.shake_offset = 0
                    self.move(self.base_pos.x() + self.shake_offset, self.base_pos.y())
                self.mouse_history.clear()
        else:
            if self.shake_offset != 0:
                self.shake_offset = int(self.shake_offset * 0.5)
                if abs(self.shake_offset) < 1: self.shake_offset = 0
                self.move(self.base_pos.x() + self.shake_offset, self.base_pos.y())
            self.mouse_history.clear()

    def trigger_petting(self):
        if not self.is_being_petted:
            self.is_being_petted = True
            self.set_media(self.pet_loader.get_sprite('pet', 'idle'))
            if 'pet' in self.pet_loader.audio:
                self.play_sound('pet')
            else:
                self.play_sound('laugh')
            if self.pet_loader.features.get("particles_enabled", True) and self.particle_pixmap:
                self.particle_timer.start()
        self.petting_timeout.start(2000)

    def finish_petting(self):
        self.is_being_petted = False
        self.petting_cooldown_active = True
        self.particle_timer.stop()
        for p in self.particles: p['widget'].deleteLater()
        self.particles.clear()
        self.base_pos = self.pos()
        self.go_idle(skip_special=True)
        QTimer.singleShot(4000, self.end_cooldown)

    def end_cooldown(self):
        self.petting_cooldown_active = False

    def spawn_particle(self):
        if not self.particle_pixmap: return
        label = QLabel(self)
        label.setPixmap(self.particle_pixmap)
        label.setStyleSheet("background: transparent;")
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        start_x = (self.width() // 2) + random.randint(-20, 20)
        start_y = (self.height() // 4) + random.randint(-10, 10)
        label.move(start_x, start_y)
        label.show()
        self.particles.append({
            'widget': label, 'x': float(start_x), 'y': float(start_y),
            'dx': random.uniform(-1.5, 1.5), 'dy': random.uniform(-4.5, -1.5),
            'life': 1.0, 'decay': random.uniform(0.02, 0.04)
        })

    def update_particles(self):
        if self.is_being_petted and random.random() < 0.5: self.spawn_particle()
        dead = []
        for p in self.particles:
            p['x'] += p['dx']; p['y'] += p['dy']; p['life'] -= p['decay']
            if p['life'] <= 0: dead.append(p)
            else: p['widget'].move(int(p['x']), int(p['y']))
        for p in dead:
            p['widget'].deleteLater()
            self.particles.remove(p)

    def play_overlay_gif(self, gif_path):
        if self.overlay_movie:
            self.overlay_movie.stop()
            try: self.overlay_movie.frameChanged.disconnect(self.update_overlay_frame)
            except TypeError: pass
        self.overlay_movie = QMovie(gif_path)
        if not self.overlay_movie.isValid(): return
        self.last_overlay_frame = -1
        self.overlay_movie.frameChanged.connect(self.update_overlay_frame)
        self.overlay_movie.start()
        self.overlay_label.show()
        self.overlay_label.raise_()

    def update_overlay_frame(self):
        if not self.overlay_movie: return
        current_frame = self.overlay_movie.currentFrameNumber()
        if current_frame < self.last_overlay_frame:
            self.overlay_movie.stop(); self.hide_overlay(); return
        self.last_overlay_frame = current_frame
        pixmap = self.overlay_movie.currentPixmap()
        scale_factor = 4.0 * self.pixel_scale
        scaled_w = int(pixmap.width() * scale_factor)
        scaled_h = int(pixmap.height() * scale_factor)
        scaled = pixmap.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        x = (self.width() - scaled_w) // 2
        y = (self.height() - scaled_h) // 2
        self.overlay_label.setGeometry(x, y, scaled_w, scaled_h)
        self.overlay_label.setPixmap(scaled)

    def hide_overlay(self):
        if self.overlay_movie:
            self.overlay_movie.stop()
            try: self.overlay_movie.frameChanged.disconnect(self.update_overlay_frame)
            except TypeError: pass
        self.last_overlay_frame = -1
        self.overlay_label.hide(); self.overlay_label.clear()

    def decide_next_state(self):
        if self.is_being_petted or self.is_dragging: return
        if not self.wandering_enabled and self.state == 'walking':
            self.move_timer.stop(); self.go_idle(skip_special=True); return
        if self.state == 'walking':
            self.state_timer.start(1000); return
        if self.wandering_enabled and random.random() < 0.6: self.start_wander()
        else: self.go_idle()

    def go_idle(self, skip_special=False):
        self.state = 'idle'
        self.wandering = False
        self.idle_pos = self.pos()
        self.move_timer.stop()
        
        if skip_special:
            self.set_media(self.pet_loader.get_sprite('idle'))
            self.state_timer.start(random.randint(3000, 8000))
            return
        
        if not hasattr(self, '_temp_sounds'):
            self._temp_sounds = []

        if random.random() < 0.3 or not self.pet_loader.random_actions:
            self.set_media(self.pet_loader.get_sprite('idle'))
        else:
            action = random.choice(self.pet_loader.random_actions)
            sprite_path = self.pet_loader.pet_dir / 'sprites' / action.get('sprite', '')
            
            if sprite_path.exists():
                self.set_media(str(sprite_path))
            else:
                self.set_media(self.pet_loader.get_sprite('idle'))
                
            audio_file = action.get('audio')
            if audio_file:
                audio_path = self.pet_loader.pet_dir / 'audio' / audio_file
                if audio_path.exists():
                    effect = QSoundEffect()
                    effect.setSource(QUrl.fromLocalFile(str(audio_path)))
                    vol = self.settings.value("volume", 50, type=int)
                    effect.setVolume((vol / 100.0) if self.sound_enabled else 0.0)
                    effect.play()
                    
                    self._temp_sounds.append(effect)
                    if len(self._temp_sounds) > 5:
                        old_effect = self._temp_sounds.pop(0)
                        old_effect.deleteLater()
        
        self.state_timer.start(random.randint(3000, 8000))

    def start_wander(self):
        screen = QApplication.primaryScreen().geometry()
        max_x = screen.width() - self.width()
        max_y = screen.height() - self.height()
        self.target_pos = QPoint(random.randint(0, max(0, max_x)), random.randint(0, max(0, max_y)))
        current = self.pos()
        dx = self.target_pos.x() - current.x()
        dy = self.target_pos.y() - current.y()
        if abs(dx) > abs(dy): 
            self.direction = 'walkright' if dx > 0 else 'walkleft'
        else: 
            self.direction = 'walkdown' if dy > 0 else 'walkup'
        self.set_media(self.pet_loader.get_sprite(self.direction, 'idle'))
        self.state = 'walking'
        self.wandering = True
        self.move_timer.start(16)
        self.state_timer.start(random.randint(4000, 9000))
    
    def step_toward_target(self):
        current = self.pos()
        dx = self.target_pos.x() - current.x()
        dy = self.target_pos.y() - current.y()
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist < 4:
            self.move(self.target_pos); self.move_timer.stop(); self.go_idle(); return
        speed = self.walk_speed
        step_x = current.x() + int(speed * dx / dist)
        step_y = current.y() + int(speed * dy / dist)
        self.move(step_x, step_y)

class SettingsDialog(QDialog):
    def __init__(self, parent=None, manager=None):
        super().__init__(parent)
        self.target = parent
        self.manager = manager or (parent.app_manager if parent and hasattr(parent, 'app_manager') else None)
        self.setWindowTitle("PDPEngine Settings")
        self.setFixedSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #ffffff; }
            QListWidget { background-color: #1e1e1e; color: #ffffff; border: none; font-size: 14px; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #3d3d3d; }
            QListWidget::item:selected { background-color: #ff8a90; color: #ffffff; font-weight: bold; }
            QListWidget::item:hover { background-color: #3d3d3d; }
            QGroupBox { background-color: #333333; color: #ffffff; border: 1px solid #555555; border-radius: 5px; margin-top: 10px; padding-top: 5px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #aaaaaa; }
            QLabel { color: #ffffff; background-color: transparent; }
            QSlider::groove:horizontal { border: 1px solid #555555; height: 4px; background: #444444; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ff8a90; border: 1px solid #005a9e; width: 12px; margin: -4px 0; border-radius: 2px; }
            QDoubleSpinBox, QComboBox { background-color: #444444; color: #ffffff; border: 1px solid #555555; padding: 4px; border-radius: 3px; }
            QCheckBox { color: #ffffff; background-color: transparent; spacing: 5px; }
            QPushButton { background-color: #ff8a90; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton#cancelBtn { background-color: #555555; }
            QPushButton#cancelBtn:hover { background-color: #666666; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(160)
        self.sidebar.addItems(["About", "My Pets", "Appearance", "Behavior", "Audio", "System"])
        self.sidebar.currentRowChanged.connect(self.change_page)
        main_layout.addWidget(self.sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 10, 20, 20)

        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelBtn")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Save and Close")
        self.save_button.clicked.connect(self.save_and_close)
        btn_layout.addWidget(self.cancel_button)
        btn_layout.addWidget(self.save_button)
        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel, 1)

        outer.addLayout(main_layout, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { background: #1e1e1e; color: #aaaaaa; border-top: 1px solid #3d3d3d; font-size: 12px; }")
        
        self.target_combo = QComboBox()
        self.target_combo.setFixedWidth(200)
        self.target_combo.setMinimumHeight(24)
        self.target_combo.setToolTip("Choose which pet to edit")
        self.target_combo.setStyleSheet("""
            QComboBox { background-color: #444444; color: #ffffff; border: 1px solid #555555; padding: 3px 6px; border-radius: 3px; font-size: 12px; }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView { background-color: #333333; color: #ffffff; selection-background-color: #ff8a90; }
        """)
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)
        self.status_bar.addPermanentWidget(self.target_combo)
        
        outer.addWidget(self.status_bar)

        self.content_stack.addWidget(self.create_about_page())
        self.content_stack.addWidget(self.create_pets_page(parent))
        self.content_stack.addWidget(self.create_appearance_page(parent))
        self.content_stack.addWidget(self.create_behavior_page(parent))
        self.content_stack.addWidget(self.create_audio_page(parent))
        self.content_stack.addWidget(self.create_system_page())
        self.sidebar.setCurrentRow(0)

        if self.manager:
            self.manager.active_window_changed.connect(self.on_active_window_changed)

        self.refresh_target_combo(select=parent)
        self.refresh_controls()
        self.update_status()

    def change_page(self, index): 
        self.content_stack.setCurrentIndex(index)

    def create_about_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel()
        icon_path = str(BASE_DIR / 'assets' / 'icon.png')
        icon_pixmap = QPixmap(icon_path)
        if not icon_pixmap.isNull():
            scaled_icon = icon_pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            icon_label.setPixmap(scaled_icon); icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("margin-bottom: 15px;"); layout.addWidget(icon_label)
        
        title = QLabel("PDPEngine")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #ff8a90; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(title)
        
        version = QLabel("Version 1.0.0"); version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: #aaaaaa;"); layout.addWidget(version)
        
        desc = QLabel("A cross-platform desktop pet engine\n Derived from PinkDesktopPet \nCreated by nothavoc, 2026.")
        desc.setWordWrap(True); desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #cccccc; margin-top: 20px; font-size: 14px;"); layout.addWidget(desc)
        
        def make_link(text, url):
            lbl = QLabel(f'<a href="{url}" style="color: #ff8a90; text-decoration: none;">{text}</a>')
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("QLabel { margin-top: 8px; font-size: 14px; background: transparent; } QLabel:hover { color: #4da6ff; text-decoration: underline; }")
            lbl.linkActivated.connect(self.open_github_link)
            return lbl

        layout.addWidget(make_link("Check for Updates on GitHub", "https://github.com/NotHavocc/PDPEngine/releases/latest"))
        layout.addWidget(make_link("Documentation", "https://github.com/NotHavocc/PDPEngine/blob/main/docs/README.md"))
        layout.addWidget(make_link("My Website", "https://nothavoc.is-a.dev"))
        
        layout.addStretch()
        return page
    
    def create_pets_page(self, parent):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("petsScroll")
        scroll.viewport().setObjectName("petsViewport")
        scroll.setStyleSheet("""
            QScrollArea#petsScroll { border: none; background: transparent; }
            QWidget#petsViewport { background: transparent; }
            QWidget#petsPageContent { background: transparent; }
        """)
        
        content = QWidget()
        content.setObjectName("petsPageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)
        
        selector_group = QGroupBox("Spawn Pets")
        selector_layout = QVBoxLayout()
        selector_layout.setSpacing(10)
        selector_layout.setContentsMargins(15, 5, 15, 15)
        
        combo_row = QHBoxLayout()
        combo_lbl = QLabel("Pet Type:")
        combo_lbl.setFixedWidth(70)
        self.pet_combo = QComboBox()
        self.pet_combo.setMinimumWidth(260)
        self.pet_combo.setMinimumHeight(32)
        self.pet_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pet_combo.setStyleSheet("""
            QComboBox { background-color: #444444; color: #ffffff; border: 1px solid #555555; padding: 6px; border-radius: 3px; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView { background-color: #333333; color: #ffffff; selection-background-color: #ff8a90; }
        """)
        pets_folder = PETS_DIR
        if pets_folder.exists():
            for d in sorted(pets_folder.iterdir()):
                if d.is_dir():
                    self.pet_combo.addItem(d.name.replace('_', ' ').title(), d.name)
        combo_row.addWidget(combo_lbl)
        combo_row.addWidget(self.pet_combo, 1)
        selector_layout.addLayout(combo_row)
        
        spawn_btn = QPushButton("Spawn Selected Pet")
        spawn_btn.setMinimumHeight(36)
        spawn_btn.clicked.connect(self.spawn_selected_pet)
        selector_layout.addWidget(spawn_btn)
        selector_group.setLayout(selector_layout)
        layout.addWidget(selector_group)
        
        share_group = QGroupBox("Share Pets")
        share_layout = QHBoxLayout()
        share_layout.setSpacing(10)
        share_layout.setContentsMargins(15, 10, 15, 12)
        
        self.export_btn = QPushButton("Export Current Pet...")
        self.export_btn.setMinimumHeight(36)
        self.export_btn.setStyleSheet("background-color: #555555;")
        self.export_btn.clicked.connect(self.export_current_pet)
        self.export_btn.setEnabled(self.target is not None)
        share_layout.addWidget(self.export_btn)
        
        import_btn = QPushButton("Import Pet Pack...")
        import_btn.setMinimumHeight(36)
        import_btn.setStyleSheet("background-color: #555555;")
        import_btn.clicked.connect(self.import_pet_pack)
        share_layout.addWidget(import_btn)
        
        share_group.setLayout(share_layout)
        layout.addWidget(share_group)
        
        maker_group = QGroupBox("Pet Management")
        maker_layout = QVBoxLayout()
        maker_layout.setSpacing(10)
        maker_layout.setContentsMargins(15, 5, 15, 15)
        
        maker_info = QLabel("Create, edit, or permanently delete pets.")
        maker_info.setWordWrap(True)
        maker_info.setStyleSheet("color: #aaaaaa;")
        maker_layout.addWidget(maker_info)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.edit_btn = QPushButton("Edit Current Pet")
        self.edit_btn.setMinimumHeight(36)
        self.edit_btn.setStyleSheet("background-color: #555555;")
        self.edit_btn.clicked.connect(self.open_edit_maker)
        self.edit_btn.setEnabled(self.target is not None)
        btn_layout.addWidget(self.edit_btn)
        
        self.maker_btn = QPushButton("Create New Pet...")
        self.maker_btn.setMinimumHeight(36)
        self.maker_btn.clicked.connect(self.open_maker)
        btn_layout.addWidget(self.maker_btn)
        maker_layout.addLayout(btn_layout)
        
        self.delete_btn = QPushButton("Delete Selected Pet...")
        self.delete_btn.setMinimumHeight(36)
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: #8b2635; color: #ffffff; }
            QPushButton:hover { background-color: #d73030; }
            QPushButton:disabled { background-color: #444444; color: #888888; }
        """)
        self.delete_btn.clicked.connect(self.delete_selected_pet)
        self.delete_btn.setEnabled(self.pet_combo.count() > 0)
        maker_layout.addWidget(self.delete_btn)
        
        maker_group.setLayout(maker_layout)
        layout.addWidget(maker_group)
        
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page
    
    def create_system_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)

        startup_group = QGroupBox("System Startup")
        startup_layout = QVBoxLayout()
        startup_layout.setContentsMargins(15, 25, 15, 12)
        startup_layout.setSpacing(10)

        self.autostart_checkbox = QCheckBox("Launch PDPEngine automatically when I log in")
        self.autostart_checkbox.setChecked(get_autostart())
        self.autostart_checkbox.stateChanged.connect(self.on_autostart_changed)
        startup_layout.addWidget(self.autostart_checkbox)

        mode_row = QHBoxLayout()
        mode_lbl = QLabel("On startup:")
        mode_lbl.setFixedWidth(80)
        self.startup_mode_combo = QComboBox()
        self.startup_mode_combo.addItem("Open the Settings window", "settings")
        self.startup_mode_combo.addItem("Spawn my last used pet", "last_pet")
        self.startup_mode_combo.addItem("Restore previous session's pets", "session")
        s = self.manager.settings if self.manager else QSettings("Pink", "DesktopPet")
        idx = self.startup_mode_combo.findData(s.value("startup_mode", "settings", type=str))
        if idx != -1:
            self.startup_mode_combo.setCurrentIndex(idx)
        self.startup_mode_combo.currentIndexChanged.connect(self.on_startup_mode_changed)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.startup_mode_combo, 1)
        startup_layout.addLayout(mode_row)

        method_lbl = QLabel(f"Autostart method on this OS: {_autostart_method_name()}")
        method_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        startup_layout.addWidget(method_lbl)
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)

        app_group = QGroupBox("Application Behavior")
        app_layout = QVBoxLayout()
        app_layout.setContentsMargins(15, 25, 15, 12)
        app_layout.setSpacing(10)

        self.quit_empty_checkbox = QCheckBox("Quit the app when all pets are closed")
        self.quit_empty_checkbox.setChecked(s.value("quit_when_empty", True, type=bool))
        self.quit_empty_checkbox.stateChanged.connect(self.on_quit_when_empty_changed)
        app_layout.addWidget(self.quit_empty_checkbox)

        hint = QLabel("If unchecked, PDPEngine keeps running in the system tray after the last pet is closed.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888; font-size: 11px;")
        app_layout.addWidget(hint)
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()
        return page

    def on_autostart_changed(self, state):
        ok, err = set_autostart(bool(state))
        if not ok:
            self.autostart_checkbox.blockSignals(True)
            self.autostart_checkbox.setChecked(get_autostart())
            self.autostart_checkbox.blockSignals(False)
            QMessageBox.warning(self, "Autostart", f"Could not change the startup entry:\n{err}")

    def on_startup_mode_changed(self, index):
        mode = self.startup_mode_combo.itemData(index)
        if mode:
            s = self.manager.settings if self.manager else QSettings("PDP", "DesktopPet")
            s.setValue("startup_mode", mode)
            s.sync()

    def on_quit_when_empty_changed(self, state):
        s = self.manager.settings if self.manager else QSettings("PDP", "DesktopPet")
        s.setValue("quit_when_empty", bool(state))
        s.sync()

    def spawn_selected_pet(self):
        pet_folder_name = self.pet_combo.currentData()
        if pet_folder_name and self.manager:
            self.manager.spawn_pet(pet_folder_name)
            self.refresh_target_combo(select=self.manager.windows[-1])
            self.update_status()

    def delete_selected_pet(self):
        pet_folder = self.pet_combo.currentData()
        if not pet_folder:
            QMessageBox.warning(self, "Delete Pet", "No pet selected.")
            return
        
        if self.manager:
            active = [w for w in self.manager.windows
                      if w.pet_loader and w.pet_loader.pet_name == pet_folder]
            if active:
                QMessageBox.warning(
                    self, "Delete Pet",
                    f"'{pet_folder}' still has {len(active)} active instance(s) on screen.\n"
                    "Close them first (tray icon > Active Pets > Close All Pets)."
                )
                return
        
        reply = QMessageBox.question(
            self, "Delete Pet",
            f"Permanently delete pet '{pet_folder}'?\n\nThis removes its sprites, audio and config forever.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        pet_dir = PETS_DIR / pet_folder
        try:
            shutil.rmtree(pet_dir)
            self.refresh_pet_combo()
            if hasattr(self, 'delete_btn'):
                self.delete_btn.setEnabled(self.pet_combo.count() > 0)
            QMessageBox.information(self, "Deleted", f"Pet '{pet_folder}' was deleted.")
        except Exception as e:
            QMessageBox.critical(self, "Delete Failed", str(e))

    def refresh_pet_combo(self, select_name=None):
        self.pet_combo.blockSignals(True)
        self.pet_combo.clear()
        pets_folder = PETS_DIR
        if pets_folder.exists():
            for d in sorted(pets_folder.iterdir()):
                if d.is_dir():
                    self.pet_combo.addItem(d.name.replace('_', ' ').title(), d.name)
        if select_name:
            idx = self.pet_combo.findData(select_name)
            if idx != -1:
                self.pet_combo.setCurrentIndex(idx)
        self.pet_combo.blockSignals(False)

    def open_maker(self):
        dialog = PetMakerDialog(self.target if self.target else self.parent())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_pet_combo(select_name=getattr(dialog, 'new_pet_name', None))
            if self.manager:
                new_pet = getattr(dialog, 'new_pet_name', None)
                if new_pet:
                    self.manager.spawn_pet(new_pet)
                    self.refresh_target_combo(select=self.manager.windows[-1])

    def open_edit_maker(self):
        t = self.target if self.target else self.parent()
        if t and hasattr(t, 'pet_loader') and t.pet_loader:
            current_pet = t.pet_loader.pet_name
            dialog = PetMakerDialog(t, edit_pet_name=current_pet)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_pet_name = getattr(dialog, 'new_pet_name', current_pet)
                self.refresh_pet_combo(select_name=new_pet_name)
                
    def update_pet_buttons(self):
        has = self.target is not None
        if hasattr(self, 'edit_btn'):
            self.edit_btn.setEnabled(has)
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(has)

    def export_current_pet(self):
        t = self.target
        if not t or not t.pet_loader:
            QMessageBox.warning(self, "Export", "No active pet to export.")
            return
        pet_name = t.pet_loader.pet_name
        path, _ = QFileDialog.getSaveFileName(self, "Export Pet", f"{pet_name}{PET_EXTENSION}", PET_FILTER)
        if not path:
            return
        if not path.lower().endswith(PET_EXTENSION):
            path += PET_EXTENSION
        try:
            export_pet_pack(pet_name, path)
            QMessageBox.information(self, "Export Complete", f"Pet exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def import_pet_pack(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Pet Pack", "", PET_FILTER + ";;All Files (*)")
        if not path:
            return
        ok, msg, folder = import_pet_pack(path)
        if ok:
            self.refresh_pet_combo(select_name=folder)
            QMessageBox.information(self, "Import Complete", f"{msg}\n!")
        else:
            QMessageBox.critical(self, "Import Failed", msg)

    def create_appearance_page(self, parent):
        page = QWidget(); layout = QVBoxLayout(page)
        group = QGroupBox("Sprite Scale"); form = QFormLayout()
        self.scale_spinbox = QDoubleSpinBox()
        self.scale_spinbox.setRange(0.1, 10.0); self.scale_spinbox.setDecimals(1); self.scale_spinbox.setSingleStep(0.5)
        self.scale_spinbox.setValue(1.0)
        if parent: self.scale_spinbox.setValue(parent.pixel_scale)
        self.scale_spinbox.valueChanged.connect(self.on_scale_changed); self.scale_spinbox.setSuffix("x")
        form.addRow("Scale:", self.scale_spinbox); group.setLayout(form); layout.addWidget(group)
        layout.addStretch(); return page

    def create_behavior_page(self, parent):
        page = QWidget(); layout = QVBoxLayout(page)
        wander_group = QGroupBox("Wandering"); wander_layout = QVBoxLayout()
        self.wander_checkbox = QCheckBox("Enable Wandering"); self.wander_checkbox.setChecked(True)
        if parent: self.wander_checkbox.setChecked(parent.wandering_enabled)
        self.wander_checkbox.stateChanged.connect(self.on_wander_changed)
        wander_layout.addWidget(self.wander_checkbox); wander_group.setLayout(wander_layout); layout.addWidget(wander_group)
        
        speed_group = QGroupBox("Movement Speed"); speed_layout = QFormLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10); self.speed_slider.setValue(2)
        if parent: self.speed_slider.setValue(parent.walk_speed)
        self.speed_label = QLabel(str(self.speed_slider.value()))
        self.speed_slider.valueChanged.connect(lambda v: self.speed_label.setText(str(v)))
        speed_layout.addRow("Speed:", self.speed_slider); speed_layout.addRow("", self.speed_label)
        speed_group.setLayout(speed_layout); layout.addWidget(speed_group)

        interaction_group = QGroupBox("Interaction"); interaction_layout = QVBoxLayout()
        self.drag_checkbox = QCheckBox("Enable Dragging"); self.drag_checkbox.setChecked(True)
        if parent: self.drag_checkbox.setChecked(parent.drag_enabled)
        self.drag_checkbox.stateChanged.connect(self.on_drag_changed)
        interaction_layout.addWidget(self.drag_checkbox); interaction_group.setLayout(interaction_layout); layout.addWidget(interaction_group)
        layout.addStretch(); return page

    def create_audio_page(self, parent):
        page = QWidget(); layout = QVBoxLayout(page)
        vol_group = QGroupBox("Volume"); vol_layout = QFormLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100); self.volume_slider.setValue(50)
        if parent and parent.sounds:
            first_sound = list(parent.sounds.values())[0]
            self.volume_slider.setValue(int(first_sound.volume() * 100))
        self.volume_label = QLabel(str(self.volume_slider.value()) + "%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(str(v) + "%"))
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        vol_layout.addRow("Volume:", self.volume_slider); vol_layout.addRow("", self.volume_label)
        vol_group.setLayout(vol_layout); layout.addWidget(vol_group)
        
        sound_group = QGroupBox("Sound Effects"); sound_layout = QVBoxLayout()
        self.sound_checkbox = QCheckBox("Enable Sound Effects"); self.sound_checkbox.setChecked(True)
        if parent: self.sound_checkbox.setChecked(parent.sound_enabled)
        self.sound_checkbox.stateChanged.connect(self.on_sound_changed)
        sound_layout.addWidget(self.sound_checkbox); sound_group.setLayout(sound_layout); layout.addWidget(sound_group)
        layout.addStretch(); return page

    def on_target_changed(self, index):
        self.target = self.target_combo.itemData(index)
        self.refresh_controls()
        self.update_status()
        self.update_pet_buttons()

    def on_active_window_changed(self, window):
        if self.isVisible():
            self.refresh_target_combo(select=window)

    def refresh_target_combo(self, select=None):
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        if self.manager:
            for i, w in enumerate(self.manager.windows):
                name = w.pet_loader.name if w.pet_loader else "Unknown"
                self.target_combo.addItem(f"{name} (#{i+1})", w)
        if self.target_combo.count() == 0:
            self.target_combo.addItem("No pets spawned", None)
        if select is not None:
            idx = self.target_combo.findData(select)
            if idx != -1:
                self.target_combo.setCurrentIndex(idx)
        self.target_combo.blockSignals(False)
        
        self.on_target_changed(self.target_combo.currentIndex())

    def update_status(self):
        t = getattr(self, 'target', None)
        if t is not None:
            try:
                name = t.pet_loader.name
            except RuntimeError:
                name = "?"
            self.status_bar.showMessage(f"Editing: {name}")
        else:
            self.status_bar.showMessage("No pet selected, spawn one from the 'My Pets' tab")

    def refresh_controls(self):
        t = getattr(self, 'target', None)
        if not t:
            return
        try:
            _ = t.pixel_scale
        except RuntimeError:
            return
        self.scale_spinbox.blockSignals(True); self.scale_spinbox.setValue(t.pixel_scale); self.scale_spinbox.blockSignals(False)
        self.wander_checkbox.blockSignals(True); self.wander_checkbox.setChecked(t.wandering_enabled); self.wander_checkbox.blockSignals(False)
        self.speed_slider.blockSignals(True); self.speed_slider.setValue(t.walk_speed); self.speed_slider.blockSignals(False)
        self.drag_checkbox.blockSignals(True); self.drag_checkbox.setChecked(t.drag_enabled); self.drag_checkbox.blockSignals(False)
        self.sound_checkbox.blockSignals(True); self.sound_checkbox.setChecked(t.sound_enabled); self.sound_checkbox.blockSignals(False)
        if t.sounds:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(int(list(t.sounds.values())[0].volume() * 100))
            self.volume_slider.blockSignals(False)

    def on_wander_changed(self, state):
        t = getattr(self, 'target', None)
        if t: t.wandering_enabled = bool(state)

    def on_drag_changed(self, state):
        t = getattr(self, 'target', None)
        if t: t.drag_enabled = bool(state)

    def on_sound_changed(self, state):
        t = getattr(self, 'target', None)
        if t:
            t.sound_enabled = bool(state)
            vol = t.settings.value("volume", 50, type=int)
            vol_float = (vol / 100.0) if t.sound_enabled else 0.0
            for effect in t.sounds.values(): effect.setVolume(vol_float)

    def on_volume_changed(self, value):
        self.volume_label.setText(str(value) + "%")
        t = getattr(self, 'target', None)
        if t and t.sound_enabled:
            vol_float = value / 100.0
            for effect in t.sounds.values(): effect.setVolume(vol_float)

    def on_scale_changed(self, value):
        t = getattr(self, 'target', None)
        if t:
            t.pixel_scale = float(value)
            t.apply_scale()
            
    def open_github_link(self, url): 
        QDesktopServices.openUrl(QUrl(url))

    def save_and_close(self):
        t = getattr(self, 'target', None)
        if t:
            t.walk_speed = self.speed_slider.value()
            t.save_settings()
        self.accept()

class PetMakerDialog(QDialog):
    CORE_FIELD_SET = "background-color: #1e1e1e; color: #4da6ff; border: 1px solid #3d3d3d; border-radius: 4px; padding: 6px 8px; font-size: 11px;"
    CORE_FIELD_IDLE = "background-color: #1e1e1e; color: #666666; border: 1px solid #3d3d3d; border-radius: 4px; padding: 6px 8px; font-size: 11px;"
    CHIP_IDLE = """
            background-color: #1e1e1e; color: #777777;
            border: 1px solid #444444; border-radius: 3px;
            padding: 4px 6px; font-size: 11px;
    """
    CHIP_SET = """
            background-color: #1e1e1e; color: #4da6ff;
            border: 1px solid #444444; border-radius: 3px;
            padding: 4px 6px; font-size: 11px;
    """
    
    def __init__(self, parent=None, edit_pet_name=None):
        super().__init__(parent)
        self.edit_mode = edit_pet_name is not None
        self.edit_pet_name = edit_pet_name
        self.new_pet_name = edit_pet_name
        
        self.setWindowTitle("PDPEngine - Edit Pet" if self.edit_mode else "PDPEngine - Pet Maker")
        self.setFixedSize(750, 550)
                        
        self.random_actions_layout = QVBoxLayout()
        self.random_actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.random_action_frames = []
        self.static_files = {}
        
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #ffffff; }
            QListWidget { background-color: #1e1e1e; color: #ffffff; border: none; font-size: 14px; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #3d3d3d; }
            QListWidget::item:selected { background-color: #ff8a90; color: #ffffff; font-weight: bold; }
            QListWidget::item:hover { background-color: #3d3d3d; }
            QGroupBox { background-color: #333333; color: #ffffff; border: 1px solid #555555; border-radius: 5px; margin-top: 10px; padding-top: 5px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #aaaaaa; }
            QLabel { color: #ffffff; background-color: transparent; }
            QLineEdit, QDoubleSpinBox, QComboBox { background-color: #444444; color: #ffffff; border: 1px solid #555555; padding: 4px; border-radius: 3px; }
            QCheckBox { color: #ffffff; background-color: transparent; spacing: 5px; }
            QPushButton { background-color: #ff8a90; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton#cancelBtn { background-color: #555555; }
            QPushButton#cancelBtn:hover { background-color: #666666; }
            QPushButton#browseBtn { background-color: #444444; padding: 4px 8px; font-size: 12px; }
            QPushButton#browseBtn:hover { background-color: #555555; }
            QPushButton#deleteBtn { background-color: #d73030; padding: 4px 8px; font-size: 12px; }
            QPushButton#deleteBtn:hover { background-color: #a02020; }
            QPushButton#addBtn { background-color: #2ea043; padding: 10px; font-size: 14px; margin-top: 10px; }
            QPushButton#addBtn:hover { background-color: #238636; }
            QFrame { background-color: #252525; border: 1px solid #444444; border-radius: 4px; padding: 5px; margin-bottom: 5px; }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.addItems(["Basic Info", "Core Animations", "Random Actions", "Features"])
        self.sidebar.currentRowChanged.connect(self.change_page)
        main_layout.addWidget(self.sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelBtn")
        self.cancel_button.clicked.connect(self.reject)
        self.create_button = QPushButton("Save Changes" if self.edit_mode else "Create Pet")
        self.create_button.clicked.connect(self.create_pet)
        btn_layout.addWidget(self.cancel_button)
        btn_layout.addWidget(self.create_button)
        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel, 1)

        self.content_stack.addWidget(self.create_info_page())
        self.content_stack.addWidget(self.create_core_page())
        self.content_stack.addWidget(self.create_random_page())
        self.content_stack.addWidget(self.create_features_page())
        self.sidebar.setCurrentRow(0)

        if self.edit_mode:
            self.load_existing_pet(edit_pet_name)

    def change_page(self, index): 
        self.content_stack.setCurrentIndex(index)

    def load_existing_pet(self, pet_name):
        pet_dir = PETS_DIR / pet_name
        config_path = pet_dir / 'config.json'
        if not config_path.exists(): return
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        self.name_input.setText(config.get("name", ""))
        self.author_input.setText(config.get("author", ""))
        self.scale_input.setValue(config.get("default_scale", 1.0))
        
        if config.get("scaling_type") == "smooth":
            self.scaling_type_combo.setCurrentIndex(1)
            
        self.petting_checkbox.setChecked(config.get("features", {}).get("petting_enabled", True))
        self.particles_checkbox.setChecked(config.get("features", {}).get("particles_enabled", True))
        
        sprite_dir = pet_dir / 'sprites'
        audio_dir = pet_dir / 'audio'
        
        core_states = ["idle", "walkleft", "walkright", "walkup", "walkdown", "grab", "pet"]
        for state in core_states:
            if state in config.get("sprites", {}):
                filename = config["sprites"][state]
                filepath = str(sprite_dir / filename)
                if os.path.exists(filepath):
                    self.static_files[state] = filepath
                    if state in getattr(self, 'core_labels', {}):
                        self.core_labels[state].setText(filename)
                        self.core_labels[state].setStyleSheet(self.CORE_FIELD_SET)
                    self._set_preview(state, filepath)
                        
        if "pet_effect" in config.get("overlay", {}):
            filename = config["overlay"]["pet_effect"]
            filepath = str(sprite_dir / filename)
            if os.path.exists(filepath):
                self.static_files["particle"] = filepath
                self.particle_lbl.setText(filename)
                self.particle_lbl.setStyleSheet("color: #4da6ff; font-size: 12px;")
                
        for action in config.get("random_actions", []):
            sprite_path = None
            audio_path = None
            
            if "sprite" in action:
                filepath = sprite_dir / action["sprite"]
                if filepath.exists():
                    sprite_path = str(filepath)
                    
            if "audio" in action:
                filepath = audio_dir / action["audio"]
                if filepath.exists():
                    audio_path = str(filepath)
            
            self.add_random_action_row(
                name=action.get("name", ""),
                sprite_path=sprite_path,
                audio_path=audio_path
            )
        
        for state in ["grab", "pet"]:
            if state in config.get("audio", {}):
                filename = config["audio"][state]
                filepath = str(audio_dir / filename)
                if os.path.exists(filepath):
                    self.static_files[f"{state}_audio"] = filepath
                    if state in getattr(self, 'core_audio_labels', {}):
                        self.core_audio_labels[state].setText(filename)
                        self.core_audio_labels[state].setStyleSheet(self.CORE_FIELD_SET)

    def create_info_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        group = QGroupBox("Pet Details"); form = QFormLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("e.g., MewMew") # the ultimate life form
        self.author_input = QLineEdit(); self.author_input.setPlaceholderText("e.g., YourName")
        self.scale_input = QDoubleSpinBox()
        self.scale_input.setRange(0.1, 10.0); self.scale_input.setSingleStep(0.1); self.scale_input.setValue(1.0)
        form.addRow("Pet Name:", self.name_input); form.addRow("Author:", self.author_input); form.addRow("Default Scale:", self.scale_input)
        group.setLayout(form); layout.addWidget(group); layout.addStretch()
        return page

    def create_core_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)
        self.core_labels = {}
        self.core_audio_labels = {}
        self.core_previews = {}

        preview_style = "background-color: #1e1e1e; border: 1px solid #3d3d3d; border-radius: 4px;"
        btn_style = """
            QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #4a4a4a; border-radius: 4px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #4a4a4a; border: 1px solid #5a5a5a; }
            QPushButton:pressed { background-color: #333333; }
        """

        def make_section(title, items):
            ROW_H = 34
            group = QGroupBox(title)
            grid = QGridLayout()
            grid.setContentsMargins(15, 25, 15, 15)
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(12)

            for row, (label_text, state, is_audio) in enumerate(items):
                lbl = QLabel(label_text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                lbl.setStyleSheet("color: #dddddd; font-weight: bold; font-size: 12px; background: transparent; border: none; padding: 2px 0px;")
                lbl.setFixedWidth(140)
                lbl.setMinimumHeight(ROW_H)

                preview = QLabel("–")
                preview.setFixedSize(ROW_H, ROW_H)
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if is_audio:
                    preview.setText("🎵")
                    preview.setStyleSheet(preview_style + " font-size: 15px; color: #888888;")
                else:
                    preview.setStyleSheet(preview_style + " color: #555555;")
                    self.core_previews[state] = preview

                file_lbl = QLabel("Not selected")
                file_lbl.setStyleSheet(self.CORE_FIELD_IDLE)
                file_lbl.setMinimumHeight(ROW_H)

                btn = QPushButton("Audio…" if is_audio else "Sprite…")
                btn.setFixedWidth(90)
                btn.setMinimumHeight(ROW_H)
                btn.setStyleSheet(btn_style)

                if is_audio:
                    self.core_audio_labels[state] = file_lbl
                    key, filt = f"{state}_audio", "Audio (*.wav)"
                else:
                    self.core_labels[state] = file_lbl
                    key, filt = state, "Images (*.png *.gif)"

                btn.clicked.connect(lambda checked, k=key, l=file_lbl, f=filt: self.browse_file(k, l, f))

                grid.addWidget(lbl, row, 0)
                grid.addWidget(preview, row, 1)
                grid.addWidget(file_lbl, row, 2)
                grid.addWidget(btn, row, 3)

            grid.setColumnStretch(2, 1)
            group.setLayout(grid)
            return group

        main_layout.addWidget(make_section("Essential Movement", [
            ("Idle (Required):", "idle", False),
            ("Walk Left:", "walkleft", False),
            ("Walk Right:", "walkright", False),
            ("Walk Up:", "walkup", False),
            ("Walk Down:", "walkdown", False),
        ]))
        main_layout.addWidget(make_section("Specific Interactions", [
            ("Grabbing Sprite:", "grab", False),
            ("Grabbing Audio:", "grab", True),
            ("Petting Sprite:", "pet", False),
            ("Petting Audio:", "pet", True),
        ]))
        main_layout.addStretch()
        return page
    
    def create_random_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        info = QLabel("Add unlimited custom animations. The pet will randomly play these while idle.\nYou can optionally attach a sound effect to play when the animation starts.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaaaaa; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.random_actions_layout = QVBoxLayout(container)
        self.random_actions_layout.setSpacing(12)
        self.random_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.random_actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.empty_state_lbl = QLabel("No custom actions yet.\nClick the button below to add one!")
        self.empty_state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_lbl.setStyleSheet("color: #666666; font-size: 14px; padding: 40px; background: #252525; border-radius: 6px; border: 1px dashed #444444;")
        self.random_actions_layout.addWidget(self.empty_state_lbl)

        add_btn = QPushButton("Add New Action")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(lambda: self.add_random_action_row())
        layout.addWidget(add_btn)
        
        return page

    def add_random_action_row(self, name="", sprite_path=None, audio_path=None):
        if not isinstance(name, str):
            name = ""
        if not isinstance(sprite_path, str):
            sprite_path = None
        if not isinstance(audio_path, str):
            audio_path = None

        if hasattr(self, 'empty_state_lbl'):
            self.empty_state_lbl.hide()

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(10)

        header_row = QHBoxLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Action Name (e.g., Dance, Sleep, Spin)")
        name_edit.setText(name)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #222222; color: #ffffff; 
                border: 1px solid #555555; border-radius: 4px; 
                padding: 8px; font-size: 13px; font-weight: bold;
            }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)
        header_row.addWidget(name_edit, 1)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Remove Action")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #444444; color: #aaaaaa; 
                border: none; border-radius: 14px; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #d73030; color: white; }
        """)
        del_btn.clicked.connect(lambda: self.remove_random_action(card))
        header_row.addWidget(del_btn)
        card_layout.addLayout(header_row)

        def make_file_row(label_text, btn_text, file_filter, state_key):
            row = QHBoxLayout()
            row.setSpacing(10)
            
            lbl_title = QLabel(label_text)
            lbl_title.setFixedWidth(50)
            lbl_title.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold; background: transparent; border: none;")
            
            file_lbl = QLabel("Not selected")
            file_lbl.setStyleSheet("""
                background-color: #222222; color: #888888; 
                border: 1px solid #444444; border-radius: 4px; 
                padding: 6px; font-size: 11px;
            """)
            
            browse_btn = QPushButton(btn_text)
            browse_btn.setFixedWidth(80)
            browse_btn.setStyleSheet("""
                QPushButton { background-color: #444444; color: #ffffff; border: none; border-radius: 4px; padding: 6px; font-size: 11px; }
                QPushButton:hover { background-color: #555555; }
            """)
            
            browse_btn.clicked.connect(lambda: self.browse_action_file(file_lbl, state_key, file_filter, card))
            
            row.addWidget(lbl_title)
            row.addWidget(file_lbl, 1)
            row.addWidget(browse_btn)
            return row, file_lbl

        sprite_row, sprite_lbl = make_file_row("Sprite:", "Browse...", "Images (*.png *.gif)", "sprite")
        card_layout.addLayout(sprite_row)

        audio_row, audio_lbl = make_file_row("Audio:", "Browse...", "Audio (*.wav)", "audio")
        card_layout.addLayout(audio_row)

        card.name_edit = name_edit
        card.sprite_lbl = sprite_lbl
        card.sprite_path = sprite_path
        card.audio_lbl = audio_lbl
        card.audio_path = audio_path

        if sprite_path:
            sprite_lbl.setText(Path(sprite_path).name)
            sprite_lbl.setStyleSheet("background-color: #222222; color: #4da6ff; border: 1px solid #444444; border-radius: 4px; padding: 6px; font-size: 11px;")
        if audio_path:
            audio_lbl.setText(Path(audio_path).name)
            audio_lbl.setStyleSheet("background-color: #222222; color: #4da6ff; border: 1px solid #444444; border-radius: 4px; padding: 6px; font-size: 11px;")

        self.random_action_frames.append(card)
        self.random_actions_layout.addWidget(card)

    def remove_random_action(self, card):
        if card in self.random_action_frames:
            self.random_action_frames.remove(card)
        
        self.random_actions_layout.removeWidget(card)
        card.deleteLater()
        
        if not self.random_action_frames and hasattr(self, 'empty_state_lbl'):
            self.empty_state_lbl.show()

    def browse_action_file(self, label_widget, state_key, file_filter, card):
        filepath, _ = QFileDialog.getOpenFileName(self, f"Select {state_key}", "", file_filter)
        if filepath:
            label_widget.setText(Path(filepath).name)
            label_widget.setStyleSheet("background-color: #222222; color: #4da6ff; border: 1px solid #444444; border-radius: 4px; padding: 6px; font-size: 11px;")
            if state_key == "sprite":
                card.sprite_path = filepath
            elif state_key == "audio":
                card.audio_path = filepath

    def create_features_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        g1 = QGroupBox("Interactions"); f1 = QVBoxLayout()
        self.petting_checkbox = QCheckBox("Enable Petting (Shake mouse over head)"); self.petting_checkbox.setChecked(True)
        f1.addWidget(self.petting_checkbox); g1.setLayout(f1); layout.addWidget(g1)

        g2 = QGroupBox("Particles"); f2 = QVBoxLayout()
        self.particles_checkbox = QCheckBox("Enable Particles while Petting"); self.particles_checkbox.setChecked(True)
        f2.addWidget(self.particles_checkbox)
        particle_row = QHBoxLayout()
        self.particle_lbl = QLabel("Not selected"); self.particle_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        particle_btn = QPushButton("Browse Particle Sprite..."); particle_btn.setObjectName("browseBtn")
        particle_btn.clicked.connect(lambda: self.browse_file("particle", self.particle_lbl, "Images (*.png)"))
        particle_row.addWidget(self.particle_lbl, 1); particle_row.addWidget(particle_btn)
        f2.addLayout(particle_row); g2.setLayout(f2); layout.addWidget(g2)

        g3 = QGroupBox("Rendering"); f3 = QFormLayout()
        self.scaling_type_combo = QComboBox()
        self.scaling_type_combo.addItems(["Nearest Neighbor (Crisp Pixel Art)", "Smooth (Bilinear)"])
        f3.addRow("Scaling Type:", self.scaling_type_combo); g3.setLayout(f3); layout.addWidget(g3)
        layout.addStretch(); return page
    
    def create_pet(self):
        pet_name_raw = self.name_input.text().strip()
        if not pet_name_raw:
            QMessageBox.warning(self, "Error", "Pet Name is required!")
            self.sidebar.setCurrentRow(0)
            return

        if "idle" not in getattr(self, 'static_files', {}):
            QMessageBox.warning(self, "Error", "An 'idle' sprite is required in Core Animations!")
            self.sidebar.setCurrentRow(1)
            return

        if self.edit_mode:
            new_folder_name = re.sub(r'[^a-zA-Z0-9_]', '_', pet_name_raw.lower())
            old_dir = PETS_DIR / self.edit_pet_name
            new_dir = PETS_DIR / new_folder_name
            
            if new_folder_name != self.edit_pet_name:
                if new_dir.exists():
                    QMessageBox.warning(self, "Error", "A pet with this new name already exists!")
                    return
                old_dir.rename(new_dir)
            
            folder_name = new_folder_name
            self.new_pet_name = new_folder_name
            pet_dir = new_dir
        else:
            folder_name = re.sub(r'[^a-zA-Z0-9_]', '_', pet_name_raw.lower())
            pet_dir = PETS_DIR / folder_name
            self.new_pet_name = folder_name
            
        sprite_dir = pet_dir / 'sprites'
        audio_dir = pet_dir / 'audio'
        
        try:
            pet_dir.mkdir(parents=True, exist_ok=True)
            sprite_dir.mkdir(exist_ok=True)
            audio_dir.mkdir(exist_ok=True)
            
            config = {
                "name": pet_name_raw, 
                "author": self.author_input.text().strip() or "Unknown", 
                "version": "1.0",
                "default_scale": self.scale_input.value(),
                "scaling_type": "nearest" if self.scaling_type_combo.currentIndex() == 0 else "smooth",
                "sprites": {}, 
                "audio": {}, 
                "overlay": {},
                "features": {
                    "petting_enabled": self.petting_checkbox.isChecked(),
                    "particles_enabled": self.particles_checkbox.isChecked()
                },
                "random_actions": []
            }

            def safe_copy(source_path, dest_path):
                source = Path(source_path).resolve()
                dest = Path(dest_path).resolve()
                if source != dest:
                    shutil.copy(source, dest)
                return Path(dest_path).name

            core_states = ["idle", "walkleft", "walkright", "walkup", "walkdown", "grab", "pet"]
            for state in core_states:
                if state in getattr(self, 'static_files', {}):
                    path = self.static_files[state]
                    ext = Path(path).suffix
                    dest_name = f"{state}{ext}"
                    safe_copy(path, sprite_dir / dest_name)
                    config["sprites"][state] = dest_name

            for state in ["grab", "pet"]:
                if f"{state}_audio" in getattr(self, 'static_files', {}):
                    path = self.static_files[f"{state}_audio"]
                    dest_name = f"{state}.wav"
                    safe_copy(path, audio_dir / dest_name)
                    config["audio"][state] = dest_name

            if "particle" in getattr(self, 'static_files', {}):
                path = self.static_files["particle"]
                ext = Path(path).suffix
                dest_name = f"particle{ext}"
                safe_copy(path, sprite_dir / dest_name)
                config["overlay"]["pet_effect"] = dest_name

            for card in self.random_action_frames:
                name = card.name_edit.text().strip()
                if not name:
                    continue
                
                action_data = {"name": name}
                
                if card.sprite_path:
                    ext = Path(card.sprite_path).suffix
                    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
                    dest_sprite = f"rand_{safe_name}_sprite{ext}"
                    safe_copy(card.sprite_path, sprite_dir / dest_sprite)
                    action_data["sprite"] = dest_sprite
                    
                    if card.audio_path:
                        dest_audio = f"rand_{safe_name}_audio.wav"
                        safe_copy(card.audio_path, audio_dir / dest_audio)
                        action_data["audio"] = dest_audio
                        
                config["random_actions"].append(action_data)

            with open(pet_dir / 'config.json', 'w', encoding='utf-8') as f: 
                json.dump(config, f, indent=2)
            
            msg = "Pet updated successfully!" if self.edit_mode else f"Pet '{pet_name_raw}' created successfully!"
            QMessageBox.information(self, "Success!", msg)
            self.accept()
        except Exception as e: 
            QMessageBox.critical(self, "Error", f"Failed to save pet:\n{str(e)}")

    def _set_preview(self, state, filepath):
        prev = getattr(self, 'core_previews', {}).get(state)
        if not prev:
            return
        if filepath and os.path.exists(filepath):
            pix = QPixmap(filepath)
            if not pix.isNull():
                prev.setPixmap(pix.scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.FastTransformation))
                prev.setText("")
                return
        prev.clear()
        prev.setText("–")

    def browse_file(self, state, label_widget, file_filter):
        filepath, _ = QFileDialog.getOpenFileName(self, f"Select {state}", "", file_filter)
        if filepath:
            if not hasattr(self, 'static_files'):
                self.static_files = {}
            self.static_files[state] = filepath
            label_widget.setText(filepath.split('/')[-1])
            label_widget.setStyleSheet(self.CORE_FIELD_SET)
            self._set_preview(state, filepath)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    OLD_PETS_DIR = EXE_DIR / 'pets'
    if OLD_PETS_DIR.exists() and OLD_PETS_DIR != PETS_DIR:
        for pet in OLD_PETS_DIR.iterdir():
            if pet.is_dir():
                dest = PETS_DIR / pet.name
                if not dest.exists():
                    try:
                        shutil.move(str(pet), str(dest))
                    except Exception:
                        pass
        try:
            OLD_PETS_DIR.rmdir()
        except OSError:
            pass

    manager = AppManager()

    pets_folder = PETS_DIR
    available = [d.name for d in pets_folder.iterdir() if d.is_dir()] if pets_folder.exists() else []
    mode = manager.settings.value("startup_mode", "settings", type=str)

    def launch():
        if not available:
            manager.open_settings()
        elif mode == "last_pet":
            last = manager.settings.value("last_used_pet", "", type=str)
            manager.spawn_pet(last if last in available else available[0])
        elif mode == "session":
            names = [n for n in manager.settings.value("session_pets", "", type=str).split(',') if n in available]
            if names:
                for n in names:
                    manager.spawn_pet(n)
            else:
                manager.open_settings()
        else:
            manager.open_settings()

    QTimer.singleShot(300, launch)
    sys.exit(app.exec())