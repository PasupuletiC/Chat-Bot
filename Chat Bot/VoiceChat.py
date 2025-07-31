import speech_recognition as sr
import webbrowser
import pyttsx3
import datetime
import wikipedia
import platform
import random
import os
import requests
import time
import json
import sys
from playsound import playsound
import threading

# ---- Text-to-Speech Engine ----
try:
    engine = pyttsx3.init()
except (ImportError, RuntimeError):
    print("Failed to initialize pyttsx3. Please ensure it is installed and that you have the necessary speech drivers.")
    sys.exit()

# --- Voice and Rate Customization ---
voices = engine.getProperty('voices')
# You can select a different voice here if you have multiple installed
# engine.setProperty('voice', voices[1].id)
engine.setProperty('rate', 180)

# ---- Global Variables & Configuration ----
memory = {}
command_log_path = "commands.log"
is_awake = threading.Event()  # Use a threading event for clearer wake/sleep state

# Easily add or change websites here
common_websites = {
    'youtube': 'https://www.youtube.com',
    'google': 'https://www.google.com',
    'wikipedia': 'https://www.wikipedia.org',
    'facebook': 'https://www.facebook.com',
    'twitter': 'https://www.twitter.com',
    'instagram': 'https://www.instagram.com',
    'gmail': 'https://mail.google.com',
    'whatsapp': 'https://web.whatsapp.com'
}

# IMPORTANT: Replace with your OpenWeatherMap and News API keys
WEATHER_API_KEY = "22b6d2b4cbdcd21b09a1cf2a6eefe745"  # Get a free key from openweathermap.org
NEWS_API_KEY = "a6d6cb2a7266432d8b5b770fc7c50ea3"       # Get a free key from newsapi.org

# --- IMPORTANT: Update these paths to your actual sound files ---
# Download short .wav or .mp3 files for these.
# A good place to find free sounds is freesound.org
start_sound = 'path/to/start_listening.wav' # Plays when Ruby wakes up
stop_sound = 'path/to/stop_listening.wav'   # Plays when Ruby goes to sleep

# ---- Core Voice Functions ----

def speak(text):
    """Converts text to speech and prints it."""
    print(f"Ruby: {text}")
    engine.say(text)
    engine.runAndWait()

