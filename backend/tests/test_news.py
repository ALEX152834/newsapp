"""
News 接口测试

测试 /v1/news 端点的功能和响应格式。

Requirements: 7.2
"""

import re
from typing import Callable, List

from fastapi.testclient import TestClient

from app.models.article import Article


class TestNewsEndpointSuccess:
    """
    /v1/news 端点成功场景测试类
    
    验证新闻列表接口的正确性。
    """

    def test_news_returns_200(self, client: TestClient):
        """
        测试 /v1/news 返回 200 状态码
        
        Validates: Requirements 4.1
        """
        response = client.get("/v1/news")
        assert response.status_code == 200

    def test_news_response_structure(self, client: TestClient):
        """
        测试响应结构符合统一格式
        
        成功响应格式：{ "data": {...}, "meta": {...}, "error": null }
        
        Validates: Requirements 4.6, 5.1
        """
        response = client.get("/v1/news")
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证成功响应 error 为 null
        assert data["error"] is None
        
        # 验证 data 非空
        assert data["data"] is not None

    def test_news_data_contains_items_list(self, client: TestClient):
        """
        测试 data.items 是一个列表
        
        Validates: Requirements 4.7
        """
        response = client.get("/v1/news")
        data = response.json()
        
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)

    def test_news_meta_contains_count_and_next_cursor(self, client: TestClient):
        """
        测试 meta 包含 count 和 next_cursor 字段
        
        Validates: Requirements 4.8, 5.3
        """
        response = client.get("/v1/news")
        data = response.json()
        
        assert "count" in data["meta"]
        assert "next_cursor" in data["meta"]

    def test_news_empty_database_returns_empty_items(self, client: TestClient):
        """
        测试空数据库返回空 items 数组
        
        Validates: Requirements 4.1, 4.7
        """
        response = client.get("/v1/news")
        data = response.json()
        
        assert data["data"]["items"] == []
        assert data["meta"]["count"] == 0
        assert data["meta"]["next_cursor"] is None


