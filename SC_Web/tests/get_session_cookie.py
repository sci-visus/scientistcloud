#!/usr/bin/env python3
"""
Helper script to get PHPSESSID cookie from SC_Web after authentication.

SC_Web uses PHP sessions with PHPSESSID cookie for authentication.
After logging in via Auth0, SC_Web sets a PHPSESSID cookie that we need for tests.

Usage:
    # Method 1: Manual (Recommended - Simplest)
    1. Login to SC_Web in your browser: http://localhost:8080/login.php
    2. Complete Auth0 login flow
    3. After successful login, open DevTools (F12)
    4. Go to: Application/Storage → Cookies → http://localhost:8080
    5. Find and copy the value of 'PHPSESSID' cookie
    6. Export: export SC_WEB_SESSION_COOKIE="<paste_cookie_value_here>"
    7. Run tests: pytest test_upload_e2e.py -v

    # Method 2: This script (opens browser for you)
    python get_session_cookie.py
    (Then follow steps 3-7 above)

Note: The PHPSESSID cookie is different from Auth0 session cookies.
SC_Web creates its own PHP session after Auth0 authentication.
"""

import os
import sys
import requests
from urllib.parse import urlparse, parse_qs
import webbrowser
import time

# Configuration
SC_WEB_BASE_URL = os.getenv('SC_WEB_BASE_URL', 'http://localhost:8080')
LOGIN_URL = f"{SC_WEB_BASE_URL}/login.php"

def get_cookie_from_browser():
    """
    Interactive method: Opens browser for user to login, then extracts cookie.
    
    Note: This is a simplified version. For full OAuth flow, you'd need to:
    1. Start a local server to receive the OAuth callback
    2. Handle the Auth0 redirect
    3. Extract the session cookie from the callback
    
    For now, we'll use the manual method (see instructions above).
    """
    print("="*60)
    print("SC_Web Session Cookie Extractor")
    print("="*60)
    print(f"\nSC_Web URL: {SC_WEB_BASE_URL}")
    print(f"Login URL: {LOGIN_URL}")
    print("\n" + "="*60)
    print("MANUAL METHOD (Recommended):")
    print("="*60)
    print("1. Open your browser and go to:")
    print(f"   {LOGIN_URL}")
    print("\n2. Complete the Auth0 login flow")
    print("\n3. After login, open browser DevTools (F12)")
    print("   → Go to Application/Storage tab")
    print("   → Click on Cookies → http://localhost:8080")
    print("   → Find 'PHPSESSID' cookie")
    print("   → Copy its value")
    print("\n4. Export the cookie:")
    print("   export SC_WEB_SESSION_COOKIE=\"<paste_cookie_value_here>\"")
    print("\n5. Run your tests:")
    print("   pytest test_upload_e2e.py -v")
    print("\n" + "="*60)
    print("PROGRAMMATIC METHOD (Alternative):")
    print("="*60)
    print("If you want to extract the cookie programmatically, you can:")
    print("1. Use browser automation (Selenium/Playwright)")
    print("2. Or use the manual method above (simpler)")
    print("\n" + "="*60)
    
    # Try to open browser
    try:
        print(f"\nOpening browser to {LOGIN_URL}...")
        webbrowser.open(LOGIN_URL)
        print("After you login, check your browser's cookies for PHPSESSID")
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually visit: {LOGIN_URL}")

def extract_cookie_from_response(response):
    """Extract PHPSESSID cookie from a response."""
    cookies = response.cookies
    if 'PHPSESSID' in cookies:
        return cookies['PHPSESSID']
    return None

def check_existing_session():
    """Check if we can access SC_Web with existing session."""
    session = requests.Session()
    
    # Try to access a protected page
    try:
        response = session.get(f"{SC_WEB_BASE_URL}/index.php", allow_redirects=True, timeout=5)
        
        # Check if we got redirected to login (not authenticated)
        if 'login' in response.url.lower():
            return None, "Not authenticated - redirected to login"
        
        # Check for PHPSESSID in cookies
        phpsessid = extract_cookie_from_response(response)
        if phpsessid:
            return phpsessid, "Found existing session"
        
        return None, "No session cookie found"
        
    except Exception as e:
        return None, f"Error checking session: {e}"

if __name__ == "__main__":
    print("\nChecking for existing session...")
    cookie, message = check_existing_session()
    
    if cookie:
        print(f"✅ {message}")
        print(f"\nPHPSESSID: {cookie}")
        print(f"\nExport this cookie:")
        print(f'export SC_WEB_SESSION_COOKIE="{cookie}"')
    else:
        print(f"❌ {message}")
        print("\n" + "="*60)
        get_cookie_from_browser()

