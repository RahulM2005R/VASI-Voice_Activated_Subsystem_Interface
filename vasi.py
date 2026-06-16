"""
=============================================================================
VASI — Voice Activated Subsystem Interface  v3.3
=============================================================================
  ElevenLabs Voice + Groq AI Edition

  SETUP
  ─────
  pip install SpeechRecognition pyttsx3 pyaudio spacy
              groq send2trash pywin32 elevenlabs
              sounddevice soundfile

  python -m spacy download en_core_web_sm

  Fill in GROQ_API_KEY and ELEVENLABS_API_KEY below.
=============================================================================
"""

# =============================================================================
# SECTION 0 — IMPORTS
# =============================================================================

import os
import sys
import re
import io
import time
import shutil
import winreg
import subprocess
import multiprocessing
import threading
import datetime
import webbrowser
from pathlib import Path
from typing import Optional

import speech_recognition as sr
import pyttsx3

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    HAS_SPACY = True
except (ImportError, OSError):
    HAS_SPACY = False
    _nlp = None

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

try:
    import win32clipboard
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    from elevenlabs.client import ElevenLabs
    import sounddevice as sd
    import soundfile as sf
    HAS_ELEVENLABS_LIB = True
except ImportError:
    HAS_ELEVENLABS_LIB = False

def set_ui_state(state: str) -> None:
    """Write current state to file so the UI overlay can read it."""
    try:
        with open("vasi_state.txt", "w") as f:
            f.write(state)
    except Exception:
        pass
# =============================================================================
# SECTION 1 — CONFIGURATION
# =============================================================================

ELEVENLABS_API_KEY:  str = "sk_81e649fcb2ca8631a902431f72a94febed6997b813652458"
GROQ_API_KEY:        str = "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"

ELEVENLABS_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"
GROQ_MODEL:          str = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS:     int = 4096 

WAKE_WORD:     str = "hello"
NOTES_FILE:    str = "notes.txt"
IDLE_TIMEOUT:  int = 20
AI_MEMORY_LEN: int = 10

HOME      = Path.home()
DESKTOP   = HOME / "Desktop"
DOWNLOADS = HOME / "Downloads"
DOCUMENTS = HOME / "Documents"

SYSTEM_PROMPT = """
You are VASI — Voice Activated Subsystem Interface — a highly intelligent,
witty, and slightly sarcastic AI assistant running on the user's Windows PC.

Your personality:
- You are calm, confident, and precise — like Jarvis from Iron Man.
- You use dry humour occasionally but never at the user's expense.
- You address the user as "sir" when being formal.
- Never use filler words like "certainly!" or "absolutely!" or "Sure!".
- Keep responses CONCISE — you are a voice assistant, so no bullet lists,
  no markdown, no long paragraphs. Speak in natural flowing sentences.
- Maximum 3 sentences for most answers. Go longer only if truly needed.
- If asked to do something you cannot do, say so honestly.
- You have already handled PC control commands locally. This conversation
  is for everything else: questions, calculations, creative tasks, analysis,
  coding help, general conversation, etc.
- Always answer with the most current and accurate information you have.

Never start a response with "I", "Sure", "Of course", "Certainly", or "Absolutely".
"""


# =============================================================================
# SECTION 2 — MAPS
# =============================================================================

SETTINGS_MAP: dict[str, str] = {
    "wifi":              "ms-settings:network-wifi",
    "bluetooth":         "ms-settings:bluetooth",
    "display":           "ms-settings:display",
    "brightness":        "ms-settings:display",
    "sound":             "ms-settings:sound",
    "audio":             "ms-settings:sound",
    "notifications":     "ms-settings:notifications",
    "battery":           "ms-settings:batterysaver",
    "storage":           "ms-settings:storagesense",
    "apps":              "ms-settings:appsfeatures",
    "installed apps":    "ms-settings:appsfeatures",
    "startup":           "ms-settings:startupapps",
    "startup apps":      "ms-settings:startupapps",
    "privacy":           "ms-settings:privacy",
    "update":            "ms-settings:windowsupdate",
    "windows update":    "ms-settings:windowsupdate",
    "accounts":          "ms-settings:accounts",
    "language":          "ms-settings:regionlanguage",
    "region":            "ms-settings:regionlanguage",
    "mouse":             "ms-settings:mousetouchpad",
    "touchpad":          "ms-settings:mousetouchpad",
    "keyboard":          "ms-settings:typing",
    "camera":            "ms-settings:camera",
    "microphone":        "ms-settings:privacy-microphone",
    "vpn":               "ms-settings:network-vpn",
    "airplane mode":     "ms-settings:network-airplanemode",
    "theme":             "ms-settings:themes",
    "personalization":   "ms-settings:personalization",
    "wallpaper":         "ms-settings:personalization-background",
    "taskbar":           "ms-settings:taskbar",
    "default apps":      "ms-settings:defaultapps",
    "accessibility":     "ms-settings:easeofaccess",
    "developer":         "ms-settings:developers",
    "about":             "ms-settings:about",
    "date and time":     "ms-settings:dateandtime",
    "color":             "ms-settings:colors",
    "night light":       "ms-settings:nightlight",
    "focus":             "ms-settings:quiethours",
    "do not disturb":    "ms-settings:quiethours",
    "power":             "ms-settings:powersleep",
    "screen timeout":    "ms-settings:powersleep",
}

