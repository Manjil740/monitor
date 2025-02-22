import instaloader
from dotenv import load_dotenv
import os
import requests
from discord.ext import commands, tasks
from flask import Flask
import time

# Load environment variables from .env file
load_dotenv()

# Get Instagram credentials and Discord bot token from environment variables
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Ensure that environment variables are loaded correctly
if not IG_USERNAME or not IG_PASSWORD or not DISCORD_TOKEN or not WEBHOOK_URL:
    print(
        "Missing one or more environment variables. Please check your .env file."
    )
    exit()

# Debugging: Check if IG_USERNAME is being correctly set
print(f"Instagram username loaded: {IG_USERNAME}")

# Create an Instaloader instance
L = instaloader.Instaloader()

# Explicit session file path
session_file = f"/home/runner/workspace/sessions/session-{IG_USERNAME}"


# Function to login and save session
def login_to_instagram():
    retries = 3
    while retries > 0:
        try:
            print(f"Attempting to load session from: {session_file}")
            L.load_session_from_file(session_file)  # Load session if it exists
            print("Session loaded successfully!")
            return
        except FileNotFoundError:
            print("No existing session found. Logging in with credentials...")
            try:
                L.login(IG_USERNAME, IG_PASSWORD)  # Login with credentials
                print("Logged in successfully!")
                L.save_session_to_file(
                    session_file)  # Save session for future use
                print("Session saved successfully!")
                return
            except instaloader.exceptions.LoginException as e:
                print(f"Login failed: {e}")
                retries -= 1
                time.sleep(5)  # Wait before retrying
            except Exception as e:
                print(f"Unexpected error during login: {e}")
                retries -= 1
                time.sleep(5)
    print("All login attempts failed. Exiting.")
    exit()


# Call the function to login
login_to_instagram()

# Discord bot setup
bot = commands.Bot(command_prefix="!", intents=commands.Intents.default())

# Monitoring Task
last_followers, last_following = None, None


@tasks.loop(minutes=10)
async def check_followers():
    global last_followers, last_following

    # Fetch Instagram profile data
    try:
        profile = instaloader.Profile.from_username(
            L.context, "queridaax")  # Account to be monitored
        followers = profile.followers
        following = profile.followees
    except Exception as e:
        print(f"Error fetching profile data: {e}")
        return

    # Send notifications when follower/following count changes
    if last_followers is not None and last_followers != followers:
        message = f"📢 {IG_USERNAME} follower count changed: {last_followers} ➝ {followers}"
        requests.post(WEBHOOK_URL, json={"content": message})

    if last_following is not None and last_following != following:
        message = f"📢 {IG_USERNAME} following count changed: {last_following} ➝ {following}"
        requests.post(WEBHOOK_URL, json={"content": message})

    # Update last_followers and last_following
    last_followers, last_following = followers, following


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    check_followers.start()


# Flask app to keep Replit running
app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is running 24/7!"


# Run the bot and Flask app
bot.loop.create_task(app.run_task("0.0.0.0", port=3000))

bot.run(DISCORD_TOKEN)
