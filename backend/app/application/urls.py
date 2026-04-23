from app.api.endpoints import config_center, dashboard, skills, task, login


urlpatterns = [
    {"ApiRouter": login.router, "prefix": "", "tags": ["Authentication"]},
    {"ApiRouter": task.router, "prefix": "", "tags": ["Use Cases Generation"]},
    {"ApiRouter": config_center.router, "prefix": "", "tags": ["Config Center"]},
    {"ApiRouter": dashboard.router, "prefix": "", "tags": ["Dashboard"]},
    {"ApiRouter": skills.router, "prefix": "", "tags": ["QA Skills"]},
]
