#!/usr/bin/env python3
"""
Enhanced screenshot capture script for py-perf-viewer dashboard views.
Captures both dark mode and light mode screenshots.
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Failed to start Chrome driver: {e}")
        return None

def set_theme(driver, theme):
    """Set the theme to dark or light mode."""
    try:
        # Execute JavaScript to set theme
        driver.execute_script(f"""
            document.documentElement.setAttribute('data-theme', '{theme}');
            localStorage.setItem('theme', '{theme}');
        """)
        
        # Update the icon to match the theme
        if theme == 'dark':
            driver.execute_script("""
                const icon = document.getElementById('darkModeIcon');
                if (icon) {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-lightbulb');
                    document.getElementById('darkModeToggle').title = 'Switch to Light Mode';
                }
            """)
        else:
            driver.execute_script("""
                const icon = document.getElementById('darkModeIcon');
                if (icon) {
                    icon.classList.remove('fa-lightbulb');
                    icon.classList.add('fa-moon');
                    document.getElementById('darkModeToggle').title = 'Switch to Dark Mode';
                }
            """)
        
        time.sleep(0.5)  # Wait for theme to apply
        print(f"  ✅ Set theme to {theme} mode")
        return True
        
    except Exception as e:
        print(f"  ❌ Error setting theme to {theme}: {e}")
        return False

def capture_screenshot(driver, url, filename, theme, description="", wait_element=None):
    """Capture a screenshot of the given URL in the specified theme."""
    print(f"📸 Capturing {description} ({theme} mode)")
    
    try:
        driver.get(url)
        
        # Wait for page to load
        if wait_element:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, wait_element))
                )
            except TimeoutException:
                print(f"  ⚠️  Timeout waiting for {wait_element}, proceeding anyway")
        else:
            time.sleep(3)  # Generic wait
        
        # Set the theme
        if not set_theme(driver, theme):
            return False
        
        # Take screenshot
        screenshot_path = f"screenshots/{filename}"
        driver.save_screenshot(screenshot_path)
        print(f"  ✅ Screenshot saved: {screenshot_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error capturing {url}: {e}")
        return False

def get_sample_data_urls(driver):
    """Try to find sample record and function URLs from the main page."""
    urls = {}
    
    try:
        driver.get("http://localhost:8000/records/")
        time.sleep(2)
        
        # Try to find a sample record link
        try:
            record_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/records/']")
            if record_links:
                for link in record_links:
                    href = link.get_attribute('href')
                    if href and href != "http://localhost:8000/records/":
                        urls['sample_record'] = href
                        break
        except NoSuchElementException:
            pass
        
        # Try to find a sample function link
        try:
            function_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/functions/']")
            if function_links:
                urls['sample_function'] = function_links[0].get_attribute('href')
        except NoSuchElementException:
            pass
            
    except Exception as e:
        print(f"Error finding sample URLs: {e}")
    
    return urls

def main():
    """Main screenshot capture process for both themes."""
    print("🎨 Starting PyPerf Dashboard Theme Screenshot Capture")
    print("=" * 60)
    
    # Set up driver
    driver = setup_driver()
    if not driver:
        return
    
    try:
        # Screenshots to capture
        screenshots_config = [
            {
                'url': 'http://localhost:8000/',
                'filename_template': '{theme}_dashboard_home.png',
                'description': 'Main Dashboard Home',
                'wait_element': 'body'
            },
            {
                'url': 'http://localhost:8000/records/',
                'filename_template': '{theme}_performance_records.png', 
                'description': 'Performance Records List',
                'wait_element': 'body'
            }
        ]
        
        # Capture screenshots for both themes
        themes = ['dark', 'light']
        
        for theme in themes:
            print(f"\n🌙 Capturing {theme.upper()} MODE screenshots")
            print("-" * 40)
            
            for config in screenshots_config:
                filename = config['filename_template'].format(theme=theme)
                capture_screenshot(
                    driver,
                    config['url'],
                    filename,
                    theme,
                    config['description'],
                    config.get('wait_element')
                )
                time.sleep(1)
        
        # Try to capture sample record and function pages for both themes
        print(f"\n🔍 Finding sample data URLs...")
        sample_urls = get_sample_data_urls(driver)
        
        if sample_urls:
            for theme in themes:
                print(f"\n📄 Capturing sample pages in {theme.upper()} mode")
                print("-" * 40)
                
                if 'sample_record' in sample_urls:
                    capture_screenshot(
                        driver,
                        sample_urls['sample_record'],
                        f'{theme}_record_detail.png',
                        theme,
                        'Individual Record Detail',
                        'body'
                    )
                    time.sleep(1)
                    
                if 'sample_function' in sample_urls:
                    capture_screenshot(
                        driver,
                        sample_urls['sample_function'],
                        f'{theme}_function_analysis.png',
                        theme,
                        'Function Analysis View',
                        'body'
                    )
                    time.sleep(1)
        else:
            print("⚠️  No sample data found, skipping detailed views")
        
        # Capture API endpoint in dark mode only (for variety)
        print(f"\n🔌 Capturing API endpoint")
        print("-" * 40)
        capture_screenshot(
            driver,
            'http://localhost:8000/api/metrics/',
            'dark_api_metrics.png',
            'dark',
            'API Metrics Endpoint',
            'body'
        )
        
    finally:
        driver.quit()
        print("\n✅ Theme screenshot capture complete!")
        print("📁 Check the screenshots/ directory for new theme-based screenshots.")

if __name__ == "__main__":
    main()