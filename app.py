import streamlit as st
import os
import whisper
import requests
from groq import Groq
from dotenv import load_dotenv
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from streamlit_drawable_canvas import st_canvas
import io
import base64
import sqlite3
from datetime import datetime
import json

@st.cache_data(ttl=3600)
def fetch_jisho_n2_data():
    """Fetches live N2 vocabulary directly from the Jisho.org API."""
    # Jisho's official API endpoint searching specifically for JLPT N2 words
    url = "https://jisho.org/api/v1/search/words?keyword=%23jlpt-n2"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        kanji_dict = {}
        
        # Loop through the API results and format them for our app
        for item in data.get('data', []):
            jp_data = item['japanese'][0]
            
            # Some words are just Kana, some are Kanji. We safely grab whatever is available.
            word = jp_data.get('word', jp_data.get('reading', ''))
            reading = jp_data.get('reading', '')
            
            # Extract the primary English definition
            english = item['senses'][0]['english_definitions'][0]
            
            # Format the label for the Streamlit dropdown menu
            label = f"{english} ({reading})"
            
            kanji_dict[label] = {
                "char": word,
                "gif": "" # Jisho doesn't provide GIFs, but our app will safely ignore this!
            }
            
        return kanji_dict
        
    except Exception as e:
        st.error(f"Failed to connect to Jisho API: {e}")
        return {}

# 1. INITIALIZATION & API SETUP
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

st.set_page_config(page_title="Hoda | AI Japanese Engine", layout="wide", page_icon="🇯🇵")

