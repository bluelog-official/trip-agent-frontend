"""앱 기동은 OpenRouter 우회를 당장 불러오지 않는다."""


def test_app_imports_without_loading_litellm():
    import app.main as main

    assert main.app.title
    assert any(route.path == "/api/v1/rewards/overview" for route in main.app.routes)
    assert any(route.path == "/api/auth/providers" for route in main.app.routes)
    assert any(route.path == "/api/v1/wallet" for route in main.app.routes)
    assert any(route.path == "/api/partners" for route in main.app.routes)
    assert any(route.path == "/api/vouchers/claim" for route in main.app.routes)
    assert any(route.path == "/api/vouchers/verify" for route in main.app.routes)