CONTROL_MAP: dict[str, str] = {
    "control panel":          "control",
    "programs":               "control appwiz.cpl",
    "uninstall":              "control appwiz.cpl",
    "add remove programs":    "control appwiz.cpl",
    "device manager":         "devmgmt.msc",
    "disk management":        "diskmgmt.msc",
    "task scheduler":         "taskschd.msc",
    "event viewer":           "eventvwr.msc",
    "services":               "services.msc",
    "registry editor":        "regedit",
    "registry":               "regedit",
    "firewall":                "firewall.cpl",
    "network connections":    "ncpa.cpl",
    "system properties":      "sysdm.cpl",
    "sound settings":         "mmsys.cpl",
    "user accounts":          "netplwiz",
    "credential manager":     "control /name Microsoft.CredentialManager",
    "power options":          "powercfg.cpl",
    "internet options":       "inetcpl.cpl",
    "mouse settings":         "main.cpl",
    "date and time":          "timedate.cpl",
    "region settings":        "intl.cpl",
    "troubleshoot":           "control /name Microsoft.Troubleshooting",
    "backup":                 "sdclt",
    "system restore":         "rstrui",
    "recovery":               "rstrui",
    "environment variables":  "rundll32 sysdm.cpl,EditEnvironmentVariables",
    "group policy":           "gpedit.msc",
    "local security":         "secpol.msc",
    "computer management":    "compmgmt.msc",
    "resource monitor":       "resmon",
    "performance monitor":    "perfmon",
    "task manager":           "taskmgr",
    "msconfig":               "msconfig",
    "directx":                "dxdiag",
    "disk cleanup":           "cleanmgr",
    "defragment":             "dfrgui",
    "character map":          "charmap",
    "snipping tool":          "snippingtool",
    "magnifier":              "magnify",
    "on screen keyboard":     "osk",
    "narrator":               "narrator",
    "paint":                  "mspaint",
    "wordpad":                "wordpad",
    "cmd":                    "cmd",
    "command prompt":         "cmd",
    "powershell":             "powershell",
    "windows terminal":       "wt",
    "file explorer":          "explorer",
    "this pc":                "explorer ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
    "recycle bin":            "explorer ::{645FF040-5081-101B-9F08-00AA002F954E}",
    "network":                "explorer ::{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}",
    "calculator":             "calc",
    "notepad":                "notepad",
    "sticky notes":           "stikynot",
}

WEBSITE_MAP: dict[str, str] = {
    "youtube":         "https://youtube.com",
    "google":          "https://google.com",
    "gmail":           "https://mail.google.com",
    "facebook":        "https://facebook.com",
    "instagram":       "https://instagram.com",
    "twitter":         "https://twitter.com",
    "x":               "https://x.com",
    "reddit":          "https://reddit.com",
    "github":          "https://github.com",
    "whatsapp":        "https://web.whatsapp.com",
    "netflix":         "https://netflix.com",
    "amazon":          "https://amazon.in",
    "flipkart":        "https://flipkart.com",
    "spotify":         "https://open.spotify.com",
    "chatgpt":         "https://chat.openai.com",
    "claude":          "https://claude.ai",
    "maps":            "https://maps.google.com",
    "google maps":     "https://maps.google.com",
    "drive":           "https://drive.google.com",
    "google drive":    "https://drive.google.com",
    "docs":            "https://docs.google.com",
    "sheets":          "https://sheets.google.com",
    "slides":          "https://slides.google.com",
    "translate":       "https://translate.google.com",
    "stack overflow":  "https://stackoverflow.com",
    "wikipedia":       "https://wikipedia.org",
    "linkedin":        "https://linkedin.com",
    "zoom":            "https://zoom.us",
    "meet":            "https://meet.google.com",
    "teams":           "https://teams.microsoft.com",
    "notion":          "https://notion.so",
    "figma":           "https://figma.com",
    "canva":           "https://canva.com",
    "twitch":          "https://twitch.tv",
    "prime":           "https://primevideo.com",
    "hotstar":         "https://hotstar.com",
    "jiocinema":       "https://jiocinema.com",
}

INTENT_VERBS: dict[str, set] = {
    "open":      {"open", "launch", "start", "run", "pull up", "load",
                  "bring up", "boot", "fire up", "show", "go to"},
    "close":     {"close", "kill", "shut", "exit", "quit", "end",
                  "terminate", "force quit"},
    "search":    {"search", "google", "find", "look up", "look for",
                  "browse", "check"},
    "delete":    {"delete", "remove", "trash", "get rid of", "erase",
                  "wipe", "destroy"},
    "create":    {"create", "make", "new", "build", "generate", "add"},
    "note":      {"note", "write", "jot", "save", "remember", "record"},
    "system":    {"shutdown", "restart", "reboot", "lock", "hibernate",
                  "sleep", "log off", "sign out", "turn off"},
    "volume":    {"mute", "unmute", "louder", "quieter", "volume"},
    "settings":  {"settings", "setting", "configure", "change", "adjust"},
    "ask":       {"what", "who", "where", "when", "why", "how", "tell",
                  "explain", "define", "describe", "calculate", "compute"},
    "greeting":  {"hello", "hi", "hey", "morning", "evening", "afternoon"},
    "exit_vasi": {"goodbye", "bye", "stop listening",
                  "shut yourself down", "turn yourself off"},
}

CLOSE_TRIGGERS = ("close", "kill", "terminate", "force quit")


# =============================================================================
# SECTION 3 — TTS ENGINE (ElevenLabs + pyttsx3 fallback)
# =============================================================================

