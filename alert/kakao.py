import json
import logging
import os
from pathlib import Path

import requests
from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

# 공개 저장소에 커밋되므로 반드시 암호화해서 저장한다. 키는 GitHub Secret(KAKAO_TOKEN_KEY)에만 있다.
TOKEN_FILE = Path("state/kakao_token.enc")
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def client_params() -> dict[str, str]:
    params = {"client_id": os.environ["KAKAO_REST_API_KEY"]}
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        params["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    return params


def save_refresh_token(refresh_token: str) -> None:
    fernet = Fernet(os.environ["KAKAO_TOKEN_KEY"])
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_bytes(fernet.encrypt(json.dumps({"refresh_token": refresh_token}).encode()))


def _load_refresh_token() -> str:
    fernet = Fernet(os.environ["KAKAO_TOKEN_KEY"])
    return json.loads(fernet.decrypt(TOKEN_FILE.read_bytes()))["refresh_token"]


def check_response(resp: requests.Response) -> dict:
    if not resp.ok:
        raise RuntimeError(f"카카오 API 오류 {resp.status_code}: {resp.text}")
    return resp.json()


def access_token() -> str:
    # 리프레시 토큰은 만료 1개월 전부터 갱신 요청 시 새로 발급되므로, 받으면 저장해야 계속 쓸 수 있다
    body = check_response(requests.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": _load_refresh_token(), **client_params()},
        timeout=10,
    ))
    if body.get("refresh_token"):
        save_refresh_token(body["refresh_token"])
        log.info("카카오 리프레시 토큰이 새로 발급되어 저장했습니다")
    return body["access_token"]


def send(token: str, text: str) -> None:
    # buttons를 생략하면 "자세히 보기" 기본 버튼이 붙으므로 빈 목록을 명시한다
    template = {"object_type": "text", "text": text, "link": {}, "buttons": []}
    check_response(requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=10,
    ))
