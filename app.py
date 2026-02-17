from flask import Flask, render_template, request, jsonify
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from groq import Groq
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import threading
import atexit

# PIL imports for image generation
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL (Pillow) not installed.")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SCHEDULED_FOLDER'] = 'scheduled_uploads'
app.config['GENERATED_IMAGES_FOLDER'] = 'generated_images'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size for videos
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'webm'}

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SCHEDULED_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_IMAGES_FOLDER'], exist_ok=True)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Scheduled posts storage
SCHEDULED_POSTS_FILE = 'scheduled_posts.json'
scheduled_posts_lock = threading.Lock()

def load_scheduled_posts():
    """Load scheduled posts from JSON file"""
    if os.path.exists(SCHEDULED_POSTS_FILE):
        try:
            with open(SCHEDULED_POSTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_scheduled_posts(posts):
    """Save scheduled posts to JSON file"""
    with open(SCHEDULED_POSTS_FILE, 'w') as f:
        json.dump(posts, f, indent=2)

# Initialize Groq client
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_caption_with_groq(prompt, platform=None):
    """Generate professional caption using Groq AI for specific platform"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        platform_instructions = {
            'linkedin': "Create a professional, business-focused caption for LinkedIn. Use industry insights and thought leadership. No emojis. Keep it concise and impactful. Add 3-5 relevant professional hashtags at the end.",
            'twitter': "Create a concise, engaging caption for Twitter. Maximum 280 characters. Be direct and conversational. No emojis. Add 2-3 relevant hashtags.",
            'instagram': "Create an engaging, authentic caption for Instagram. Tell a story or share value. No emojis. Use line breaks for readability. Add 5-8 relevant hashtags at the end on separate lines.",
            'facebook': "Create a friendly, conversational caption for Facebook. Can be longer and more detailed. Encourage engagement. No emojis. Add 3-5 relevant hashtags.",
            'pinterest': "Create a descriptive, searchable title for Pinterest. Include keywords people search for. Maximum 100 characters. No emojis. Focus on what the pin is about and benefits.",
            'youtube': "Create an engaging video title (max 100 chars) and description. Title should be clickable and SEO-friendly. Description should be detailed with timestamps if applicable. No emojis. Add relevant tags.",
            'youtubepost': "Create an engaging caption for YouTube Community post. Be conversational and encourage discussion. No emojis. Can include questions to engage audience. Add 2-3 relevant hashtags."
        }
        
        if platform and platform in platform_instructions:
            system_content = f"You are a professional social media copywriter. {platform_instructions[platform]} IMPORTANT: Return ONLY the caption text without any quotes, markdown, or extra formatting. Never use emojis."
        else:
            system_content = "You are a professional social media copywriter. Create clear, engaging captions without emojis. Keep it professional and concise. IMPORTANT: Return ONLY the caption text without any quotes, markdown, or extra formatting."
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": f"Generate a professional social media caption for: {prompt}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=300
        )
        caption = chat_completion.choices[0].message.content.strip()
        caption = caption.strip('"').strip("'").strip()
        return caption
    except Exception as e:
        return f"Error generating caption: {str(e)}"

def get_chrome_driver(headless=True):
    """Create Chrome driver with optimized settings for file uploads"""
    options = Options()
    
    # Critical: Keep headless mode OFF for file uploads to work reliably
    if headless:
        options.add_argument('--headless=new')
    
    # Essential arguments
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    
    # Disable GPU for stability
    options.add_argument('--disable-gpu')
    
    # Allow file access (CRITICAL for file uploads)
    options.add_argument('--allow-file-access-from-files')
    options.add_argument('--enable-local-file-accesses')
    
    # Add preferences to handle file uploads
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    
    # Set page load timeout
    driver.set_page_load_timeout(60)
    
    return driver

def load_cookies(driver, platform):
    """Load cookies from JSON file"""
    cookie_file = f"{platform}_cookies.json"
    if not os.path.exists(cookie_file):
        return False
    
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        return True
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return False

def safe_click(driver, element, method="default"):
    """Safely click an element using multiple methods"""
    try:
        if method == "default":
            element.click()
        elif method == "js":
            driver.execute_script("arguments[0].click();", element)
        elif method == "action":
            ActionChains(driver).move_to_element(element).click().perform()
        return True
    except Exception as e:
        print(f"Click method '{method}' failed: {e}")
        return False

def find_and_upload_file(driver, file_path, wait_time=15):
    """Universal file upload function with multiple strategies"""
    print(f"\n🔍 Searching for file input...")
    print(f"📁 File to upload: {file_path}")
    print(f"📊 File exists: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False
    
    # Convert to absolute path
    absolute_path = os.path.abspath(file_path)
    print(f"📍 Absolute path: {absolute_path}")
    
    try:
        # Strategy 1: Look for visible file inputs
        file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
        print(f"Found {len(file_inputs)} file input(s)")
        
        for idx, file_input in enumerate(file_inputs):
            try:
                # Make input visible if hidden
                driver.execute_script("""
                    arguments[0].style.opacity = '1';
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.height = 'auto';
                    arguments[0].style.width = 'auto';
                    arguments[0].removeAttribute('hidden');
                """, file_input)
                
                # Send file path
                file_input.send_keys(absolute_path)
                print(f"✅ File uploaded via input #{idx}")
                return True
            except Exception as e:
                print(f"⚠️  Input #{idx} failed: {e}")
                continue
        
        # Strategy 2: Wait for new file input to appear
        print("Waiting for file input to appear...")
        file_input = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )
        
        # Ensure it's interactable
        driver.execute_script("""
            arguments[0].style.opacity = '1';
            arguments[0].style.display = 'block';
            arguments[0].style.visibility = 'visible';
        """, file_input)
        
        file_input.send_keys(absolute_path)
        print(f"✅ File uploaded via waited input")
        return True
        
    except Exception as e:
        print(f"❌ All file upload strategies failed: {e}")
        return False

def post_to_linkedin(caption, image_path=None, headless=False):
    """Post to LinkedIn - FIXED for Chrome updates"""
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== LinkedIn Posting ===")
        driver.get('https://www.linkedin.com')
        time.sleep(2)
        
        if not load_cookies(driver, 'linkedin'):
            return {"success": False, "message": "LinkedIn cookies not found"}
        
        driver.get('https://www.linkedin.com/feed/')
        time.sleep(4)
        
        if 'login' in driver.current_url.lower():
            return {"success": False, "message": "LinkedIn authentication failed"}
        
        print("✓ Logged in")
        
        # Click Start a post
        try:
            start_post_selectors = [
                "//button[contains(@class, 'artdeco-button') and contains(., 'Start a post')]",
                "//button[contains(., 'Start a post')]",
                ".share-box-feed-entry__trigger"
            ]
            
            start_post = None
            for selector in start_post_selectors:
                try:
                    if selector.startswith('.'):
                        start_post = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    else:
                        start_post = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    break
                except:
                    continue
            
            if not start_post:
                return {"success": False, "message": "Could not find post button"}
            
            safe_click(driver, start_post, "js")
            time.sleep(3)
            print("✓ Opened post dialog")
            
        except Exception as e:
            return {"success": False, "message": f"Error opening post dialog: {str(e)}"}
        
        # Upload image if provided
        if image_path and os.path.exists(image_path):
            try:
                print("📸 Uploading image...")
                
                # Click media button
                media_button_selectors = [
                    "//button[contains(@aria-label, 'Add media') or contains(@aria-label, 'Add photo')]",
                    "//button[.//svg[contains(@data-test-icon, 'image')]]",
                    "//button[contains(., 'Photo')]"
                ]
                
                media_button = None
                for selector in media_button_selectors:
                    try:
                        media_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        break
                    except:
                        continue
                
                if media_button:
                    safe_click(driver, media_button, "js")
                    time.sleep(2)
                    print("✓ Media button clicked")
                    
                    # Upload file
                    if find_and_upload_file(driver, image_path, wait_time=10):
                        print("✓ Image uploaded")
                        time.sleep(5)
                        
                        # Click Next if present
                        try:
                            next_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Next')]]"))
                            )
                            safe_click(driver, next_button, "js")
                            time.sleep(2)
                        except:
                            pass
                    else:
                        print("⚠️  Image upload failed, continuing with text only")
                
            except Exception as e:
                print(f"⚠️  Image upload error: {e}, continuing with text only")
        
        # Enter caption
        try:
            caption_selectors = [
                "//div[contains(@class, 'ql-editor') and @contenteditable='true']",
                "//div[@contenteditable='true' and @role='textbox']",
                "//div[@data-placeholder='What do you want to talk about?']"
            ]
            
            caption_box = None
            for selector in caption_selectors:
                try:
                    caption_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if caption_box:
                caption_box.click()
                time.sleep(1)
                caption_box.send_keys(caption)
                time.sleep(2)
                print("✓ Caption entered")
            
        except Exception as e:
            print(f"⚠️  Caption entry error: {e}")
        
        # Click Post
        try:
            post_button_selectors = [
                "//button[.//span[contains(@class, 'artdeco-button__text') and text()='Post']]",
                "//button[contains(@class, 'share-actions__primary-action') and .//span[text()='Post']]",
                "//button[contains(., 'Post') and contains(@class, 'share-actions')]"
            ]
            
            post_button = None
            for selector in post_button_selectors:
                try:
                    post_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if post_button:
                driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
                time.sleep(1)
                safe_click(driver, post_button, "js")
                time.sleep(5)
                print("✓ Posted")
                return {"success": True, "message": "Posted to LinkedIn successfully"}
            else:
                return {"success": False, "message": "Could not find post button"}
            
        except Exception as e:
            return {"success": False, "message": f"Error posting: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"LinkedIn error: {str(e)}"}
    finally:
        driver.quit()

def post_to_twitter(caption, image_path=None, headless=False):
    """Post to Twitter/X - FIXED for Chrome updates"""
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== Twitter Posting ===")
        driver.get('https://twitter.com')
        time.sleep(2)
        
        if not load_cookies(driver, 'twitter'):
            return {"success": False, "message": "Twitter cookies not found"}
        
        driver.get('https://twitter.com/home')
        time.sleep(4)
        
        if 'login' in driver.current_url.lower():
            return {"success": False, "message": "Twitter authentication failed"}
        
        print("✓ Logged in")
        
        # Click tweet box
        try:
            tweet_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='tweetTextarea_0']"))
            )
            tweet_box.click()
            time.sleep(2)
            print("✓ Tweet box clicked")
        except:
            return {"success": False, "message": "Could not find tweet box"}
        
        # Upload image if provided
        if image_path and os.path.exists(image_path):
            try:
                print("📸 Uploading image...")
                
                if find_and_upload_file(driver, image_path, wait_time=10):
                    print("✓ Image uploaded")
                    time.sleep(6)
                else:
                    print("⚠️  Image upload failed")
                    
            except Exception as e:
                print(f"⚠️  Image upload error: {e}")
        
        # Enter caption
        try:
            tweet_box = driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
            tweet_box.click()
            time.sleep(1)
            
            for char in caption:
                tweet_box.send_keys(char)
                time.sleep(0.05)
            
            time.sleep(2)
            print("✓ Caption entered")
        except Exception as e:
            print(f"⚠️  Caption entry error: {e}")
        
        # Click Tweet button
        try:
            tweet_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButtonInline']"))
            )
            safe_click(driver, tweet_button, "js")
            time.sleep(5)
            print("✓ Posted")
            
            return {"success": True, "message": "Posted to Twitter successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Error posting tweet: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Twitter error: {str(e)}"}
    finally:
        driver.quit()

def post_to_instagram(caption, image_path=None, headless=False):
    """Post to Instagram - FIXED with improved reliability"""
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "message": "Instagram requires an image or video"}
    
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== Instagram Posting ===")
        driver.get('https://www.instagram.com')
        time.sleep(3)
        
        if not load_cookies(driver, 'instagram'):
            return {"success": False, "message": "Instagram cookies not found"}
        
        driver.get('https://www.instagram.com')
        time.sleep(5)
        
        if 'login' in driver.current_url.lower():
            return {"success": False, "message": "Instagram authentication failed"}
        
        print("✓ Logged in")
        
        # Click Create
        try:
            create_selectors = [
                "//a[contains(@href, '/create/')]",
                "//svg[@aria-label='New post' or @aria-label='Create']/..",
                "//*[name()='svg' and contains(@aria-label, 'New')]/..",
                "//span[text()='Create']/ancestor::a"
            ]
            
            create_button = None
            for selector in create_selectors:
                try:
                    create_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not create_button:
                return {"success": False, "message": "Could not find Create button"}
            
            safe_click(driver, create_button, "js")
            time.sleep(4)
            print("✓ Create clicked")
            
        except Exception as e:
            return {"success": False, "message": f"Error clicking create: {str(e)}"}
        
        # Upload image
        try:
            print("📸 Uploading image...")
            
            if find_and_upload_file(driver, image_path, wait_time=10):
                print("✓ Image uploaded")
                time.sleep(6)
            else:
                return {"success": False, "message": "Failed to upload image"}
            
        except Exception as e:
            return {"success": False, "message": f"Image upload error: {str(e)}"}
        
        # Click Next (crop)
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and text()='Next']"))
            )
            safe_click(driver, next_button, "js")
            time.sleep(4)
            print("✓ First Next")
        except Exception as e:
            return {"success": False, "message": f"First Next error: {str(e)}"}
        
        # Click Next (filter)
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and text()='Next']"))
            )
            safe_click(driver, next_button, "js")
            time.sleep(5)
            print("✓ Second Next")
        except Exception as e:
            return {"success": False, "message": f"Second Next error: {str(e)}"}
        
        # Enter caption with improved method
        try:
            print("📝 Entering caption...")
            time.sleep(3)
            
            caption_selectors = [
                "//textarea[@aria-label='Write a caption...']",
                "//div[@contenteditable='true' and @role='textbox']",
                "//p[@contenteditable='true']"
            ]
            
            caption_input = None
            for selector in caption_selectors:
                try:
                    caption_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not caption_input:
                return {"success": False, "message": "Could not find caption input"}
            
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caption_input)
            time.sleep(1)
            
            # Focus and enter text
            driver.execute_script("arguments[0].focus();", caption_input)
            time.sleep(0.5)
            caption_input.click()
            time.sleep(1)
            
            # Use JavaScript to set text reliably
            driver.execute_script("""
                var element = arguments[0];
                var text = arguments[1];
                
                if (element.tagName === 'TEXTAREA') {
                    element.value = text;
                } else {
                    element.textContent = text;
                    element.innerText = text;
                }
                
                // Trigger events
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                element.focus();
            """, caption_input, caption)
            
            time.sleep(3)
            
            # Verify
            current_text = driver.execute_script("return arguments[0].value || arguments[0].textContent || arguments[0].innerText;", caption_input)
            print(f"✓ Caption verified: {current_text[:50]}...")
            
        except Exception as e:
            return {"success": False, "message": f"Caption entry failed: {str(e)}"}
        
        # Click Share
        try:
            time.sleep(2)
            
            share_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and text()='Share']"))
            )
            
            safe_click(driver, share_button, "js")
            time.sleep(8)
            print("✓ Posted")
            
            return {"success": True, "message": "Posted to Instagram successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Share error: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Instagram error: {str(e)}"}
    finally:
        driver.quit()

def post_to_facebook(caption, image_path=None, headless=False):
    """Post to Facebook - FIXED"""
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== Facebook Posting ===")
        driver.get('https://www.facebook.com')
        time.sleep(3)
        
        if not load_cookies(driver, 'facebook'):
            return {"success": False, "message": "Facebook cookies not found"}
        
        driver.get('https://www.facebook.com')
        time.sleep(5)
        
        if 'login' in driver.current_url.lower():
            return {"success": False, "message": "Facebook authentication failed"}
        
        print("✓ Logged in")
        
        # Click post box
        try:
            post_box = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), \"What's on your mind\")]"))
            )
            post_box.click()
            time.sleep(5)
            print("✓ Post box opened")
        except:
            return {"success": False, "message": "Could not open post dialog"}
        
        # Enter caption
        try:
            caption_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @role='textbox']"))
            )
            caption_box.click()
            time.sleep(1)
            caption_box.send_keys(caption)
            time.sleep(2)
            print("✓ Caption entered")
        except Exception as e:
            print(f"⚠️  Caption error: {e}")
        
        # Upload image
        if image_path and os.path.exists(image_path):
            try:
                print("📸 Uploading image...")
                time.sleep(2)
                
                photo_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Photo/video']"))
                )
                safe_click(driver, photo_button, "js")
                time.sleep(2)
                
                if find_and_upload_file(driver, image_path, wait_time=10):
                    print("✓ Image uploaded")
                    time.sleep(8)
                else:
                    print("⚠️  Image upload failed")
                    
            except Exception as e:
                print(f"⚠️  Image upload error: {e}")
        
        # Click Post
        try:
            time.sleep(3)
            post_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Post']/ancestor::div[@role='button']"))
            )
            safe_click(driver, post_button, "js")
            time.sleep(6)
            print("✓ Posted")
            
            return {"success": True, "message": "Posted to Facebook successfully"}
        except:
            return {"success": False, "message": "Post button error"}
        
    except Exception as e:
        return {"success": False, "message": f"Facebook error: {str(e)}"}
    finally:
        driver.quit()

def post_to_pinterest(title, image_path=None, link=None, description="", headless=False):
    """Post to Pinterest - FIXED"""
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "message": "Pinterest requires an image"}
    
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== Pinterest Posting ===")
        driver.get('https://www.pinterest.com')
        time.sleep(3)
        
        if not load_cookies(driver, 'pinterest'):
            return {"success": False, "message": "Pinterest cookies not found"}
        
        driver.get('https://www.pinterest.com')
        time.sleep(5)
        
        if 'login' in driver.current_url.lower():
            return {"success": False, "message": "Pinterest authentication failed"}
        
        print("✓ Logged in")
        
        try:
            create_pin_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Create Pin')]"))
            )
            create_pin_button.click()
            time.sleep(3)
            print("✓ Create Pin clicked")
        except:
            return {"success": False, "message": "Could not find Create Pin button"}
        
        try:
            print("📸 Uploading image...")
            if find_and_upload_file(driver, image_path, wait_time=10):
                print("✓ Image uploaded")
                time.sleep(8)
            else:
                return {"success": False, "message": "Image upload failed"}
        except:
            return {"success": False, "message": "Image upload error"}
        
        try:
            title_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@id='storyboard-selector-title']"))
            )
            title_input.click()
            time.sleep(1)
            title_input.send_keys(title[:100])
            time.sleep(2)
            print("✓ Title entered")
        except:
            return {"success": False, "message": "Title entry failed"}
        
        if description:
            try:
                desc_input = driver.find_element(By.XPATH, "//textarea[@id='storyboard-selector-description']")
                desc_input.click()
                desc_input.send_keys(description)
                time.sleep(2)
            except:
                pass
        
        try:
            publish_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'lIkAnG') and text()='Publish']"))
            )
            safe_click(driver, publish_button, "js")
            time.sleep(8)
            print("✓ Posted")
            
            return {"success": True, "message": "Posted to Pinterest successfully"}
        except:
            return {"success": False, "message": "Publishing error"}
        
    except Exception as e:
        return {"success": False, "message": f"Pinterest error: {str(e)}"}
    finally:
        driver.quit()

def post_to_youtube_post(caption, image_path=None, headless=False):
    """Post to YouTube Community - FIXED"""
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== YouTube Community Post ===")
        driver.get('https://www.youtube.com')
        time.sleep(3)
        
        if not load_cookies(driver, 'youtube'):
            return {"success": False, "message": "YouTube cookies not found"}
        
        driver.get('https://www.youtube.com')
        time.sleep(5)
        
        if 'accounts.google.com' in driver.current_url.lower():
            return {"success": False, "message": "YouTube authentication failed"}
        
        print("✓ Logged in")
        
        # Click Create
        try:
            create_selectors = [
                "//button[@aria-label='Create']",
                "//ytd-topbar-menu-button-renderer[@id='upload-button']//button"
            ]
            
            create_button = None
            for selector in create_selectors:
                try:
                    create_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not create_button:
                return {"success": False, "message": "Could not find Create button"}
            
            safe_click(driver, create_button, "js")
            time.sleep(3)
            print("✓ Create clicked")
            
        except Exception as e:
            return {"success": False, "message": f"Error clicking Create: {str(e)}"}
        
        # Click Create post
        try:
            create_post_option = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//yt-formatted-string[text()='Create post']"))
            )
            
            safe_click(driver, create_post_option, "js")
            time.sleep(5)
            print("✓ Create post clicked")
            
        except Exception as e:
            return {"success": False, "message": f"Error clicking Create post: {str(e)}"}
        
        # Upload image if provided
        if image_path and os.path.exists(image_path):
            try:
                print("📸 Uploading image...")
                time.sleep(3)
                
                # Click image button
                upload_button_selectors = [
                    "//button[contains(@aria-label, 'image') or contains(@aria-label, 'photo')]",
                    "//button[contains(@aria-label, 'Image') or contains(@aria-label, 'Photo')]"
                ]
                
                for selector in upload_button_selectors:
                    try:
                        buttons = driver.find_elements(By.XPATH, selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                safe_click(driver, button, "js")
                                time.sleep(3)
                                break
                        break
                    except:
                        continue
                
                # Upload file
                if find_and_upload_file(driver, image_path, wait_time=10):
                    print("✓ Image uploaded")
                    time.sleep(10)
                else:
                    print("⚠️  Image upload failed")
                    
            except Exception as e:
                print(f"⚠️  Image upload error: {e}")
        
        # Enter caption
        try:
            print("📝 Entering caption...")
            time.sleep(2)
            
            caption_selectors = [
                "//div[@id='contenteditable-root' and @contenteditable='true']",
                "//div[@contenteditable='true' and @role='textbox']"
            ]
            
            caption_box = None
            for selector in caption_selectors:
                try:
                    caption_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if caption_box.is_displayed():
                        break
                except:
                    continue
            
            if not caption_box:
                return {"success": False, "message": "Could not find caption text box"}
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caption_box)
            time.sleep(1)
            driver.execute_script("arguments[0].focus();", caption_box)
            time.sleep(0.5)
            caption_box.click()
            time.sleep(1)
            
            # Type caption
            for char in caption:
                caption_box.send_keys(char)
                time.sleep(0.03)
            
            time.sleep(2)
            print("✓ Caption entered")
            
        except Exception as e:
            return {"success": False, "message": f"Caption entry error: {str(e)}"}
        
        # Click Post
        try:
            time.sleep(2)
            
            post_button_selectors = [
                "//button[contains(@aria-label, 'Post')]",
                "//button[contains(., 'Post')]"
            ]
            
            post_button = None
            for selector in post_button_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            post_button = btn
                            break
                    if post_button:
                        break
                except:
                    continue
            
            if not post_button:
                return {"success": False, "message": "Could not find Post button"}
            
            safe_click(driver, post_button, "js")
            time.sleep(8)
            print("✓ Posted")
            
            return {"success": True, "message": "Posted to YouTube Community successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Post button error: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"YouTube Post error: {str(e)}"}
    finally:
        driver.quit()

def post_to_youtube(title, description, video_path, visibility='public', headless=False):
    """Post video to YouTube - FIXED"""
    if not video_path or not os.path.exists(video_path):
        return {"success": False, "message": "YouTube requires a video file"}
    
    driver = get_chrome_driver(headless=headless)
    
    try:
        print("\n=== YouTube Video Upload ===")
        driver.get('https://www.youtube.com')
        time.sleep(3)
        
        if not load_cookies(driver, 'youtube'):
            return {"success": False, "message": "YouTube cookies not found"}
        
        driver.get('https://www.youtube.com')
        time.sleep(5)
        
        if 'accounts.google.com' in driver.current_url.lower():
            return {"success": False, "message": "YouTube authentication failed"}
        
        # Click Create
        try:
            create_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Create']"))
            )
            safe_click(driver, create_button, "js")
            time.sleep(3)
        except Exception as e:
            return {"success": False, "message": f"Error clicking Create: {str(e)}"}
        
        # Click Upload video
        try:
            upload_option = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//yt-formatted-string[text()='Upload video']"))
            )
            safe_click(driver, upload_option, "js")
            time.sleep(5)
        except Exception as e:
            return {"success": False, "message": f"Error clicking Upload video: {str(e)}"}
        
        # Upload file
        try:
            if find_and_upload_file(driver, video_path, wait_time=15):
                print("✓ Video uploaded")
                time.sleep(10)
            else:
                return {"success": False, "message": "Video upload failed"}
        except:
            return {"success": False, "message": "Video upload error"}
        
        # Enter title
        try:
            title_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='textbox' and @contenteditable='true']"))
            )
            title_input.click()
            time.sleep(1)
            title_input.send_keys(Keys.CONTROL + "a")
            time.sleep(0.5)
            title_input.send_keys(Keys.DELETE)
            time.sleep(0.5)
            
            for char in title[:100]:
                title_input.send_keys(char)
                time.sleep(0.03)
            
            time.sleep(2)
        except Exception as e:
            return {"success": False, "message": f"Title entry error: {str(e)}"}
        
        # Enter description
        if description:
            try:
                desc_inputs = driver.find_elements(By.XPATH, "//div[@id='textbox' and @contenteditable='true']")
                if len(desc_inputs) > 1:
                    desc_input = desc_inputs[1]
                    desc_input.click()
                    time.sleep(1)
                    
                    for char in description[:5000]:
                        desc_input.send_keys(char)
                        time.sleep(0.02)
                    
                    time.sleep(2)
            except Exception as e:
                print(f"⚠️  Description entry error: {e}")
        
        # Select "No, it's not made for kids"
        try:
            not_for_kids = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//tp-yt-paper-radio-button[@name='VIDEO_MADE_FOR_KIDS_NOT_MFK']"))
            )
            safe_click(driver, not_for_kids, "js")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Kids option error: {e}")
        
        # Click Next 3 times
        for i in range(3):
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@id='next-button']"))
                )
                safe_click(driver, next_button, "js")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️  Next button {i+1} error: {e}")
        
        # Select visibility
        try:
            visibility_map = {'public': 'PUBLIC', 'unlisted': 'UNLISTED', 'private': 'PRIVATE'}
            visibility_value = visibility_map.get(visibility.lower(), 'PUBLIC')
            
            visibility_option = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//tp-yt-paper-radio-button[@name='{visibility_value}']"))
            )
            safe_click(driver, visibility_option, "js")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Visibility error: {e}")
        
        # Click Publish
        try:
            publish_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@id='done-button']"))
            )
            safe_click(driver, publish_button, "js")
            time.sleep(10)
            
            return {"success": True, "message": f"Video uploaded to YouTube successfully as {visibility}"}
            
        except Exception as e:
            return {"success": False, "message": f"Publishing error: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"YouTube error: {str(e)}"}
    finally:
        driver.quit()

def execute_scheduled_post(post_id):
    """Execute a scheduled post"""
    print(f"\n{'='*70}")
    print(f"🚀 EXECUTING SCHEDULED POST: {post_id}")
    print(f"{'='*70}")
    
    with scheduled_posts_lock:
        posts = load_scheduled_posts()
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            print(f"❌ Post {post_id} not found")
            return
        
        captions = post.get('captions', {})
        platforms = post['platforms']
        image_path = post.get('image_path')
        pinterest_title = post.get('pinterest_title', '')
        pinterest_link = post.get('pinterest_link', '')
        youtube_title = post.get('youtube_title', '')
        youtube_description = post.get('youtube_description', '')
        youtube_visibility = post.get('youtube_visibility', 'public')
        
        # Verify media file
        media_path = None
        if image_path and os.path.exists(image_path):
            media_path = os.path.abspath(image_path)
            print(f"✓ Media file found: {media_path}")
        
        results = {}
        
        # CRITICAL: Use headless=False for scheduled posts
        headless_mode = False
        
        if 'linkedin' in platforms:
            results['linkedin'] = post_to_linkedin(captions.get('linkedin', ''), media_path, headless_mode)
        
        if 'twitter' in platforms:
            results['twitter'] = post_to_twitter(captions.get('twitter', ''), media_path, headless_mode)
        
        if 'instagram' in platforms:
            if media_path:
                results['instagram'] = post_to_instagram(captions.get('instagram', ''), media_path, headless_mode)
            else:
                results['instagram'] = {"success": False, "message": "Instagram requires media"}
        
        if 'facebook' in platforms:
            results['facebook'] = post_to_facebook(captions.get('facebook', ''), media_path, headless_mode)
        
        if 'pinterest' in platforms:
            if media_path:
                title = pinterest_title if pinterest_title else captions.get('pinterest', '')
                results['pinterest'] = post_to_pinterest(title, media_path, pinterest_link, captions.get('pinterest', ''), headless_mode)
            else:
                results['pinterest'] = {"success": False, "message": "Pinterest requires media"}
        
        if 'youtube' in platforms:
            if media_path:
                title = youtube_title if youtube_title else captions.get('youtube', '')
                results['youtube'] = post_to_youtube(title, youtube_description, media_path, youtube_visibility, headless_mode)
            else:
                results['youtube'] = {"success": False, "message": "YouTube requires media"}
        
        if 'youtubepost' in platforms:
            results['youtubepost'] = post_to_youtube_post(captions.get('youtubepost', ''), media_path, headless_mode)
        
        # Update post status
        post['status'] = 'completed'
        post['executed_at'] = datetime.now().isoformat()
        post['results'] = results
        
        # Clean up media
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"🗑️  Cleaned up: {image_path}")
            except Exception as e:
                print(f"⚠️  Cleanup failed: {e}")
        
        save_scheduled_posts(posts)
        
        print(f"\n✅ COMPLETED: {post_id}")
        for platform, result in results.items():
            status = "✅" if result.get('success') else "❌"
            print(f"{status} {platform}: {result.get('message')}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-caption', methods=['POST'])
def generate_caption():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        platform = data.get('platform')
        
        if not prompt:
            return jsonify({"success": False, "message": "Prompt is required"})
        
        caption = generate_caption_with_groq(prompt, platform)
        return jsonify({"success": True, "caption": caption})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/generate-all-captions', methods=['POST'])
def generate_all_captions():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        platforms = data.get('platforms', [])
        
        if not prompt:
            return jsonify({"success": False, "message": "Prompt is required"})
        
        if not platforms:
            return jsonify({"success": False, "message": "At least one platform must be selected"})
        
        captions = {}
        for platform in platforms:
            captions[platform] = generate_caption_with_groq(prompt, platform)
        
        return jsonify({"success": True, "captions": captions})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/post', methods=['POST'])
def post():
    try:
        data = request.form
        platforms = request.form.getlist('platforms[]')
        headless = request.form.get('headless') == 'true'
        
        # OVERRIDE: Force headless=False for reliability
        headless = False
        
        captions = {}
        for platform in platforms:
            caption_key = f'caption_{platform}'
            captions[platform] = data.get(caption_key, '')
        
        pinterest_title = data.get('pinterest_title', '')
        pinterest_link = data.get('pinterest_link', '')
        youtube_title = data.get('youtube_title', '')
        youtube_description = data.get('youtube_description', '')
        youtube_visibility = data.get('youtube_visibility', 'public')
        
        if not any(captions.values()) and not pinterest_title and not youtube_title:
            return jsonify({"success": False, "message": "At least one caption or title is required"})
        
        if not platforms:
            return jsonify({"success": False, "message": "At least one platform must be selected"})
        
        media_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(media_path)
                media_path = os.path.abspath(media_path)
        
        results = {}
        
        if 'linkedin' in platforms:
            results['linkedin'] = post_to_linkedin(captions.get('linkedin', ''), media_path, headless)
        
        if 'twitter' in platforms:
            results['twitter'] = post_to_twitter(captions.get('twitter', ''), media_path, headless)
        
        if 'instagram' in platforms:
            results['instagram'] = post_to_instagram(captions.get('instagram', ''), media_path, headless)
        
        if 'facebook' in platforms:
            results['facebook'] = post_to_facebook(captions.get('facebook', ''), media_path, headless)
        
        if 'pinterest' in platforms:
            title = pinterest_title if pinterest_title else captions.get('pinterest', '')
            description = captions.get('pinterest', '')
            results['pinterest'] = post_to_pinterest(title, media_path, pinterest_link, description, headless)
        
        if 'youtube' in platforms:
            title = youtube_title if youtube_title else captions.get('youtube', '')
            description = youtube_description
            results['youtube'] = post_to_youtube(title, description, media_path, youtube_visibility, headless)
        
        if 'youtubepost' in platforms:
            results['youtubepost'] = post_to_youtube_post(captions.get('youtubepost', ''), media_path, headless)
        
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
            except:
                pass
        
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/schedule-post', methods=['POST'])
def schedule_post():
    try:
        data = request.form
        platforms = request.form.getlist('platforms[]')
        schedule_datetime = request.form.get('schedule_datetime')
        
        pinterest_title = data.get('pinterest_title', '')
        pinterest_link = data.get('pinterest_link', '')
        youtube_title = data.get('youtube_title', '')
        youtube_description = data.get('youtube_description', '')
        youtube_visibility = data.get('youtube_visibility', 'public')
        
        captions = {}
        for platform in platforms:
            caption_key = f'caption_{platform}'
            captions[platform] = data.get(caption_key, '')
        
        if not any(captions.values()) and not pinterest_title and not youtube_title:
            return jsonify({"success": False, "message": "At least one caption or title is required"})
        
        if not platforms:
            return jsonify({"success": False, "message": "At least one platform must be selected"})
        
        if not schedule_datetime:
            return jsonify({"success": False, "message": "Schedule date/time is required"})
        
        try:
            scheduled_time = datetime.fromisoformat(schedule_datetime)
        except:
            return jsonify({"success": False, "message": "Invalid datetime format"})
        
        now = datetime.now()
        if scheduled_time <= now:
            return jsonify({"success": False, "message": "Scheduled time must be in the future"})
        
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{int(time.time())}_{file.filename}")
                image_path = os.path.join(app.config['SCHEDULED_FOLDER'], filename)
                file.save(image_path)
                image_path = os.path.abspath(image_path)
        
        post_id = f"post_{int(time.time() * 1000)}"
        post_data = {
            'id': post_id,
            'captions': captions,
            'platforms': platforms,
            'scheduled_time': scheduled_time.isoformat(),
            'image_path': image_path,
            'pinterest_title': pinterest_title,
            'pinterest_link': pinterest_link,
            'youtube_title': youtube_title,
            'youtube_description': youtube_description,
            'youtube_visibility': youtube_visibility,
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        
        with scheduled_posts_lock:
            posts = load_scheduled_posts()
            posts.append(post_data)
            save_scheduled_posts(posts)
        
        try:
            scheduler.add_job(
                func=execute_scheduled_post,
                trigger=DateTrigger(run_date=scheduled_time),
                args=[post_id],
                id=post_id,
                replace_existing=True
            )
        except Exception as e:
            return jsonify({"success": False, "message": f"Error scheduling job: {str(e)}"})
        
        return jsonify({
            "success": True,
            "message": f"Post scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}",
            "post_id": post_id
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/get-scheduled-posts', methods=['GET'])
def get_scheduled_posts():
    try:
        with scheduled_posts_lock:
            posts = load_scheduled_posts()
            cutoff_time = datetime.now() - timedelta(hours=24)
            active_posts = []
            
            for p in posts:
                if p['status'] != 'completed':
                    active_posts.append(p)
                else:
                    executed_at = p.get('executed_at')
                    if executed_at:
                        try:
                            exec_time = datetime.fromisoformat(executed_at)
                            if exec_time > cutoff_time:
                                active_posts.append(p)
                        except:
                            pass
            
            return jsonify({"success": True, "posts": active_posts})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/cancel-scheduled-post/<post_id>', methods=['DELETE'])
def cancel_scheduled_post(post_id):
    try:
        with scheduled_posts_lock:
            posts = load_scheduled_posts()
            post = next((p for p in posts if p['id'] == post_id), None)
            
            if not post:
                return jsonify({"success": False, "message": "Post not found"})
            
            try:
                scheduler.remove_job(post_id)
            except:
                pass
            
            if post.get('image_path') and os.path.exists(post['image_path']):
                try:
                    os.remove(post['image_path'])
                except:
                    pass
            
            posts = [p for p in posts if p['id'] != post_id]
            save_scheduled_posts(posts)
            
        return jsonify({"success": True, "message": "Scheduled post cancelled"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete-completed-post/<post_id>', methods=['DELETE'])
def delete_completed_post(post_id):
    try:
        with scheduled_posts_lock:
            posts = load_scheduled_posts()
            post = next((p for p in posts if p['id'] == post_id), None)
            
            if not post:
                return jsonify({"success": False, "message": "Post not found"})
            
            if post.get('image_path') and os.path.exists(post['image_path']):
                try:
                    os.remove(post['image_path'])
                except:
                    pass
            
            posts = [p for p in posts if p['id'] != post_id]
            save_scheduled_posts(posts)
            
        return jsonify({"success": True, "message": "Post deleted successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def restore_scheduled_jobs():
    """Restore scheduled jobs on startup"""
    print("\n" + "="*60)
    print("RESTORING SCHEDULED JOBS")
    print("="*60)
    
    with scheduled_posts_lock:
        posts = load_scheduled_posts()
        current_time = datetime.now()
        
        for post in posts:
            if post['status'] == 'scheduled':
                try:
                    scheduled_time = datetime.fromisoformat(post['scheduled_time'])
                    
                    if scheduled_time > current_time:
                        scheduler.add_job(
                            func=execute_scheduled_post,
                            trigger=DateTrigger(run_date=scheduled_time),
                            args=[post['id']],
                            id=post['id'],
                            replace_existing=True
                        )
                        print(f"✓ Restored job: {post['id']}")
                    else:
                        post['status'] = 'missed'
                        print(f"✗ Missed: {post['id']}")
                        
                except Exception as e:
                    print(f"✗ Error: {e}")
        
        save_scheduled_posts(posts)
        print(f"Restored {len([p for p in posts if p['status'] == 'scheduled'])} jobs")
        print("="*60 + "\n")

@app.route('/scheduler-status', methods=['GET'])
def scheduler_status():
    """Debug endpoint"""
    try:
        jobs = scheduler.get_jobs()
        posts = load_scheduled_posts()
        
        return jsonify({
            "success": True,
            "scheduler_running": scheduler.running,
            "active_jobs": len(jobs),
            "stored_posts": len(posts)
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def check_missed_posts():
    """Periodic check for missed posts"""
    with scheduled_posts_lock:
        posts = load_scheduled_posts()
        current_time = datetime.now()
        
        for post in posts:
            if post['status'] == 'scheduled':
                try:
                    scheduled_time = datetime.fromisoformat(post['scheduled_time'])
                    
                    if scheduled_time < current_time:
                        print(f"[CHECK] Executing overdue post: {post['id']}")
                        thread = threading.Thread(target=execute_scheduled_post, args=[post['id']])
                        thread.start()
                        
                except Exception as e:
                    print(f"[CHECK] Error: {e}")

scheduler.add_job(
    func=check_missed_posts,
    trigger='interval',
    seconds=60,
    id='missed_posts_check',
    replace_existing=True
)

restore_scheduled_jobs()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True, port=5000)