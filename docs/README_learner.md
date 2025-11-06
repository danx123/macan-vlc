# 🎬 Macan VLC — Learner Edition  
### *A clean, open, and educational version of Macan VLC — built for learning and inspiration.*

---

## 🧩 Overview  
**Macan VLC (Learner Edition)** is a simplified version of the original **Macan VLC**, a modern media player developed by **Danx Exodus** as part of the **Macan Angkasa Ecosystem**.  

This version is designed for **students, hobbyists, and beginner developers** who want to understand how to build a fully functional multimedia player using Python and Qt — with simple, readable logic and JSON-based data storage.  

---

## 🧠 Key Learning Concepts
This edition focuses on **clarity over complexity**.  
You will learn how to:
- Build a responsive GUI using **PySide6 (Qt for Python)**.  
- Integrate **VLC** to play video and audio using the `python-vlc` module.  
- Handle file playback, URL streaming, and drag & drop support.  
- Save user preferences (volume, playlist, theme) using **JSON files**.  
- Understand event-driven programming (signals and slots).  
- Structure a Python project for scalability and modularity.  

---

## ⚙️ Tech Stack
| Component | Description |
|------------|-------------|
| **Python 3.9+** | Core programming language |
| **PySide6 (Qt)** | GUI framework |
| **python-vlc** | Video and audio engine |
| **json** | Lightweight data storage for user preferences |
| **QtAwesome** | Icon toolkit for modern interfaces |
| **threading** | Background tasks for thumbnail or metadata loading |

---

## 🧩 Project Structure

macan_vlc/
┣ main.py # Main entry point
┣ ui_main.py # GUI layout (PySide6 Designer)
┣ player_controller.py # VLC playback logic
┣ playlist.json # Playlist data file (auto-generated)
┣ settings.json # User settings (theme, volume, etc.)
┣ resources/ # Icons, themes, and assets
┗ readme_learners.md # This document

---

## 🚀 How to Run
1. **Install dependencies:**
   ```bash
   pip install PySide6 python-vlc qtawesome

Run the player:
python main.py

Drag and drop a video file, or use the Open File button to start playback.
Your settings (like volume and theme) will be saved automatically to settings.json.
The playlist is also stored locally in playlist.json.

🎨 Features Overview
✅ Simple & Clean UI — Lightweight PySide6 interface with modern icons.
✅ Drag & Drop Support — Instantly play media files from your desktop.
✅ JSON Persistence — User settings and playlists are human-readable.
✅ Theming System — Change color themes dynamically.
✅ Learning-Oriented Code — All functions and classes are well-organized and commented.

💡 Why JSON Instead of QSettings?
The professional version of Macan VLC uses QSettings, which stores data directly in the OS registry or system preferences.
However, in this learner edition, we use JSON files instead — because:
It’s easy to read and edit manually.
You can visually inspect what’s stored.
Perfect for learning data serialization in Python.
This helps beginners understand how data persistence works before exploring more advanced techniques like QSettings.

🧱 How It Works (Simplified Flow)
User opens media file
   ↓
PlayerController loads file via VLC
   ↓
UI updates playback controls
   ↓
Settings/playlist written to JSON file
   ↓
Next launch → loads last used theme and volume

All major actions are event-driven — meaning every button or user action triggers a signal, which is then connected to a specific function (slot).
This is the essence of Qt programming.

🏗️ Suggested Learning Path
Understand UI Layouts — Open ui_main.py and learn how PySide6 widgets work.
Explore PlayerController — Study how VLC commands are called and connected to buttons.
Check JSON Storage — See how settings.json and playlist.json are saved and loaded.
Add Your Own Feature — Try building your own button or custom theme!

📦 Upgrade Path
Once you understand this version, you can explore:
Macan VLC (Pro) — The full edition that uses QSettings, OpenCV, and native streaming via macan-engine.
Macan Media Suite — The complete suite for managing audio, video, and network playback.

🏢 About Macan Angkasa
Macan Angkasa is an independent software ecosystem founded by Danx Exodus, focusing on modern, modular, and intelligent applications built entirely with Python and Qt.
It represents the spirit of innovation, discipline, and independent development.
Learn. Build. Evolve.
— Macan Angkasa

📜 License
This project is licensed under the MIT License.
You are free to use, modify, and distribute this version for learning and educational purposes.

© 2025 Danx Exodus
Macan Angkasa — Redefining Independent Software Engineering
