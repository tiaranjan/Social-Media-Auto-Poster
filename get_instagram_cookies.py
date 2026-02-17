"""
Instagram Cookie Extractor
This script helps you extract cookies from Instagram after manual login
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import os

def extract_instagram_cookies():
    """
    Extract Instagram cookies after manual login
    """
    print("=" * 60)
    print("Instagram Cookie Extractor")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Open Instagram in a browser")
    print("2. Wait for you to log in manually")
    print("3. Extract and save cookies to instagram_cookies.json")
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
        # Navigate to Instagram login
        driver.get('https://www.instagram.com/accounts/login/')
        time.sleep(3)
        print("✅ Instagram login page loaded")
        
        print("\n" + "=" * 60)
        print("⚠️  PLEASE LOG IN TO INSTAGRAM NOW")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Enter your Instagram username/email/phone")
        print("2. Enter your password")
        print("3. Complete any verification if required")
        print("4. Click 'Save Info' or 'Not Now' when prompted")
        print("5. Wait until you see your Instagram feed")
        print("6. Come back to this terminal and press Enter")
        print("\n⚠️  IMPORTANT NOTES:")
        print("   - Instagram may ask to save login info (choose 'Save Info')")
        print("   - May ask to turn on notifications (choose 'Not Now')")
        print("   - Make sure you see posts in your feed")
        print("\n⏳ Waiting for you to log in...")
        
        # Wait for user to log in
        input("\n👉 Press Enter after you've logged in and see your feed...")
        
        # Verify login by checking URL
        current_url = driver.current_url
        print(f"\n📍 Current URL: {current_url}")
        
        # Check if still on login page
        if 'login' in current_url.lower() or 'accounts/login' in current_url.lower():
            print("\n❌ Still on login page. Please complete the login first!")
            print("Rerun the script and make sure you:")
            print("  - Enter correct credentials")
            print("  - Complete all security checks")
            print("  - See your Instagram feed")
            return False
        
        # Navigate to home to ensure we're logged in
        print("\n🔄 Navigating to Instagram home to verify login...")
        driver.get('https://www.instagram.com/')
        time.sleep(3)
        
        current_url = driver.current_url
        if 'login' in current_url.lower():
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
        filename = 'instagram_cookies.json'
        with open(filename, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n✅ Cookies saved to: {filename}")
        print("\n" + "=" * 60)
        print("Cookie Details:")
        print("=" * 60)
        
        # Show important cookies for Instagram
        important_cookies = ['sessionid', 'csrftoken', 'ds_user_id', 'mid']
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
        if 'sessionid' not in found_cookies:
            print("\n⚠️  WARNING: 'sessionid' cookie missing!")
            print("This is the most important cookie for Instagram authentication.")
            print("You may need to log in again.")
            return False
        
        if 'csrftoken' not in found_cookies:
            print("\n⚠️  WARNING: 'csrftoken' missing!")
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
        print("   - Cookies typically last 60-90 days")
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

def verify_instagram_cookies():
    """
    Verify if the extracted Instagram cookies work
    """
    print("\n" + "=" * 60)
    print("Verifying Instagram Cookies...")
    print("=" * 60)
    
    if not os.path.exists('instagram_cookies.json'):
        print("❌ instagram_cookies.json not found!")
        return False
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Load Instagram
        driver.get('https://www.instagram.com')
        time.sleep(2)
        
        # Load cookies
        with open('instagram_cookies.json', 'r') as f:
            cookies = json.load(f)
        
        print(f"Loading {len(cookies)} cookies...")
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Warning: Could not add cookie {cookie.get('name', 'unknown')}: {e}")
        
        # Refresh to apply cookies
        driver.get('https://www.instagram.com/')
        time.sleep(4)
        
        current_url = driver.current_url.lower()
        
        # Check if logged in
        if 'login' in current_url or 'accounts/login' in current_url:
            print("❌ Cookies verification failed - Not logged in")
            print("💡 The cookies might have expired. Please extract them again.")
            print(f"Current URL: {driver.current_url}")
            return False
        else:
            print("✅ Cookies verified successfully!")
            print("✅ You are logged in to Instagram")
            print(f"✅ Current URL: {driver.current_url}")
            
            # Try to find feed elements to confirm we're logged in
            try:
                driver.find_element(By.XPATH, "//article[@role='presentation' or contains(@class, 'post')]")
                print("✅ Instagram feed detected - fully authenticated!")
            except:
                print("⚠️  Feed not detected, but login successful")
            
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
    print("  INSTAGRAM COOKIE EXTRACTOR")
    print("=" * 60)
    print("\n📸 IMPORTANT INFORMATION:")
    print("\nInstagram posting requirements:")
    print("  • Images/videos are REQUIRED (no text-only posts)")
    print("  • Web posting has some limitations")
    print("  • May ask to save login info")
    print("  • May ask to turn on notifications")
    print("\n💡 TIPS FOR SUCCESS:")
    print("  • Use your actual Instagram account")
    print("  • Complete all prompts during login")
    print("  • Make sure you see your feed before pressing Enter")
    print("  • Keep images under 5MB for best results")
    print("=" * 60)
    
    proceed = input("\n👉 Do you want to continue? (y/n): ").lower().strip()
    
    if proceed != 'y':
        print("\n👋 Goodbye!")
        return
    
    # Extract cookies
    success = extract_instagram_cookies()
    
    if success:
        print("\n" + "=" * 60)
        verify = input("\n🔍 Do you want to verify the cookies? (y/n): ").lower().strip()
        
        if verify == 'y':
            verify_instagram_cookies()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print("\n💡 TIPS:")
    print("   - Instagram cookies typically last 60-90 days")
    print("   - Re-run this script if your cookies expire")
    print("   - Keep the cookies file secure")
    print("   - Don't share or commit to Git")
    print("   - Add to .gitignore: *.json")
    print("\n📝 NEXT STEPS:")
    print("   1. Place instagram_cookies.json in same folder as app.py")
    print("   2. Run: python app.py")
    print("   3. Open: http://localhost:5000")
    print("   4. Select Instagram and UPLOAD AN IMAGE")
    print("   5. Add caption and post!")
    print("\n⚠️  REMEMBER:")
    print("   Instagram REQUIRES an image or video!")
    print("   Text-only posts won't work!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
    