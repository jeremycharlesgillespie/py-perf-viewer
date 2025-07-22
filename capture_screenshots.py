#!/usr/bin/env python3
"""
Screenshot capture script for py-perf-viewer dashboard views.
Uses Selenium with Chrome/Chromium in headless mode.
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
    
    # Try different Chrome binary locations
    chrome_binaries = [
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium'
    ]
    
    for binary in chrome_binaries:
        if os.path.exists(binary):
            chrome_options.binary_location = binary
            break
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Failed to start Chrome driver: {e}")
        print("Please install ChromeDriver or ensure Chrome/Chromium is installed")
        return None

def capture_screenshot(driver, url, filename, wait_element=None, description=""):
    """Capture a screenshot of the given URL."""
    print(f"📸 Capturing {description}: {url}")
    
    try:
        driver.get(url)
        
        # Wait for page to load
        if wait_element:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, wait_element))
                )
            except TimeoutException:
                print(f"⚠️  Timeout waiting for {wait_element}, proceeding anyway")
        else:
            time.sleep(3)  # Generic wait
        
        # Take screenshot
        screenshot_path = f"screenshots/{filename}"
        driver.save_screenshot(screenshot_path)
        print(f"✅ Screenshot saved: {screenshot_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error capturing {url}: {e}")
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
            print("No record links found")
        
        # Try to find a sample function link
        try:
            function_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/functions/']")
            if function_links:
                urls['sample_function'] = function_links[0].get_attribute('href')
        except NoSuchElementException:
            print("No function links found")
            
    except Exception as e:
        print(f"Error finding sample URLs: {e}")
    
    return urls

def main():
    """Main screenshot capture process."""
    print("🚀 Starting PyPerf Dashboard Screenshot Capture")
    print("=" * 50)
    
    # Set up driver
    driver = setup_driver()
    if not driver:
        return
    
    try:
        # Base URLs to capture
        screenshots = [
            {
                'url': 'http://localhost:8000/',
                'filename': '01_dashboard_home.png',
                'description': 'Main Dashboard Home',
                'wait_element': 'body'
            },
            {
                'url': 'http://localhost:8000/records/',
                'filename': '02_performance_records.png', 
                'description': 'Performance Records List',
                'wait_element': 'body'
            }
        ]
        
        # Capture main screenshots
        for screenshot in screenshots:
            capture_screenshot(
                driver,
                screenshot['url'],
                screenshot['filename'],
                screenshot.get('wait_element'),
                screenshot['description']
            )
            time.sleep(1)
        
        # Try to find and capture sample record and function pages
        sample_urls = get_sample_data_urls(driver)
        
        if 'sample_record' in sample_urls:
            capture_screenshot(
                driver,
                sample_urls['sample_record'],
                '03_record_detail.png',
                'body',
                'Individual Record Detail'
            )
        else:
            print("⚠️  No sample record found, skipping record detail screenshot")
            
        if 'sample_function' in sample_urls:
            capture_screenshot(
                driver,
                sample_urls['sample_function'],
                '04_function_analysis.png',
                'body', 
                'Function Analysis View'
            )
        else:
            print("⚠️  No sample function found, skipping function analysis screenshot")
        
        # Capture API endpoints (JSON responses)
        api_endpoints = [
            ('http://localhost:8000/api/metrics/', '05_api_metrics.png', 'API Metrics Endpoint'),
            ('http://localhost:8000/api/hostnames/', '06_api_hostnames.png', 'API Hostnames Endpoint'),
            ('http://localhost:8000/api/functions/', '07_api_functions.png', 'API Functions Endpoint')
        ]
        
        for url, filename, description in api_endpoints:
            capture_screenshot(driver, url, filename, 'body', description)
            time.sleep(1)
        
    finally:
        driver.quit()
        print("\n✅ Screenshot capture complete! Check the screenshots/ directory.")

if __name__ == "__main__":
    main()