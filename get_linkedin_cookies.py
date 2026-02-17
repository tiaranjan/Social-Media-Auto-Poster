"""
LinkedIn Cookie Extractor
This script helps you extract cookies from LinkedIn after manual login
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time

def extract_linkedin_cookies():
    """
    Extract LinkedIn cookies after manual login
    """
    print("=" * 60)
    print("LinkedIn Cookie Extractor")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Open LinkedIn in a browser")
    print("2. Wait for you to log in manually")
    print("3. Extract and save cookies to linkedin_cookies.json")
    print("\n" + "=" * 60)
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add user agent to appear more like a real browser
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    print("\n🌐 Opening Chrome browser...")
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to LinkedIn
        driver.get('https://www.linkedin.com/login')
        print("✅ LinkedIn login page loaded")
        
        print("\n" + "=" * 60)
        print("⚠️  PLEASE LOG IN TO LINKEDIN NOW")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Enter your LinkedIn email and password")
        print("2. Complete any 2FA/verification if required")
        print("3. Wait until you see your LinkedIn feed")
        print("4. Come back to this terminal and press Enter")
        print("\n⏳ Waiting for you to log in...")
        
        # Wait for user to log in
        input("\n👉 Press Enter after you've logged in and see your feed...")
        
        # Verify login by checking if we're on the feed page
        current_url = driver.current_url
        print(f"\n📍 Current URL: {current_url}")
        
        if 'login' in current_url.lower():
            print("\n❌ Still on login page. Please log in first!")
            print("Rerun the script and make sure you complete the login.")
            return False
        
        print("\n✅ Login detected! Extracting cookies...")
        
        # Get all cookies
        cookies = driver.get_cookies()
        
        if not cookies:
            print("\n❌ No cookies found!")
            return False
        
        print(f"✅ Found {len(cookies)} cookies")
        
        # Save cookies to JSON file
        filename = 'linkedin_cookies.json'
        with open(filename, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n✅ Cookies saved to: {filename}")
        print("\n" + "=" * 60)
        print("Cookie Details:")
        print("=" * 60)
        
        # Show important cookies
        important_cookies = ['li_at', 'JSESSIONID', 'lidc']
        for cookie_name in important_cookies:
            cookie = next((c for c in cookies if c['name'] == cookie_name), None)
            if cookie:
                print(f"✓ {cookie_name}: Found")
            else:
                print(f"✗ {cookie_name}: Not found (might cause issues)")
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"\nYour cookies have been saved to: {filename}")
        print("\nYou can now use this file with the Social Media Auto Poster!")
        print("\n⚠️  Keep this file private - it contains your login session!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
        
    finally:
        print("\n🔒 Closing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("✅ Browser closed")

def verify_cookies():
    """
    Verify if the extracted cookies work
    """
    print("\n" + "=" * 60)
    print("Verifying Cookies...")
    print("=" * 60)
    
    if not os.path.exists('linkedin_cookies.json'):
        print("❌ linkedin_cookies.json not found!")
        return False
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Load LinkedIn
        driver.get('https://www.linkedin.com')
        time.sleep(2)
        
        # Load cookies
        with open('linkedin_cookies.json', 'r') as f:
            cookies = json.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except:
                pass
        
        # Refresh to apply cookies
        driver.get('https://www.linkedin.com/feed/')
        time.sleep(3)
        
        # Check if logged in
        if 'login' in driver.current_url.lower():
            print("❌ Cookies verification failed - Not logged in")
            print("💡 The cookies might have expired. Please extract them again.")
            return False
        else:
            print("✅ Cookies verified successfully!")
            print("✅ You are logged in to LinkedIn")
            return True
            
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    import os
    
    print("\n" + "=" * 60)
    print("  LINKEDIN COOKIE EXTRACTOR")
    print("=" * 60)
    
    # Extract cookies
    success = extract_linkedin_cookies()
    
    if success:
        print("\n" + "=" * 60)
        verify = input("\n🔍 Do you want to verify the cookies? (y/n): ").lower().strip()
        
        if verify == 'y':
            verify_cookies()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print("\n💡 Tips:")
    print("   - Cookies typically last 30-90 days")
    print("   - Re-run this script if your cookies expire")
    print("   - Keep the cookies file secure")
    print("   - Don't share or commit to Git")
    print("\n✅ You can now use linkedin_cookies.json with the auto poster!")
    print("=" * 60 + "\n")