def _build_tts() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    for v in voices:
        if any(n in v.name.lower() for n in ("david", "mark", "george")):
            engine.setProperty("voice", v.id)
            break
    else:
        if voices:
            engine.setProperty("voice", voices[0].id)
    return engine

_tts: pyttsx3.Engine = _build_tts()
HAS_ELEVENLABS = False
_el_client = None

if HAS_ELEVENLABS_LIB:
    try:
        _el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        _el_client.voices.get_all()
        HAS_ELEVENLABS = True
        print("  [TTS] ElevenLabs voice online — Adam.")
    except Exception as e:
        print(f"  [TTS] ElevenLabs unavailable: {e} — using pyttsx3.")
else:
    print("  [TTS] elevenlabs / sounddevice / soundfile not installed — using pyttsx3.")


def _play_audio(audio_generator) -> None:
    try:
        audio_bytes = b"".join(audio_generator)
        buf = io.BytesIO(audio_bytes)
        data, samplerate = sf.read(buf)
        sd.play(data, samplerate)
        sd.wait()
    except Exception as e:
        print(f"  [TTS] Playback error: {e} — falling back to pyttsx3.")
        raise


def _speak_elevenlabs(text: str) -> None:
    try:
        audio = _el_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_turbo_v2",
            output_format="mp3_44100_128",
            voice_settings={
                "stability":         0.55,
                "similarity_boost":  0.80,
                "style":             0.20,
                "use_speaker_boost": True,
            }
        )
        _play_audio(audio)
    except Exception as e:
        print(f"  [TTS] ElevenLabs error: {e} — falling back to pyttsx3.")
        _tts.say(text)
        _tts.runAndWait()

def speak(text: str) -> None:
    global _active_timer
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"`+",   "", text)
    text = text.strip()
    if not text:
        return
    print(f"\n  VASI > {text}")

    if _active_timer:
        _active_timer.pause()
    set_ui_state("speaking")        # ← tell UI we are speaking

    try:
        if HAS_ELEVENLABS:
            _speak_elevenlabs(text)
        else:
            _tts.say(text)
            _tts.runAndWait()
    finally:
        if _active_timer:
            _active_timer.resume()
        set_ui_state("listening")   # ← tell UI we are back to listening


# =============================================================================
# SECTION 4 — SPEECH RECOGNITION
# =============================================================================

def _build_recognizer() -> sr.Recognizer:
    r = sr.Recognizer()
    r.energy_threshold         = 300
    r.dynamic_energy_threshold = False
    r.pause_threshold          = 0.8
    return r

_rec: sr.Recognizer = _build_recognizer()


def listen_once(timeout: Optional[int] = None,
                phrase_limit: Optional[int] = 10) -> Optional[str]:
    with sr.Microphone() as src:
        _rec.adjust_for_ambient_noise(src, duration=0.3)
        try:
            audio = _rec.listen(src, timeout=timeout,
                                phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None
    try:
        return _rec.recognize_google(audio).lower().strip()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"  [STT ERROR] {e}")
        return None


# =============================================================================
# SECTION 5 — IDLE TIMER
# =============================================================================

_active_timer: Optional["IdleTimer"] = None


class IdleTimer:
    def __init__(self, timeout: int = IDLE_TIMEOUT) -> None:
        self._timeout = timeout
        self._last    = time.time()
        self._lock    = threading.Lock()
        self._paused  = False

    def reset(self) -> None:
        with self._lock:
            self._last = time.time()

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self._last   = time.time()

    def is_expired(self) -> bool:
        with self._lock:
            if self._paused:
                return False
            return (time.time() - self._last) >= self._timeout

    def remaining(self) -> float:
        with self._lock:
            if self._paused:
                return float(self._timeout)
            return max(0.0, self._timeout - (time.time() - self._last))


# =============================================================================
# SECTION 6 — NLP ENGINE
# =============================================================================

