from app.api.endpoints import (
    config_center, dashboard, skills, skill_role_config, task, login,
    projects, requirements, hr, defects, api_automation, performance,
    test_cases, efficiency_tools,
)


urlpatterns = [
    {"ApiRouter": login.router, "prefix": "", "tags": ["Authentication"]},
    {"ApiRouter": task.router, "prefix": "", "tags": ["Use Cases Generation"]},
    {"ApiRouter": config_center.router, "prefix": "", "tags": ["Config Center"]},
    {"ApiRouter": dashboard.router, "prefix": "", "tags": ["Dashboard"]},
    {"ApiRouter": skill_role_config.router, "prefix": "", "tags": ["Skill Role Config"]},
    {"ApiRouter": skills.router, "prefix": "", "tags": ["QA Skills"]},
    {"ApiRouter": projects.router, "prefix": "", "tags": ["Projects"]},
    {"ApiRouter": requirements.router, "prefix": "", "tags": ["Requirements"]},
    {"ApiRouter": hr.router, "prefix": "", "tags": ["HR Management"]},
    {"ApiRouter": defects.router, "prefix": "", "tags": ["Defects"]},
    {"ApiRouter": api_automation.router, "prefix": "", "tags": ["API Automation"]},
    {"ApiRouter": performance.router, "prefix": "", "tags": ["Performance"]},
    {"ApiRouter": test_cases.router, "prefix": "", "tags": ["Test Cases"]},
    {"ApiRouter": test_cases.exec_router, "prefix": "", "tags": ["Test Executions"]},
    {"ApiRouter": test_cases.report_router, "prefix": "", "tags": ["Test Reports"]},
    {"ApiRouter": efficiency_tools.router, "prefix": "", "tags": ["Efficiency Tools"]},
]
