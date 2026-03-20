from app.api.endpoints import config_center, dashboard, generate, login


urlpatterns = [
    {"ApiRouter": login.router, "prefix": "", "tags": ["Authentication"]},
    {"ApiRouter": generate.router, "prefix": "", "tags": ["Use Cases Generation"]},
    {"ApiRouter": config_center.router, "prefix": "", "tags": ["Config Center"]},
    {"ApiRouter": dashboard.router, "prefix": "", "tags": ["Dashboard"]},
]