class NLPEngine:
    FILLERS = [
        r"^(can you|could you|would you|please|kindly|hey vasi|vasi)\s+",
        r"\s+(for me|please|now|quickly|right now|immediately)$",
        r"^(i want you to|i need you to|i want to|i need to)\s+",
        r"^(go ahead and|just|simply)\s+",
    ]

    def normalize(self, text: str) -> str:
        t = text.lower().strip()
        for pattern in self.FILLERS:
            t = re.sub(pattern, "", t, flags=re.IGNORECASE).strip()
        return t

    def intent(self, text: str) -> str:
        t = self.normalize(text)
        if HAS_SPACY and _nlp:
            doc = _nlp(t)
            for token in doc:
                lemma = token.lemma_.lower()
                for intent_name, verbs in INTENT_VERBS.items():
                    if lemma in verbs:
                        return intent_name
            for intent_name, verbs in INTENT_VERBS.items():
                for verb in verbs:
                    if " " in verb and verb in t:
                        return intent_name
        else:
            for intent_name, verbs in INTENT_VERBS.items():
                for verb in verbs:
                    if verb in t:
                        return intent_name
        return "unknown"

    def subject(self, text: str) -> str:
        t = self.normalize(text)
        for verbs in INTENT_VERBS.values():
            for verb in sorted(verbs, key=len, reverse=True):
                pattern = rf"^{re.escape(verb)}\s+"
                cleaned = re.sub(pattern, "", t, flags=re.IGNORECASE).strip()
                if cleaned != t:
                    t = cleaned
                    break
        t = re.sub(r"^(the|a|an|up|for|to|at|on|in)\s+", "", t).strip()
        t = re.sub(r"^(me |please )", "", t).strip()
        return t

    def extract_search_query(self, text: str) -> Optional[str]:
        patterns = [
            r"search(?:\s+\w+)?\s+for\s+(.+)",
            r"google\s+(.+)",
            r"look up\s+(.+)",
            r"find\s+(.+?)(?:\s+online|\s+on\s+\w+)?$",
            r"what is\s+(.+)",
            r"who is\s+(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def extract_rename_args(self, text: str) -> Optional[tuple]:
        m = re.search(r"rename (.+?) (?:to|as) (.+)", text, re.IGNORECASE)
        return (m.group(1).strip(), m.group(2).strip()) if m else None

    def extract_copy_move_args(self, text: str) -> Optional[tuple]:
        m = re.search(r"(?:copy|move) (.+?) (?:to|into) (.+)",
                      text, re.IGNORECASE)
        return (m.group(1).strip(), m.group(2).strip()) if m else None


_nlp_engine = NLPEngine()


def _is_conversational(cmd: str) -> bool:
    """
    Returns True if the command is complex/conversational and should go
    straight to Groq rather than local PC handlers.
    Never flags as conversational if a known app/site/system keyword is present.
    """
    LOCAL_ANCHORS = (
        # apps & tools
        "notepad", "chrome", "firefox", "edge", "explorer", "calculator",
        "paint", "word", "excel", "powerpoint", "outlook", "spotify",
        "discord", "steam", "vlc", "task manager", "cmd", "powershell",
        "terminal", "vs code", "vscode", "file explorer", "recycle bin",
        # websites
        "youtube", "google", "gmail", "instagram", "whatsapp", "netflix",
        "github", "reddit", "twitter", "facebook", "chatgpt",
        "claude", "drive", "maps", "notion", "figma", "canva",
        # system actions
        "shutdown", "restart", "lock", "hibernate", "log off", "sign out",
        "volume", "mute", "screenshot",
        # settings & control
        "wifi", "bluetooth", "display", "brightness", "battery", "settings",
        "control panel", "device manager", "registry", "firewall",
        # file ops
        "desktop", "downloads", "documents", "folder", "rename", "delete",
        "copy", "move",
    )
    if any(anchor in cmd for anchor in LOCAL_ANCHORS):
        return False

    words = cmd.strip().split()
    if len(words) <= 4:
        return False

    question_starters = (
        "what", "why", "how", "when", "who", "where",
        "can you", "could you", "tell me", "explain",
        "is there", "do you", "does", "will", "would",
    )
    if any(cmd.startswith(q) for q in question_starters):
        return True

    complex_markers = (
        " in ", " using ", " with ", " about ", " for ",
        " on ", " from ", " into ", " through ",
    )
    action_verbs = (
        "type", "write", "create", "generate", "make",
        "calculate", "code", "explain", "show", "help",
        "find", "give", "tell", "print", "display",
    )
    if any(m in cmd for m in complex_markers):
        if any(cmd.startswith(v) or f" {v} " in cmd for v in action_verbs):
            return True

    return False


# =============================================================================
# SECTION 7 — GROQ AI BRAIN
# =============================================================================

class GroqBrain:
    def __init__(self) -> None:
        self._ready   = False
        self._history: list[dict] = []
        self._client  = None

        if not HAS_GROQ:
            print("  [AI] groq package not installed. Run: pip install groq")
            return
        if GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
            print("  [AI] Groq API key not set.")
            return
        try:
            self._client = Groq(api_key=GROQ_API_KEY)
            self._client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            self._ready = True
            print(f"  [AI] Groq online — {GROQ_MODEL}")
        except Exception as e:
            print(f"  [AI] Groq unavailable: {e}")

    @property
    def ready(self) -> bool:
        return self._ready

    def ask(self, user_text: str, max_tokens: int = GROQ_MAX_TOKENS) -> str:
        if not self._ready or self._client is None:
            return "My AI brain is offline. Please check the API key."

        self._history.append({"role": "user", "content": user_text})
        if len(self._history) > AI_MEMORY_LEN * 2:
            self._history = self._history[-(AI_MEMORY_LEN * 2):]

        try:
            response = self._client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self._history
                ]
            )
            reply = response.choices[0].message.content.strip()
            self._history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            self._history.pop()
            return f"Neural link error: {e}"

    def clear_memory(self) -> None:
        self._history.clear()


_brain = GroqBrain()
# =============================================================================
# SECTION 8 — SYSTEM UTILITIES
# =============================================================================

def run(cmd: str, *, shell: bool = True) -> None:
    subprocess.Popen(cmd, shell=shell,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _resolve_path(raw: str) -> Optional[Path]:
    raw = raw.strip()
    p = Path(raw)
    if p.exists():
        return p
    for root in (DESKTOP, DOWNLOADS, DOCUMENTS, HOME):
        matches = list(root.glob(f"*{raw}*"))
        if matches:
            return matches[0]
    return None


def _start_menu_search(name: str) -> Optional[str]:
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) /
        "Microsoft/Windows/Start Menu/Programs",
        Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
    ]
    nl = name.lower()
    for base in start_dirs:
        if not base.exists():
            continue
        for lnk in base.rglob("*.lnk"):
            if nl in lnk.stem.lower():
                return str(lnk)
    return None


