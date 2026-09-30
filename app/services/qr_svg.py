"""바우처 문자열을 스캔 가능한 SVG QR로 그린다. LLM 의존성 없음."""

from app.services.qrcodegen import QrCode


def qr_svg(text: str, border: int = 2) -> str:
    qr = QrCode.encode_text(str(text or ""), QrCode.Ecc.MEDIUM)
    modules = qr.get_size()
    size = modules + border * 2
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {0} {0}" shape-rendering="crispEdges" role="img">'.format(size),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    for y in range(modules):
        for x in range(modules):
            if qr.get_module(x, y):
                parts.append(
                    '<rect x="{0}" y="{1}" width="1" height="1" fill="#111111"/>'.format(
                        x + border,
                        y + border,
                    )
                )
    parts.append("</svg>")
    return "".join(parts)