def listen():
    """Listens for a command and converts it to text."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for a command...")
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            command = r.recognize_google(audio)
            print(f"You said: {command}")
            return command.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            speak(f"There was an issue with the speech recognition service; {e}")
            return None
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print(e)
            return None

def background_listener_callback(recognizer, audio):
    """Listens for the wake word in the background."""
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"Background: Heard '{command}'")
        if "hey ruby" in command and not is_awake.is_set():
            print("Wake word detected!")
            is_awake.set()  # Signal the main loop to wake up
    except (sr.UnknownValueError, sr.RequestError):
        pass

# ---- Command Handling Functions ----

def open_website(command):
    """Opens a website from a predefined list or by searching."""
    for name, url in common_websites.items():
        if name in command:
            speak(f"Certainly, opening {name}.")
            webbrowser.open(url)
            return
    speak("Which website should I open?")
    site = listen()
    if site:
        for name, url in common_websites.items():
            if name in site:
                speak(f"Got it, opening {name}.")
                webbrowser.open(url)
                return
        speak(f"I couldn't find that in my list, so I'll search for {site} on Google.")
        webbrowser.open(f"https://www.google.com/search?q={site}")

def tell_time(_):
    """Tells the current time."""
    time_now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"It is currently {time_now}.")

def tell_day(_):
    """Tells the current day of the week."""
    today = datetime.date.today().strftime('%A')
    speak(f"Today is {today}.")

def search_wikipedia(command):
    """Searches Wikipedia and provides a summary."""
    query = command.replace('wikipedia', '').replace('who is', '').replace('what is', '').strip()
    if not query:
        speak("What would you like me to look up on Wikipedia?")
        query = listen()
    if query:
        try:
            speak(f"Searching Wikipedia for {query}.")
            summary = wikipedia.summary(query, sentences=2, auto_suggest=False)
            speak(summary)
        except wikipedia.exceptions.PageError:
            speak(f"I'm sorry, I couldn't find a Wikipedia page for {query}.")
        except wikipedia.exceptions.DisambiguationError as e:
            speak(f"{query} could refer to multiple things. For example: {', '.join(e.options[:3])}.")
        except Exception as e:
            print(f"Wikipedia Error: {e}")
            speak("Sorry, I was unable to retrieve information from Wikipedia.")

def get_weather(_):
    """Fetches and reports the weather."""
    if WEATHER_API_KEY == "YOUR_WEATHER_API_KEY":
        speak("The weather service is not configured. Please add an API key.")
        return
    city = memory.get('last_city')
    if not city:
        speak("Of course, for which city?")
        city = listen()
    if city:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            speak(f"The current weather in {city} is {description} with a temperature of {temperature:.0f} degrees Celsius.")
            memory['last_city'] = city
        except requests.exceptions.HTTPError:
            speak("I'm sorry, I could not find that city. Please check the spelling.")
            memory.pop('last_city', None) # Remove invalid city
        except requests.exceptions.RequestException:
            speak("I was unable to connect to the weather service.")

def get_news(_):
    """Fetches and reads top news headlines."""
    if NEWS_API_KEY == "YOUR_NEWS_API_KEY":
        speak("The news service is not configured. Please add a News API key.")
        return
    try:
        speak("Fetching the latest news headlines.")
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        if not articles:
            speak("I couldn't find any news at the moment.")
            return
        speak("Here are the top headlines:")
        for article in articles[:3]:
            speak(article['title'])
    except requests.exceptions.RequestException as e:
        speak(f"Sorry, I couldn't connect to the news service. {e}")
    except Exception as e:
        speak(f"An error occurred while fetching the news: {e}")

def play_music(_):
    """Plays a random song from the Music folder."""
    music_folder = os.path.join(os.path.expanduser("~"), "Music")
    if not os.path.isdir(music_folder):
        speak("I could not find a 'Music' folder in your home directory.")
        return
    try:
        songs = [f for f in os.listdir(music_folder) if f.lower().endswith(('.mp3', '.wav', '.flac'))]
        if songs:
            song = random.choice(songs)
            song_path = os.path.join(music_folder, song)
            speak(f"Now playing {os.path.splitext(song)[0]}.")
            if platform.system() == "Windows":
                os.startfile(song_path)
            else:
                os.system(f'open "{song_path}"' if platform.system() == "Darwin" else f'xdg-open "{song_path}"')
        else:
            speak("I couldn't find any music files in your Music folder.")
    except Exception as e:
        print(e)
        speak("I encountered an error trying to play music.")

def open_application(command):
    """Opens a system application."""
    app_name = command.replace("open", "").strip()
    speak(f"Trying to open {app_name}.")
    try:
        if platform.system() == "Windows":
            if "calculator" in app_name:
                os.system("start calc")
            elif "notepad" in app_name or "text editor" in app_name:
                os.system("start notepad")
            else:
                speak(f"I don't know how to open {app_name} on Windows.")
        elif platform.system() == "Darwin":  # macOS
            if "calculator" in app_name:
                os.system("open -a Calculator")
            elif "textedit" in app_name or "text editor" in app_name:
                os.system("open -a TextEdit")
            else:
                speak(f"I don't know how to open {app_name} on macOS.")
        else:  # Linux
            if "calculator" in app_name:
                os.system("gnome-calculator")
            elif "text editor" in app_name:
                os.system("gedit")
            else:
                speak(f"I don't know how to open {app_name} on Linux.")
    except Exception as e:
        speak(f"I couldn't open {app_name}. Error: {e}")


def remember_name(command):
    """Remembers the user's name."""
    if "my name is" in command:
        name = command.split("my name is")[-1].strip()
        memory["name"] = name
        speak(f"It's a pleasure to meet you, {name}. I'll remember that.")

def greet_user(_):
    """Greets the user based on the time of day."""
    name = memory.get("name", "friend")
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12: greeting = "Good morning"
    elif 12 <= hour < 18: greeting = "Good afternoon"
    else: greeting = "Good evening"
    speak(f"{greeting}, {name}! How can I help you?")

def small_talk(command):
    """Handles simple conversational phrases."""
    if "how are you" in command:
        speak("I'm operating at full capacity! Thanks for asking.")
    elif "who are you" in command:
        speak("I am Ruby, a voice assistant created to help you with your tasks.")
    elif "thank you" in command or "thanks" in command:
        speak("You're welcome!")
    elif "joke" in command:
        try:
            res = requests.get("https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&type=single")
            res.raise_for_status()
            joke = res.json().get('joke')
            if joke: speak(joke)
            else: raise ValueError("No joke found")
        except:
            speak("Why don't scientists trust atoms? Because they make up everything!")

