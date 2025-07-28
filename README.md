

# 📐 GeoGen — Geometry AI Assistant

GeoGen is a modern, cross-platform Python app that lets you generate geometry drawings and AI-generated math solutions with beautiful LaTeX rendering. Powered by Google's Gemini 2.5 models, the app provides a clean, Apple-inspired UI with support for light and dark modes.

---

## ✨ Features

- 🧠 **AI-Powered Reasoning** with Gemini 2.5 Pro
- ✏️ **Diagram Generation** using Gemini 2.5 Flash
- 📄 **Real-Time Streaming Output** rendered in LaTeX
- 🖋️ **PDF Export** with clean formatting
- 🌗 **Automatic Light/Dark Mode Support**
- 🖥️ **Apple-like Modern UI** with rounded corners and SF Pro font
- 🪟 **Responsive Design** for Windows, macOS, and Linux

---

## 🧰 Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/geogen.git
cd geogen
```

### 2. Install required dependencies
You need Python 3.10+ installed.

```bash
pip install -r requirements.txt
```

Install LaTeX if you want PDF export:
- macOS: `brew install --cask mactex`
- Ubuntu/Debian: `sudo apt install texlive-latex-base`
- Windows: [Install MiKTeX](https://miktex.org/download)

---

## 🚀 Running the App

```bash
python geogen.py
```

---

## 🔑 Environment Variables

Create a `.env` file or set environment variables directly:

```
GOOGLE_API_KEY=your_api_key_here
```

You can obtain a key from Google AI Studio.

---

## ❗ Disclaimer

> This tool uses AI to assist with geometry problem solving. Always double-check the results — errors can occur!

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
