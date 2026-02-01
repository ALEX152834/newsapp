"""
属性测试 (Property-Based Tests)

使用 Hypothesis 库验证系统的正确性属性。

Requirements: 2.2, 2.5, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3, 6.2, 8.3
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.article import Article


# ============================================================
# Hypothesis 策略定义
# ============================================================


@st.composite
def article_data(draw):
    """
    生成 Article 数据的 Hypothesis 策略
    
    生成有效的 Article 字段值。
    """
    unique_id = draw(st.uuids())
    title = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    source = draw(st.sampled_from([
        "新华社", "人民日报", "央视新闻", "澎湃新闻", "财新网",
        "界面新闻", "36氪", "虎嗅网", "钛媒体", "第一财经"
    ]))
    url = f"https://example.com/news/{unique_id}"
    
    # 生成过去 30 天内的时间
    days_ago = draw(st.integers(min_value=0, max_value=30))
    hours_ago = draw(st.integers(min_value=0, max_value=23))
    minutes_ago = draw(st.integers(min_value=0, max_value=59))
    seconds_ago = draw(st.integers(min_value=0, max_value=59))
    
    published_at = datetime.now(timezone.utc) - timedelta(
        days=days_ago,
        hours=hours_ago,
        minutes=minutes_ago,
        seconds=seconds_ago
    )
    
    return {
        "id": unique_id,
        "title": title,
        "source": source,
        "url": url,
        "published_at": published_at,
        "summary": draw(st.none() | st.text(max_size=500)),
    }


@st.composite
def valid_limit(draw):
    """生成有效的 limit 参数值 (1-50)"""
    return draw(st.integers(min_value=1, max_value=50))


@st.composite
def invalid_limit_below(draw):
    """生成无效的 limit 参数值 (< 1)"""
    return draw(st.integers(max_value=0))


@st.composite
def invalid_limit_above(draw):
    """生成无效的 limit 参数值 (> 50)"""
    return draw(st.integers(min_value=51, max_value=1000))


# ============================================================
# Property 1: URL 唯一约束
# ============================================================


class TestProperty1URLUniqueness:
    """
    Property 1: URL 唯一约束
    
    *For any* 两条 Article 记录，如果它们具有相同的 url 值，
    则第二条记录的插入操作应该失败并抛出唯一约束冲突错误。
    
    **Validates: Requirements 2.2, 2.5**
    """

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(data=article_data())
    def test_duplicate_url_raises_integrity_error(
        self, db_session: Session, data: dict
    ):
        """
        测试插入重复 URL 时抛出 IntegrityError
        
        **Validates: Requirements 2.2, 2.5**
        """
        # 创建第一条记录
        article1 = Article(
            id=data["id"],
            title=data["title"],
            source=data["source"],
            url=data["url"],
            published_at=data["published_at"],
            summary=data["summary"],
        )
        db_session.add(article1)
        db_session.flush()
        
        # 尝试创建具有相同 URL 的第二条记录
        article2 = Article(
            id=uuid.uuid4(),  # 不同的 ID
            title="另一个标题",
            source="另一个来源",
            url=data["url"],  # 相同的 URL
            published_at=datetime.now(timezone.utc),
            summary=None,
        )
        db_session.add(article2)
        
        # 应该抛出 IntegrityError
        with pytest.raises(IntegrityError):
            db_session.flush()
        
        # 回滚以便下一次测试
        db_session.rollback()


# ============================================================
# Property 2: 新闻列表排序正确性
# ============================================================


class TestProperty2SortingCorrectness:
    """
    Property 2: 新闻列表排序正确性
    
    *For any* 从 /v1/news 接口返回的新闻列表，列表中的每一项的 
    (published_at, id) 都应该大于等于其后一项的 (published_at, id)，
    即按 published_at DESC, id DESC 排序。
    
    **Validates: Requirements 4.2**
    """

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(count=st.integers(min_value=2, max_value=50))
    def test_news_list_sorted_correctly(
        self,
        client: TestClient,
        db_session: Session,
        count: int,
    ):
        """
        测试新闻列表按 (published_at DESC, id DESC) 排序
        
        **Validates: Requirements 4.2**
        """
        # 清理之前的数据
        db_session.query(Article).delete()
        db_session.commit()
        
        # 创建测试数据
        base_time = datetime.now(timezone.utc)
        for i in range(count):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        # 请求新闻列表
        response = client.get(f"/v1/news?limit={min(count, 50)}")
        assert response.status_code == 200
        
        data = response.json()
        items = data["data"]["items"]
        
        # 验证排序
        for i in range(len(items) - 1):
            current = items[i]
            next_item = items[i + 1]
            
            current_time = current["published_at"]
            next_time = next_item["published_at"]
            
            # published_at 应该降序
            if current_time == next_time:
                # 相同时间时，id 应该降序
                assert current["id"] > next_item["id"], \
                    f"排序错误：相同 published_at 时，id 应降序"
            else:
                assert current_time >= next_time, \
                    f"排序错误：published_at 应降序"


# ============================================================
# Property 3: limit 参数范围验证
# ============================================================


class TestProperty3LimitValidation:
    """
    Property 3: limit 参数范围验证
    
    *For any* 对 /v1/news 接口的请求：
    - 当 limit 在 1-50 范围内时，返回的 items 数量应该不超过 limit
    - 当 limit 小于 1 或大于 50 时，应该返回 HTTP 400 错误
    
    **Validates: Requirements 4.3, 4.4**
    """

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=valid_limit())
    def test_valid_limit_returns_correct_count(
        self,
        client: TestClient,
        db_session: Session,
        limit: int,
    ):
        """
        测试有效 limit 返回不超过 limit 数量的 items
        
        **Validates: Requirements 4.3**
        """
        # 清理并创建足够的测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        # 创建 60 条数据确保有足够数据
        base_time = datetime.now(timezone.utc)
        for i in range(60):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 200
        
        data = response.json()
        items = data["data"]["items"]
        
        # items 数量不应超过 limit
        assert len(items) <= limit, \
            f"items 数量 ({len(items)}) 不应超过 limit ({limit})"

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=invalid_limit_below())
    def test_invalid_limit_below_returns_400(
        self,
        client: TestClient,
        limit: int,
    ):
        """
        测试 limit < 1 返回 400 + VALIDATION_ERROR
        
        **Validates: Requirements 4.4**
        """
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=invalid_limit_above())
    def test_invalid_limit_above_returns_400(
        self,
        client: TestClient,
        limit: int,
    ):
        """
        测试 limit > 50 返回 400 + VALIDATION_ERROR
        
        **Validates: Requirements 4.4**
        """
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"



# ============================================================
# Property 4: 游标分页正确性
# ============================================================


class TestProperty4CursorPagination:
    """
    Property 4: 游标分页正确性
    
    *For any* 包含 N 条记录的数据集，使用游标分页遍历所有数据时：
    - 每次请求返回的数据不应与之前请求的数据重复
    - 所有分页请求返回的数据合集应该等于完整数据集
    - 分页顺序应该与单次请求大量数据的顺序一致
    
    **Validates: Requirements 4.5**
    """

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    )
    @given(
        total_count=st.integers(min_value=10, max_value=100),
        page_size=st.integers(min_value=5, max_value=20),
    )
    def test_pagination_no_duplicates(
        self,
        client: TestClient,
        db_session: Session,
        total_count: int,
        page_size: int,
    ):
        """
        测试分页遍历无重复数据
        
        **Validates: Requirements 4.5**
        """
        # 清理并创建测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        base_time = datetime.now(timezone.utc)
        created_ids = set()
        
        for i in range(total_count):
            article_id = uuid.uuid4()
            created_ids.add(str(article_id))
            article = Article(
                id=article_id,
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{article_id}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        # 遍历所有分页
        all_ids = set()
        cursor = None
        page_count = 0
        max_pages = (total_count // page_size) + 5  # 防止无限循环
        
        while page_count < max_pages:
            url = f"/v1/news?limit={page_size}"
            if cursor:
                url += f"&cursor={cursor}"
            
            response = client.get(url)
            assert response.status_code == 200
            
            data = response.json()
            items = data["data"]["items"]
            
            # 检查本页数据不与之前重复
            for item in items:
                item_id = item["id"]
                assert item_id not in all_ids, \
                    f"发现重复数据: {item_id}"
                all_ids.add(item_id)
            
            cursor = data["meta"]["next_cursor"]
            page_count += 1
            
            if cursor is None:
                break
        
        # 验证遍历了所有数据
        assert all_ids == created_ids, \
            f"分页遍历应返回所有数据，缺少: {created_ids - all_ids}"

    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    )
    @given(
        total_count=st.integers(min_value=20, max_value=60),
        page_size=st.integers(min_value=5, max_value=15),
    )
    def test_pagination_order_consistency(
        self,
        client: TestClient,
        db_session: Session,
        total_count: int,
        page_size: int,
    ):
        """
        测试分页顺序与单次请求一致
        
        **Validates: Requirements 4.5**
        """
        # 清理并创建测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        base_time = datetime.now(timezone.utc)
        
        for i in range(total_count):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        # 获取单次请求的完整顺序（最多 50 条）
        single_response = client.get(f"/v1/news?limit=50")
        single_items = single_response.json()["data"]["items"]
        single_order = [item["id"] for item in single_items]
        
        # 通过分页获取相同数量的数据
        paginated_order = []
        cursor = None
        items_collected = 0
        
        while items_collected < len(single_order):
            url = f"/v1/news?limit={page_size}"
            if cursor:
                url += f"&cursor={cursor}"
            
            response = client.get(url)
            data = response.json()
            items = data["data"]["items"]
            
            for item in items:
                if items_collected < len(single_order):
                    paginated_order.append(item["id"])
                    items_collected += 1
            
            cursor = data["meta"]["next_cursor"]
            if cursor is None:
                break
        
        # 验证顺序一致
        assert paginated_order == single_order[:len(paginated_order)], \
            "分页顺序应与单次请求一致"


# ============================================================
# Property 5: 成功响应格式一致性
# ============================================================


class TestProperty5SuccessResponseFormat:
    """
    Property 5: 成功响应格式一致性
    
    *For any* 成功的 API 请求，响应 JSON 应该符合以下结构：
    - 包含 data 字段（非 null）
    - 包含 meta 字段
    - error 字段为 null
    - 对于分页接口，meta 应包含 count 和 next_cursor 字段
    - 对于新闻列表，data.items 中每项应包含 id、title、source、url、published_at 字段
    - 时间字段格式为 ISO 8601 UTC（以 Z 结尾）
    
    **Validates: Requirements 4.6, 4.7, 4.8, 5.1, 5.3**
    """

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=valid_limit())
    def test_success_response_structure(
        self,
        client: TestClient,
        db_session: Session,
        limit: int,
    ):
        """
        测试成功响应结构符合规范
        
        **Validates: Requirements 4.6, 5.1**
        """
        # 创建一些测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data, "响应应包含 data 字段"
        assert "meta" in data, "响应应包含 meta 字段"
        assert "error" in data, "响应应包含 error 字段"
        
        # 验证成功响应
        assert data["data"] is not None, "成功响应 data 不应为 null"
        assert data["error"] is None, "成功响应 error 应为 null"

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=valid_limit())
    def test_meta_contains_pagination_fields(
        self,
        client: TestClient,
        db_session: Session,
        limit: int,
    ):
        """
        测试 meta 包含分页字段
        
        **Validates: Requirements 4.8, 5.3**
        """
        response = client.get(f"/v1/news?limit={limit}")
        data = response.json()
        
        meta = data["meta"]
        assert "count" in meta, "meta 应包含 count 字段"
        assert "next_cursor" in meta, "meta 应包含 next_cursor 字段"

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(count=st.integers(min_value=1, max_value=20))
    def test_items_have_required_fields(
        self,
        client: TestClient,
        db_session: Session,
        count: int,
    ):
        """
        测试 items 包含必需字段
        
        **Validates: Requirements 4.7**
        """
        # 创建测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        base_time = datetime.now(timezone.utc)
        for i in range(count):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        response = client.get("/v1/news")
        data = response.json()
        items = data["data"]["items"]
        
        required_fields = ["id", "title", "source", "url", "published_at"]
        
        for item in items:
            for field in required_fields:
                assert field in item, f"item 应包含 {field} 字段"
                assert item[field] is not None, f"item.{field} 不应为 null"

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(count=st.integers(min_value=1, max_value=20))
    def test_datetime_format_ends_with_z(
        self,
        client: TestClient,
        db_session: Session,
        count: int,
    ):
        """
        测试时间字段格式为 ISO 8601 UTC（以 Z 结尾）
        
        **Validates: Requirements 4.7**
        """
        # 创建测试数据
        db_session.query(Article).delete()
        db_session.commit()
        
        base_time = datetime.now(timezone.utc)
        for i in range(count):
            article = Article(
                id=uuid.uuid4(),
                title=f"测试新闻 {i}",
                source="测试来源",
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=base_time - timedelta(seconds=i),
                summary=None,
            )
            db_session.add(article)
        db_session.commit()
        
        response = client.get("/v1/news")
        data = response.json()
        items = data["data"]["items"]
        
        iso8601_utc_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        
        for item in items:
            published_at = item["published_at"]
            
            # 验证以 Z 结尾
            assert published_at.endswith("Z"), \
                f"published_at 应以 Z 结尾: {published_at}"
            
            # 验证不包含 +00:00
            assert "+00:00" not in published_at, \
                f"published_at 不应包含 +00:00: {published_at}"
            
            # 验证完整格式
            assert re.match(iso8601_utc_pattern, published_at), \
                f"published_at 格式不正确: {published_at}"



# ============================================================
# Property 6: 错误响应格式一致性
# ============================================================


class TestProperty6ErrorResponseFormat:
    """
    Property 6: 错误响应格式一致性
    
    *For any* 失败的 API 请求（如参数验证失败），响应 JSON 应该符合以下结构：
    - data 字段为 null
    - 包含 meta 字段
    - error 字段非 null，包含 code 和 message
    - error.code 必须为 MVP 允许的错误码之一：VALIDATION_ERROR、INVALID_CURSOR、INTERNAL_ERROR
    
    **Validates: Requirements 5.2, 8.3**
    """

    ALLOWED_ERROR_CODES = {"VALIDATION_ERROR", "INVALID_CURSOR", "INTERNAL_ERROR"}

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=invalid_limit_below())
    def test_error_response_structure_for_invalid_limit_below(
        self,
        client: TestClient,
        limit: int,
    ):
        """
        测试 limit < 1 的错误响应结构
        
        **Validates: Requirements 5.2, 8.3**
        """
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 400
        
        data = response.json()
        
        # 验证顶层结构
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        
        # 验证错误响应
        assert data["data"] is None, "错误响应 data 应为 null"
        assert isinstance(data["meta"], dict), "meta 应为对象"
        assert data["error"] is not None, "错误响应 error 不应为 null"
        
        # 验证 error 结构
        assert "code" in data["error"], "error 应包含 code"
        assert "message" in data["error"], "error 应包含 message"
        
        # 验证 error.code 是允许的值
        assert data["error"]["code"] in self.ALLOWED_ERROR_CODES, \
            f"error.code 应为允许的值之一，实际为: {data['error']['code']}"

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(limit=invalid_limit_above())
    def test_error_response_structure_for_invalid_limit_above(
        self,
        client: TestClient,
        limit: int,
    ):
        """
        测试 limit > 50 的错误响应结构
        
        **Validates: Requirements 5.2, 8.3**
        """
        response = client.get(f"/v1/news?limit={limit}")
        assert response.status_code == 400
        
        data = response.json()
        
        # 验证错误响应结构
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] in self.ALLOWED_ERROR_CODES
        assert "message" in data["error"]
        assert len(data["error"]["message"]) > 0

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(cursor=st.text(min_size=1, max_size=50).filter(
        lambda x: not x.isalnum() or len(x) < 4
    ))
    def test_error_response_structure_for_invalid_cursor(
        self,
        client: TestClient,
        cursor: str,
    ):
        """
        测试无效 cursor 的错误响应结构
        
        **Validates: Requirements 5.2, 8.3**
        """
        # 跳过可能是有效 base64 的字符串
        assume(not cursor.replace("-", "+").replace("_", "/").isalnum())
        
        import urllib.parse
        encoded_cursor = urllib.parse.quote(cursor)
        
        response = client.get(f"/v1/news?cursor={encoded_cursor}")
        
        # 无效 cursor 应返回 400，不是 500
        assert response.status_code != 500, \
            f"无效 cursor 不应返回 500，实际返回 {response.status_code}"
        
        if response.status_code == 400:
            data = response.json()
            
            # 验证错误响应结构
            assert data["data"] is None
            assert data["error"] is not None
            assert data["error"]["code"] in self.ALLOWED_ERROR_CODES


# ============================================================
# Property 7: 种子脚本幂等性
# ============================================================


class TestProperty7SeedIdempotency:
    """
    Property 7: 种子脚本幂等性
    
    *For any* 执行次数 N（N >= 1），多次执行种子脚本后数据库中的记录数
    应该与执行一次相同，即 f(x) = f(f(x))。
    
    **Validates: Requirements 6.2**
    """

    def test_seed_script_idempotent(self, db_session: Session):
        """
        测试种子脚本幂等性
        
        模拟种子脚本的 upsert 逻辑，验证多次执行结果一致。
        
        **Validates: Requirements 6.2**
        """
        from sqlalchemy.dialects.postgresql import insert
        
        # 清理数据
        db_session.query(Article).delete()
        db_session.commit()
        
        # 模拟种子数据
        seed_data = [
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "title": "种子新闻 1",
                "source": "测试来源",
                "url": "https://example.com/seed/1",
                "published_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                "summary": "摘要 1",
            },
            {
                "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "title": "种子新闻 2",
                "source": "测试来源",
                "url": "https://example.com/seed/2",
                "published_at": datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                "summary": "摘要 2",
            },
            {
                "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
                "title": "种子新闻 3",
                "source": "测试来源",
                "url": "https://example.com/seed/3",
                "published_at": datetime(2024, 1, 3, 12, 0, 0, tzinfo=timezone.utc),
                "summary": "摘要 3",
            },
        ]
        
        def run_seed():
            """模拟种子脚本的 upsert 逻辑"""
            for data in seed_data:
                stmt = insert(Article).values(**data)
                stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
                db_session.execute(stmt)
            db_session.commit()
        
        # 第一次执行
        run_seed()
        count_after_first = db_session.query(Article).count()
        
        # 第二次执行
        run_seed()
        count_after_second = db_session.query(Article).count()
        
        # 第三次执行
        run_seed()
        count_after_third = db_session.query(Article).count()
        
        # 验证幂等性
        assert count_after_first == len(seed_data), \
            f"第一次执行后应有 {len(seed_data)} 条记录"
        assert count_after_second == count_after_first, \
            "第二次执行后记录数应与第一次相同"
        assert count_after_third == count_after_first, \
            "第三次执行后记录数应与第一次相同"

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(execution_count=st.integers(min_value=1, max_value=5))
    def test_seed_idempotent_property(
        self,
        db_session: Session,
        execution_count: int,
    ):
        """
        属性测试：任意执行次数后记录数一致
        
        **Validates: Requirements 6.2**
        """
        from sqlalchemy.dialects.postgresql import insert
        
        # 清理数据
        db_session.query(Article).delete()
        db_session.commit()
        
        # 固定的种子数据
        seed_data = [
            {
                "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "title": "属性测试新闻 1",
                "source": "测试来源",
                "url": "https://example.com/prop/1",
                "published_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                "summary": None,
            },
            {
                "id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                "title": "属性测试新闻 2",
                "source": "测试来源",
                "url": "https://example.com/prop/2",
                "published_at": datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                "summary": None,
            },
        ]
        
        def run_seed():
            for data in seed_data:
                stmt = insert(Article).values(**data)
                stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
                db_session.execute(stmt)
            db_session.commit()
        
        # 执行 N 次
        for _ in range(execution_count):
            run_seed()
        
        final_count = db_session.query(Article).count()
        
        # 无论执行多少次，记录数都应该等于种子数据数量
        assert final_count == len(seed_data), \
            f"执行 {execution_count} 次后应有 {len(seed_data)} 条记录，实际有 {final_count} 条"
