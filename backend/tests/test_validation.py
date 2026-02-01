"""
参数验证测试

测试 /v1/news 端点的参数验证功能。

Requirements: 7.3
"""

from fastapi.testclient import TestClient


class TestLimitParameterValidation:
    """
    limit 参数验证测试类
    
    验证 limit 参数超出有效范围（1-50）时返回 400 错误。
    """

    def test_limit_100_returns_400(self, client: TestClient):
        """
        测试 limit=100 返回 400 状态码
        
        limit 超出最大值 50，应返回验证错误。
        
        Validates: Requirements 7.3, 4.4
        """
        response = client.get("/v1/news?limit=100")
        assert response.status_code == 400

    def test_limit_100_returns_validation_error_code(self, client: TestClient):
        """
        测试 limit=100 返回 error.code = VALIDATION_ERROR
        
        Validates: Requirements 7.3, 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_limit_51_returns_400(self, client: TestClient):
        """
        测试 limit=51 返回 400 状态码
        
        limit 刚好超出最大值 50，应返回验证错误。
        
        Validates: Requirements 4.4
        """
        response = client.get("/v1/news?limit=51")
        assert response.status_code == 400

    def test_limit_51_returns_validation_error_code(self, client: TestClient):
        """
        测试 limit=51 返回 error.code = VALIDATION_ERROR
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=51")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_limit_0_returns_400(self, client: TestClient):
        """
        测试 limit=0 返回 400 状态码
        
        limit 小于最小值 1，应返回验证错误。
        
        Validates: Requirements 7.3, 4.4
        """
        response = client.get("/v1/news?limit=0")
        assert response.status_code == 400

    def test_limit_0_returns_validation_error_code(self, client: TestClient):
        """
        测试 limit=0 返回 error.code = VALIDATION_ERROR
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=0")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_limit_negative_returns_400(self, client: TestClient):
        """
        测试 limit=-1 返回 400 状态码
        
        limit 为负数，应返回验证错误。
        
        Validates: Requirements 7.3, 4.4
        """
        response = client.get("/v1/news?limit=-1")
        assert response.status_code == 400

    def test_limit_negative_returns_validation_error_code(self, client: TestClient):
        """
        测试 limit=-1 返回 error.code = VALIDATION_ERROR
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=-1")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "VALIDATION_ERROR"