def _registry_search(name: str) -> Optional[str]:
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    nl = name.lower()
    for rp in reg_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rp)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub      = winreg.OpenKey(key, sub_name)
                    display  = winreg.QueryValueEx(sub, "DisplayName")[0]
                    if nl in display.lower():
                        try:
                            loc  = winreg.QueryValueEx(sub, "InstallLocation")[0]
                            exes = list(Path(loc).glob("*.exe"))
                            if exes:
                                return str(exes[0])
                        except FileNotFoundError:
                            pass
                        try:
                            icon = winreg.QueryValueEx(sub, "DisplayIcon")[0]
                            exe  = icon.split(",")[0].strip('"')
                            if exe.endswith(".exe") and Path(exe).exists():
                                return exe
                        except FileNotFoundError:
                            pass
                except (FileNotFoundError, OSError):
                    continue
        except (FileNotFoundError, OSError):
            continue
    return None


def _path_search(name: str) -> Optional[str]:
    return shutil.which(name) or shutil.which(name + ".exe")


def _deep_search(name: str) -> Optional[str]:
    roots = [
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path(os.environ.get("APPDATA", "")),
    ]
    nl = name.lower()
    for root in roots:
        if not root.exists():
            continue
        for exe in root.glob("**/*.exe"):
            try:
                if nl in exe.stem.lower():
                    return str(exe)
            except (OSError, PermissionError):
                continue
    return None


def find_app(name: str) -> Optional[str]:
    return (_start_menu_search(name)
            or _registry_search(name)
            or _path_search(name)
            or _deep_search(name))


# =============================================================================
# SECTION 9 — COMMAND HANDLERS
# =============================================================================

def handle_exit(cmd: str) -> bool:
    farewells = ("go to sleep", "goodbye", "good bye", "bye",
                 "stop listening", "terminate yourself",
                 "shut yourself down", "turn yourself off")
    return any(f in cmd for f in farewells)


def handle_greeting(cmd: str) -> bool:
    greetings = ("good morning", "good afternoon", "good evening",
                 "what's up", "howdy")
    is_hello_only = cmd.strip() in (
        "hello", "hello vasi", "hey vasi", "hi vasi",
        "hi", "hey", "morning", "evening", "afternoon",
    )
    matched = is_hello_only or any(cmd.strip() == g for g in greetings)
    if not matched:
        return False
    hour = datetime.datetime.now().hour
    tg   = ("Good morning" if hour < 12
            else "Good afternoon" if hour < 17 else "Good evening")
    speak(f"{tg}. VASI online. What do you need?")
    return True


def handle_meta(cmd: str) -> bool:
    if "who are you" in cmd or "what are you" in cmd:
        speak("VASI — Voice Activated Subsystem Interface. "
              "Your personal Jarvis, sir.")
        return True
    if "what can you do" in cmd or "your capabilities" in cmd:
        speak("I can open apps, websites and Windows settings, "
              "manage files, control your system, take notes, "
              "search the web, and hold a full conversation.")
        return True
    if "how are you" in cmd:
        speak("All systems nominal, sir.")
        return True
    if "clear memory" in cmd or "forget everything" in cmd:
        _brain.clear_memory()
        speak("Memory cleared. Fresh start.")
        return True
    return False


def handle_time_date(cmd: str) -> bool:
    if "time" in cmd and "date" not in cmd and "timer" not in cmd:
        t = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"It is {t}, sir.")
        return True
    if "date" in cmd or "what day" in cmd or "day is it" in cmd:
        d = datetime.datetime.now().strftime("%A, %B %d, %Y")
        speak(f"Today is {d}.")
        return True
    return False


def handle_settings(cmd: str) -> bool:
    if any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    norm = _nlp_engine.normalize(cmd)
    opening_words = ("open", "show", "launch", "go to", "settings",
                     "configure", "change", "adjust")
    if not any(w in norm for w in opening_words):
        return False
    matched_uri = ""
    matched_key = ""
    for key, uri in SETTINGS_MAP.items():
        if key in norm and len(key) > len(matched_key):
            matched_uri = uri
            matched_key = key
    if not matched_uri:
        return False
    speak(f"Opening {matched_key} settings.")
    run(f'start "" "{matched_uri}"')
    return True


def handle_control(cmd: str) -> bool:
    if any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    norm = _nlp_engine.normalize(cmd)
    matched_cmd = ""
    matched_key = ""
    for key, win_cmd in CONTROL_MAP.items():
        if key in norm and len(key) > len(matched_key):
            matched_cmd = win_cmd
            matched_key = key
    if not matched_cmd:
        return False
    speak(f"Opening {matched_key}.")
    run(matched_cmd)
    return True


def handle_system(cmd: str) -> bool:
    if any(x in cmd for x in ("shut down", "shutdown", "turn off the pc",
                               "turn off my pc", "turn off computer")):
        speak("Shutting down in 10 seconds. Say cancel to abort.")
        confirm = listen_once(timeout=7)
        if confirm and "cancel" in confirm:
            run("shutdown /a")
            speak("Shutdown cancelled.")
        else:
            speak("Initiating shutdown. Goodbye, sir.")
            run("shutdown /s /t 10")
        return True
    if any(x in cmd for x in ("restart", "reboot")):
        speak("Restarting in 10 seconds.")
        run("shutdown /r /t 10")
        return True
    if "lock" in cmd and any(x in cmd for x in ("screen", "pc", "computer")):
        speak("Locking the workstation.")
        run("rundll32.exe user32.dll,LockWorkStation")
        return True
    if "hibernate" in cmd:
        speak("Sending the system into hibernation.")
        run("shutdown /h")
        return True
    if "log off" in cmd or "sign out" in cmd:
        speak("Signing you out.")
        run("shutdown /l")
        return True
    if "empty recycle bin" in cmd or "clear recycle bin" in cmd:
        speak("Emptying the Recycle Bin.")
        run("PowerShell -Command Clear-RecycleBin -Force")
        return True
    if "screenshot" in cmd:
        speak("Opening Snipping Tool.")
        run("snippingtool")
        return True
    if "volume up" in cmd or "increase volume" in cmd or "louder" in cmd:
        _set_volume("up");   return True
    if "volume down" in cmd or "decrease volume" in cmd or "quieter" in cmd:
        _set_volume("down"); return True
    if "mute" in cmd:
        _set_volume("mute"); return True
    return False