def go_to_sleep(_):
    """Puts Ruby back into background listening mode."""
    speak("Okay, going back to sleep. Just say 'Hey Ruby' if you need me again.")
    return "SLEEP"  # Special return value to signal the active loop to break

def system_action(command):
    """Performs system actions like shutdown or restart."""
    if "shutdown" in command:
        speak("Are you sure you want to shut down your computer?")
        response = listen()
        if response and "yes" in response:
            speak("Shutting down.")
            os.system("shutdown /s /t 1")
        else:
            speak("Shutdown cancelled.")
    elif "restart" in command:
        speak("Are you sure you want to restart your computer?")
        response = listen()
        if response and "yes" in response:
            speak("Restarting.")
            os.system("shutdown /r /t 1")
        else:
            speak("Restart cancelled.")

def stop_bot(_):
    """Stops the voice assistant entirely."""
    speak("Shutting down. Goodbye!")
    raise KeyboardInterrupt

def log_command(command):
    """Logs the executed command with a timestamp."""
    with open(command_log_path, "a") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} - {command}\n")

# ---- Command Mapping ----
commands = [
    # System & Core
    {'keywords': ['exit', 'shut down assistant', 'goodbye ruby'], 'function': stop_bot},
    {'keywords': ['go to sleep', 'stop listening', "that's all"], 'function': go_to_sleep},
    {'keywords': ['hello', 'hi'], 'function': greet_user},
    # Information
    {'keywords': ['time'], 'function': tell_time},
    {'keywords': ['day'], 'function': tell_day},
    {'keywords': ['wikipedia', 'who is', 'what is'], 'function': search_wikipedia},
    {'keywords': ['weather'], 'function': get_weather},
    {'keywords': ['news', 'headlines'], 'function': get_news},
    # Actions
    {'keywords': ['open website', 'go to'] + list(common_websites.keys()), 'function': open_website},
    {'keywords': ['open application', 'launch'], 'function': open_application},
    {'keywords': ['play music', 'start music'], 'function': play_music},
    {'keywords': ['shutdown computer', 'restart computer'], 'function': system_action},
    # Personalization & Conversation
    {'keywords': ['my name is'], 'function': remember_name},
    {'keywords': ['how are you', 'who are you', 'thank you', 'thanks', 'joke'], 'function': small_talk},
]

def handle_command(command):
    """Matches command to function and returns any special signals."""
    if not command:
        speak("I didn't catch that. Could you please repeat?")
        return None

    log_command(command)

    for cmd in commands:
        if any(keyword in command for keyword in cmd['keywords']):
            return cmd['function'](command)

    speak(f"I'm not sure how to handle that. Would you like me to search Google for '{command}'?")
    response = listen()
    if response and 'yes' in response:
        webbrowser.open(f"https://www.google.com/search?q={command}")
        speak(f"Here is what I found on Google for {command}.")
    else:
        speak("Okay, I won't search.")
    return None

def active_mode():
    """The main loop for when Ruby is awake and continuously listening for commands."""
    if os.path.exists(start_sound):
        playsound(start_sound, block=False)
    greet_user(None)

    while True:
        command = listen()
        if command:
            result = handle_command(command)
            if result == "SLEEP":
                break  # Exit the continuous loop and go back to sleep
    
    if os.path.exists(stop_sound):
        playsound(stop_sound, block=False)
    print("Returning to background listening mode.")

# ---- Main Execution ----
if __name__ == "__main__":
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    if not os.path.exists(start_sound) or not os.path.exists(stop_sound):
        print("Warning: Start/stop sound files not found. Please update the paths.")
        
    speak("Hello, I'm Ruby. I'm now listening for the wake word 'hey ruby'.")
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        
    stop_listening = recognizer.listen_in_background(microphone, background_listener_callback, phrase_time_limit=3)
    
    print("Background listener is active. Say 'Hey Ruby' to issue a command.")
    
    try:
        while True:
            is_awake.wait()  # Wait here until 'hey ruby' is heard
            active_mode()  # Enter the continuous command mode
            is_awake.clear()  # Go back to waiting for the event
    except KeyboardInterrupt:
        print("\nShutting down assistant.")
    finally:
        stop_listening(wait_for_stop=False)
        print("Goodbye!")