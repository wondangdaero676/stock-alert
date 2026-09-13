"""처음 한 번만 내 PC에서 실행: Finnhub 키 확인 → 카카오 로그인 → 토큰 암호화 저장 → GitHub Secrets 등록"""
import getpass
import os
import subprocess
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from cryptography.fernet import Fernet

from alert import kakao, quotes

REDIRECT_URI = "http://localhost:8080"


def ask(prompt: str, required: bool = True) -> str:
    while True:
        value = getpass.getpass(prompt).strip()
        if value or not required:
            return value


def receive_auth_code() -> str:
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("카카오 로그인 완료. 이 창을 닫고 터미널로 돌아가세요.".encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 8080), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()
    if "error" in result:
        raise SystemExit(f"카카오 로그인 실패: {result}")
    return result["code"]


def main() -> None:
    print("[1/4] Finnhub API 키 확인 (입력 내용은 화면에 표시되지 않습니다)")
    os.environ["FINNHUB_API_KEY"] = ask("  Finnhub API 키: ")
    q = quotes.fetch("US", "QLD")
    print(f"  QLD ${q.price:,.2f} ({q.change_pct:+.2f}%) 조회 성공")

    print("[2/4] 카카오 로그인")
    os.environ["KAKAO_REST_API_KEY"] = ask("  카카오 REST API 키: ")
    client_secret = ask("  카카오 클라이언트 시크릿 (사용 안 하면 그냥 엔터): ", required=False)
    if client_secret:
        os.environ["KAKAO_CLIENT_SECRET"] = client_secret

    auth_url = "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message",
    })
    print("  브라우저에서 카카오 로그인 후 동의해 주세요. 창이 안 열리면 아래 주소로 접속하세요.\n  " + auth_url)
    webbrowser.open(auth_url)
    code = receive_auth_code()

    tokens = kakao.check_response(requests.post(
        kakao.TOKEN_URL,
        data={"grant_type": "authorization_code", "redirect_uri": REDIRECT_URI, "code": code, **kakao.client_params()},
        timeout=10,
    ))
    os.environ["KAKAO_TOKEN_KEY"] = Fernet.generate_key().decode()
    kakao.save_refresh_token(tokens["refresh_token"])
    print(f"  토큰을 암호화해 {kakao.TOKEN_FILE}에 저장했습니다")

    print("[3/4] 카카오톡 테스트 메시지 전송")
    kakao.send(tokens["access_token"], "[주식 알림] 설정 완료! 이 메시지가 보이면 연결이 정상입니다.")
    print("  카카오톡 '나와의 채팅'을 확인하세요")

    print("[4/4] GitHub Secrets 등록")
    names = ["FINNHUB_API_KEY", "KAKAO_REST_API_KEY", "KAKAO_TOKEN_KEY"]
    if client_secret:
        names.append("KAKAO_CLIENT_SECRET")
    for name in names:
        subprocess.run(["gh", "secret", "set", name], input=os.environ[name], text=True, check=True)

    print("\n완료! 이제 state/kakao_token.enc 파일을 커밋하고 푸시하면 됩니다.")


if __name__ == "__main__":
    main()
