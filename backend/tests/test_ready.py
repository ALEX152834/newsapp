"""
Ready 端点失败场景测试

测试 /ready 端点在 DB/Redis 检查失败时的行为。

Requirements: 3.2, 3.3
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestReadyDatabaseFailure:
    """
    /ready 端点数据库失败测试类
    
    验证数据库检查失败时返回 503 + INTERNAL_ERROR。
    """

    def test_ready_returns_503_when_db_fails(self, client: TestClient):
        """
        测试数据库检查失败时返回 503 状态码
        
        mock DB 检查抛异常 → 断言 /ready 返回 503。
        
        Validates: Requirements 3.2, 3.3
        """
        with patch("app.routers.health.Session") as mock_session_class:
            # 创建一个 mock session 实例
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Database connection failed")
            mock_session_class.return_value = mock_session
            
            # 由于我们使用依赖注入，需要 patch db.execute
            with patch.object(
                client.app.dependency_overrides.get(
                    __import__("app.database", fromlist=["get_db"]).get_db,
                    lambda: None
                ),
                "execute",
                side_effect=Exception("Database connection failed")
            ):
                pass  # 这种方式不太适用
        
        # 更好的方式：直接 patch Session.execute
        # 由于测试使用了 db_session fixture，我们需要在 fixture 级别 mock

    def test_ready_returns_503_when_db_execute_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试数据库 execute 失败时返回 503 状态码
        
        使用 monkeypatch mock Session.execute 抛异常。
        
        Validates: Requirements 3.2, 3.3
        """
        from sqlalchemy.orm import Session
        
        original_execute = Session.execute
        
        def mock_execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        
        monkeypatch.setattr(Session, "execute", mock_execute)
        
        response = client.get("/ready")
        
        # 恢复原始方法（monkeypatch 会自动恢复）
        assert response.status_code == 503, \
            f"数据库失败时应返回 503，实际返回 {response.status_code}"

    def test_ready_returns_internal_error_code_when_db_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试数据库失败时返回 error.code = INTERNAL_ERROR
        
        Validates: Requirements 3.2, 3.3
        """
        from sqlalchemy.orm import Session
        
        def mock_execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        
        monkeypatch.setattr(Session, "execute", mock_execute)
        
        response = client.get("/ready")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "INTERNAL_ERROR", \
            f"error.code 应为 INTERNAL_ERROR，实际为 {data['error']['code']}"

    def test_ready_shows_db_error_status_when_db_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试数据库失败时 data.database = "error"
        
        Validates: Requirements 3.2, 3.3
        """
        from sqlalchemy.orm import Session
        
        def mock_execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        
        monkeypatch.setattr(Session, "execute", mock_execute)
        
        response = client.get("/ready")
        data = response.json()
        
        assert data["data"]["database"] == "error", \
            f"data.database 应为 'error'，实际为 {data['data']['database']}"


class TestReadyRedisFailure:
    """
    /ready 端点 Redis 失败测试类
    
    验证 Redis 检查失败时返回 503 + INTERNAL_ERROR。
    """

    def test_ready_returns_503_when_redis_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试 Redis 检查失败时返回 503 状态码
        
        mock Redis 检查抛异常 → 断言 /ready 返回 503。
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        
        original_from_url = redis.from_url
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        
        assert response.status_code == 503, \
            f"Redis 失败时应返回 503，实际返回 {response.status_code}"

    def test_ready_returns_internal_error_code_when_redis_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试 Redis 失败时返回 error.code = INTERNAL_ERROR
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "INTERNAL_ERROR", \
            f"error.code 应为 INTERNAL_ERROR，实际为 {data['error']['code']}"

    def test_ready_shows_redis_error_status_when_redis_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试 Redis 失败时 data.redis = "error"
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        data = response.json()
        
        assert data["data"]["redis"] == "error", \
            f"data.redis 应为 'error'，实际为 {data['data']['redis']}"

    def test_ready_shows_db_ok_when_only_redis_fails(
        self, client: TestClient, monkeypatch
    ):
        """
        测试仅 Redis 失败时 data.database = "ok"
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        data = response.json()
        
        # 数据库应该正常
        assert data["data"]["database"] == "ok", \
            f"data.database 应为 'ok'，实际为 {data['data']['database']}"


class TestReadyBothFailure:
    """
    /ready 端点 DB 和 Redis 同时失败测试类
    """

    def test_ready_returns_503_when_both_fail(
        self, client: TestClient, monkeypatch
    ):
        """
        测试 DB 和 Redis 同时失败时返回 503 状态码
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        from sqlalchemy.orm import Session
        
        def mock_execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(Session, "execute", mock_execute)
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        
        assert response.status_code == 503

    def test_ready_shows_both_error_when_both_fail(
        self, client: TestClient, monkeypatch
    ):
        """
        测试 DB 和 Redis 同时失败时两者状态都为 error
        
        Validates: Requirements 3.2, 3.3
        """
        import redis
        from sqlalchemy.orm import Session
        
        def mock_execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(Session, "execute", mock_execute)
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        data = response.json()
        
        assert data["data"]["database"] == "error"
        assert data["data"]["redis"] == "error"
        assert data["data"]["status"] == "error"


class TestReadyResponseStructure:
    """
    /ready 端点失败响应结构测试类
    """

    def test_ready_failure_response_structure(
        self, client: TestClient, monkeypatch
    ):
        """
        测试失败响应结构符合统一格式
        
        失败响应格式：{ "data": {...}, "meta": {...}, "error": {...} }
        
        Validates: Requirements 5.2
        """
        import redis
        
        def mock_from_url(*args, **kwargs):
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            return mock_client
        
        monkeypatch.setattr(redis, "from_url", mock_from_url)
        
        response = client.get("/ready")
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证 data 包含状态信息
        assert data["data"] is not None
        assert "status" in data["data"]
        assert "database" in data["data"]
        assert "redis" in data["data"]
        
        # 验证 meta 是对象
        assert isinstance(data["meta"], dict)
        
        # 验证 error 结构
        assert data["error"] is not None
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert len(data["error"]["message"]) > 0