class TestNewsEndpointWithData:
    """
    /v1/news 端点有数据场景测试类
    
    使用测试数据工厂验证新闻列表接口的正确性。
    """

    def test_news_returns_items_count(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试返回的 items 数量与 meta.count 一致
        
        Validates: Requirements 4.8
        """
        # 创建 10 条测试数据
        articles_with_different_times(count=10)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        count = data["meta"]["count"]
        
        assert len(items) == count
        assert count == 10

    def test_news_items_have_required_fields(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试每个 item 包含必需字段：id, title, source, url, published_at
        
        Validates: Requirements 4.7
        """
        # 创建测试数据
        articles_with_different_times(count=3)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        required_fields = ["id", "title", "source", "url", "published_at"]
        
        for item in items:
            for field in required_fields:
                assert field in item, f"item 缺少必需字段: {field}"
                assert item[field] is not None, f"item.{field} 不应为 null"

    def test_news_published_at_format_ends_with_z(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试 items 中 published_at 格式为 ISO 8601 UTC，以 Z 结尾
        
        格式要求：YYYY-MM-DDTHH:MM:SSZ
        禁止输出 +00:00 格式
        
        Validates: Requirements 4.7
        """
        # 创建测试数据
        articles_with_different_times(count=5)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        iso8601_utc_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        
        for item in items:
            published_at = item["published_at"]
            
            # 验证以 Z 结尾
            assert published_at.endswith("Z"), \
                f"published_at 应以 Z 结尾，实际值: {published_at}"
            
            # 验证不包含 +00:00
            assert "+00:00" not in published_at, \
                f"published_at 不应包含 +00:00，实际值: {published_at}"
            
            # 验证完整的 ISO 8601 UTC 格式
            assert re.match(iso8601_utc_pattern, published_at), \
                f"published_at 格式不正确，期望格式: YYYY-MM-DDTHH:MM:SSZ，实际值: {published_at}"

    def test_news_response_json_not_contains_plus_zero(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试整个响应 JSON 不包含 +00:00 格式
        
        确保所有时间字段都使用 Z 结尾格式
        
        Validates: Requirements 4.7
        """
        # 创建测试数据
        articles_with_different_times(count=3)
        
        response = client.get("/v1/news")
        response_text = response.text
        
        assert "+00:00" not in response_text, \
            f"响应中不应包含 +00:00 格式，响应内容: {response_text}"

    def test_news_sorted_by_published_at_desc(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试 items 按 published_at DESC 排序
        
        Validates: Requirements 4.2
        """
        # 创建 10 条具有不同 published_at 的测试数据
        articles_with_different_times(count=10)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        
        # 验证排序：每一项的 published_at 应该大于等于后一项
        for i in range(len(items) - 1):
            current_time = items[i]["published_at"]
            next_time = items[i + 1]["published_at"]
            assert current_time >= next_time, \
                f"排序错误：items[{i}].published_at ({current_time}) 应 >= items[{i+1}].published_at ({next_time})"

    def test_news_sorted_by_id_desc_when_same_published_at(
        self,
        client: TestClient,
        articles_with_same_time: Callable[..., List[Article]],
    ):
        """
        测试相同 published_at 时按 id DESC 排序
        
        Validates: Requirements 4.2
        """
        # 创建 5 条具有相同 published_at 的测试数据
        articles_with_same_time(count=5)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        
        # 验证排序：相同 published_at 时，id 应该降序
        for i in range(len(items) - 1):
            current_time = items[i]["published_at"]
            next_time = items[i + 1]["published_at"]
            
            if current_time == next_time:
                current_id = items[i]["id"]
                next_id = items[i + 1]["id"]
                assert current_id > next_id, \
                    f"排序错误：相同 published_at 时，items[{i}].id ({current_id}) 应 > items[{i+1}].id ({next_id})"

    def test_news_default_limit_is_20(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试默认 limit 为 20
        
        Validates: Requirements 4.3
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        response = client.get("/v1/news")
        data = response.json()
        
        items = data["data"]["items"]
        count = data["meta"]["count"]
        
        assert len(items) == 20
        assert count == 20

    def test_news_custom_limit(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试自定义 limit 参数
        
        Validates: Requirements 4.3
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        response = client.get("/v1/news?limit=10")
        data = response.json()
        
        items = data["data"]["items"]
        count = data["meta"]["count"]
        
        assert len(items) == 10
        assert count == 10

    def test_news_limit_max_50(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试 limit 最大值为 50
        
        Validates: Requirements 4.3
        """
        # 创建 60 条测试数据
        articles_batch(count=60)
        
        response = client.get("/v1/news?limit=50")
        data = response.json()
        
        items = data["data"]["items"]
        count = data["meta"]["count"]
        
        assert len(items) == 50
        assert count == 50

    def test_news_next_cursor_present_when_more_data(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试有更多数据时 next_cursor 不为 null
        
        Validates: Requirements 4.8
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        response = client.get("/v1/news?limit=10")
        data = response.json()
        
        next_cursor = data["meta"]["next_cursor"]
        
        assert next_cursor is not None, "有更多数据时 next_cursor 不应为 null"

    def test_news_next_cursor_null_when_no_more_data(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试没有更多数据时 next_cursor 为 null
        
        Validates: Requirements 4.8
        """
        # 创建 5 条测试数据
        articles_batch(count=5)
        
        response = client.get("/v1/news?limit=10")
        data = response.json()
        
        next_cursor = data["meta"]["next_cursor"]
        
        assert next_cursor is None, "没有更多数据时 next_cursor 应为 null"

    def test_news_next_cursor_url_safe(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试 next_cursor 仅包含 URL-safe 字符
        
        Validates: Requirements 4.5
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        response = client.get("/v1/news?limit=10")
        data = response.json()
        
        next_cursor = data["meta"]["next_cursor"]
        
        # URL-safe base64 字符集：A-Z, a-z, 0-9, -, _, =
        url_safe_pattern = r"^[A-Za-z0-9_-]*=*$"
        assert re.match(url_safe_pattern, next_cursor), \
            f"next_cursor 应仅包含 URL-safe 字符，实际值: {next_cursor}"

    def test_news_response_has_request_id_header(
        self,
        client: TestClient,
        articles_with_different_times: Callable[..., List[Article]],
    ):
        """
        测试响应头包含 X-Request-ID
        
        Validates: Requirements 8.4
        """
        # 创建测试数据
        articles_with_different_times(count=3)
        
        response = client.get("/v1/news")
        
        assert "X-Request-ID" in response.headers, "响应头应包含 X-Request-ID"
        
        # 验证 X-Request-ID 是有效的 UUID 格式
        request_id = response.headers["X-Request-ID"]
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, request_id, re.IGNORECASE), \
            f"X-Request-ID 应为有效的 UUID 格式，实际值: {request_id}"


class TestNewsPagination:
    """
    /v1/news 分页功能测试类
    
    验证游标分页的正确性。
    """

    def test_news_pagination_with_cursor(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试使用 cursor 进行分页
        
        Validates: Requirements 4.5
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        # 第一页
        response1 = client.get("/v1/news?limit=10")
        data1 = response1.json()
        
        items1 = data1["data"]["items"]
        next_cursor = data1["meta"]["next_cursor"]
        
        assert len(items1) == 10
        assert next_cursor is not None
        
        # 第二页
        response2 = client.get(f"/v1/news?limit=10&cursor={next_cursor}")
        data2 = response2.json()
        
        items2 = data2["data"]["items"]
        
        assert len(items2) == 10
        
        # 验证第一页和第二页数据不重复
        ids1 = {item["id"] for item in items1}
        ids2 = {item["id"] for item in items2}
        
        assert ids1.isdisjoint(ids2), "分页数据不应重复"

    def test_news_pagination_complete_traversal(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试分页遍历所有数据
        
        Validates: Requirements 4.5
        """
        # 创建 25 条测试数据
        created_articles = articles_batch(count=25)
        created_ids = {str(a.id) for a in created_articles}
        
        # 遍历所有分页
        all_ids = set()
        cursor = None
        page_count = 0
        max_pages = 10  # 防止无限循环
        
        while page_count < max_pages:
            url = "/v1/news?limit=10"
            if cursor:
                url += f"&cursor={cursor}"
            
            response = client.get(url)
            data = response.json()
            
            items = data["data"]["items"]
            for item in items:
                all_ids.add(item["id"])
            
            cursor = data["meta"]["next_cursor"]
            page_count += 1
            
            if cursor is None:
                break
        
        # 验证遍历了所有数据
        assert all_ids == created_ids, "分页遍历应返回所有数据"

    def test_news_pagination_maintains_order(
        self,
        client: TestClient,
        articles_batch: Callable[..., List[Article]],
    ):
        """
        测试分页保持排序顺序
        
        Validates: Requirements 4.2, 4.5
        """
        # 创建 30 条测试数据
        articles_batch(count=30)
        
        # 收集所有分页数据
        all_items = []
        cursor = None
        
        for _ in range(5):  # 最多 5 页
            url = "/v1/news?limit=10"
            if cursor:
                url += f"&cursor={cursor}"
            
            response = client.get(url)
            data = response.json()
            
            items = data["data"]["items"]
            all_items.extend(items)
            
            cursor = data["meta"]["next_cursor"]
            if cursor is None:
                break
        
        # 验证整体排序正确
        for i in range(len(all_items) - 1):
            current = all_items[i]
            next_item = all_items[i + 1]
            
            # 按 (published_at DESC, id DESC) 排序
            if current["published_at"] == next_item["published_at"]:
                assert current["id"] > next_item["id"], \
                    f"排序错误：相同 published_at 时，id 应降序"
            else:
                assert current["published_at"] > next_item["published_at"], \
                    f"排序错误：published_at 应降序"
