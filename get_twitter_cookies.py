"""
Twitter/X Cookie Extractor
This script helps you extract cookies from Twitter/X after manual login
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import os

def extract_twitter_cookies():
    """
    Extract Twitter/X cookies after manual login
    """
    print("=" * 60)
    print("Twitter/X Cookie Extractor")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Open Twitter/X in a browser")
    print("2. Wait for you to log in manually")
    print("3. Extract and save cookies to twitter_cookies.json")
    print("\n" + "=" * 60)
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    
    # Add user agent to appear more like a real browser
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    print("\n🌐 Opening Chrome browser...")
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to Twitter login
        driver.get('https://twitter.com/i/flow/login')
        print("✅ Twitter/X login page loaded")
        
        print("\n" + "=" * 60)
        print("⚠️  PLEASE LOG IN TO TWITTER/X NOW")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Enter your Twitter/X username/email/phone")
        print("2. Enter your password")
        print("3. Complete any 2FA/verification if required")
        print("4. Wait until you see your Twitter/X home feed")
        print("5. Come back to this terminal and press Enter")
        print("\n⚠️  IMPORTANT NOTES:")
        print("   - Twitter may ask for phone verification")
        print("   - Twitter may show unusual activity warnings")
        print("   - Complete all security checks")
        print("   - Make sure you see tweets in your timeline")
        print("\n⏳ Waiting for you to log in...")
        
        # Wait for user to log in
        input("\n👉 Press Enter after you've logged in and see your feed...")
        
        # Verify login by checking URL and page elements
        current_url = driver.current_url
        print(f"\n📍 Current URL: {current_url}")
        
        # Check if still on login page
        if 'login' in current_url.lower() or 'flow' in current_url.lower():
            print("\n❌ Still on login page. Please complete the login first!")
            print("Rerun the script and make sure you:")
            print("  - Complete all verification steps")
            print("  - See your home timeline with tweets")
            print("  - Are fully logged in")
            return False
        
        # Navigate to home to ensure we're logged in
        print("\n🔄 Navigating to Twitter home to verify login...")
        driver.get('https://twitter.com/home')
        time.sleep(3)
        
        current_url = driver.current_url
        if 'login' in current_url.lower() or 'flow' in current_url.lower():
            print("\n❌ Login verification failed!")
            return False
        
        print("\n✅ Login detected! Extracting cookies...")
        
        # Get all cookies
        cookies = driver.get_cookies()
        
        if not cookies:
            print("\n❌ No cookies found!")
            return False
        
        print(f"✅ Found {len(cookies)} cookies")
        
        # Save cookies to JSON file
        filename = 'twitter_cookies.json'
        with open(filename, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n✅ Cookies saved to: {filename}")
        print("\n" + "=" * 60)
        print("Cookie Details:")
        print("=" * 60)
        
        # Show important cookies for Twitter
        important_cookies = ['auth_token', 'ct0', 'twid', 'kdt']
        found_cookies = []
        missing_cookies = []
        
        for cookie_name in important_cookies:
            cookie = next((c for c in cookies if c['name'] == cookie_name), None)
            if cookie:
                print(f"✓ {cookie_name}: Found")
                found_cookies.append(cookie_name)
            else:
                print(f"✗ {cookie_name}: Not found")
                missing_cookies.append(cookie_name)
        
        # Critical check
        if 'auth_token' not in found_cookies:
            print("\n⚠️  WARNING: 'auth_token' cookie missing!")
            print("This is the most important cookie for Twitter authentication.")
            print("You may need to log in again.")
            return False
        
        if 'ct0' not in found_cookies:
            print("\n⚠️  WARNING: 'ct0' (CSRF token) missing!")
            print("This may cause posting issues.")
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"\nYour cookies have been saved to: {filename}")
        print("\nYou can now use this file with the Social Media Auto Poster!")
        print("\n⚠️  SECURITY NOTES:")
        print("   - Keep this file PRIVATE - it contains your login session")
        print("   - Don't share or commit to Git")
        print("   - Add *.json to .gitignore")
        print("   - Cookies typically last 30-60 days")
        print("   - Re-run this script when cookies expire")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n🔒 Closing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("✅ Browser closed")

def verify_twitter_cookies():
    """
    Verify if the extracted Twitter cookies work
    """
    print("\n" + "=" * 60)
    print("Verifying Twitter Cookies...")
    print("=" * 60)
    
    if not os.path.exists('twitter_cookies.json'):
        print("❌ twitter_cookies.json not found!")
        return False
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Load Twitter
        driver.get('https://twitter.com')
        time.sleep(2)
        
        # Load cookies
        with open('twitter_cookies.json', 'r') as f:
            cookies = json.load(f)
        
        print(f"Loading {len(cookies)} cookies...")
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Warning: Could not add cookie {cookie.get('name', 'unknown')}: {e}")
        
        # Refresh to apply cookies
        driver.get('https://twitter.com/home')
        time.sleep(4)
        
        current_url = driver.current_url.lower()
        
        # Check if logged in
        if 'login' in current_url or 'flow' in current_url:
            print("❌ Cookies verification failed - Not logged in")
            print("💡 The cookies might have expired. Please extract them again.")
            print(f"Current URL: {driver.current_url}")
            return False
        else:
            print("✅ Cookies verified successfully!")
            print("✅ You are logged in to Twitter/X")
            print(f"✅ Current URL: {driver.current_url}")
            
            # Try to find a tweet element to confirm we're on home page
            try:
                driver.find_element(By.XPATH, "//article[@data-testid='tweet' or @role='article']")
                print("✅ Twitter timeline detected - fully authenticated!")
            except:
                print("⚠️  Timeline not detected, but login successful")
            
            return True
            
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

def main():
    print("\n" + "=" * 60)
    print("  TWITTER/X COOKIE EXTRACTOR")
    print("=" * 60)
    print("\n⚠️  IMPORTANT INFORMATION:")
    print("\nTwitter/X has strict automation detection:")
    print("  • May ask for phone verification")
    print("  • May show 'unusual activity' warnings")
    print("  • May require additional security checks")
    print("  • Cookies may expire faster than other platforms")
    print("\n💡 TIPS FOR SUCCESS:")
    print("  • Use your actual Twitter account")
    print("  • Complete all verification steps")
    print("  • Don't rush - wait for pages to fully load")
    print("  • Make sure you see your timeline before pressing Enter")
    print("=" * 60)
    
    proceed = input("\n👉 Do you want to continue? (y/n): ").lower().strip()
    
    if proceed != 'y':
        print("\n👋 Goodbye!")
        return
    
    # Extract cookies
    success = extract_twitter_cookies()
    
    if success:
        print("\n" + "=" * 60)
        verify = input("\n🔍 Do you want to verify the cookies? (y/n): ").lower().strip()
        
        if verify == 'y':
            verify_twitter_cookies()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print("\n💡 TIPS:")
    print("   - Twitter cookies typically last 30-60 days")
    print("   - Re-run this script if your cookies expire")
    print("   - Keep the cookies file secure")
    print("   - Don't share or commit to Git")
    print("   - Add to .gitignore: *.json")
    print("\n📝 NEXT STEPS:")
    print("   1. Place twitter_cookies.json in same folder as app.py")
    print("   2. Run: python app.py")
    print("   3. Open: http://localhost:5000")
    print("   4. Select Twitter and start posting!")
    print("\n⚠️  TROUBLESHOOTING:")
    print("   If posting fails:")
    print("   - Try re-extracting cookies")
    print("   - Use non-headless mode to see what's happening")
    print("   - Check if Twitter is asking for verification")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()