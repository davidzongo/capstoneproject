import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os
import pandas as pd
from PyPDF2 import PdfReader

# ---------------------------
# CONFIGURE GEMINI
# ---------------------------
import getpass
#APIKEY = getpass.getpass("Enter your Google API Key: ")
#genai.configure(api_key=APIKEY)

genai.configure(api_key="AIzaSyBlgCJtLIQQhl7jCamTMGL7TuFHN_tM7GA")

# Use the correct model names from the API
# The issue was that we need to include "models/" prefix
model_names = [
    "models/gemini-2.5-flash",  # Fast and efficient
    "models/gemini-2.0-flash",  # Alternative fast model
    "models/gemini-flash-latest",  # Latest flash model
    "models/gemini-2.5-pro",   # More capable but uses more quota
]

model = None
working_model = None

for model_name in model_names:
    try:
        print(f"Trying model: {model_name}")
        model = genai.GenerativeModel(model_name)
        working_model = model_name
        print(f"✅ Successfully configured model: {model_name}")
        break
    except Exception as e:
        print(f"❌ Model {model_name} failed: {e}")
        continue

if model is None:
    print("❌ No working model found. Please check your quota and API key.")
else:
    print(f"✅ Using model: {working_model}")

def translate_text(text, target_lang="French"):
    """Translate text using Gemini API"""
    if model is None:
        return "❌ No working Gemini model available. Please check your API key and model availability."
    
    try:
        prompt = f"Translate the following text into {target_lang}:\n\n{text}"
        response = model.generate_content(prompt)
        
        # Check if response has content
        if hasattr(response, 'text') and response.text:
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            return "❌ No translation content received from API"
            
    except Exception as e:
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower():
            return "❌ Quota exceeded! You've reached your Gemini API usage limit. Please wait or upgrade your plan."
        elif "404" in error_message:
            return "❌ Model not found. The specified model is not available."
        else:
            return f"❌ Error during translation: {e}"

def text_to_speech(text, lang_code="en"):
    """Convert text to speech using gTTS"""
    try:
        tts = gTTS(text=text, lang=lang_code)
        # Use absolute path to ensure file is accessible
        file_path = os.path.abspath("translation_output.mp3")
        tts.save(file_path)
        return file_path
    except Exception as e:
        st.error(f"TTS failed: {e}")
        return None

def extract_text_from_file(uploaded_file):
    """Extract text from different file types"""
    text = ""
    if uploaded_file.type == "text/plain":
        text = uploaded_file.read().decode("utf-8")

    elif uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = "".join([page.extract_text() for page in reader.pages])

    elif uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        text = " ".join(df.astype(str).sum())

    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        df = pd.read_excel(uploaded_file)
        text = " ".join(df.astype(str).sum())

    return text

# ---------------------------
# STREAMLIT UI
# ---------------------------
st.set_page_config(page_title="Capstone Translator", page_icon="🌍")
st.title("🌍 Capstone Translator & Speech Generator")
st.write("Translate text into different languages and download as MP3 speech.")

# Sidebar instructions
with st.sidebar:
    st.header("📌 Instructions")
    st.markdown("""
    1. Enter text or upload a file (TXT, PDF, CSV, Excel).  
    2. Select a target language.  
    3. Click **Translate** to get the translation.  
    4. Click **Convert to Speech** to generate audio.
    5. Use the audio player to listen or **Download MP3**.
    6. Use **Clear All** to start over.
    """)
    
    st.header("📊 Session Info")
    if st.session_state.get('translation'):
        st.success("✅ Translation ready")
    if st.session_state.get('audio_file_path'):
        st.success("🔊 Audio ready")
        
    st.header("⚠️ Troubleshooting")
    st.markdown("""
    - If you get quota errors, wait 24 hours for reset
    - Audio requires internet connection
    - Large texts may take longer to process
    """)

# Input section
user_text = st.text_area("✍️ Enter text here:")

uploaded_file = st.file_uploader("📂 Or upload a file", type=["txt","pdf","csv","xlsx"])
if uploaded_file:
    file_text = extract_text_from_file(uploaded_file)
    user_text = file_text
    st.info("✅ Text extracted from file!")

langs = {
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Hausa": "ha",
    "Swahili": "sw",
    "English": "en"
}
target_lang = st.selectbox("🌐 Choose target language:", list(langs.keys()))

# Initialize session state
if 'translation' not in st.session_state:
    st.session_state.translation = None
if 'target_language' not in st.session_state:
    st.session_state.target_language = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None

if st.button("🚀 Translate"):
    if not user_text.strip():
        st.warning("Please enter or upload some text first.")
    else:
        with st.spinner('Translating...'):
            translation = translate_text(user_text, target_lang)
            st.session_state.translation = translation
            st.session_state.target_language = target_lang
            st.session_state.audio_file_path = None  # Reset audio file

# Display translation if available
if st.session_state.translation:
    if "❌" in st.session_state.translation:
        st.error(st.session_state.translation)
    else:
        st.success(f"**Translation in {st.session_state.target_language}:**\n\n{st.session_state.translation}")
        
        # Convert to Speech button (now outside the translate button)
        if st.button("🔊 Convert to Speech"):
            lang_code = langs[st.session_state.target_language]
            with st.spinner('Converting to speech...'):
                audio_file = text_to_speech(st.session_state.translation, lang_code)
                if audio_file:
                    st.session_state.audio_file_path = audio_file
                    st.success("✅ Audio generated successfully!")
        
        # Display audio player and download if audio file exists
        if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
            st.audio(st.session_state.audio_file_path, format="audio/mp3")
            
            # Download button
            with open(st.session_state.audio_file_path, "rb") as audio_file:
                st.download_button(
                    label="⬇️ Download MP3",
                    data=audio_file.read(),
                    file_name=f"translation_{st.session_state.target_language.lower()}.mp3",
                    mime="audio/mp3"
                )

# Clear button to reset everything
if st.button("🗑️ Clear All"):
    st.session_state.translation = None
    st.session_state.target_language = None
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.remove(st.session_state.audio_file_path)
        except:
            pass
    st.session_state.audio_file_path = None
    st.rerun()
