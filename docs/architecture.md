# 🧠 Macan VLC — System Architecture Documentation  
*Part of the Macan Angkasa Software Ecosystem*  
*Author: Danx Exodus*

---

## 1. Overview  
**Macan VLC** is a high-performance multimedia player built using **Python**, **PySide6**, **python-vlc**, and **OpenCV**, designed as part of the **Macan Angkasa ecosystem**.  

It provides a modern user interface, native integration with VLC libraries, advanced thumbnail rendering, and persistent user experience through QSettings.  
This document explains the internal architecture, data flow, and technical components that make up the system.

---

## 2. System Architecture Diagram  


+---------------------------------------------------------------+
Macan VLC
Presentation Layer (PySide6 UI)
• MainWindow (controls layout, themes, actions)
• VideoFrame (QWidget rendering VLC output)
• PlaylistWidget / HistoryWidget
---------------------------------------------------------------
Logic & Control Layer
• PlayerController (handles playback via python-vlc)
• EventHandler (connects signals/slots)
• QThreadWorkers (for thumbnails, metadata)
---------------------------------------------------------------
Data & Persistence Layer
• QSettings (stores volume, theme, playlist)
• Playlist & History cache
---------------------------------------------------------------
Integration Layer
• macan-engine.exe (streaming bridge for YouTube/online)
• OpenCV (frame extraction for thumbnails)
+---------------------------------------------------------------+


---

## 3. Core Modules

### 3.1 MainWindow (UI Controller)
Handles all UI elements, menus, and window states.  
Responsible for:
- Initializing VLC instance and video output widget.  
- Managing theme changes dynamically (via QSS injection).  
- Binding UI events (play, pause, open file, change theme).  
- Interfacing with `PlayerController` for all playback actions.  

### 3.2 PlayerController
Abstracts the `python-vlc` API into a Qt-friendly interface.  
Manages:
- Playback control (play, pause, stop, resume, volume, seek).  
- Video/audio stream loading (from file path or URL).  
- Communication with `macan-engine.exe` for external media fetch.  
- Error handling and media metadata extraction.

### 3.3 ThumbnailWorker (QThread)
Handles **background frame extraction** using **OpenCV**.  
It reads video frames at intervals and emits ready QPixmaps to the main thread.  
This keeps the UI responsive while generating thumbnails for playlist or preview.  

### 3.4 HistoryManager
Stores and retrieves playback history (last 50 items by default) via QSettings.  
Provides:
- Quick resume of last played items.  
- Automatic deduplication (no duplicates in history).  
- Instant load at startup for seamless continuity.  

### 3.5 ThemeManager
Applies visual themes using Qt’s stylesheet system.  
Supports:
- Dark, Light, Neon Blue, Dark Blue, Soft Pink.  
- Persistent theme memory (saved via QSettings).  
- Runtime switching with fade transitions for smooth UX.

### 3.6 SubtitleRenderer
Uses `QGraphicsScene` to draw SRT subtitles dynamically.  
Benefits:
- Anti-aliased rendering for crisp text.  
- Font scaling with window size.  
- Layered drawing so subtitles never overlap playback UI.  

---

## 4. Data Flow Summary


User Input (file/url)
↓
PlayerController → VLC Core (via python-vlc)
↓
Playback + Frame Emission
↓
ThumbnailWorker → OpenCV Frame Decode → QPixmap → UI Thumbnail
↓
UI Rendering (PySide6)
↓
QSettings Save (volume, theme, history, playlist)

Every user action is funneled through `PlayerController`,  
while background processes (thumbnail extraction, metadata) run asynchronously through QThreads to prevent blocking.

---

## 5. Integration with macan-engine

`macan-engine.exe` acts as a **native streaming bridge**, allowing Macan VLC to play online content (e.g., YouTube links) without Python wrappers.  
Workflow:
1. User pastes a URL.  
2. Macan VLC calls macan-engine via subprocess.  
3. macan-engine returns a direct media stream URL.  
4. VLC instance begins playback using the returned link.  

This approach reduces overhead, eliminates dependency on external Python tools, and improves security and speed.

---

## 6. Key Technologies

| Component | Description |
|------------|-------------|
| **PySide6 (Qt for Python)** | Provides UI framework, widgets, signals, and persistent settings. |
| **python-vlc** | Accesses VLC playback engine directly from Python. |
| **OpenCV** | Handles video frame capture and thumbnail generation. |
| **QtAwesome** | Provides scalable vector icons for the modern UI. |
| **QSettings** | Stores user preferences natively across OS platforms. |
| **QThread** | Enables concurrent processing of media and thumbnails. |

---

## 7. Error Handling Strategy
Macan VLC employs a robust error-handling flow:
- Playback errors trigger UI notifications via `QMessageBox`.  
- Engine errors logged silently to `debug.log` (if enabled).  
- Missing file or stream fallback to placeholder message.  
- Subprocess calls (macan-engine) use try-except with timeout.  

---

## 8. Future Roadmap
- [ ] Integration with **Macan Media Suite** (centralized media catalog).  
- [ ] Real-time waveform visualization.  
- [ ] Global media hotkeys (Play/Pause/Next).  
- [ ] Advanced subtitle customization (color, position, outline).  
- [ ] Network streaming UI (DLNA, NAS support).  
- [ ] Portable build for Windows & Linux (PyInstaller/Nuitka).  

---

## 9. Summary
**Macan VLC** represents a balance of simplicity and depth —  
a fully featured media player built from scratch with an elegant interface, efficient multithreading, and tight system integration.  

It stands as a core part of the **Macan Angkasa ecosystem**,  
showcasing the power of independent software engineering when combined with vision and precision.

---

**© 2025 — Danx Exodus | Macan Angkasa**  
*An independent ecosystem redefining desktop intelligence.*