def _set_volume(direction: str) -> None:
    nircmd = shutil.which("nircmd") or shutil.which("nircmd.exe")
    if nircmd:
        mapping = {
            "up":   f'"{nircmd}" changesysvolume 5000',
            "down": f'"{nircmd}" changesysvolume -5000',
            "mute": f'"{nircmd}" mutesysvolume 2',
        }
        run(mapping.get(direction, ""))
    else:
        key_map = {"mute": 173, "up": 175, "down": 174}
        k       = key_map.get(direction, 0)
        repeats = 1 if direction == "mute" else 5
        for _ in range(repeats):
            run(f'PowerShell -Command '
                f'"(New-Object -ComObject WScript.Shell)'
                f'.SendKeys([char]{k})"')
    speak(f"Volume {direction}.")


def handle_search(cmd: str) -> bool:
    if any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    if _nlp_engine.intent(cmd) != "search":
        return False
    query = _nlp_engine.extract_search_query(cmd) or _nlp_engine.subject(cmd)
    if not query:
        speak("What would you like me to search for?")
        query = listen_once(timeout=8) or ""
    speak(f"Searching for {query}.")
    webbrowser.open(
        f"https://www.google.com/search?q={query.replace(' ', '+')}")
    return True


def handle_close(cmd: str) -> bool:
    if not any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    target = _nlp_engine.subject(cmd)
    if not target:
        return False
    for t in CLOSE_TRIGGERS:
        target = target.replace(t, "").strip()
    if not target:
        return False
    attempts = [
        target.replace(" ", "") + ".exe",
        target.split()[0] + ".exe" if target.split() else "",
        target.replace(" ", ""),
    ]
    for proc in attempts:
        if not proc:
            continue
        result = subprocess.run(
            f'taskkill /F /IM "{proc}"',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            speak(f"Closed {target}.")
            return True
    speak(f"No running process found called {target}.")
    return True
def handle_generate_and_note(cmd: str) -> bool:
    """
    Catches commands like:
    - 'give me the code for X and note it down'
    - 'i need the code for X and write it in notepad'
    - 'get me X and save it'
    - 'generate X and put it in notepad'
    """
    generate_triggers = (
        "note it down", "note this down", "write it down",
        "save it", "put it in notepad", "write it in notepad",
        "type it in notepad", "save it in notepad",
        "jot it down", "note it", "save it to notepad",
        "write in notepad", "put in notepad",
    )
    action_triggers = (
        "i need", "give me", "get me", "generate",
        "what is", "show me", "write me", "create",
        "code for", "code to", "program for", "program to",
        "script for", "script to", "function for", "function to",
        "example of", "example for", "how to", "way to",
        "syntax for", "syntax of",
    )

    has_save = any(t in cmd for t in generate_triggers)
    if not has_save:
        return False

    has_generate = any(t in cmd for t in action_triggers) or len(cmd.split()) > 5
    if not has_generate:
        return False

    # Strip out ALL save-related phrases to isolate the content request
    content_request = cmd
    for t in sorted(generate_triggers, key=len, reverse=True):
        content_request = content_request.replace(t, "").strip()

    # Clean up leftover conjunctions and filler
    content_request = re.sub(
        r"\b(and|please|also|then|just|can you|could you)\b",
        " ", content_request, flags=re.IGNORECASE
    ).strip()
    content_request = re.sub(r"\s{2,}", " ", content_request).strip()

    if not content_request or len(content_request) < 3:
        speak("What would you like me to generate?")
        return True

    speak("Generating the full code and saving it to notepad, sir.")

    # Use a stricter prompt and full token budget so nothing gets cut off
    generated = _brain.ask(
        f"Write the complete and full code for: {content_request}. "
        f"Rules: output ONLY the raw code, no explanation before or after, "
        f"no markdown, no code fences, no backticks. "
        f"Do NOT truncate or summarise. Write every single line. "
        f"The output must be complete and ready to copy and run.",
        max_tokens=4096
    )

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{ts}]\n{content_request}\n{'='*50}\n{generated}\n")
    except OSError as e:
        speak("Could not save to notes file.")
        print(f"  [ERROR] {e}")
        return True

    try:
        os.startfile(NOTES_FILE)
    except OSError:
        run("notepad")

    speak("Done, sir. Full code saved and opened in notepad.")
    return True

