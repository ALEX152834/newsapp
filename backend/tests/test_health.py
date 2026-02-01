"""
Health 接口测试

测试 /health 端点的功能和响应格式。

Requirements: 7.1
"""

import re

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """
    /health 端点测试类
    
    验证健康检查接口的正确性。
    """

    def test_health_returns_200(self, client: TestClient):
        """
        测试 /health 返回 200 状态码
        
        Validates: Requirements 3.1
        """
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        """
        测试响应结构符合统一格式
        
        成功响应格式：{ "data": {...}, "meta": {...}, "error": null }
        
        Validates: Requirements 3.2, 5.1
        """
        response = client.get("/health")
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证成功响应 error 为 null
        assert data["error"] is None
        
        # 验证 data 非空
        assert data["data"] is not None

    def test_health_data_contains_status_ok(self, client: TestClient):
        """
        测试 data.status 为 "ok"
        
        Validates: Requirements 3.3
        """
        response = client.get("/health")
        data = response.json()
        
        assert data["data"]["status"] == "ok"

    def test_health_data_contains_timestamp(self, client: TestClient):
        """
        测试 data 包含 timestamp 字段
        
        Validates: Requirements 3.2, 3.3
        """
        response = client.get("/health")
        data = response.json()
        
        assert "timestamp" in data["data"]
        assert data["data"]["timestamp"] is not None

    def test_health_timestamp_format_ends_with_z(self, client: TestClient):
        """
        测试 timestamp 格式为 ISO 8601 UTC，以 Z 结尾
        
        格式要求：YYYY-MM-DDTHH:MM:SSZ
        禁止输出 +00:00 格式
        
        Validates: Requirements 3.2
        """
        response = client.get("/health")
        data = response.json()
        
        timestamp = data["data"]["timestamp"]
        
        # 验证以 Z 结尾
        assert timestamp.endswith("Z"), f"timestamp 应以 Z 结尾，实际值: {timestamp}"
        
        # 验证不包含 +00:00
        assert "+00:00" not in timestamp, f"timestamp 不应包含 +00:00，实际值: {timestamp}"
        
        # 验证完整的 ISO 8601 UTC 格式
        iso8601_utc_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        assert re.match(iso8601_utc_pattern, timestamp), \
            f"timestamp 格式不正确，期望格式: YYYY-MM-DDTHH:MM:SSZ，实际值: {timestamp}"

    def test_health_response_has_request_id_header(self, client: TestClient):
        """
        测试响应头包含 X-Request-ID
        
        Validates: Requirements 8.4
        """
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers, "响应头应包含 X-Request-ID"
        
        # 验证 X-Request-ID 是有效的 UUID 格式
        request_id = response.headers["X-Request-ID"]
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, request_id, re.IGNORECASE), \
            f"X-Request-ID 应为有效的 UUID 格式，实际值: {request_id}"

    def test_health_meta_structure(self, client: TestClient):
        """
        测试 meta 字段结构
        
        对于非分页接口，meta 可以为空对象或包含默认值
        
        Validates: Requirements 5.1
        """
        response = client.get("/health")
        data = response.json()
        
        # meta 应该是一个对象
        assert isinstance(data["meta"], dict)

    def test_health_response_json_not_contains_plus_zero(self, client: TestClient):
        """
        测试整个响应 JSON 不包含 +00:00 格式
        
        确保所有时间字段都使用 Z 结尾格式
        
        Validates: Requirements 3.2
        """
        response = client.get("/health")
        response_text = response.text
        
        assert "+00:00" not in response_text, \
            f"响应中不应包含 +00:00 格式，响应内容: {response_text}"
