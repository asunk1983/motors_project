#!/usr/bin/env python3
"""Диагностический скрипт: проверка computed-стилей .modal-header и .detail-toolbar
в модалке карточки двигателя при прокрутке."""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'c:\motors_project')

# 1. Создаём пользователя в БД
from modules.db import db_connection, init_db
from modules.auth import auth as auth_module
from modules.auth.hashing import hash_password

init_db()
with db_connection() as conn:
    # Проверяем, есть ли уже пользователь
    user = auth_module.get_user_by_username(conn, 'diag')
    if user:
        # Обновляем пароль
        auth_module.update_user_password(conn, user['id'], 'diag123')
        print(f"User 'diag' already exists, password reset. ID={user['id']}")
    else:
        uid = auth_module.create_user(conn, 'diag', 'diag123', role='user')
        print(f"Created user 'diag' with ID={uid}")

# 2. Получаем токен через API
import urllib.request
login_data = json.dumps({'username': 'diag', 'password': 'diag123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/api/auth/login', data=login_data,
                             headers={'Content-Type': 'application/json'}, method='POST')
resp = urllib.request.urlopen(req)
login_resp = json.loads(resp.read())
token = login_resp['token']
print(f"Got token: {token[:20]}...")

# 3. Запускаем Playwright
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})

    # Устанавливаем токен в localStorage до загрузки страницы
    page.goto('http://localhost:5000/')
    page.wait_for_load_state('networkidle')

    # Вводим токен в localStorage и перезагружаем
    page.evaluate(f"""() => {{
        localStorage.setItem('motors_auth_token', '{token}');
        localStorage.setItem('motors_auth_user', JSON.stringify({{username: 'diag', role: 'user'}}));
    }}""")
    page.reload()
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    # Проверяем, что мы не на экране логина
    login_overlay = page.query_selector('#login-overlay')
    if login_overlay:
        print("WARNING: Login overlay is still visible!")
    else:
        print("Login overlay is hidden - good")

    # Кликаем по первой строке таблицы (она имеет onclick="showDetail(id)")
    first_row = page.query_selector('.clickable-row')
    if first_row:
        first_row.click()
        print("Clicked on first engine row")
    else:
        print("ERROR: No clickable-row found")
        browser.close()
        sys.exit(1)

    # Ждём появления модалки
    page.wait_for_selector('#detailModal.active', timeout=5000)
    print("Detail modal is active")

    # Ждём загрузки контента
    page.wait_for_selector('.detail-toolbar', timeout=5000)
    time.sleep(1)  # Дать время на рендер

    # Проверяем computed-стили ДО прокрутки
    print("\n=== BEFORE SCROLL ===")
    header_styles = page.evaluate("""() => {
        const h = document.querySelector('.modal-header');
        if (!h) return null;
        const s = window.getComputedStyle(h);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'classList': h.className,
            'inlineStyle': h.getAttribute('style'),
        };
    }""")
    print(f".modal-header: {json.dumps(header_styles, indent=2, ensure_ascii=False)}")

    toolbar_styles = page.evaluate("""() => {
        const t = document.querySelector('.detail-toolbar');
        if (!t) return null;
        const s = window.getComputedStyle(t);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'classList': t.className,
            'inlineStyle': t.getAttribute('style'),
        };
    }""")
    print(f".detail-toolbar: {json.dumps(toolbar_styles, indent=2, ensure_ascii=False)}")

    modal_content_styles = page.evaluate("""() => {
        const mc = document.querySelector('.modal-content');
        if (!mc) return null;
        const s = window.getComputedStyle(mc);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'filter': s.filter,
            'backdrop-filter': s.backdropFilter,
            'classList': mc.className,
            'inlineStyle': mc.getAttribute('style'),
        };
    }""")
    print(f".modal-content: {json.dumps(modal_content_styles, indent=2, ensure_ascii=False)}")

    modal_body_styles = page.evaluate("""() => {
        const mb = document.querySelector('.modal-body');
        if (!mb) return null;
        const s = window.getComputedStyle(mb);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'filter': s.filter,
            'backdrop-filter': s.backdropFilter,
            'classList': mb.className,
            'inlineStyle': mb.getAttribute('style'),
        };
    }""")
    print(f".modal-body: {json.dumps(modal_body_styles, indent=2, ensure_ascii=False)}")

    # Прокручиваем вниз
    page.evaluate("""() => {
        const body = document.querySelector('.modal-body');
        if (body) body.scrollTop = body.scrollHeight;
    }""")
    time.sleep(0.5)

    # Проверяем computed-стили ПОСЛЕ прокрутки
    print("\n=== AFTER SCROLL ===")
    header_styles2 = page.evaluate("""() => {
        const h = document.querySelector('.modal-header');
        if (!h) return null;
        const s = window.getComputedStyle(h);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'classList': h.className,
            'inlineStyle': h.getAttribute('style'),
        };
    }""")
    print(f".modal-header: {json.dumps(header_styles2, indent=2, ensure_ascii=False)}")

    toolbar_styles2 = page.evaluate("""() => {
        const t = document.querySelector('.detail-toolbar');
        if (!t) return null;
        const s = window.getComputedStyle(t);
        return {
            'background-color': s.backgroundColor,
            'background': s.background,
            'opacity': s.opacity,
            'z-index': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'classList': t.className,
            'inlineStyle': t.getAttribute('style'),
        };
    }""")
    print(f".detail-toolbar: {json.dumps(toolbar_styles2, indent=2, ensure_ascii=False)}")

    # Проверяем, какие элементы находятся под курсором в центре шапки
    print("\n=== ELEMENT UNDER CURSOR (center of modal-header) ===")
    header_rect = page.evaluate("""() => {
        const h = document.querySelector('.modal-header');
        if (!h) return null;
        const r = h.getBoundingClientRect();
        return { top: r.top, left: r.left, width: r.width, height: r.height };
    }""")
    print(f".modal-header rect: {json.dumps(header_rect, indent=2)}")

    if header_rect:
        x = header_rect['left'] + header_rect['width'] / 2
        y = header_rect['top'] + header_rect['height'] / 2
        element_under = page.evaluate(f"""() => {{
            const el = document.elementFromPoint({x}, {y});
            if (!el) return null;
            return {{
                'tagName': el.tagName,
                'className': el.className,
                'id': el.id,
                'textContent': el.textContent ? el.textContent.substring(0, 100) : '',
                'parentChain': (function() {{
                    let chain = [];
                    let p = el;
                    for (let i = 0; i < 8 && p; i++) {{
                        chain.push(p.tagName + '.' + (p.className || '') + (p.id ? '#' + p.id : ''));
                        p = p.parentElement;
                    }}
                    return chain;
                }})(),
            }};
        }}""")
        print(f"Element under cursor: {json.dumps(element_under, indent=2, ensure_ascii=False)}")

    # Проверяем stacking context
    print("\n=== STACKING CONTEXT CHECK ===")
    stacking = page.evaluate("""() => {
        const mc = document.querySelector('.modal-content');
        if (!mc) return null;
        const s = window.getComputedStyle(mc);
        return {
            'transform': s.transform,
            'opacity': s.opacity,
            'filter': s.filter,
            'backdropFilter': s.backdropFilter,
            'zIndex': s.zIndex,
            'position': s.position,
            'mixBlendMode': s.mixBlendMode,
            'isolation': s.isolation,
            'willChange': s.willChange,
            'contain': s.contain,
        };
    }""")
    print(f".modal-content stacking props: {json.dumps(stacking, indent=2)}")

    # Проверяем .modal (overlay)
    modal_overlay = page.evaluate("""() => {
        const m = document.querySelector('.modal');
        if (!m) return null;
        const s = window.getComputedStyle(m);
        return {
            'backdropFilter': s.backdropFilter,
            'zIndex': s.zIndex,
            'position': s.position,
            'transform': s.transform,
            'opacity': s.opacity,
            'filter': s.filter,
        };
    }""")
    print(f".modal overlay: {json.dumps(modal_overlay, indent=2)}")

    # Проверяем классы .glass и .slide-out
    print("\n=== GLASS/SLIDE-OUT CLASSES ===")
    classes = page.evaluate("""() => {
        const mc = document.querySelector('.modal-content');
        return {
            'modal-content classes': mc ? mc.className : 'NOT FOUND',
            'has glass': mc ? mc.classList.contains('glass') : false,
            'has slide-out': mc ? mc.classList.contains('slide-out') : false,
        };
    }""")
    print(f"Classes: {json.dumps(classes, indent=2)}")

    # Делаем скриншот для визуальной проверки
    page.screenshot(path='c:/motors_project/diag_modal_screenshot.png', full_page=False)
    print("\nScreenshot saved to diag_modal_screenshot.png")

    browser.close()
    print("\n=== DONE ===")
