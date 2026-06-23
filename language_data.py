"""Language configuration and alphabet data for Hoda."""

LANGUAGES = {
    "japanese": {
        "code": "japanese",
        "name": "Japanese",
        "flag": "🇯🇵",
        "native_name": "日本語",
        "tts_lang": "ja",
        "whisper_lang": "ja",
        "font": "NotoSansJP-Regular.ttf",
        "page_icon": "🇯🇵",
        "translit_label": "Romaji",
        "vision_script_label": "Kanji",
    },
    "hindi": {
        "code": "hindi",
        "name": "Hindi",
        "flag": "🇮🇳",
        "native_name": "हिन्दी",
        "tts_lang": "hi",
        "whisper_lang": "hi",
        "font": "NotoSansDevanagari-Regular.ttf",
        "page_icon": "🇮🇳",
        "translit_label": "Romanized Hindi",
        "vision_script_label": "Devanagari",
    },
    "malayalam": {
        "code": "malayalam",
        "name": "Malayalam",
        "flag": "🇮🇳",
        "native_name": "മലയാളം",
        "tts_lang": "ml",
        "whisper_lang": "ml",
        "font": "NotoSansMalayalam-Regular.ttf",
        "page_icon": "🇮🇳",
        "translit_label": "Romanized Malayalam",
        "vision_script_label": "Malayalam script",
    },
}

LANGUAGE_OPTIONS = [
    ("🇯🇵 Japanese", "japanese"),
    ("🇮🇳 Hindi", "hindi"),
    ("🇮🇳 Malayalam", "malayalam"),
]

LANGUAGE_PATHWAYS = {
    "japanese": [
        ("🇯🇵 Hiragana (Basics)", "hiragana"),
        ("🔠 Katakana (Foreign)", "katakana"),
        ("🏯 Kanji (N2 Level)", "advanced"),
    ],
    "hindi": [
        ("🔤 Devanagari Vowels (स्वर)", "vowels"),
        ("🔠 Devanagari Consonants (व्यंजन)", "consonants"),
        ("📚 Common Words", "advanced"),
    ],
    "malayalam": [
        ("🔤 Malayalam Vowels (സ്വരം)", "vowels"),
        ("🔠 Malayalam Consonants (വ്യഞ്ജനം)", "consonants"),
        ("📚 Common Words", "advanced"),
    ],
}


def _char_db(char_map):
    return {label: {"char": char, "gif": ""} for label, char in char_map.items()}


HIRAGANA_CHARS = {
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
    "N (n)": "ん",
}

KATAKANA_CHARS = {
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
    "N (n)": "ン",
}

HINDI_VOWELS = {
    "A (a)": "अ", "Aa (aa)": "आ", "I (i)": "इ", "Ii (ii)": "ई",
    "U (u)": "उ", "Uu (uu)": "ऊ", "Ri (ri)": "ऋ",
    "E (e)": "ए", "Ai (ai)": "ऐ", "O (o)": "ओ", "Au (au)": "औ",
    "Am (am)": "अं", "Ah (ah)": "अः",
}

HINDI_CONSONANTS = {
    "Ka (ka)": "क", "Kha (kha)": "ख", "Ga (ga)": "ग", "Gha (gha)": "घ", "Nga (nga)": "ङ",
    "Cha (cha)": "च", "Chha (chha)": "छ", "Ja (ja)": "ज", "Jha (jha)": "झ", "Nya (nya)": "ञ",
    "Ta retroflex (ta)": "ट", "Tha retroflex (tha)": "ठ", "Da retroflex (da)": "ड", "Dha retroflex (dha)": "ढ", "Na retroflex (na)": "ण",
    "Ta dental (ta)": "त", "Tha dental (tha)": "थ", "Da dental (da)": "द", "Dha dental (dha)": "ध", "Na dental (na)": "न",
    "Pa (pa)": "प", "Pha (pha)": "फ", "Ba (ba)": "ब", "Bha (bha)": "भ", "Ma (ma)": "म",
    "Ya (ya)": "य", "Ra (ra)": "र", "La (la)": "ल", "Va (va)": "व",
    "Sha palatal (sha)": "श", "Sha retroflex (sha)": "ष", "Sa (sa)": "स", "Ha (ha)": "ह",
    "Ksha (ksha)": "क्ष", "Tra (tra)": "त्र", "Gya (gya)": "ज्ञ",
}

