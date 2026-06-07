import base64
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import List
from urllib.parse import parse_qs, urlparse

import config
from core.analytics import calculate_mastery
from services.learning_service import LearningService
from utils.security import signed_cookie, verify_signed_cookie


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class LearningHandler(BaseHTTPRequestHandler):
    _service_cache = None

    def _is_allowed_host(self) -> bool:
        if not config.ALLOWED_HOSTS:
            return True
        remote = self.client_address[0]
        return remote in config.ALLOWED_HOSTS or '*' in config.ALLOWED_HOSTS

    def _get_current_user(self) -> str:
        cookie = self.headers.get('Cookie', '')
        for part in cookie.split(';'):
            if '=' not in part:
                continue
            name, value = part.strip().split('=', 1)
            if name == 'learning_user':
                return verify_signed_cookie(value, config.APP_SECRET)
        return ''

    def _set_user_cookie(self, username: str) -> None:
        cookie_value = signed_cookie(username, config.APP_SECRET)
        self.send_header('Set-Cookie', f'learning_user={cookie_value}; Path=/; HttpOnly')

    def _clear_user_cookie(self) -> None:
        self.send_header('Set-Cookie', 'learning_user=; Path=/; HttpOnly; Max-Age=0')

    def _get_service(self) -> LearningService:
        if getattr(self, '_service_cache', None) is None:
            username = self._get_current_user() or 'default'
            # Pass both profile_name and username to LearningService for user-scoped access
            self._service_cache = LearningService(profile_name=username, username=username)
        return self._service_cache

    @property
    def service(self) -> LearningService:
        return self._get_service()

    def _is_login_path(self) -> bool:
        path = urlparse(self.path).path
        return path in ('/login', '/register', '/logout', '/health', '/metrics')

    def _is_authenticated(self) -> bool:
        if self._get_current_user():
            return True
        if not config.WEB_AUTH_USER or not config.WEB_AUTH_PASS:
            return True
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return False
        encoded = auth_header.split(' ', 1)[1]
        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
        except Exception:
            return False
        if ':' not in decoded:
            return False
        username, password = decoded.split(':', 1)
        return username == config.WEB_AUTH_USER and password == config.WEB_AUTH_PASS

    def _require_auth(self) -> bool:
        if self._is_login_path() or self._is_authenticated():
            return True
        if config.WEB_AUTH_USER and config.WEB_AUTH_PASS:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Adaptive Learning Engine"')
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>401 Unauthorized</h1><p>Authentication is required to access this page.</p></body></html>')
            return False
        self.send_response(303)
        self.send_header('Location', '/login')
        self.end_headers()
        return False

    def send_error(self, code: int, message: str = None, explain: str = None) -> None:
        self.log_error('code %d, message %s', code, message)
        short_message = message or self.responses.get(code, ('', ''))[0]
        long_message = explain or self.responses.get(code, ('', ''))[1]
        content = f"""
            <html>
                <head><title>Error {code}</title></head>
                <body style='font-family:Segoe UI, sans-serif;background:#f7f9ff;color:#22303f;padding:40px;'>
                    <h1>Error {code}</h1>
                    <p><strong>{short_message}</strong></p>
                    <p>{long_message}</p>
                    <p><a href='/'>← Back to home</a></p>
                </body>
            </html>
        """
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def log_message(self, format: str, *args) -> None:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'{timestamp} {self.address_string()} - {format % args}')

    def _render_page(self, title: str, body: str) -> None:
        content = f"""
        <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        min-height: 100vh;
                        background: radial-gradient(circle at top left, #ffecf5 15%, transparent 0%),
                                    radial-gradient(circle at bottom right, #d0f0fd 20%, transparent 0%),
                                    linear-gradient(180deg, #f3f7ff 0%, #fff 100%);
                        color: #22303f;
                    }}
                            body.dark-mode {{
                                background: radial-gradient(circle at top left, rgba(85, 43, 112, 0.18) 15%, transparent 0%),
                                            radial-gradient(circle at bottom right, rgba(20, 37, 74, 0.22) 20%, transparent 0%),
                                            linear-gradient(180deg, #121429 0%, #1f2437 100%);
                                color: #f0f4ff;
                            }}
                    h1 {{
                        color: #45327e;
                        margin-bottom: 8px;
                    }}
                            body.dark-mode h1 {{ color: #f2e9ff; }}
                    p {{ color: #4e5f76; }}
                            body.dark-mode p {{ color: #d8ddef; }}
                    section {{
                        margin-bottom: 24px;
                        padding: 22px;
                        border: none;
                        border-radius: 22px;
                        background: rgba(255, 255, 255, 0.9);
                        box-shadow: 0 16px 34px rgba(68, 75, 123, 0.12);
                    }}
                            body.dark-mode section {{
                                background: rgba(22, 28, 49, 0.86);
                                box-shadow: 0 16px 34px rgba(0, 0, 0, 0.35);
                            }}
                    .hero {{
                        max-width: 1000px;
                        margin: auto;
                        padding: 20px;
                        background: rgba(255, 255, 255, 0.95);
                    }}
                            body.dark-mode .hero {{ background: rgba(34, 37, 57, 0.88); }}
                    label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
                    input, button, textarea {{
                        width: 100%;
                        max-width: 420px;
                        padding: 12px 14px;
                        margin-top: 4px;
                        border-radius: 14px;
                        border: 1px solid #d9e4fd;
                        background: #f7f9ff;
                        font-size: 0.95rem;
                    }}
                            body.dark-mode input, body.dark-mode textarea {{
                                border-color: #3f4a74;
                                background: #1d2438;
                                color: #f0f4ff;
                            }}
                    input:focus, textarea:focus {{
                        outline: none;
                        border-color: #7b6ce0;
                        box-shadow: 0 0 0 4px rgba(123, 108, 224, 0.12);
                        background: #fff;
                    }}
                            body.dark-mode input:focus, body.dark-mode textarea:focus {{
                                border-color: #a58dff;
                                box-shadow: 0 0 0 4px rgba(165, 141, 255, 0.18);
                                background: #2b324f;
                            }}
                    button {{
                        margin-top: 12px;
                        background: linear-gradient(135deg, #6a5de6, #9f7ae8);
                        color: white;
                        border: none;
                        cursor: pointer;
                        box-shadow: 0 12px 20px rgba(105, 62, 190, 0.2);
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                    }}
                            button.theme-toggle {{
                                width: auto;
                                padding: 10px 14px;
                                border-radius: 999px;
                                margin: 12px;
                                background: rgba(255, 255, 255, 0.92);
                                color: #45327e;
                                box-shadow: 0 8px 18px rgba(105, 62, 190, 0.14);
                                position: fixed;
                                top: 12px;
                                right: 12px;
                                z-index: 999;
                            }}
                            body.dark-mode button.theme-toggle {{
                                background: rgba(255, 255, 255, 0.08);
                                color: #f4f7ff;
                                box-shadow: 0 8px 18px rgba(0,0,0,0.4);
                            }}
                    button:hover {{
                        transform: translateY(-1px);
                        box-shadow: 0 18px 28px rgba(105, 62, 190, 0.25);
                    }}
                    a {{ color: #6a5de6; text-decoration: none; }}
                            body.dark-mode a {{ color: #d9c4ff; }}
                    a:hover {{ text-decoration: underline; }}
                    ul {{ padding-left: 20px; }}
                    li {{ margin-bottom: 8px; }}
                </style>
                <script>
                    function toggleTheme() {{
                        const body = document.body;
                        body.classList.toggle('dark-mode');
                        localStorage.setItem('page-theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
                        const btn = document.getElementById('theme-button');
                        if (btn) btn.innerText = body.classList.contains('dark-mode') ? 'Light' : 'Dark';
                    }}
                    window.addEventListener('DOMContentLoaded', () => {{
                        const theme = localStorage.getItem('page-theme');
                        if (theme === 'dark') document.body.classList.add('dark-mode');
                        const btn = document.getElementById('theme-button');
                        if (btn) btn.innerText = document.body.classList.contains('dark-mode') ? 'Light' : 'Dark';
                    }});
                </script>
            </head>
            <body>
                <button id='theme-button' class='theme-toggle' onclick='toggleTheme()'>Dark</button>
                <h1>Adaptive Learning Engine</h1>
                {body}
            </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header('Location', location)
        self.end_headers()

    def _parse_form(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        return {key: values[0] for key, values in parse_qs(body).items()}

    def do_GET(self) -> None:
        start = time.perf_counter()
        try:
            if not self._is_allowed_host():
                self.send_error(403, 'Forbidden: host not allowed')
                return
            if not self._require_auth():
                return
            path = urlparse(self.path).path
            if path == '/login':
                self._render_page('Login', self._login_content())
            elif path == '/register':
                self._render_page('Register', self._register_content())
            elif path == '/logout':
                self.send_response(303)
                self._clear_user_cookie()
                self.send_header('Location', '/login')
                self.end_headers()
            elif path == '/':
                self._render_page('Home', self._home_content())
            elif path == '/recommend':
                self._render_page('Recommendations', self._recommend_content())
            elif path == '/summary':
                self._render_page('Progress Summary', self._summary_content())
            elif path == '/dashboard':
                self._render_page('Dashboard', self._dashboard_content())
            elif path == '/curriculum':
                self._render_page('Curriculum', self._curriculum_content())
            elif path == '/status':
                self._render_page('System Status', self._status_content())
            elif path == '/export-history':
                csv_data = self.service.export_history_csv()
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="learning_history.csv"')
                self.end_headers()
                self.wfile.write(csv_data.encode('utf-8'))
            elif path == '/export-all':
                json_data = self.service.export_all_data()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="all_learning_data.json"')
                self.end_headers()
                self.wfile.write(json_data.encode('utf-8'))
            elif path == '/backup':
                destination = self.service.create_backup()
                self._render_page('Backup Created', f"<section><h2>Backup Created</h2><p>Saved to {destination}</p><p><a href='/status'>Return to status</a></p></section>")
            elif path == '/health':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            elif path == '/metrics':
                metrics = self._metrics_content()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(metrics.encode('utf-8'))
            else:
                self.send_error(404, 'Page not found')
        except Exception as exc:
            self.send_error(500, str(exc))
        finally:
            duration = time.perf_counter() - start
            self.log_message('Handled GET %s in %.4f sec', self.path, duration)

    def do_POST(self) -> None:
        start = time.perf_counter()
        try:
            if not self._is_allowed_host():
                self.send_error(403, 'Forbidden: host not allowed')
                return
            if not self._require_auth():
                return
            path = urlparse(self.path).path
            data = self._parse_form()
            if path == '/add-topic':
                self._handle_add_topic(data)
            elif path == '/record-attempt':
                self._handle_record_attempt(data)
            elif path == '/study-session':
                self._handle_study_session(data)
            elif path == '/create-profile':
                self._handle_create_profile(data)
            elif path == '/select-profile':
                self._handle_select_profile(data)
            elif path == '/clear-history':
                self._handle_clear_history()
            elif path == '/reset-weights-default':
                self._handle_reset_weights_default()
            elif path == '/zero-weights':
                self._handle_zero_weights()
            elif path == '/login':
                self._handle_login(data)
            elif path == '/register':
                self._handle_register(data)
            else:
                self.send_error(404, 'Action not found')
        except Exception as exc:
            self.send_error(500, str(exc))
        finally:
            duration = time.perf_counter() - start
            self.log_message('Handled POST %s in %.4f sec', self.path, duration)

    def _home_content(self) -> str:
        summary = self.service.get_progress_summary()
        weights = self.service.state.weights
        latest_recommendation = self.service.state.recommendation_history[-1]['recommended_topics'] if self.service.state.recommendation_history else []
        profiles = self.service.list_profiles()
        profile_options = ''.join(
            f"<option value='{name}'{' selected' if name == self.service.active_profile.name else ''}>{name}</option>"
            for name in profiles
        )

        summary_rows = ''.join(f'<li>{topic}: mastery {score}</li>' for topic, score in summary.items())
        weight_rows = ''.join(f'<li>{key}: {value}</li>' for key, value in weights.items())
        recommend_rows = ''.join(f'<li>{topic}</li>' for topic in latest_recommendation)

        return f"""
            <section>
                <h2>Welcome</h2>
                <p>This adaptive learning engine learns from your study sessions and improves recommendations over time.</p>
                <p><a href='/recommend'>Recommendations</a> | <a href='/summary'>Summary</a> | <a href='/dashboard'>Dashboard</a> | <a href='/curriculum'>Curriculum</a> | <a href='/status'>Status</a> | <a href='/logout'>Sign out</a></p>
            </section>
            <section>
                <h3>Learner Profiles</h3>
                <p>Active profile: <strong>{self.service.active_profile.name}</strong></p>
                <form method='post' action='/select-profile'>
                    <label>Select profile</label>
                    <select name='profile'>{profile_options}</select>
                    <button>Switch Profile</button>
                </form>
                <form method='post' action='/create-profile'>
                    <label>Create new profile</label>
                    <input name='profile' placeholder='New profile name' required />
                    <button>Create Profile</button>
                </form>
            </section>
            <section>
                <h3>Latest Recommendation</h3>
                <ul>{recommend_rows or '<li>No recommendations yet</li>'}</ul>
            </section>
            <section>
                <h3>Current Progress</h3>
                <ul>{summary_rows or '<li>No topics yet</li>'}</ul>
            </section>
            <section>
                <h3>Weight Profile</h3>
                <ul>{weight_rows}</ul>
            </section>
            <section>
                <h3>Add Topic</h3>
                <form method='post' action='/add-topic'>
                    <label>Topic name</label>
                    <input name='topic' required />
                    <label>Initial score</label>
                    <input name='score' type='number' step='0.1' required />
                    <label>Difficulty (0-1)</label>
                    <input name='difficulty' type='number' step='0.01' min='0' max='1' required />
                    <label>Subject</label>
                    <input name='subject' placeholder='Math, Science, Literature' />
                    <label>Tags (comma-separated)</label>
                    <input name='tags' placeholder='Algebra, Trigonometry' />
                    <button>Add Topic</button>
                </form>
            </section>
            <section>
                <h3>Record Attempt</h3>
                <form method='post' action='/record-attempt'>
                    <label>Topic name</label>
                    <input name='topic' required />
                    <label>New score</label>
                    <input name='score' type='number' step='0.1' required />
                    <button>Save Attempt</button>
                </form>
            </section>
            <section>
                <h3>Study Session</h3>
                <form method='post' action='/study-session'>
                    <label>Recommended topics (comma-separated)</label>
                    <input name='recommended' placeholder='Algebra, Physics' required />
                    <label>Completed scores (topic:score, comma-separated)</label>
                    <input name='completed' placeholder='Algebra:82, Physics:75' required />
                    <button>Log Session</button>
                </form>
            </section>
        """

    def _recommend_content(self) -> str:
        topics = self.service.preview_recommendations(5)
        items = ''.join(f'<li>{topic}</li>' for topic in topics)
        return f"""
            <section>
                <h2>Top Recommendations</h2>
                <p><a class='back' href='/'>←</a></p>
                <ul>{items or '<li>No topics available</li>'}</ul>
            </section>
        """

    def _dashboard_content(self) -> str:
        data = self.service.get_dashboard_data()
        return f"""
            <section>
                <h2>Learning Dashboard</h2>
                <p><a class='back' href='/'>←</a></p>
                <ul>
                    <li>Active Profile: {data['active_profile']}</li>
                    <li>Total topics: {data['topic_count']}</li>
                    <li>Topics due for review: {data['due_count']}</li>
                    <li>Weak topics: {data['weak_topics']}</li>
                    <li>Subject breakdown: {data['subject_breakdown']}</li>
                </ul>
                <p>Suggested next learning path:</p>
                <p>{data['next_learning_path'] or 'No path yet'}</p>
            </section>
        """

    def _curriculum_content(self) -> str:
        topics = self.service.get_topics()
        if not topics:
            return """
                <section>
                    <h2>Curriculum</h2>
                    <p><a class='back' href='/'>←</a></p>
                    <p>No topics have been added yet.</p>
                </section>
            """

        grouped = {}
        for topic in topics:
            grouped.setdefault(topic.subject or 'General', []).append(topic)

        sections = ''.join(
            f"<section><h3>{subject}</h3><ul>" + ''.join(
                f"<li>{topic.topic} — mastery {round(calculate_mastery(topic),1)} — next review {topic.next_review.date() if topic.next_review else 'soon'}</li>"
                for topic in entries
            ) + '</ul></section>'
            for subject, entries in grouped.items()
        )

        return f"""
            <section>
                <h2>Curriculum Overview</h2>
                <p><a class='back' href='/'>←</a></p>
                <p>Topics are grouped by subject and ordered with review due topics first.</p>
            </section>
            {sections}
        """

    def _status_content(self) -> str:
        state = self.service.state
        profile_count = len(self.service.list_profiles())
        topic_count = len(self.service.get_topics())
        heatmap_rows = ''.join(f'<li>{topic.topic}: due on {topic.next_review.date() if topic.next_review else topic.last_review.date()}</li>' for topic in self.service.get_topics())
        return f"""
            <section>
                <h2>System Status</h2>
                <p><a class='back' href='/'>←</a></p>
                <p>Running in environment: {config.APP_ENV}</p>
                <p>Profiles stored: {profile_count}</p>
                <p>Topics stored: {topic_count}</p>
                <p>Recommendations logged: {len(state.recommendation_history)}</p>
                <p>Feedback entries: {len(state.feedback_log)}</p>
                <p><a href='/export-all'>Export Full Dataset</a> | <a href='/backup'>Create Backup</a></p>
                <p><a href='/metrics'>View Metrics JSON</a></p>
                <h3>Upcoming Reviews</h3>
                <ul>{heatmap_rows or '<li>No topics yet</li>'}</ul>
            </section>
        """

    def _metrics_content(self) -> str:
        metrics = {
            'active_profile': self.service.active_profile.name,
            'topic_count': len(self.service.get_topics()),
            'profile_count': len(self.service.list_profiles()),
            'recommendation_history': len(self.service.state.recommendation_history),
            'feedback_log': len(self.service.state.feedback_log),
            'environment': config.APP_ENV,
        }
        return json.dumps(metrics)

    def _login_content(self) -> str:
        return """
            <section>
                <h2>Login</h2>
                <form method='post' action='/login'>
                    <label>Username</label>
                    <input name='username' required />
                    <label>Password</label>
                    <input name='password' type='password' required />
                    <button>Sign in</button>
                </form>
                <p>New here? <a href='/register'>Create an account</a>.</p>
            </section>
        """

    def _register_content(self) -> str:
        return """
            <section>
                <h2>Create an Account</h2>
                <form method='post' action='/register'>
                    <label>Username</label>
                    <input name='username' required />
                    <label>Password</label>
                    <input name='password' type='password' required />
                    <button>Register</button>
                </form>
                <p>Already have an account? <a href='/login'>Sign in</a>.</p>
            </section>
        """

    def _handle_login(self, data: dict) -> None:
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if username and password and self.service.authenticate_user(username, password):
            self.send_response(303)
            self._set_user_cookie(username)
            self.send_header('Location', '/')
            self.end_headers()
            return
        self._render_page('Login Failed', "<section><h2>Login Failed</h2><p>Wrong user or password.</p><p><a href='/login'>Try again</a></p></section>")

    def _handle_register(self, data: dict) -> None:
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if not username or not password:
            self._render_page('Register Failed', "<section><h2>Registration Failed</h2><p>Please provide both a username and password.</p><p><a href='/register'>Try again</a></p></section>")
            return
        try:
            self.service.create_account(username, password)
            self.send_response(303)
            self._set_user_cookie(username)
            self.send_header('Location', '/')
            self.end_headers()
        except ValueError as exc:
            self._render_page('Register Failed', f"<section><h2>Registration Failed</h2><p>{exc}</p><p><a href='/register'>Try again</a></p></section>")
        summary = self.service.get_progress_summary()
        rows = ''.join(f'<li>{topic}: mastery {score}</li>' for topic, score in summary.items())
        return f"""
            <section>
                <h2>Topic Mastery Summary</h2>
                <p><a class='back' href='/'>←</a></p>
                <ul>{rows}</ul>
            </section>
        """

    def _state_content(self) -> str:
        state = self.service.state
        weights = ''.join(f'<li>{key}: {value}</li>' for key, value in state.weights.items())
        # Show a success banner if redirected after actions
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        banner = ""
        if qs.get('cleared'):
            banner = "<p style='color:green;font-weight:700;'>History cleared — system reset to defaults.</p>"
        if qs.get('weights_reset') == ['defaults']:
            banner = "<p style='color:green;font-weight:700;'>Weights reset to default profile.</p>"
        if qs.get('weights_reset') == ['zeros']:
            banner = "<p style='color:orange;font-weight:700;'>Weights zeroed out.</p>"

        return f"""
            <section>
                <h2>System State</h2>
                <p><a class='back' href='/'>←</a></p>
                {banner}
                <p>Weights and feedback log are persisted automatically.</p>
                <form method='post' action='/clear-history' onsubmit="return confirm('Clear all recommendation and feedback history? This cannot be undone.');">
                    <button style='max-width:200px;'>Clear History</button>
                </form>
                <p><a href='/export-history'>Export History (CSV)</a></p>
                <div style='margin-top:12px'>
                    <form method='post' action='/reset-weights-default' style='display:inline'>
                        <button style='max-width:220px;'>Reset Weights to Defaults</button>
                    </form>
                    <form method='post' action='/zero-weights' style='display:inline;margin-left:8px'>
                        <button style='max-width:220px;'>Zero Out Weights</button>
                    </form>
                </div>
                <h3>Weights</h3>
                <ul>{weights}</ul>
                <p>Recommendation history: {len(state.recommendation_history)}</p>
                <p>Feedback entries: {len(state.feedback_log)}</p>
            </section>
        """

    def _handle_add_topic(self, data: dict) -> None:
        tags = [tag.strip() for tag in data.get('tags', '').split(',') if tag.strip()]
        subject = data.get('subject', '').strip()
        self.service.add_topic(
            data.get('topic', ''),
            float(data.get('score', 0)),
            float(data.get('difficulty', 0)),
            tags,
            subject,
        )
        self._redirect('/')

    def _handle_record_attempt(self, data: dict) -> None:
        self.service.record_attempt(data.get('topic', ''), float(data.get('score', 0)))
        self._redirect('/')

    def _handle_create_profile(self, data: dict) -> None:
        profile_name = data.get('profile', '').strip()
        if profile_name:
            try:
                self.service.create_profile(profile_name)
            except ValueError as exc:
                self._render_page('Error', f"<section><h2>Failed to Create Profile</h2><p>{exc}</p><p><a href='/'>Back to home</a></p></section>")
                return
        self._redirect('/')

    def _handle_select_profile(self, data: dict) -> None:
        profile_name = data.get('profile', '').strip()
        if profile_name:
            try:
                self.service.select_profile(profile_name)
            except ValueError as exc:
                # User tried to access a profile they don't own
                self._render_page('Unauthorized', f"<section><h2>Cannot Access Profile</h2><p>You do not have permission to access profile '{profile_name}'.</p><p><a href='/'>Back to home</a></p></section>")
                return
        self._redirect('/')

    def _handle_study_session(self, data: dict) -> None:
        recommended = [item.strip() for item in data.get('recommended', '').split(',') if item.strip()]
        completed = {}
        for pair in data.get('completed', '').split(','):
            if ':' not in pair:
                continue
            name, value = pair.split(':', 1)
            completed[name.strip()] = float(value.strip())
        self.service.run_study_session(recommended, completed)
        self._redirect('/')

    def _handle_clear_history(self) -> None:
        try:
            self.service.clear_history()
        except Exception:
            # If clearing fails, still redirect back to state so UI remains responsive
            pass
        # Redirect with a flag so the state page can show a success message
        self._redirect('/state?cleared=1')

    def _handle_reset_weights_default(self) -> None:
        try:
            self.service.reset_weights_to_defaults()
        except Exception:
            pass
        self._redirect('/state?weights_reset=defaults')

    def _handle_zero_weights(self) -> None:
        try:
            self.service.zero_out_weights()
        except Exception:
            pass
        self._redirect('/state?weights_reset=zeros')


def run_web_server(host: str = 'localhost', port: int = 8000) -> None:
    server = ThreadedHTTPServer((host, port), LearningHandler)
    print(f'Web server running at http://{host}:{port} (threaded, env={config.APP_ENV})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down server...')
        server.shutdown()