# --- THE MEMORY CORE (SQLite Database) ---
def init_db():
    conn = sqlite3.connect('hoda_memory.db')
    c = conn.cursor()
    
    # 1. Mistakes table (for RAG)
    c.execute('''CREATE TABLE IF NOT EXISTS mistakes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, error_type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 2. User Accounts Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
                 
    # 3. Alphabet Progress Table
    c.execute('''CREATE TABLE IF NOT EXISTS progress 
                 (username TEXT, char TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(username, char))''')
    conn.commit()
    conn.close()

# --- MISTAKE LOGGING (For RAG / Tab 2 & 3) ---
def log_mistake(word, error_type):
    """Saves a failed word/character to the database."""
    conn = sqlite3.connect('hoda_memory.db')
    c = conn.cursor()
    c.execute("INSERT INTO mistakes (word, error_type) VALUES (?, ?)", (word, error_type))
    conn.commit()
    conn.close()

def get_recent_mistakes():
    """Retrieves the top 3 most recent mistakes for the AI to use (RAG)."""
    conn = sqlite3.connect('hoda_memory.db')
    c = conn.cursor()
    c.execute("SELECT word FROM mistakes GROUP BY word ORDER BY MAX(timestamp) DESC LIMIT 3")
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]

# --- PROGRESS TRACKING (For User Accounts / Tab 1) ---
def log_progress(username, char):
    """Marks a letter as learned for a specific user."""
    conn = sqlite3.connect('hoda_memory.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO progress (username, char) VALUES (?, ?)", (username, char))
    conn.commit()
    conn.close()

def get_learned_letters(username):
    """Returns a list of characters the user has mastered."""
    if not username:
        return []
    conn = sqlite3.connect('hoda_memory.db')
    c = conn.cursor()
    c.execute("SELECT char FROM progress WHERE username = ?", (username,))
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]

# Initialize the database the moment the app starts
init_db()


def is_kanji(char):
    """Checks if a character falls within the official Kanji Unicode range."""
    return '\u4e00' <= char <= '\u9faf'

def get_kanji_gif(char):
    """Converts the Kanji to a Hex code and fetches the open-source animation."""
    if is_kanji(char):
        # hex(ord()) converts '学' into its unicode math ID '0x5b66', and [2:] strips the '0x'
        hex_code = hex(ord(char))[2:]
        # Fetches the animation from mistval's open-source Kanji image repository
        return f"https://raw.githubusercontent.com/mistval/kanji_images/master/gifs/{hex_code}.gif"
    return None

# 2. LOCAL GPU AUDIO ENGINE (Whisper)
@st.cache_resource
def load_whisper_model():
    # Uses your RX 6600M via ROCm
    return whisper.load_model("base", device="cuda")

whisper_model = load_whisper_model()

# 3. TEXT-TO-SPEECH (TTS) ENGINE
def play_japanese_audio(text):
    """Converts Japanese text to audio and renders a player in Streamlit."""
    tts = gTTS(text=text, lang='ja')
    # Save to a virtual file in memory to keep it fast
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp, format='audio/mp3')

# 4. LLM BRAIN (Llama 3)
def get_hoda_response(user_text, context="general", chat_history=None):
    
    if context == "alphabet":
        sys_prompt = """You are a highly creative, slightly eccentric Japanese teacher. The user will provide a Japanese character and its pronunciation. 
        Create a wildly unique, modern, and highly visual mnemonic trick. 
        
        CRITICAL RULES:
        1. DO NOT use boring, repetitive tropes. ABSOLUTELY NO mountains, birds, swords, or simple smiley faces.
        2. Be weird, modern, and specific (e.g., an alien spaceship, a ninja kicking a pizza, a broken rollercoaster, a skateboarder).
        3. The visual must clearly connect to the physical shape of the character.
        4. The story must clearly connect the visual to the phonetic sound.
        
        You MUST use this exact format:
        **Looks like:** [A very specific, unique object the shape resembles]
        **Memory Trick:** [A 1-sentence weird/funny story connecting the object to the sound]
        
        Do NOT write paragraphs. Keep it simple but highly memorable."""
        
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_text}],
            model="llama-3.1-8b-instant",
            temperature=0.8 # <-- Cranked up to 0.8 for maximum creativity!
        )
        return completion.choices[0].message.content
        
    elif context == "pronunciation_feedback":
        sys_prompt = """You are Hoda, a Japanese tutor. The user is a COMPLETE BEGINNER practicing pronunciation. 
        
        IMPORTANT RULES: 
        1. If the transcribed text looks like random gibberish or a hallucination, DO NOT try to explain it. Just say 'I couldn't catch that clearly. Please try speaking closer to the mic.'
        2. ALL of your explanations MUST be written entirely in ENGLISH.
        3. NEVER ask the user to say complex sentences. NEVER ask "Can you say X in Japanese?". 
        4. Focus ONLY on the exact sound or word they are trying to practice. Grade their attempt, give one simple tip, and stop.
        5. Keep feedback to 2 sentences max. Be extremely encouraging."""
        
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_text}],
            model="llama-3.1-8b-instant",
            temperature=0.3 
        )
        return completion.choices[0].message.content
        
    elif context == "conversational_voice":
        # 1. Format the history safely as a text script
        history_script = ""
        if chat_history:
            for chat in chat_history[-3:]: 
                history_script += f"User said: {chat['user']}\nYou replied: {chat['hoda_jp']}\n---\n"

        # 2. Inject it safely into the System Prompt
        sys_prompt = f"""You are Hoda, a friendly and enthusiastic Japanese language partner. 
        
        Recent Conversation History:
        {history_script}
        
        IMPORTANT RULES: 
        1. ACT LIKE A REAL PERSON. Respond naturally to keep the conversation flowing. If they ask who you are, introduce yourself playfully!
        2. DO NOT just parrot back what the user said. Have an actual back-and-forth dialogue.
        3. Keep your Japanese response conversational, natural, and short (1-2 sentences).
        4. Put any grammar corrections ONLY in the "english" JSON field so it doesn't break character in the Japanese audio.
        5. You MUST output your response as a valid JSON object using this exact structure:
        {{
          "user_translation": "Translate exactly what the user just said into English",
          "japanese": "Your conversational reply in pure Japanese characters",
          "romaji": "romaji of your reply",
          "english": "English translation of your reply, plus any brief grammar corrections here."
        }}
        """
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.6, 
            response_format={"type": "json_object"} 
        )
        return completion.choices[0].message.content
        
    else:
        # --- THE RAG MEMORY INJECTION (Tab 2 Only) ---
        recent_mistakes = get_recent_mistakes()
        
        rag_injection = ""
        if recent_mistakes:
            weaknesses = ", ".join(recent_mistakes)
            rag_injection = f"MEMORY RULE: The user recently struggled with: {weaknesses}. Try to naturally include one of these, but DO NOT ruin the main scenario to do it."

        sys_prompt = f"""You are Hoda, a Japanese tutor. 
        SCENARIO: {user_text}
        {rag_injection}
        
        Write a natural, 2-line dialogue. You MUST output ONLY a valid JSON object using this exact structure:
        {{
          "dialogue": [
            {{
              "speaker": "Person A",
              "japanese": "純粋な日本語のみ (Only pure Japanese characters, no brackets or english)",
              "romaji": "romaji here",
              "english": "english translation"
            }},
            {{
              "speaker": "Person B",
              "japanese": "純粋な日本語のみ",
              "romaji": "romaji here",
              "english": "english translation"
            }}
          ]
        }}"""

        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Scenario: {user_text}"}],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            response_format={"type": "json_object"} 
        )
        return completion.choices[0].message.content

def analyze_japanese_image(image_bytes):
    """Sends an image to Groq's Vision model to extract and translate Japanese."""
    # Convert the raw image bytes into a base64 string
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    sys_prompt = """You are Hoda, a Japanese tutor. The user has uploaded an image (like a menu, sign, or label).
    1. Extract the Japanese text.
    2. Provide the Romaji.
    3. Translate it to English.
    4. Highlight 1 or 2 difficult Kanji in the image and explain their meaning briefly.
    Keep it structured and easy to read."""

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": sys_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        temperature=0.3
    )
    return completion.choices[0].message.content

# 5. USER INTERFACE (Step-by-Step Flow)
st.title("Hoda: The AI Japanese Language Engine 🇯🇵")

# --- USER AUTHENTICATION GATE ---
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if not st.session_state.logged_in_user:
    st.subheader("Login to Hoda")
    
    auth_col1, auth_col2 = st.columns(2)
    with auth_col1:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Login / Create Account"):
                if login_user and login_pass:
                    # Very simple auth: If user doesn't exist, create them. If they do, log them in.
                    conn = sqlite3.connect('hoda_memory.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ?", (login_user,))
                    user = c.fetchone()
                    
                    if not user:
                        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (login_user, login_pass))
                        conn.commit()
                        st.success(f"Account created for {login_user}! Click Login again to enter.")
                    elif user[1] == login_pass:
                        st.session_state.logged_in_user = login_user
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                    conn.close()
                else:
                    st.warning("Please enter a username and password.")
                    
    # Stop the app from loading the tabs if they aren't logged in
    st.stop()

# If they get past the stop(), show who is logged in!
st.sidebar.success(f"👤 Logged in as: **{st.session_state.logged_in_user}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in_user = None
    st.session_state.clear() # Clears all memory
    st.rerun()

st.sidebar.header("⚙️ System Performance")
st.sidebar.success("Local GPU: RX 6600M (Active)")
st.sidebar.info("Model: Llama 4 Scout (Groq)")

st.sidebar.divider()

# RAG Dashboard
st.sidebar.header("🧠 Memory Core (RAG)")
mistakes = get_recent_mistakes()

if mistakes:
    st.sidebar.warning("Targeted Weaknesses:")
    for m in mistakes:
        st.sidebar.write(f"- {m}")
    st.sidebar.caption("Hoda is currently injecting these into your Situational Labs.")
else:
    st.sidebar.success("Database clean! No recent weaknesses detected.")
# ----------------------------------------

# Create a progressive learning path using Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔤 Step 1: Alphabet Lab", 
    "🗣️ Step 2: Situational Lab", 
    "🎙️ Step 3: Voice Practice",
    "👁️ Step 4: Real-World Lab"
])

# --- HELPER: GENERATE TRACING BACKGROUND ---
def create_tracing_background(text, width=600, height=250):
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a transparent image for the canvas background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # --- DYNAMIC FONT MATH ---
    # 1. The font shouldn't be taller than 80% of the canvas height
    max_h = int(height * 0.8)
    
    # 2. The text shouldn't be wider than 90% of the canvas width. 
    # We divide the max width by the number of letters to find the max size per letter.
    max_w = int((width * 0.9) / max(len(text), 1))
    
    # 3. The golden rule: Pick the SMALLER of the two sizes so it never overflows!
    font_size = min(max_h, max_w)
    
    # --- LOAD THE FONT ---
    try:
        # NOTE: If you are using a specific Japanese .ttf file, make sure the name matches here!
        font = ImageFont.truetype("NotoSansJP-Regular.ttf", font_size)
    except IOError:
        # Fallback just in case
        font = ImageFont.load_default()
        
    # --- PERFECT CENTERING ---
    # Get the exact pixel dimensions of the newly resized text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Calculate exact center X and Y coordinates
    x = (width - text_w) / 2
    y = (height - text_h) / 2 - bbox[1] # -bbox[1] fixes Pillow's vertical offset bug
    
    # Draw the faded tracing guide (gray with transparency)
    draw.text((x, y), text, fill=(150, 150, 150, 100), font=font)
    
    return img

# --- INITIALIZE SESSION STATE FOR TRACKING ---
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
    st.header("Step 1: Master the Alphabet (Hiragana & Katakana)")
    st.write("Stroke order is critical. Watch the animation, then trace the faded guide below.")
    
    # 1. The Complete Structured Syllabus
    katakana_chars = {
        "A (a)": "ア", "I (i)": "イ", "U (u)": "ウ", "E (e)": "エ", "O (o)": "オ",
        "Ka (ka)": "カ", "Ki (ki)": "キ", "Ku (ku)": "ク", "Ke (ke)": "ケ", "Ko (ko)": "コ",
        "Sa (sa)": "サ", "Shi (shi)": "シ", "Su (su)": "ス", "Se (se)": "セ", "So (so)": "ソ",
        "Ta (ta)": "タ", "Chi (chi)": "チ", "Tsu (tsu)": "ツ", "Te (te)": "テ", "To (to)": "ト",
        "Na (na)": "ナ", "Ni (ni)": "ニ", "Nu (nu)": "ヌ", "Ne (ne)": "ネ", "No (no)": "ノ",
        "Ha (ha)": "ハ", "Hi (hi)": "ヒ", "Fu (fu)": "フ", "He (he)": "ヘ", "Ho (ho)": "ホ",
        "Ma (ma)": "マ", "Mi (mi)": "ミ", "Mu (mu)": "ム", "Me (me)": "メ", "Mo (mo)": "モ",
        "Ya (ya)": "ヤ", "Yu (yu)": "ユ", "Yo (yo)": "ヨ",
        "Ra (ra)": "ラ", "Ri (ri)": "リ", "Ru (ru)": "ル", "Re (re)": "レ", "Ro (ro)": "ロ",
        "Wa (wa)": "ワ", "Wo (o)": "ヲ",
        "N (n)": "ン"
    }
    
    full_katakana = {}
    for label, char in katakana_chars.items():
        full_katakana[label] = {
            "char": char,
            "gif": f"https://commons.wikimedia.org/wiki/Special:FilePath/Katakana_{char}_stroke_order_animation.gif"
        }
    
    hiragana_chars = {
        "A (a)": "あ", "I (i)": "い", "U (u)": "う", "E (e)": "え", "O (o)": "お",
        "Ka (ka)": "か", "Ki (ki)": "き", "Ku (ku)": "く", "Ke (ke)": "け", "Ko (ko)": "こ",
        "Sa (sa)": "さ", "Shi (shi)": "し", "Su (su)": "す", "Se (se)": "せ", "So (so)": "そ",
        "Ta (ta)": "た", "Chi (chi)": "ち", "Tsu (tsu)": "つ", "Te (te)": "て", "To (to)": "と",
        "Na (na)": "な", "Ni (ni)": "に", "Nu (nu)": "ぬ", "Ne (ne)": "ね", "No (no)": "の",
        "Ha (ha)": "は", "Hi (hi)": "ひ", "Fu (fu)": "ふ", "He (he)": "へ", "Ho (ho)": "ほ",
        "Ma (ma)": "ま", "Mi (mi)": "み", "Mu (mu)": "む", "Me (me)": "め", "Mo (mo)": "も",
        "Ya (ya)": "や", "Yu (yu)": "ゆ", "Yo (yo)": "よ",
        "Ra (ra)": "ら", "Ri (ri)": "り", "Ru (ru)": "る", "Re (re)": "れ", "Ro (ro)": "ろ",
        "Wa (wa)": "わ", "Wo (o)": "を",
        "N (n)": "ん"
    }
    
    full_hiragana = {}
    for label, char in hiragana_chars.items():
        full_hiragana[label] = {
            "char": char,
            "gif": f"https://commons.wikimedia.org/wiki/Special:FilePath/Hiragana_{char}_stroke_order_animation.gif"
        }

    # 1. The Mastery Pathway Toggle
    script_choice = st.radio(
        "Select your mastery pathway:", 
        ["🇯🇵 Hiragana (Basics)", "🔠 Katakana (Foreign)", "🏯 Kanji (N2 Level)"], 
        horizontal=True
    )
    
    st.divider()

    # 2. Dynamically load the correct database based on the toggle
    if script_choice == "🇯🇵 Hiragana (Basics)":
        active_database = full_hiragana
    elif script_choice == "🔠 Katakana (Foreign)":
        active_database = full_katakana
    else:
        # --- NOW WE HIT THE INTERNET INSTEAD OF A LOCAL FILE ---
        active_database = fetch_jisho_n2_data()

    # 3. Feed the selected database into the UI
    char_labels = list(active_database.keys())
    
    if "current_char_label" not in st.session_state or st.session_state.current_char_label not in char_labels:
        st.session_state.current_char_label = char_labels[0] if char_labels else ""
        
    current_idx = char_labels.index(st.session_state.current_char_label) if st.session_state.current_char_label in char_labels else 0
    
    learned_chars = get_learned_letters(st.session_state.logged_in_user)
    
    def display_with_checkmark(label):
        if active_database[label]["char"] in learned_chars:
            return f"✅ {label}"
        return label

    selected_char_label = st.selectbox(
        "Choose a character to learn today:", 
        char_labels, 
        index=current_idx,
        format_func=display_with_checkmark
    )
    
    if selected_char_label != st.session_state.current_char_label:
        st.session_state.current_char_label = selected_char_label
        st.session_state.draw_attempts = 0
        st.rerun()

    # 4. Extract the data safely
    target_char = active_database[st.session_state.current_char_label]["char"]
    target_gif = active_database[st.session_state.current_char_label].get("gif", "")
    
    st.divider()

    col_learn, col_draw = st.columns([1, 1])

    with col_learn:
        st.subheader("1. AI Memory Story")
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #ff4b4b; margin-bottom: 0px;'>{target_char}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; margin-top: 0px;'>Pronunciation: {selected_char_label}</h3>", unsafe_allow_html=True)
        
        # Instant Pronunciation Audio
        tts_char = gTTS(text=target_char, lang='ja')
        audio_fp = io.BytesIO()
        tts_char.write_to_fp(audio_fp)
        
        st.audio(audio_fp, format='audio/mp3')
        
        st.write("Click below to unlock Hoda's memory trick for this shape.")
        if target_char in st.session_state.saved_mnemonics:
            st.info(st.session_state.saved_mnemonics[target_char])
        else:
            if st.button(f"Generate Mnemonic for {target_char}"):
                with st.spinner("Analyzing shape..."):
                    prompt = f"Character: {target_char}. Pronunciation: {selected_char_label}."
                    story = get_hoda_response(prompt, context="alphabet")
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
        
        # 1. NEW LAYOUT: Put the GIFs above the canvas instead of beside it!
        if target_gif:
            st.image(target_gif, width=100)
        else:
            gif_urls = []
            for char in target_char:
                gif_url = get_kanji_gif(char)
                if gif_url:
                    gif_urls.append(gif_url)
            
            if gif_urls:
                # Streamlit is smart enough to display a list of images side-by-side automatically!
                st.image(gif_urls, width=100)
            else:
                st.info("No stroke order animation available.")

        # 2. THE SAFE WIDESCREEN CANVAS (400x200)
        tracing_bg = create_tracing_background(target_char, width=400, height=200)
        
        canvas_result = st_canvas(
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

    # --- AUTOMATIC PROGRESSION SYSTEM ---
    if st.session_state.draw_attempts >= 5:
        st.success(f"🎉 You've mastered '{target_char}'! Muscle memory locked in.")
        
        log_progress(st.session_state.logged_in_user, target_char)

        if st.button("➡️ Go to Next Letter", type="primary"):
            next_idx = (current_idx + 1) % len(char_labels)
            st.session_state.current_char_label = char_labels[next_idx]
            st.session_state.draw_attempts = 0
            st.rerun()

# --- TAB 2: SITUATIONAL LAB (Fixed Form Logic) ---
with tab2:
    st.header("Step 2: Learn Contextual Phrases")
    st.write("Type any situation. Hoda will write a custom script and generate the native audio.")
    
    # 1. The Form Container (Prevents the UI freeze)
    with st.form(key="scenario_form"):
        scenario_input = st.text_input("Type a life scenario:", placeholder="e.g. Asking where the train station is")
        # The button is now a form_submit_button
        submit_button = st.form_submit_button(label="Generate Lesson")
        
    # 2. Process the AI Request ONLY when the button is clicked
    if submit_button and scenario_input:
        with st.spinner("Hoda is writing the dialogue..."):
            raw_response = get_hoda_response(scenario_input, context="scenario")
            
            try:
                lesson_data = json.loads(raw_response)
                dialogue_lines = lesson_data.get("dialogue", [])
                
                # These are the variables we are defining
                display_lesson = ""
                pure_japanese_for_audio = ""
                
                for line in dialogue_lines:
                    speaker = line.get("speaker", "Speaker")
                    jp = line.get("japanese", "")
                    ro = line.get("romaji", "")
                    en = line.get("english", "")
                    
                    display_lesson += f"**👤 {speaker}:**\n{jp}\n*{ro}*\n{en}\n\n---\n"
                    pure_japanese_for_audio += jp + "。 " 
                
                audio_fp = None
                if pure_japanese_for_audio.strip():
                    tts = gTTS(text=pure_japanese_for_audio, lang='ja')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)

                # Assigning the variables we just created to the session state
                st.session_state.current_lesson = display_lesson
                st.session_state.current_audio = audio_fp
                
            except Exception as e:
                st.error(f"Formatting error: {e}")

    # 3. Display the lesson from the Memory Bank (so it never disappears!)
    if st.session_state.current_lesson:
        st.divider()
        st.markdown("### 📖 Your Custom Lesson")
        st.write(st.session_state.current_lesson)
        
        if st.session_state.current_audio:
            st.markdown("**Listen to the pronunciation:**")
            st.audio(st.session_state.current_audio, format='audio/mp3')

# --- TAB 3: VOICE PRACTICE (Conversational Chat) ---
with tab3:
    st.header("Step 3: Conversational Voice Lab")
    st.write("Have a real-time conversation with Hoda. Speak freely, and she will reply!")
    
    # The Audio Input Engine
    audio = mic_recorder(
        start_prompt="🎙️ Tap to Speak",
        stop_prompt="⏹️ Stop & Send",
        key='hoda_conversational_mic'
    )

    # 1. Check if we have audio AND if it's a brand NEW recording
    if audio and audio['id'] != st.session_state.last_audio_id:
        # Lock the ID so Streamlit doesn't process this recording again on refresh
        st.session_state.last_audio_id = audio['id'] 
        
        with open("temp_speech.wav", "wb") as f:
            f.write(audio['bytes'])
        
        with st.spinner("Hoda is listening..."):
            result = whisper_model.transcribe("temp_speech.wav", language="ja")
            transcribed_text = result['text'].strip()
            
        with st.spinner("Hoda is thinking..."):
            try:
                raw_response = get_hoda_response(
                    transcribed_text, 
                    context="conversational_voice", 
                    chat_history=st.session_state.chat_history
                )
                chat_data = json.loads(raw_response)
                
                # Extract the new user translation!
                user_en = chat_data.get("user_translation", "")
                
                hoda_jp = chat_data.get("japanese", "")
                hoda_ro = chat_data.get("romaji", "")
                hoda_en = chat_data.get("english", "")
                
                audio_bytes_data = None
                if hoda_jp:
                    tts = gTTS(text=hoda_jp, lang='ja')
                    reply_audio_fp = io.BytesIO()
                    tts.write_to_fp(reply_audio_fp)
                    audio_bytes_data = reply_audio_fp.getvalue()

                # Save EVERYTHING to our Chat History array
                st.session_state.chat_history.append({
                    "user": transcribed_text,
                    "user_en": user_en,  # <-- Added this line
                    "hoda_jp": hoda_jp,
                    "hoda_ro": hoda_ro,
                    "hoda_en": hoda_en,
                    "audio": audio_bytes_data,
                    "autoplay": True 
                })
                        
            except Exception as e:
                st.error(f"Hoda got confused during the conversation. Error details: {e}")

    # 2. Render the Chat History on the screen
    for i, chat in enumerate(st.session_state.chat_history):
        # Display what you said AND your translation
        with st.chat_message("user"):
            st.write(f"**You:** {chat['user']}")
            # Use .get() just in case older chat history doesn't have this key yet
            if chat.get('user_en'):
                st.caption(f"*(You said: {chat['user_en']})*")
        
        # Display Hoda's reply
        with st.chat_message("assistant"):
            st.write(f"**🇯🇵 {chat['hoda_jp']}**")
            st.write(f"*{chat['hoda_ro']}*")
            st.caption(f"🇬🇧 {chat['hoda_en']}")
            
            if chat['audio']:
                st.audio(chat['audio'], format='audio/mp3', autoplay=chat['autoplay'])
                st.session_state.chat_history[i]["autoplay"] = False
 
# --- TAB 4: REAL-WORLD LAB (Vision OCR) ---
with tab4:
    st.header("Step 4: Real-World Lab")
    st.write("Upload a photo or snap a picture of a Japanese menu, sign, or label. Hoda will read it for you.")
    
    # Let the user choose their input method (Upload is first, so the camera stays off!)
    input_method = st.radio(
        "Choose input method:", 
        ["📁 Upload an Image", "📸 Take a Photo"], 
        horizontal=True
    )
    
    img_file_buffer = None
    
    # 2. Render only the tool the user actually selects
    if input_method == "📁 Upload an Image":
        img_file_buffer = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    else:
        st.info("⚠️ Hoda needs camera permissions to take a live photo.")
        img_file_buffer = st.camera_input("Snap a picture of some Japanese text")
        
    if img_file_buffer is not None:
        # Display the image back to the user
        st.image(img_file_buffer, caption="Analyzing this image...", use_column_width=True)
        
        if st.button("Translate & Explain Kanji", key="vision_btn"):
            with st.spinner("Hoda is looking at the image..."):
                try:
                    # Read the bytes from the uploaded file/camera
                    image_bytes = img_file_buffer.getvalue()
                    
                    # Send to the Groq Vision model
                    vision_result = analyze_japanese_image(image_bytes)
                    
                    st.markdown("### 👁️ Hoda's Vision Report")
                    st.write(vision_result)
                    
                except Exception as e:
                    st.error(f"Something went wrong with the Vision API: {e}")