class TestErrorResponseStructure:
    """
    错误响应结构测试类
    
    验证参数验证失败时的响应结构符合统一格式。
    """

    def test_error_response_has_data_null(self, client: TestClient):
        """
        测试错误响应 data 字段为 null
        
        失败响应格式：{ "data": null, "meta": {...}, "error": {...} }
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert data["data"] is None

    def test_error_response_has_meta(self, client: TestClient):
        """
        测试错误响应包含 meta 字段
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert "meta" in data
        assert isinstance(data["meta"], dict)

    def test_error_response_has_error_object(self, client: TestClient):
        """
        测试错误响应包含 error 对象
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert "error" in data
        assert data["error"] is not None
        assert isinstance(data["error"], dict)

    def test_error_object_has_code(self, client: TestClient):
        """
        测试 error 对象包含 code 字段
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert "code" in data["error"]
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_error_object_has_message(self, client: TestClient):
        """
        测试 error 对象包含 message 字段
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        assert "message" in data["error"]
        assert data["error"]["message"] is not None
        assert len(data["error"]["message"]) > 0

    def test_error_response_complete_structure(self, client: TestClient):
        """
        测试完整的错误响应结构
        
        验证响应包含所有必需字段：
        - data: null
        - meta: {...}
        - error: { code: "...", message: "..." }
        
        Validates: Requirements 5.2
        """
        response = client.get("/v1/news?limit=100")
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证 data 为 null
        assert data["data"] is None
        
        # 验证 meta 是对象
        assert isinstance(data["meta"], dict)
        
        # 验证 error 结构
        assert data["error"] is not None
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert len(data["error"]["message"]) > 0


class TestBoundaryValues:
    """
    边界值测试类
    
    验证 limit 参数在边界值附近的行为。
    """

    def test_limit_1_is_valid(self, client: TestClient):
        """
        测试 limit=1 是有效值，返回 200
        
        Validates: Requirements 4.3
        """
        response = client.get("/v1/news?limit=1")
        assert response.status_code == 200

    def test_limit_50_is_valid(self, client: TestClient):
        """
        测试 limit=50 是有效值，返回 200
        
        Validates: Requirements 4.3
        """
        response = client.get("/v1/news?limit=50")
        assert response.status_code == 200

    def test_limit_boundary_below_min(self, client: TestClient):
        """
        测试 limit=0（最小值-1）返回 400
        
        Validates: Requirements 4.4
        """
        response = client.get("/v1/news?limit=0")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_limit_boundary_above_max(self, client: TestClient):
        """
        测试 limit=51（最大值+1）返回 400
        
        Validates: Requirements 4.4
        """
        response = client.get("/v1/news?limit=51")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"



class TestCursorValidation:
    """
    cursor 参数验证测试类
    
    验证非法 cursor 返回 400 + INVALID_CURSOR，不返回 500。
    
    Requirements: 4.4, 8.3
    """

    def test_invalid_base64_cursor_returns_400(self, client: TestClient):
        """
        测试非法 base64 cursor 返回 400 状态码
        
        cursor=not_base64!! 包含非法字符，应返回 400。
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=not_base64!!")
        assert response.status_code == 400, \
            f"非法 cursor 应返回 400，实际返回 {response.status_code}"

    def test_invalid_base64_cursor_returns_invalid_cursor_code(self, client: TestClient):
        """
        测试非法 base64 cursor 返回 error.code = INVALID_CURSOR
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=not_base64!!")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "INVALID_CURSOR", \
            f"error.code 应为 INVALID_CURSOR，实际为 {data['error']['code']}"

    def test_cursor_with_space_returns_400(self, client: TestClient):
        """
        测试包含空格的 cursor 返回 400 状态码
        
        cursor 包含空格（URL 编码为 %20）应返回 400。
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=abc%20def")
        assert response.status_code == 400, \
            f"包含空格的 cursor 应返回 400，实际返回 {response.status_code}"

    def test_cursor_with_space_returns_invalid_cursor_code(self, client: TestClient):
        """
        测试包含空格的 cursor 返回 error.code = INVALID_CURSOR
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=abc%20def")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "INVALID_CURSOR"

    def test_cursor_missing_padding_returns_400(self, client: TestClient):
        """
        测试缺少 padding 的 cursor 返回 400 状态码
        
        cursor=abc 缺少 base64 padding，应返回 400。
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=abc")
        assert response.status_code == 400, \
            f"缺少 padding 的 cursor 应返回 400，实际返回 {response.status_code}"

    def test_cursor_missing_padding_returns_invalid_cursor_code(self, client: TestClient):
        """
        测试缺少 padding 的 cursor 返回 error.code = INVALID_CURSOR
        
        Validates: Requirements 4.4, 8.3
        """
        response = client.get("/v1/news?cursor=abc")
        data = response.json()
        
        assert data["error"] is not None
        assert data["error"]["code"] == "INVALID_CURSOR"

    def test_invalid_cursor_never_returns_500(self, client: TestClient):
        """
        测试各种非法 cursor 都不返回 500
        
        任何非法 cursor 输入，status 必须为 400，不得返回 500。
        
        Validates: Requirements 4.4, 8.3
        """
        invalid_cursors = [
            "not_base64!!",  # 非法字符
            "abc%20def",     # 包含空格
            "abc",           # 缺少 padding
            "!!!",           # 全部非法字符
            "a" * 1000,      # 超长字符串
            "",              # 空字符串（如果传递）
            "YWJj",          # 有效 base64 但内容无效
            "MjAyNC0wMS0xNQ==",  # 有效 base64 但格式不对（缺少 |）
        ]
        
        for cursor in invalid_cursors:
            if cursor:  # 跳过空字符串
                response = client.get(f"/v1/news?cursor={cursor}")
                assert response.status_code != 500, \
                    f"cursor={cursor} 不应返回 500，实际返回 {response.status_code}"
                # 非法 cursor 应返回 400
                assert response.status_code == 400, \
                    f"cursor={cursor} 应返回 400，实际返回 {response.status_code}"

    def test_invalid_cursor_response_structure(self, client: TestClient):
        """
        测试非法 cursor 的响应结构符合统一格式
        
        失败响应格式：{ "data": null, "meta": {...}, "error": {...} }
        
        Validates: Requirements 5.2, 8.3
        """
        response = client.get("/v1/news?cursor=not_base64!!")
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证 data 为 null
        assert data["data"] is None
        
        # 验证 meta 是对象
        assert isinstance(data["meta"], dict)
        
        # 验证 error 结构
        assert data["error"] is not None
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "INVALID_CURSOR"
        assert len(data["error"]["message"]) > 0

    def test_valid_format_but_invalid_content_cursor_returns_400(self, client: TestClient):
        """
        测试格式正确但内容无效的 cursor 返回 400
        
        base64 编码有效，但解码后内容不符合 timestamp|uuid 格式。
        
        Validates: Requirements 4.4, 8.3
        """
        import base64
        
        # 编码一个不符合格式的字符串
        invalid_content = "invalid_content_without_pipe"
        encoded = base64.urlsafe_b64encode(invalid_content.encode()).decode()
        
        response = client.get(f"/v1/news?cursor={encoded}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "INVALID_CURSOR"

    def test_cursor_with_invalid_timestamp_format_returns_400(self, client: TestClient):
        """
        测试时间戳格式无效的 cursor 返回 400
        
        cursor 解码后时间戳不以 Z 结尾。
        
        Validates: Requirements 4.4, 8.3
        """
        import base64
        
        # 编码一个时间戳不以 Z 结尾的字符串
        invalid_timestamp = "2024-01-15T10:30:00+00:00|123e4567-e89b-12d3-a456-426614174000"
        encoded = base64.urlsafe_b64encode(invalid_timestamp.encode()).decode()
        
        response = client.get(f"/v1/news?cursor={encoded}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "INVALID_CURSOR"

    def test_cursor_with_invalid_uuid_returns_400(self, client: TestClient):
        """
        测试 UUID 无效的 cursor 返回 400
        
        cursor 解码后 UUID 格式无效。
        
        Validates: Requirements 4.4, 8.3
        """
        import base64
        
        # 编码一个 UUID 无效的字符串
        invalid_uuid = "2024-01-15T10:30:00Z|not-a-valid-uuid"
        encoded = base64.urlsafe_b64encode(invalid_uuid.encode()).decode()
        
        response = client.get(f"/v1/news?cursor={encoded}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "INVALID_CURSOR"
