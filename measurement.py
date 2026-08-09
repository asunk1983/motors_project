#!/usr/bin/env python3
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'c:\motors_project')

# 1. Create user in DB
from modules.db import db_connection, init_db
from modules.auth import auth as auth_module
from modules.auth.hashing import hash_password

init_db()
with db_connection() as conn:
    user = auth_module.get_user_by_username(conn, 'diag')
    if user:
        auth_module.update_user_password(conn, user['id'], 'diag123')
        print(f"User 'diag' already exists, password reset. ID={user['id']}")
    else:
        uid = auth_module.create_user(conn, 'diag', 'diag123', role='user')
        print(f"Created user 'diag' with ID={uid}")

# 2. Get token via API
import urllib.request
login_data = json.dumps({'username': 'diag', 'password': 'diag123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/api/auth/login', data=login_data,
                             headers={'Content-Type': 'application/json'}, method='POST')
resp = urllib.request.urlopen(req)
login_resp = json.loads(resp.read())
token = login_resp['token']
print(f"Got token: {token[:20]}...")

# 3. Launch Playwright
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})

    page.goto('http://localhost:5000/')
    page.wait_for_load_state('networkidle')

    # Set token in localStorage
    set_token_js = (
        "() => {"
        "localStorage.setItem('motors_auth_token', '" + token + "');"
        "localStorage.setItem('motors_auth_user', JSON.stringify({username: 'diag', role: 'user'}));"
        "}"
    )
    page.evaluate(set_token_js)
    page.reload()
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    login_overlay = page.query_selector('#login-overlay')
    if login_overlay:
        print("WARNING: Login overlay is still visible!")
    else:
        print("Login overlay is hidden - good")

    first_row = page.query_selector('.clickable-row')
    if first_row:
        first_row.click()
        print("Clicked on first engine row")
    else:
        print("ERROR: No clickable-row found")
        browser.close()
        sys.exit(1)

    page.wait_for_selector('#detailModal.active', timeout=5000)
    print("Detail modal is active")
    page.wait_for_selector('.detail-toolbar', timeout=5000)
    time.sleep(1)

    # Function to get measurements
    def get_measurements():
        data = page.evaluate("""() => {
            const getStyle = (el) => {
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return {
                    offsetTop: el.offsetTop,
                    offsetHeight: el.offsetHeight,
                    clientHeight: el.clientHeight,
                    scrollHeight: el.scrollHeight,
                    boundingClientRect: el.getBoundingClientRect(),
                    position: s.position,
                    display: s.display,
                    margin: [s.marginTop, s.marginRight, s.marginBottom, s.marginLeft],
                    padding: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft],
                    border: [s.borderTopWidth, s.borderRightWidth, s.borderBottomWidth, s.borderLeftWidth],
                    boxSizing: s.boxSizing,
                    transform: s.transform,
                    overflow: s.overflow,
                    zIndex: s.zIndex
                };
            };
            const detailContent = document.querySelector('#detailContent');
            const detailToolbar = document.querySelector('.detail-toolbar');
            const detailToolbarInfo = document.querySelector('.detail-toolbar-info');
            const detailToolbarNav = document.querySelector('.detail-toolbar-nav');
            const firstSubsectionHeader = document.querySelector('.detail-subsection-header');
            return {
                detailContent: getStyle(detailContent),
                detailToolbar: getStyle(detailToolbar),
                detailToolbarInfo: getStyle(detailToolbarInfo),
                detailToolbarNav: getStyle(detailToolbarNav),
                firstSubsectionHeader: getStyle(firstSubsectionHeader)
            };
        }""")
        return data

    print("=== BEFORE SCROLL ===")
    before = get_measurements()
    print(json.dumps(before, indent=2, ensure_ascii=False))

    # Scroll to bottom
    page.evaluate("""() => {
        const body = document.querySelector('.modal-body');
        if (body) body.scrollTop = body.scrollHeight;
    }""")
    time.sleep(0.5)

    print("=== AFTER SCROLL ===")
    after = get_measurements()
    print(json.dumps(after, indent=2, ensure_ascii=False))

    # For .detail-toolbar and first .detail-subsection-header output top, bottom, height
    def get_positions(state_label, data):
        toolbar = data['detailToolbar']
        subsection = data['firstSubsectionHeader']
        if toolbar:
            rect = toolbar['boundingClientRect']
            print(f"{state_label} .detail-toolbar: top={rect.top}, bottom={rect.bottom}, height={rect.height}")
        if subsection:
            rect = subsection['boundingClientRect']
            print(f"{state_label} first .detail-subsection-header: top={rect.top}, bottom={rect.bottom}, height={rect.height}")

    get_positions("BEFORE", before)
    get_positions("AFTER", after)

    page.screenshot(path='c:/motors_project/measurement_screenshot.png', full_page=False)
    print("\nScreenshot saved to measurement_screenshot.png")

    browser.close()
    print("\n=== DONE ===")
</arg_value></tool_call>