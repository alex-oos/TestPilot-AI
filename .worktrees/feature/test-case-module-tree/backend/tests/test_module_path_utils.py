"""module_path_utils 单元测试。"""

from app.util.module_path_utils import join_module_path, module_prefix_filter, parse_module_path


def test_parse_module_path_with_space_slash():
    assert parse_module_path("注册 / 登录 / 忘记密码") == ["注册", "登录", "忘记密码"]


def test_parse_module_path_with_slash():
    assert parse_module_path("项目评审相关页面/流程") == ["项目评审相关页面", "流程"]


def test_join_module_path():
    assert join_module_path(["注册", "登录"]) == "注册 / 登录"


def test_module_prefix_filter_sql_elements():
    clause = module_prefix_filter("注册 / 登录")
    assert clause is not None
