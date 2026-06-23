import streamlit as st
import os
import re
import whisper
import requests
import sqlite3
from groq import Groq
from dotenv import load_dotenv
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas
import io
import base64
import json

from language_data import (
    LANGUAGES,
    LANGUAGE_OPTIONS,
    LANGUAGE_PATHWAYS,
    STATIC_ALPHABET,
    HIRAGANA_CHARS,
    KATAKANA_CHARS,
    get_lang_config,
    get_pathway_labels,
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

st.set_page_config(
    page_title="Hoda | AI Language Engine",
    layout="wide",
    page_icon="🌏",
)


@st.cache_data(ttl=3600)
def fetch_jisho_n2_data():
    """Fetches live N2 vocabulary directly from the Jisho.org API."""
    url = "https://jisho.org/api/v1/search/words?keyword=%23jlpt-n2"

    try:
        response = requests.get(url)
        data = response.json()
        kanji_dict = {}

        for item in data.get("data", []):
            jp_data = item["japanese"][0]
            word = jp_data.get("word", jp_data.get("reading", ""))
            reading = jp_data.get("reading", "")
            english = item["senses"][0]["english_definitions"][0]
            label = f"{english} ({reading})"
            kanji_dict[label] = {"char": word, "gif": ""}

        return kanji_dict

    except Exception as e:
        st.error(f"Failed to connect to Jisho API: {e}")
        return {}


def build_japanese_pathway_database(pathway_key):
    if pathway_key == "hiragana":
        char_map = HIRAGANA_CHARS
        prefix = "Hiragana"
    elif pathway_key == "katakana":
        char_map = KATAKANA_CHARS
        prefix = "Katakana"
    else:
        return fetch_jisho_n2_data()

    database = {}
    for label, char in char_map.items():
        database[label] = {
            "char": char,
            "gif": f"https://commons.wikimedia.org/wiki/Special:FilePath/{prefix}_{char}_stroke_order_animation.gif",
        }
    return database


def get_alphabet_database(language, pathway_key):
    if language == "japanese":
        return build_japanese_pathway_database(pathway_key)

    static = STATIC_ALPHABET.get(language, {}).get(pathway_key)
    return static or {}


def pathway_key_from_label(language, pathway_label):
    for label, key in LANGUAGE_PATHWAYS.get(language, []):
        if label == pathway_label:
            return key
    return LANGUAGE_PATHWAYS[language][0][1]


# 1. INITIALIZATION & API SETUP (load_dotenv + client moved above set_page_config)


def init_db():
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            error_type TEXT,
            language TEXT DEFAULT 'japanese',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            learning_language TEXT DEFAULT 'japanese'
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS progress (
            username TEXT,
            char TEXT,
            language TEXT DEFAULT 'japanese',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, char, language)
        )"""
    )
    conn.commit()

    for column_sql in (
        "ALTER TABLE users ADD COLUMN learning_language TEXT DEFAULT 'japanese'",
        "ALTER TABLE mistakes ADD COLUMN language TEXT DEFAULT 'japanese'",
        "ALTER TABLE progress ADD COLUMN language TEXT DEFAULT 'japanese'",
    ):
        try:
            c.execute(column_sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()


init_db()


def log_mistake(word, error_type, language="japanese"):
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO mistakes (word, error_type, language) VALUES (?, ?, ?)",
        (word, error_type, language),
    )
    conn.commit()
    conn.close()


def get_recent_mistakes(language="japanese"):
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        """SELECT word FROM mistakes
           WHERE language = ?
           GROUP BY word
           ORDER BY MAX(timestamp) DESC
           LIMIT 3""",
        (language,),
    )
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]


def log_progress(username, char, language="japanese"):
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO progress (username, char, language) VALUES (?, ?, ?)",
        (username, char, language),
    )
    conn.commit()
    conn.close()


def get_learned_letters(username, language="japanese"):
    if not username:
        return []
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        "SELECT char FROM progress WHERE username = ? AND language = ?",
        (username, language),
    )
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]


def get_user_language(username):
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute("SELECT learning_language FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0] in LANGUAGES:
        return row[0]
    return "japanese"


def set_user_language(username, language):
    if language not in LANGUAGES:
        return
    conn = sqlite3.connect("hoda_memory.db")
    c = conn.cursor()
    c.execute(
        "UPDATE users SET learning_language = ? WHERE username = ?",
        (language, username),
    )
    conn.commit()
    conn.close()


def is_kanji(char):
    return "\u4e00" <= char <= "\u9faf"


def get_kanji_gif(char):
    if is_kanji(char):
        hex_code = hex(ord(char))[2:]
        return f"https://raw.githubusercontent.com/mistval/kanji_images/master/gifs/{hex_code}.gif"
    return None


@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")


whisper_model = load_whisper_model()


def text_to_speech_bytes(text, language_code):
    lang_cfg = get_lang_config(language_code)
    tts = gTTS(text=text, lang=lang_cfg["tts_lang"])
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()


def clean_native_text(text):
    clean = re.sub(r"\(.*?\)", "", text)
    clean = re.sub(r"[a-zA-Z]", "", clean)
    return clean.strip()


def get_hoda_response(user_text, language="japanese", context="general", chat_history=None):
    lang_cfg = get_lang_config(language)
    lang_name = lang_cfg["name"]
    native_name = lang_cfg["native_name"]
    translit_label = lang_cfg["translit_label"]

    if context == "alphabet":
        sys_prompt = f"""You are a highly creative, slightly eccentric {lang_name} teacher. The user will provide a {lang_name} character and its pronunciation.
        Create a wildly unique, modern, and highly visual mnemonic trick.

        CRITICAL RULES:
        1. DO NOT use boring, repetitive tropes. Be weird, modern, and specific.
        2. The visual must clearly connect to the physical shape of the character.
        3. The story must clearly connect the visual to the phonetic sound.

        You MUST use this exact format:
        **Looks like:** [A very specific, unique object the shape resembles]
        **Memory Trick:** [A 1-sentence weird/funny story connecting the object to the sound]

        Do NOT write paragraphs. Keep it simple but highly memorable."""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.8,
        )
        return completion.choices[0].message.content

    if context == "pronunciation_feedback":
        sys_prompt = f"""You are Hoda, a {lang_name} tutor. The user is a COMPLETE BEGINNER practicing pronunciation.

        IMPORTANT RULES:
        1. If the transcribed text looks like random gibberish, say you couldn't catch it clearly.
        2. ALL explanations MUST be in ENGLISH.
        3. Focus ONLY on the exact sound or word they are practicing.
        4. Keep feedback to 2 sentences max. Be extremely encouraging."""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )
        return completion.choices[0].message.content

    if context == "conversational_voice":
        history_script = ""
        if chat_history:
            for chat in chat_history[-3:]:
                reply = chat.get("hoda_native") or chat.get("hoda_jp", "")
                history_script += f"User said: {chat['user']}\nYou replied: {reply}\n---\n"

        sys_prompt = f"""You are Hoda, a friendly and enthusiastic {lang_name} language partner.

        Recent Conversation History:
        {history_script}

        IMPORTANT RULES:
        1. ACT LIKE A REAL PERSON. Respond naturally to keep the conversation flowing.
        2. DO NOT just parrot back what the user said. Have an actual back-and-forth dialogue.
        3. Keep your {lang_name} response conversational, natural, and short (1-2 sentences) in {native_name} script.
        4. Put grammar corrections ONLY in the "english" JSON field.
        5. You MUST output your response as a valid JSON object using this exact structure:
        {{
          "user_translation": "Translate exactly what the user just said into English",
          "native": "Your conversational reply in pure {native_name} script only",
          "transliteration": "{translit_label} of your reply",
          "english": "English translation of your reply, plus any brief grammar corrections here."
        }}"""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content

    recent_mistakes = get_recent_mistakes(language)
    rag_injection = ""
    if recent_mistakes:
        weaknesses = ", ".join(recent_mistakes)
        rag_injection = (
            f"MEMORY RULE: The user recently struggled with: {weaknesses}. "
            "Try to naturally include one of these, but DO NOT ruin the main scenario to do it."
        )

    sys_prompt = f"""You are Hoda, a {lang_name} tutor.
        SCENARIO: {user_text}
        {rag_injection}

        Write a natural, 2-line dialogue. You MUST output ONLY a valid JSON object using this exact structure:
        {{
          "dialogue": [
            {{
              "speaker": "Person A",
              "native": "Only pure {native_name} script, no brackets or English",
              "transliteration": "{translit_label} here",
              "english": "english translation"
            }},
            {{
              "speaker": "Person B",
              "native": "Only pure {native_name} script",
              "transliteration": "{translit_label} here",
              "english": "english translation"
            }}
          ]
        }}"""

    completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Scenario: {user_text}"},
        ],
        model="llama-3.1-8b-instant",
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return completion.choices[0].message.content


def analyze_language_image(image_bytes, language="japanese"):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    lang_cfg = get_lang_config(language)
    lang_name = lang_cfg["name"]
    script_label = lang_cfg["vision_script_label"]

    sys_prompt = f"""You are Hoda, a {lang_name} tutor. The user has uploaded an image (like a menu, sign, or label).
    1. Extract the {lang_name} text.
    2. Provide the {lang_cfg['translit_label']}.
    3. Translate it to English.
    4. Highlight 1 or 2 difficult {script_label} characters or words and explain their meaning briefly.
    Keep it structured and easy to read."""

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": sys_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        temperature=0.3,
    )
    return completion.choices[0].message.content


def create_tracing_background(text, font_file, width=600, height=250):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    max_h = int(height * 0.8)
    max_w = int((width * 0.9) / max(len(text), 1))
    font_size = min(max_h, max_w)

    try:
        font = ImageFont.truetype(font_file, font_size)
    except IOError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) / 2
    y = (height - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=(150, 150, 150, 100), font=font)
    return img


def parse_dialogue_line(line, translit_label):
    native = line.get("native") or line.get("japanese", "")
    translit = line.get("transliteration") or line.get("romaji", "")
    english = line.get("english", "")
    speaker = line.get("speaker", "Speaker")
    display = f"**👤 {speaker}:**\n{native}\n*{translit}*\n{english}\n\n---\n"
    return display, clean_native_text(native)


def parse_voice_response(chat_data):
    return {
        "user_translation": chat_data.get("user_translation", ""),
        "native": chat_data.get("native") or chat_data.get("japanese", ""),
        "transliteration": chat_data.get("transliteration") or chat_data.get("romaji", ""),
        "english": chat_data.get("english", ""),
    }


# --- SESSION STATE DEFAULTS ---
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "learning_language" not in st.session_state:
    st.session_state.learning_language = "japanese"

current_lang = st.session_state.learning_language
lang_cfg = get_lang_config(current_lang)

# --- USER AUTHENTICATION GATE ---
if not st.session_state.logged_in_user:
    st.title("Hoda: AI Language Learning Engine")
    st.subheader("Login or Create Account")

    auth_col1, auth_col2 = st.columns(2)
    with auth_col1:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            language_choice = st.selectbox(
                "Which language do you want to learn?",
                options=[code for _, code in LANGUAGE_OPTIONS],
                format_func=lambda code: next(
                    label for label, value in LANGUAGE_OPTIONS if value == code
                ),
            )
            if st.form_submit_button("Login / Create Account"):
                if login_user and login_pass:
                    conn = sqlite3.connect("hoda_memory.db")
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ?", (login_user,))
                    user = c.fetchone()

                    if not user:
                        c.execute(
                            "INSERT INTO users (username, password, learning_language) VALUES (?, ?, ?)",
                            (login_user, login_pass, language_choice),
                        )
                        conn.commit()
                        st.success(
                            f"Account created for {login_user}! "
                            f"You'll learn {get_lang_config(language_choice)['name']}. Click Login again to enter."
                        )
                    elif user[1] == login_pass:
                        saved_lang = user[2] if len(user) > 2 and user[2] else "japanese"
                        st.session_state.logged_in_user = login_user
                        st.session_state.learning_language = saved_lang
                        st.rerun()
                    else:
                        st.error("Incorrect password.")

                    conn.close()
                else:
                    st.warning("Please enter a username and password.")

    with auth_col2:
        st.info(
            "**Choose your language at signup.** Each account tracks progress separately "
            "for Japanese 🇯🇵, Hindi 🇮🇳, or Malayalam 🇮🇳. You can switch languages later from the sidebar."
        )

    st.stop()

# Reload language from DB after login
st.session_state.learning_language = get_user_language(st.session_state.logged_in_user)
current_lang = st.session_state.learning_language
lang_cfg = get_lang_config(current_lang)

st.title(f"Hoda: The AI {lang_cfg['name']} Language Engine {lang_cfg['flag']}")

st.sidebar.success(f"👤 Logged in as: **{st.session_state.logged_in_user}**")
st.sidebar.info(f"📚 Learning: **{lang_cfg['name']}** {lang_cfg['flag']}")

sidebar_lang = st.sidebar.selectbox(
    "Switch learning language",
    options=[code for _, code in LANGUAGE_OPTIONS],
    index=[code for _, code in LANGUAGE_OPTIONS].index(current_lang),
    format_func=lambda code: next(
        label for label, value in LANGUAGE_OPTIONS if value == code
    ),
)
if sidebar_lang != current_lang:
    set_user_language(st.session_state.logged_in_user, sidebar_lang)
    st.session_state.learning_language = sidebar_lang
    st.session_state.current_char_label = ""
    st.session_state.draw_attempts = 0
    st.session_state.current_lesson = ""
    st.session_state.current_audio = None
    st.session_state.chat_history = []
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.logged_in_user = None
    st.session_state.clear()
    st.rerun()

st.sidebar.header("⚙️ System Performance")
st.sidebar.success("Local GPU: RX 6600M (Active)")
st.sidebar.info("Model: Llama 4 Scout (Groq)")
st.sidebar.divider()

st.sidebar.header("🧠 Memory Core (RAG)")
mistakes = get_recent_mistakes(current_lang)
if mistakes:
    st.sidebar.warning("Targeted Weaknesses:")
    for m in mistakes:
        st.sidebar.write(f"- {m}")
    st.sidebar.caption("Hoda is currently injecting these into your Situational Labs.")
else:
    st.sidebar.success("Database clean! No recent weaknesses detected.")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔤 Step 1: Alphabet Lab",
    "🗣️ Step 2: Situational Lab",
    "🎙️ Step 3: Voice Practice",
    "👁️ Step 4: Real-World Lab",
])

if "draw_attempts" not in st.session_state:
    st.session_state.draw_attempts = 0
if "current_char_label" not in st.session_state:
    st.session_state.current_char_label = ""
if "saved_mnemonics" not in st.session_state:
    st.session_state.saved_mnemonics = {}
if "current_lesson" not in st.session_state:
    st.session_state.current_lesson = ""
if "current_audio" not in st.session_state:
    st.session_state.current_audio = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

# --- TAB 1: ALPHABET LAB ---
with tab1:
    pathway_labels = get_pathway_labels(current_lang)
    if current_lang == "japanese":
        st.header("Step 1: Master the Alphabet (Hiragana & Katakana)")
    elif current_lang == "hindi":
        st.header("Step 1: Master the Devanagari Alphabet")
    else:
        st.header("Step 1: Master the Malayalam Alphabet")

    st.write("Watch the animation when available, then trace the faded guide below.")

    script_choice = st.radio(
        "Select your mastery pathway:",
        pathway_labels,
        horizontal=True,
    )
    pathway_key = pathway_key_from_label(current_lang, script_choice)
    active_database = get_alphabet_database(current_lang, pathway_key)

    st.divider()
    char_labels = list(active_database.keys())

    if not char_labels:
        st.warning("No characters available for this pathway yet.")
    else:
        if (
            "current_char_label" not in st.session_state
            or st.session_state.current_char_label not in char_labels
        ):
            st.session_state.current_char_label = char_labels[0]

        current_idx = char_labels.index(st.session_state.current_char_label)
        learned_chars = get_learned_letters(st.session_state.logged_in_user, current_lang)

        def display_with_checkmark(label):
            if active_database[label]["char"] in learned_chars:
                return f"✅ {label}"
            return label

        selected_char_label = st.selectbox(
            "Choose a character to learn today:",
            char_labels,
            index=current_idx,
            format_func=display_with_checkmark,
        )

        if selected_char_label != st.session_state.current_char_label:
            st.session_state.current_char_label = selected_char_label
            st.session_state.draw_attempts = 0
            st.rerun()

        target_char = active_database[st.session_state.current_char_label]["char"]
        target_gif = active_database[st.session_state.current_char_label].get("gif", "")

        st.divider()
        col_learn, col_draw = st.columns([1, 1])

        with col_learn:
            st.subheader("1. AI Memory Story")
            st.markdown(
                f"<h1 style='text-align: center; font-size: 80px; color: #ff4b4b; margin-bottom: 0px;'>{target_char}</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<h3 style='text-align: center; margin-top: 0px;'>Pronunciation: {selected_char_label}</h3>",
                unsafe_allow_html=True,
            )

            audio_bytes = text_to_speech_bytes(target_char, current_lang)
            st.audio(audio_bytes, format="audio/mp3")

            st.write("Click below to unlock Hoda's memory trick for this shape.")
            if target_char in st.session_state.saved_mnemonics:
                st.info(st.session_state.saved_mnemonics[target_char])
            elif st.button(f"Generate Mnemonic for {target_char}"):
                with st.spinner("Analyzing shape..."):
                    prompt = f"Character: {target_char}. Pronunciation: {selected_char_label}."
                    story = get_hoda_response(prompt, language=current_lang, context="alphabet")
                    st.session_state.saved_mnemonics[target_char] = story
                    st.rerun()

        with col_draw:
            st.subheader("2. Trace & Practice")
            st.markdown("**Challenge:** Trace the letter **at least 5 times**!")

            attempts = st.session_state.draw_attempts
            st.progress(min(attempts / 5.0, 1.0))

            if attempts >= 5:
                st.success(f"🎉 Fantastic! You completed {attempts} practice rounds.")
            else:
                st.warning(f"Practice Round: {attempts} / 5 completed.")

            st.write("**Stroke Order:**")
            if target_gif:
                st.image(target_gif, width=100)
            elif current_lang == "japanese":
                gif_urls = []
                for char in target_char:
                    gif_url = get_kanji_gif(char)
                    if gif_url:
                        gif_urls.append(gif_url)
                if gif_urls:
                    st.image(gif_urls, width=100)
                else:
                    st.info("No stroke order animation available.")
            else:
                st.info("No stroke order animation available for this script yet.")

            tracing_bg = create_tracing_background(
                target_char,
                lang_cfg["font"],
                width=400,
                height=200,
            )

            st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=4,
                stroke_color="#FFFFFF",
                background_image=tracing_bg,
                height=200,
                width=400,
                drawing_mode="freedraw",
                key=f"canvas_{target_char}_{attempts}",
            )

            if st.button("Log Attempt & Clear Canvas", key="clear_btn"):
                st.session_state.draw_attempts += 1
                st.rerun()

        if st.session_state.draw_attempts >= 5:
            st.success(f"🎉 You've mastered '{target_char}'! Muscle memory locked in.")
            log_progress(st.session_state.logged_in_user, target_char, current_lang)

            if st.button("➡️ Go to Next Letter", type="primary"):
                next_idx = (current_idx + 1) % len(char_labels)
                st.session_state.current_char_label = char_labels[next_idx]
                st.session_state.draw_attempts = 0
                st.rerun()

# --- TAB 2: SITUATIONAL LAB ---
with tab2:
    st.header(f"Step 2: Learn Contextual {lang_cfg['name']} Phrases")
    st.write("Type any situation. Hoda will write a custom script and generate the native audio.")

    with st.form(key="scenario_form"):
        scenario_input = st.text_input(
            "Type a life scenario:",
            placeholder="e.g. Asking where the train station is",
        )
        submit_button = st.form_submit_button(label="Generate Lesson")

    if submit_button and scenario_input:
        with st.spinner("Hoda is writing the dialogue..."):
            raw_response = get_hoda_response(
                scenario_input,
                language=current_lang,
                context="scenario",
            )

            try:
                lesson_data = json.loads(raw_response)
                dialogue_lines = lesson_data.get("dialogue", [])

                display_lesson = ""
                native_for_audio = ""

                for line in dialogue_lines:
                    block, clean_native = parse_dialogue_line(line, lang_cfg["translit_label"])
                    display_lesson += block
                    native_for_audio += clean_native + " "

                audio_bytes_data = None
                if native_for_audio.strip():
                    audio_bytes_data = text_to_speech_bytes(native_for_audio, current_lang)

                st.session_state.current_lesson = display_lesson
                st.session_state.current_audio = audio_bytes_data

            except Exception as e:
                st.error(f"Formatting error: {e}")

    if st.session_state.current_lesson:
        st.divider()
        st.markdown("### 📖 Your Custom Lesson")
        st.write(st.session_state.current_lesson)

        if st.session_state.current_audio:
            st.markdown("**Listen to the pronunciation:**")
            st.audio(st.session_state.current_audio, format="audio/mp3")

# --- TAB 3: VOICE PRACTICE ---
with tab3:
    st.header(f"Step 3: Conversational {lang_cfg['name']} Voice Lab")
    st.write("Have a real-time conversation with Hoda. Speak freely, and she will reply!")

    audio = mic_recorder(
        start_prompt="🎙️ Tap to Speak",
        stop_prompt="⏹️ Stop & Send",
        key="hoda_conversational_mic",
    )

    if audio and audio["id"] != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio["id"]

        with open("temp_speech.wav", "wb") as f:
            f.write(audio["bytes"])

        with st.spinner("Hoda is listening..."):
            result = whisper_model.transcribe(
                "temp_speech.wav",
                language=lang_cfg["whisper_lang"],
            )
            transcribed_text = result["text"].strip()

        with st.spinner("Hoda is thinking..."):
            try:
                raw_response = get_hoda_response(
                    transcribed_text,
                    language=current_lang,
                    context="conversational_voice",
                    chat_history=st.session_state.chat_history,
                )
                chat_data = json.loads(raw_response)
                parsed = parse_voice_response(chat_data)

                audio_bytes_data = None
                if parsed["native"]:
                    audio_bytes_data = text_to_speech_bytes(parsed["native"], current_lang)

                st.session_state.chat_history.append({
                    "user": transcribed_text,
                    "user_en": parsed["user_translation"],
                    "hoda_native": parsed["native"],
                    "hoda_translit": parsed["transliteration"],
                    "hoda_en": parsed["english"],
                    "audio": audio_bytes_data,
                    "autoplay": True,
                })

            except Exception as e:
                st.error(f"Hoda got confused during the conversation. Error details: {e}")

    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(f"**You:** {chat['user']}")
            if chat.get("user_en"):
                st.caption(f"*(You said: {chat['user_en']})*")

        with st.chat_message("assistant"):
            native = chat.get("hoda_native") or chat.get("hoda_jp", "")
            translit = chat.get("hoda_translit") or chat.get("hoda_ro", "")
            st.write(f"**{lang_cfg['flag']} {native}**")
            st.write(f"*{translit}*")
            st.caption(f"🇬🇧 {chat.get('hoda_en', '')}")

            if chat.get("audio"):
                st.audio(chat["audio"], format="audio/mp3", autoplay=chat["autoplay"])
                st.session_state.chat_history[i]["autoplay"] = False

# --- TAB 4: REAL-WORLD LAB ---
with tab4:
    st.header(f"Step 4: Real-World {lang_cfg['name']} Lab")
    st.write(
        f"Upload a photo or snap a picture of a {lang_cfg['name']} menu, sign, or label. "
        "Hoda will read it for you."
    )

    input_method = st.radio(
        "Choose input method:",
        ["📁 Upload an Image", "📸 Take a Photo"],
        horizontal=True,
    )

    img_file_buffer = None
    if input_method == "📁 Upload an Image":
        img_file_buffer = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    else:
        st.info("⚠️ Hoda needs camera permissions to take a live photo.")
        img_file_buffer = st.camera_input(f"Snap a picture of some {lang_cfg['name']} text")

    if img_file_buffer is not None:
        st.image(img_file_buffer, caption="Analyzing this image...", use_column_width=True)

        button_label = (
            "Translate & Explain Kanji"
            if current_lang == "japanese"
            else f"Translate & Explain {lang_cfg['vision_script_label']}"
        )
        if st.button(button_label, key="vision_btn"):
            with st.spinner("Hoda is looking at the image..."):
                try:
                    image_bytes = img_file_buffer.getvalue()
                    vision_result = analyze_language_image(image_bytes, current_lang)
                    st.markdown("### 👁️ Hoda's Vision Report")
                    st.write(vision_result)
                except Exception as e:
                    st.error(f"Something went wrong with the Vision API: {e}")