def handle_note(cmd: str) -> bool:
    triggers = ("note down", "write this down", "take a note", "make a note",
                 "add a note", "remember this", "save this", "jot down",
                 "note this", "note that")
    triggered   = any(t in cmd for t in triggers)
    bare_note   = re.match(r"^note\s+(.+)$", cmd.strip())
    intent_note = _nlp_engine.intent(cmd) == "note"
    if not (triggered or bare_note or intent_note):
        return False
    note_text = cmd.strip()
    for t in sorted(triggers, key=len, reverse=True):
        if t in note_text:
            note_text = note_text.replace(t, "").strip()
            break
    note_text = re.sub(r"^note\s+", "", note_text, flags=re.IGNORECASE).strip()
    note_text = re.sub(
        r"^(that|the following|this|down|:)\s*", "", note_text).strip()
    if not note_text or len(note_text) < 2:
        speak("What would you like me to note down?")
        note_text = listen_once(timeout=10, phrase_limit=30) or ""
        if not note_text:
            speak("Nothing heard. Note not saved.")
            return True
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{ts}]\n{note_text}\n")
        speak("Noted, sir.")
        try:
            os.startfile(NOTES_FILE)
        except OSError:
            pass
    except OSError as e:
        speak("File error. Could not save the note.")
        print(f"  [ERROR] {e}")
    return True


def handle_file_ops(cmd: str) -> bool:
    if any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    intent = _nlp_engine.intent(cmd)

    if intent == "delete":
        raw  = _nlp_engine.subject(cmd)
        path = _resolve_path(raw)
        if not path:
            speak(f"Cannot find anything called {raw}.")
            return True
        speak(f"Delete {path.name}? Say yes to confirm.")
        confirm = listen_once(timeout=7)
        if confirm and "yes" in confirm:
            if HAS_SEND2TRASH:
                send2trash.send2trash(str(path))
                speak(f"{path.name} moved to Recycle Bin.")
            else:
                shutil.rmtree(path) if path.is_dir() else path.unlink()
                speak(f"{path.name} permanently deleted.")
        else:
            speak("Deletion cancelled.")
        return True

    if intent == "create" and ("folder" in cmd or "directory" in cmd):
        name = _nlp_engine.subject(cmd)
        name = re.sub(r"\b(folder|directory|called|named)\b", "",
                      name).strip()
        if not name:
            speak("What should I name the folder?")
            name = listen_once(timeout=8) or ""
        if name:
            (DESKTOP / name).mkdir(parents=True, exist_ok=True)
            speak(f"Folder {name} created on your Desktop.")
        else:
            speak("No name provided.")
        return True

    if "rename" in cmd:
        args = _nlp_engine.extract_rename_args(cmd)
        if args:
            old_path = _resolve_path(args[0])
            if old_path:
                old_path.rename(old_path.parent / args[1])
                speak(f"Renamed to {args[1]}.")
            else:
                speak(f"Could not find {args[0]}.")
        return True

    if "copy" in cmd and " to " in cmd:
        args = _nlp_engine.extract_copy_move_args(cmd)
        if args:
            src = _resolve_path(args[0])
            dst = Path(args[1]) if Path(args[1]).is_absolute() \
                  else DESKTOP / args[1]
            if src:
                shutil.copytree(str(src), str(dst)) if src.is_dir() \
                    else shutil.copy2(str(src), str(dst))
                speak(f"Copied {src.name}.")
            else:
                speak(f"Source not found: {args[0]}.")
        return True

    if "move" in cmd and " to " in cmd:
        args = _nlp_move_args(cmd) # type: ignore
        if args:
            src = _resolve_path(args[0])
            dst = Path(args[1]) if Path(args[1]).is_absolute() \
                  else DESKTOP / args[1]
            if src:
                shutil.move(str(src), str(dst))
                speak(f"Moved {src.name}.")
            else:
                speak(f"Source not found: {args[0]}.")
        return True

    return False


def handle_clipboard(cmd: str) -> bool:
    if not (cmd.startswith("copy ") and " to " not in cmd):
        return False
    text = cmd.replace("copy ", "", 1).strip()
    if HAS_WIN32:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
        win32clipboard.CloseClipboard()
    else:
        run(f"PowerShell -Command \"Set-Clipboard -Value '{text}'\"")
    speak("Copied to clipboard.")
    return True


def handle_uninstall(cmd: str) -> bool:
    triggers = ("uninstall", "remove program", "remove software",
                 "programs and features", "add or remove")
    if not any(t in cmd for t in triggers):
        return False
    speak("Opening Programs and Features.")
    run("control appwiz.cpl")
    return True


def _type_into_active_window(text: str) -> None:
    try:
        import win32gui
        time.sleep(0.5)
        hwnd = win32gui.GetForegroundWindow()
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
    except Exception:
        pass
    safe = text.replace("'", "''").replace("\n", "`n").replace('"', '`"')
    script = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.SendKeys]::SendWait('{safe}')"
    )
    run(f'powershell -Command "{script}"')


