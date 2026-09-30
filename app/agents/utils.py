import os
from typing import Optional, Tuple

# import 시점의 원격 가격표 다운로드(및 그로 인한 타임아웃)를 막는다. litellm import보다 먼저 설정해야 한다.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

load_dotenv()

# litellm은 OpenRouter 우회에서만 쓴다. 모듈 로드 시점의 NameError(InputAudio)가
# FastAPI 기동과 테스트 전체를 막지 않도록 호출 직전까지 수입을 미룬다.
_litellm_module = None

PRIMARY_GEMINI_MODEL = "gemini-3.6-flash"

# 1순위 모델이 429/503 등으로 막혔을 때 순서대로 시도할 Gemini 대체 모델
# (gemini-2.5-* 계열은 신규 사용자에게 404로 막혀 있어 제외한다)
GEMINI_MODEL_CHAIN = [
    PRIMARY_GEMINI_MODEL,
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]

# Gemini 경로가 모두 막혔을 때 순서대로 시도할 OpenRouter 백업 모델
OPENROUTER_MODELS = [
    "openrouter/meta-llama/llama-3.3-70b-instruct",
    "openrouter/mistralai/mistral-small-3.2-24b-instruct",
]

OPENROUTER_TIMEOUT = 60.0

_gemini_client: Optional["genai.Client"] = None


def _load_litellm():
    """OpenRouter 호출 직전에만 litellm을 불러온다. 수입 실패는 그 경로의 오류로 남긴다."""
    global _litellm_module
    if _litellm_module is not None:
        return _litellm_module
    try:
        import litellm
    except Exception as exc:  # noqa: BLE001 - 깨진 타입 수입도 앱 기동과 분리한다
        raise RuntimeError("OpenRouter fallback is unavailable: {0}".format(exc)) from exc
    litellm.drop_params = True
    litellm.suppress_debug_info = True
    litellm.disable_aiohttp_transport = True
    _litellm_module = litellm
    return litellm


def get_gemini_client() -> "genai.Client":
    """프로세스 단위로 재사용하는 Gemini 클라이언트."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("[오류] .env 파일에 GEMINI_API_KEY가 설정되어 있지 않습니다.")
        # 커스텀 transport를 넘기면 SDK가 aiohttp 대신 httpx를 쓴다.
        # aiohttp 세션은 이벤트 루프 종료 시 닫히지 않아 경고를 남긴다.
        _gemini_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                async_client_args={"transport": httpx.AsyncHTTPTransport()}
            ),
        )
    return _gemini_client


def _fallback_forced() -> bool:
    """백업 경로를 강제로 검증할 때 쓰는 스위치 (FORCE_LLM_FALLBACK=1)."""
    return os.getenv("FORCE_LLM_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


async def _call_gemini(prompt: str, config: Optional[types.GenerateContentConfig]) -> Tuple[str, str]:
    """Gemini 모델 체인을 순서대로 시도한다. 전부 실패하면 마지막 예외를 올린다."""
    client = get_gemini_client()
    last_error: Optional[Exception] = None

    for model in GEMINI_MODEL_CHAIN:
        try:
            print("📌 [시도 1단계] Gemini '{0}' 직접 호출 중...".format(model))
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            if not text.strip():
                raise RuntimeError("빈 응답을 반환했습니다.")
            return text, "Gemini Direct ({0})".format(model)
        except Exception as exc:  # noqa: BLE001 - 다음 Gemini 모델로 계속 진행
            last_error = exc
            print("⚠️ [{0}] 호출 실패: {1}".format(model, exc))

    raise RuntimeError("모든 Gemini 모델이 실패했습니다: {0}".format(last_error))


async def _call_openrouter(prompt: str, system_prompt: str, expect_json: bool) -> Tuple[str, str]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    last_error: Optional[Exception] = None

    for model in OPENROUTER_MODELS:
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "num_retries": 1,
                "timeout": OPENROUTER_TIMEOUT,
            }
            if expect_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = await _load_litellm().acompletion(**kwargs)
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise RuntimeError("빈 응답을 반환했습니다.")
            return text, "OpenRouter Fallback ({0})".format(model.replace("openrouter/", ""))
        except Exception as exc:  # noqa: BLE001 - 다음 백업 모델로 계속 진행
            last_error = exc
            print("⚠️ [{0}] 백업 모델 호출 실패: {1}".format(model, exc))

    raise RuntimeError("모든 OpenRouter 백업 모델이 실패했습니다: {0}".format(last_error))


async def generate_with_fallback(
    prompt: str,
    system_prompt: str,
    config: Optional[types.GenerateContentConfig] = None,
    expect_json: bool = False,
) -> Tuple[str, str]:
    """Gemini 직접 호출 -> 실패 시 OpenRouter 우회. (응답 원문, 사용 모델명) 반환."""
    if not _fallback_forced():
        try:
            text, model_used = await _call_gemini(prompt, config)
            print("✨ [성공] Gemini 직접 호출 성공 (사용 모델: {0})".format(model_used))
            return text, model_used
        except Exception as gemini_err:  # noqa: BLE001 - 어떤 실패든 백업 경로로 우회
            print("⚠️ [알림] Gemini 경로 전체 실패: {0}".format(gemini_err))
    else:
        print("🧪 [강제 우회] FORCE_LLM_FALLBACK=1 이므로 Gemini를 건너뜁니다.")

    print("🔄 [시도 2단계] OpenRouter 백업 경로로 전환합니다...")
    text, model_used = await _call_openrouter(prompt, system_prompt, expect_json)
    print("🛡️ [우회 성공] {0} 경로로 처리했습니다.".format(model_used))
    return text, model_used