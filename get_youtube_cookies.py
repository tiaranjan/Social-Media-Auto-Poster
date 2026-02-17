from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

def get_youtube_cookies():
    """
    Get YouTube cookies by logging in manually
    This will open a browser where you need to log in to YouTube
    """
    print("=" * 60)
    print("YouTube Cookie Extractor")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Open YouTube in a browser")
    print("2. Wait for you to log in manually")
    print("3. Save your cookies to 'youtube_cookies.json'")
    print("\nIMPORTANT: You have 5 minutes to log in!")
    print("=" * 60)
    
    # Setup Chrome with visible window (NOT headless)
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Go to YouTube
        print("\n✓ Opening YouTube...")
        driver.get('https://www.youtube.com')
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("PLEASE LOG IN TO YOUTUBE NOW")
        print("=" * 60)
        print("\nSteps:")
        print("1. Click 'Sign in' button in the browser")
        print("2. Enter your email and password")
        print("3. Complete any 2FA if required")
        print("4. Wait until you see your YouTube homepage")
        print("\nYou have 5 minutes to complete login...")
        print("=" * 60)
        
        # Wait for user to log in (5 minutes timeout)
        wait_time = 300  # 5 minutes
        interval = 5
        elapsed = 0
        
        logged_in = False
        
        while elapsed < wait_time:
            # Check if logged in by looking for user avatar or account button
            try:
                # Check for multiple indicators of being logged in
                indicators = [
                    "//button[@id='avatar-btn']",  # User avatar button
                    "//img[@id='img']",  # Profile image
                    "//yt-icon-button[@id='guide-button']",  # Guide button (left menu)
                    "//ytd-topbar-menu-button-renderer[@id='button-shape']"  # Account button
                ]
                
                for indicator in indicators:
                    try:
                        element = driver.find_element(By.XPATH, indicator)
                        if element:
                            logged_in = True
                            break
                    except:
                        continue
                
                if logged_in:
                    print(f"\n✓ Login detected!")
                    break
                    
            except:
                pass
            
            # Show countdown
            remaining = wait_time - elapsed
            mins = remaining // 60
            secs = remaining % 60
            print(f"\rWaiting for login... Time remaining: {mins}m {secs}s", end="", flush=True)
            
            time.sleep(interval)
            elapsed += interval
        
        if not logged_in:
            print("\n\n❌ Timeout! Login not detected.")
            print("Please try again and log in faster.")
            return False
        
        # Give a bit more time for all cookies to load
        print("\n\n✓ Login successful! Waiting for cookies to load...")
        time.sleep(5)
        
        # Get all cookies
        cookies = driver.get_cookies()
        
        # Save to file
        with open('youtube_cookies.json', 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n✓ SUCCESS! Saved {len(cookies)} cookies to 'youtube_cookies.json'")
        print("\n" + "=" * 60)
        print("Cookie Summary:")
        print("=" * 60)
        
        important_cookies = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'LOGIN_INFO']
        found_important = []
        
        for cookie in cookies:
            if cookie['name'] in important_cookies:
                found_important.append(cookie['name'])
                print(f"✓ Found: {cookie['name']}")
        
        if len(found_important) >= 3:
            print("\n✓ All important cookies captured!")
            print("\nYou can now close the browser.")
            print("Your cookies are saved in 'youtube_cookies.json'")
        else:
            print("\n⚠ Warning: Some important cookies might be missing")
            print("You may need to try again")
        
        print("=" * 60)
        
        # Keep browser open for 10 seconds so user can see the message
        print("\nBrowser will close in 10 seconds...")
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
        
    finally:
        driver.quit()
        print("\n✓ Browser closed")


if __name__ == "__main__":
    print("\n")
    input("Press ENTER to start the cookie extraction process...")
    print("\n")
    
    success = get_youtube_cookies()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ DONE! Your YouTube cookies are ready to use.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Failed to get cookies. Please try again.")
        print("=" * 60)
    
    print("\n")