def handle_open(cmd: str) -> bool:
    if any(t in cmd for t in CLOSE_TRIGGERS):
        return False
    if _nlp_engine.intent(cmd) != "open":
        return False

    target = _nlp_engine.subject(cmd)
    if not target:
        return False

    # ── "type/write X in <app>" pattern ──────────────────────────────────
    type_match = re.search(
        r"^(?:type|write|put|enter)\s+(.+?)\s+(?:in|into|on)\s+(\w[\w\s]*)$",
        cmd.strip(), re.IGNORECASE
    )
    if type_match:
        content_raw = type_match.group(1).strip()
        app_name    = type_match.group(2).strip().lower()

        speak(f"Generating content and opening {app_name}.")
        generated = _brain.ask(
            f"Give me only the raw output for: {content_raw}. "
            f"No explanation, no markdown, no code fences. "
            f"Just the plain text or code itself."
        )

        app_path = find_app(app_name)
        if app_path:
            try:
                os.startfile(app_path)
            except OSError:
                run(f'"{app_path}"')
        else:
            run(app_name)

        time.sleep(2.5)
        _type_into_active_window(generated)
        speak("Done, sir.")
        return True

    # ── normal open logic ─────────────────────────────────────────────────
    for site, url in WEBSITE_MAP.items():
        if site in target or target in site:
            speak(f"Opening {site}.")
            webbrowser.open(url)
            return True

    for key, uri in SETTINGS_MAP.items():
        if key in target:
            speak(f"Opening {key} settings.")
            run(f'start "" "{uri}"')
            return True

    for key, win_cmd in CONTROL_MAP.items():
        if key in target:
            speak(f"Opening {key}.")
            run(win_cmd)
            return True

    speak(f"Searching for {target} on your system.")
    app_path = find_app(target)
    if app_path:
        speak(f"Launching {target}.")
        try:
            os.startfile(app_path)
        except OSError:
            run(f'"{app_path}"')
        return True

    try:
        os.startfile(target)
        speak(f"Opening {target}.")
    except (OSError, FileNotFoundError):
        speak(f"Could not locate {target} on this system.")
    return True


def handle_ai(cmd: str) -> bool:
    print("  [AI] Routing to Groq…")
    speak(_brain.ask(cmd))
    return True


# =============================================================================
# SECTION 10 — ACTIVE LOOP
# =============================================================================

HANDLERS = [
    handle_meta,
    handle_greeting,
    handle_time_date,
    handle_system,
    handle_settings,
    handle_control,
    handle_search,
    handle_generate_and_note,   # ← new, must be before handle_note
    handle_note,
    handle_file_ops,
    handle_clipboard,
    handle_uninstall,
    handle_close,
    handle_open,
    handle_ai,
]
def active_loop() -> None:
    global _active_timer
    timer         = IdleTimer(timeout=IDLE_TIMEOUT)
    _active_timer = timer

    speak("Online. At your command, sir.")
    set_ui_state("listening")       # ← set listening state when active

    while True:
        if timer.is_expired():
            speak("Going passive. Say hello when you need me.")
            _active_timer = None
            set_ui_state("passive") # ← set passive when timing out
            return

        remaining = int(timer.remaining())
        print(f"  Listening... [{remaining}s]          ", end="\r")
        command: Optional[str] = listen_once(timeout=3, phrase_limit=20)

        if not command:
            continue

        timer.reset()
        print(f"\n  You > {command}")

        if handle_exit(command):
            speak("Shutting down. It has been a pleasure, sir.")
            _active_timer = None
            set_ui_state("passive")
            sys.exit(0)

        for handler in HANDLERS:
            try:
                if handler is not handle_ai and _is_conversational(command):
                    continue
                if handler(command):
                    break
            except Exception as exc:
                print(f"  [ERROR in {handler.__name__}] {exc}")
                speak("An error occurred. Please try again.")
                break
# =============================================================================
# SECTION 11 — PASSIVE LOOP
# =============================================================================

def passive_loop() -> None:
    set_ui_state("passive")         # ← already in your code, keep it
    print(f"\n  --- PASSIVE  |  Say '{WAKE_WORD.upper()}' to activate ---\n")
    while True:
        heard: Optional[str] = listen_once(timeout=None, phrase_limit=4)
        if heard and WAKE_WORD in heard:
            print(f"\n  Wake word detected: '{heard}'")
            active_loop()
# =============================================================================
# SECTION 12 — ENTRY POINT
# =============================================================================

def run_ui() -> None:
    """Runs the Jarvis UI overlay in a separate process."""
    try:
        import tkinter as tk
        from ui import VASIOverlay
        root = tk.Tk()
        app  = VASIOverlay(root)
        root.mainloop()
    except Exception as e:
        print(f"  [UI] Failed to start overlay: {e}")


def main() -> None:
    print("=" * 60)
    print("  VASI — Voice Activated Subsystem Interface  v3.3")
    print("  ElevenLabs Adam Voice + Groq AI Edition")
    print("=" * 60)
    print(f"  Wake word    : '{WAKE_WORD.upper()}'")
    print(f"  Idle timeout : {IDLE_TIMEOUT}s")
    print(f"  Notes file   : {os.path.abspath(NOTES_FILE)}")
    print(f"  spaCy NLP    : {'YES' if HAS_SPACY else 'NO'}")
    print(f"  ElevenLabs   : {'YES — Adam voice' if HAS_ELEVENLABS else 'NO — pyttsx3 fallback'}")
    ai_label = f"YES — {GROQ_MODEL}" if _brain.ready else "NO"
    print(f"  Groq AI      : {ai_label}")
    print(f"  send2trash   : {'YES' if HAS_SEND2TRASH else 'NO'}")
    print(f"  pywin32      : {'YES' if HAS_WIN32 else 'NO'}")
    print("=" * 60)

    # ── Launch UI overlay in separate process ─────────────────────────────
    ui_process = multiprocessing.Process(target=run_ui, daemon=True)
    ui_process.start()
    print("  [UI] Overlay launched.")

    speak("VASI version 3.3 initialised. "
          + ("Voice core active." if HAS_ELEVENLABS else "Using system voice.")
          + f" Say {WAKE_WORD} to begin.")

    try:
        passive_loop()
    except KeyboardInterrupt:
        speak("Interrupt received. Shutting down.")
        ui_process.terminate()
        sys.exit(0)
    except Exception as exc:
        print(f"\n  [FATAL] {exc}")
        speak("Critical fault. Shutting down.")
        ui_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()   # required on Windows
    main()