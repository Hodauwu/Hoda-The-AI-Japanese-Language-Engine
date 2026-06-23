# 🌏 Hoda: AI Language Learning Engine

Hoda is an advanced, immersive multi-language learning web application powered by cutting-edge AI models. Designed to take users from absolute beginner script mastery to fluid conversational practice, Hoda adapts dynamically to user mistakes, generating custom situational dialogues, handling localized voice conversations, and acting as an optical translation tool for real-world texts.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_svg.svg)](https://github.com/Hodauwu/Hoda-The-AI-Japanese-Language-Engine)

---

## 🚀 Key Features

Hoda breaks down language acquisition into an engineered **4-Step Laboratory System**:

### 🔤 Step 1: Alphabet Lab
* **Interactive Mastery Pathways:** Supports Hiragana & Katakana (Japanese), Devanagari (Hindi), and the Malayalam script.
* **AI Memory Stories:** Leverages `llama-3.1-8b-instant` to generate eccentric, highly unforgettable visual mnemonics tailored to character shapes.
* **Muscle Memory Tracing:** Features an interactive canvas over faded font guidelines, tracking stroke orders with animated GIFs to require at least 5 completed tracing reps before logging completion.

### 🗣️ Step 2: Situational Lab
* **Custom Prompt Scenarios:** Type in any life scenario (e.g., *"Ordering a coffee in Kyoto"* or *"Asking for train directions"*).
* **Dynamic RAG Injection:** Automatically pulls user performance history from a local SQLite engine to subtly weave past weaknesses and mistakes into new scenarios.
* **Seamless Translation Blocks:** Displays natural 2-line native script dialogues, alongside transliterations and English translations.

### 🎙️ Step 3: Conversational Voice Lab
* **Real-time Transcriptions:** Processed locally using the high-fidelity OpenAI **Whisper Turbo** model.
* **Back-and-Forth Dialogue:** Responds via structured JSON completions that synthesize contextual conversational replies, grammatical corrections, and immediate automated Text-to-Speech (`gTTS`) playbacks.

### 👁️ Step 4: Real-World Lab (Vision)
* **Multimodal Translation Engine:** Uses `llama-4-scout-17b-16e-instruct` via Groq to extract native script elements from uploaded images or live camera snaps.
* **Contextual Breakdown Reports:** Translates street signs, food menus, or item labels into clear English, isolating and explaining difficult target characters.

---

## 🛠️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit | Clean, responsive, multi-tab layout web application framework. |
| **Database** | SQLite3 | Local storage tracking account credentials, progress metrics, and aggregated mistake logs. |
| **LLM Core** | Groq API (`Llama 3.1 & 4`) | Ultra-fast text generation and multimodal vision parsing. |
| **Speech-to-Text** | Whisper (`Turbo`) | High-accuracy audio transcription handling local mic inputs. |
| **Text-to-Speech** | gTTS | Native audio stream synthesis for pronunciation scripts. |
| **Canvas Tracing** | `streamlit-drawable-canvas` | Captures brush strokes and monitors active user muscle memory attempts. |

---

## 📦 Installation & Setup

Follow these steps to deploy Hoda locally on your machine:

### 1. Clone the Repository
```bash
git clone [https://github.com/Hodauwu/Hoda-The-AI-Japanese-Language-Engine.git](https://github.com/Hodauwu/Hoda-The-AI-Japanese-Language-Engine.git)
cd Hoda-The-AI-Japanese-Language-Engine
```

### 2. Install Dependencies
Ensure you have Python 3.9+ installed, then run:
```bash
pip install -r requirements.txt
```
*(Note: If `whisper` requires it, make sure your system has `ffmpeg` installed).*

### 3. Environment Variables
Create a `.env` file in the root directory and securely include your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the Web Application
```bash
streamlit run app.py
```

---

## 🧠 Database Schema & State Management

Hoda relies on an automatic self-healing SQLite database (`hoda_memory.db`) structured as follows:
* `users`: Stores usernames, password hashes, and user-scoped target language configurations.
* `progress`: Logs which script characters have been thoroughly mastered by individual users.
* `mistakes`: Captures weak vocabulary strings and structural errors to feed the internal RAG system.

> ⚠️ **System Performance Note:** The application's core pipeline is highly optimized to run locally on dedicated consumer GPUs for audio transcription tasks alongside rapid remote API endpoints.

---

## 🤝 Contributing
Contributions, issue reports, and feature requests for additional language pathways are always welcome! Feel free to open a pull request or submit an issue in the tracker.