HINDI_COMMON_WORDS = {
    "Hello (namaste)": "नमस्ते", "Thank you (dhanyavaad)": "धन्यवाद",
    "Water (paani)": "पानी", "Food (khaana)": "खाना", "House (ghar)": "घर",
    "Friend (dost)": "दोस्त", "Mother (maata)": "माता", "Father (pita)": "पिता",
    "Book (kitaab)": "किताब", "School (vidyaalaya)": "विद्यालय",
    "Good morning (suprabhaat)": "सुप्रभात", "Good night (shubh raatri)": "शुभ रात्रि",
    "How are you? (aap kaise hain)": "आप कैसे हैं", "Yes (haan)": "हाँ", "No (nahin)": "नहीं",
    "Please (kripya)": "कृपया", "Sorry (maaf kijiye)": "माफ़ कीजिए",
    "I love you (main tumse pyaar karta hoon)": "मैं तुमसे प्यार करता हूँ",
    "Beautiful (sundar)": "सुंदर", "Happy (khush)": "खुश",
}

MALAYALAM_VOWELS = {
    "A (a)": "അ", "Aa (aa)": "ആ", "I (i)": "ഇ", "Ii (ii)": "ഈ",
    "U (u)": "ഉ", "Uu (uu)": "ഊ", "Ri (ri)": "ഋ", "Li (li)": "ഌ",
    "E (e)": "എ", "Ee (ee)": "ഏ", "Ai (ai)": "ഐ", "O (o)": "ഒ", "Au (au)": "ഔ",
    "Am (am)": "അം", "Ah (ah)": "അഃ",
}

MALAYALAM_CONSONANTS = {
    "Ka (ka)": "ക", "Kha (kha)": "ഖ", "Ga (ga)": "ഗ", "Gha (gha)": "ഘ", "Nga (nga)": "ങ",
    "Cha (cha)": "ച", "Chha (chha)": "ഛ", "Ja (ja)": "ജ", "Jha (jha)": "ഝ", "Nya (nya)": "ഞ",
    "Ta retroflex (ta)": "ട", "Tha retroflex (tha)": "ഠ", "Da retroflex (da)": "ഡ", "Dha retroflex (dha)": "ഢ", "Na retroflex (na)": "ണ",
    "Ta dental (ta)": "ത", "Tha dental (tha)": "ഥ", "Da dental (da)": "ദ", "Dha dental (dha)": "ധ", "Na dental (na)": "ന",
    "Pa (pa)": "പ", "Pha (pha)": "ഫ", "Ba (ba)": "ബ", "Bha (bha)": "ഭ", "Ma (ma)": "മ",
    "Ya (ya)": "യ", "Ra (ra)": "ര", "La (la)": "ല", "Va (va)": "വ",
    "Sha palatal (sha)": "ശ", "Sha retroflex (sha)": "ഷ", "Sa (sa)": "സ", "Ha (ha)": "ഹ",
    "La retroflex (la)": "ള", "La dental (la)": "ഴ", "Ra trill (ra)": "റ",
}

MALAYALAM_COMMON_WORDS = {
    "Hello (namaskaram)": "നമസ്കാരം", "Thank you (nanni)": "നന്ദി",
    "Water (vellam)": "വെള്ളം", "Food (bhakshanam)": "ഭക്ഷണം", "House (veedu)": "വീട്",
    "Friend (sneham)": "സുഹൃത്ത്", "Mother (amma)": "അമ്മ", "Father (achan)": "അച്ഛൻ",
    "Book (pustakam)": "പുസ്തകം", "School (vidyalayam)": "വിദ്യാലയം",
    "Good morning (suprabhaatham)": "സുപ്രഭാതം", "Good night (subha raathri)": "ശുഭ രാത്രി",
    "How are you? (engane und)": "എങ്ങനെ ഉണ്ട്", "Yes (athe)": "അതെ", "No (illa)": "ഇല്ല",
    "Please (dayavayi)": "ദയവായി", "Sorry (kshemikkoo)": "ക്ഷമിക്കൂ",
    "I love you (enikku ninne ishtam aanu)": "എനിക്ക് നിന്നെ ഇഷ്ടമാണ്",
    "Beautiful (sundaram)": "സുന്ദരം", "Happy (santhosham)": "സന്തോഷം",
}

STATIC_ALPHABET = {
    "japanese": {
        "hiragana": _char_db(HIRAGANA_CHARS),
        "katakana": _char_db(KATAKANA_CHARS),
        "advanced": None,
    },
    "hindi": {
        "vowels": _char_db(HINDI_VOWELS),
        "consonants": _char_db(HINDI_CONSONANTS),
        "advanced": _char_db(HINDI_COMMON_WORDS),
    },
    "malayalam": {
        "vowels": _char_db(MALAYALAM_VOWELS),
        "consonants": _char_db(MALAYALAM_CONSONANTS),
        "advanced": _char_db(MALAYALAM_COMMON_WORDS),
    },
}


def get_lang_config(language_code):
    return LANGUAGES.get(language_code, LANGUAGES["japanese"])


def get_pathway_labels(language_code):
    return [label for label, _ in LANGUAGE_PATHWAYS.get(language_code, LANGUAGE_PATHWAYS["japanese"])]
