# 🎬 Macan VLC  
### *An intelligent, cross-platform media player built on the Macan Angkasa ecosystem.*

---

## 🧩 Overview  
**Macan VLC** is a modern multimedia player developed as part of the **Macan Angkasa Software Ecosystem**, designed to deliver high-performance playback with advanced integration and a sleek user interface.  

Built using **Python** and **PySide6**, it combines the flexibility of open-source VLC technology with a refined experience layer that includes persistent settings, theming, thumbnail previews, and native streaming integration via the **Macan Engine**.

---

## 📸 Screenshot
<img width="703" height="581" alt="Screenshot 2025-11-18 073604" src="https://github.com/user-attachments/assets/4159a604-364c-4c94-91bc-e49c79cc5e8f" />
---


## ⚙️ Core Features  
✅ **Modern UI Design** — Adaptive themes (Dark, Light, Neon Blue, Dark Blue, Soft Pink) with real-time theme switching.  
✅ **Native Online Streaming** — Integrated via *macan-engine* for smooth YouTube and media streaming.  
✅ **Smart Playlist System** — Drag & drop support with persistent playlists stored via QSettings.  
✅ **Playback History** — Auto-records and stores recently played media for easy access.  
✅ **Subtitle Rendering (SRT)** — Advanced subtitle engine with QGraphicsScene rendering for clarity and anti-aliasing.  
✅ **Thumbnail Preview** — Frame-accurate previews using OpenCV and QPixmap rendering.  
✅ **Persistent User Settings** — Volume, theme, playlist, and window geometry saved automatically.  
✅ **Cross-Platform Ready** — Built to run seamlessly on Windows, Linux, and macOS.

---

## 🧠 Technical Highlights  
- **Framework:** PySide6 (Qt for Python)  
- **Core Engine:** VLC via `python-vlc`  
- **Streaming Utility:** `macan-engine.exe` for online media  
- **Thumbnail Generator:** OpenCV (`opencv-python-headless`)  
- **UI Components:** QtAwesome icons and custom QSS themes  
- **Storage System:** QSettings for persistent user data  
- **Concurrency:** QThread for background tasks (metadata & thumbnail generation)

Macan VLC’s architecture focuses on modularity and performance — ensuring a responsive, stable, and elegant playback experience.

---

## 🚀 Installation & Usage  
1. **Install dependencies:**
   ```bash
   pip install PySide6 python-vlc qtawesome opencv-python-headless

Ensure macan-engine.exe is placed in the same directory as the main script.
Run the player:
python macan_vlc.py

Drag and drop local media files, or paste a YouTube/stream URL to play instantly.

🏢 About Macan Angkasa
Macan Angkasa is an independent technology ecosystem engineered by Danx Exodus, focusing on intelligent desktop systems, AI integration, and next-generation productivity tools.
From AI suites to browsers and media frameworks, the ecosystem embodies the fusion of art, logic, and precision in modern computing.
Engineered with integrity and imagination — built to inspire creators worldwide.
— Macan Angkasa

📜 License
Macan VLC is licensed under the MIT License.
MIT License

Copyright (c) 2026 Danx Exodus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
---

Danx Exodus — Founder & Lead Developer
Macan Angkasa Ecosystem
Redefining intelligent desktop software.
