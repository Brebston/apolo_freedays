"""Віддає зібраний React-застосунок (webapp/dist/index.html) за адресою /app/."""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt

INDEX_PATH = settings.BASE_DIR / "webapp" / "dist" / "index.html"


@xframe_options_exempt  # Telegram Web/Desktop відкриває Mini App в iframe
def webapp_index(request):
    try:
        html = INDEX_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HttpResponse(
            "Mini App не зібрано: виконайте `npm run build` у директорії webapp/.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    response = HttpResponse(html)
    response["Cache-Control"] = "no-cache"
    return response


def healthz(request):
    return JsonResponse({"status": "ok"})
