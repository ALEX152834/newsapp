"""
Smoke Test: 验证测试数据库连接

确保在 docker-compose 环境中：
1. TEST_DATABASE_URL=postgresql://test:test@postgres:5432/test 能正常连接
2. current_database() 返回 'test'，证明连接的是测试库而非主库
3. 不会误连主库 'news'

这是一个关键的安全验收测试，防止测试数据污染生产数据。
"""

import os

import pytest
from sqlalchemy import create_engine, text


class TestDatabaseConnectionSmoke:
    """
    数据库连接 Smoke Test
    
    验证 host=postgres 在测试网络中正确解析到测试库。
    """

    def test_connection_uses_test_database(self):
        """
        验证连接的是测试数据库 'test'，而非主库 'news'
        
        使用 SELECT current_database() 断言数据库名必须为 'test'。
        如果返回 'news'，说明误连了主库，测试必须失败。
        """
        # 获取测试数据库 URL
        test_db_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://test:test@postgres:5432/test"
        )
        
        # 创建引擎并连接
        engine = create_engine(test_db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            
            # 断言必须连接到 'test' 数据库
            assert current_db == "test", (
                f"FATAL: 测试连接到了错误的数据库！\n"
                f"期望: 'test'\n"
                f"实际: '{current_db}'\n"
                f"TEST_DATABASE_URL: {test_db_url}\n"
                f"这可能导致测试数据污染生产数据库！"
            )
            
            print(f"\n✓ 数据库连接验证通过:")
            print(f"  - current_database() = '{current_db}'")
            print(f"  - TEST_DATABASE_URL = {test_db_url}")

    def test_connection_not_main_database(self):
        """
        验证绝对不会连接到主库 'news'
        
        这是一个防御性测试，确保即使配置错误也能被检测到。
        """
        test_db_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://test:test@postgres:5432/test"
        )
        
        engine = create_engine(test_db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            
            # 绝对不能是主库
            assert current_db != "news", (
                f"CRITICAL: 测试连接到了主库 'news'！\n"
                f"这是严重的配置错误，可能导致生产数据被测试污染！\n"
                f"请检查 docker-compose 网络配置和 TEST_DATABASE_URL。"
            )

    def test_host_postgres_resolves_correctly(self):
        """
        验证 host=postgres 在测试网络中正确解析
        
        在 test-network 中，postgres 别名应该指向 test_postgres 服务。
        """
        test_db_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://test:test@postgres:5432/test"
        )
        
        # 验证 URL 使用 host=postgres
        assert "postgres:5432" in test_db_url or "@postgres/" in test_db_url, (
            f"TEST_DATABASE_URL 应该使用 host=postgres\n"
            f"实际: {test_db_url}"
        )
        
        # 验证能成功连接
        engine = create_engine(test_db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1, "数据库连接失败"
            
            # 验证是测试库
            result = conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            assert current_db == "test", f"期望 'test'，实际 '{current_db}'"
            
            print(f"\n✓ host=postgres 解析验证通过:")
            print(f"  - 成功连接到数据库")
            print(f"  - current_database() = '{current_db}'")


class TestCredentialsIsolation:
    """
    凭据隔离测试
    
    验证测试凭据 (test:test) 只能访问测试库，不能访问主库。
    """

    def test_test_credentials_cannot_access_main_db(self):
        """
        验证测试凭据无法访问主库
        
        使用测试凭据尝试连接主库 'news'，应该失败。
        """
        # 尝试用测试凭据连接主库
        main_db_url = "postgresql://test:test@postgres:5432/news"
        
        engine = create_engine(main_db_url)
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT current_database()"))
                current_db = result.scalar()
                
                # 如果能连接成功，检查是否真的是主库
                if current_db == "news":
                    pytest.fail(
                        "SECURITY ISSUE: 测试凭据 (test:test) 能够访问主库 'news'！\n"
                        "这是严重的安全问题，请检查数据库权限配置。"
                    )
        except Exception:
            # 连接失败是预期行为（测试凭据不应能访问主库）
            print("\n✓ 凭据隔离验证通过: 测试凭据无法访问主库")
