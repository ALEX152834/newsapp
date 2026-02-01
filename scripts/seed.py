#!/usr/bin/env python3
"""
种子数据脚本

向 articles 表插入 10 条假新闻数据。
支持重复执行（幂等性）：通过检查 URL 是否存在来跳过重复记录。

使用方式：
    make seed
    # 或
    docker compose -f infra/docker-compose.yml run --rm -v $(PWD)/scripts:/app/scripts api python /app/scripts/seed.py

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 在容器中运行时，/app 是 backend 目录
# 将 /app 添加到 Python 路径，以便导入 app 模块
# 同时支持本地开发环境（backend 目录在父目录中）
container_app_path = Path("/app")
local_backend_path = Path(__file__).parent.parent / "backend"

if container_app_path.exists() and (container_app_path / "app").exists():
    sys.path.insert(0, str(container_app_path))
else:
    sys.path.insert(0, str(local_backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.article import Article
from app.database import Base


# 10 条假新闻数据
SEED_ARTICLES = [
    {
        "title": "人工智能在医疗领域取得重大突破",
        "source": "科技日报",
        "url": "https://example.com/news/ai-medical-breakthrough",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "summary": "最新研究表明，AI 辅助诊断系统在早期癌症检测中准确率达到 95%。",
    },
    {
        "title": "全球气候峰会达成新协议",
        "source": "环球时报",
        "url": "https://example.com/news/climate-summit-agreement",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "summary": "各国领导人承诺在 2030 年前将碳排放减少 50%。",
    },
    {
        "title": "新能源汽车销量创历史新高",
        "source": "汽车之家",
        "url": "https://example.com/news/ev-sales-record",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "summary": "2024 年第一季度，新能源汽车销量同比增长 120%。",
    },
    {
        "title": "量子计算机实现重要里程碑",
        "source": "科学网",
        "url": "https://example.com/news/quantum-computing-milestone",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=4),
        "summary": "研究团队成功实现 1000 量子比特的稳定运行。",
    },
    {
        "title": "国际空间站迎来新一批宇航员",
        "source": "航天新闻",
        "url": "https://example.com/news/iss-new-astronauts",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=5),
        "summary": "来自三个国家的六名宇航员将在空间站进行为期六个月的科学实验。",
    },
    {
        "title": "5G 网络覆盖率突破 80%",
        "source": "通信世界",
        "url": "https://example.com/news/5g-coverage-80-percent",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=6),
        "summary": "全国主要城市 5G 网络覆盖率已达到 80%，农村地区加速推进中。",
    },
    {
        "title": "生物技术公司发布新型疫苗",
        "source": "健康时报",
        "url": "https://example.com/news/new-vaccine-release",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=7),
        "summary": "新型 mRNA 疫苗在临床试验中显示出 98% 的有效性。",
    },
    {
        "title": "智能家居市场规模突破千亿",
        "source": "经济观察报",
        "url": "https://example.com/news/smart-home-market-growth",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=8),
        "summary": "预计到 2025 年，智能家居市场规模将达到 1500 亿元。",
    },
    {
        "title": "可再生能源发电量首次超过化石燃料",
        "source": "能源周刊",
        "url": "https://example.com/news/renewable-energy-milestone",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=9),
        "summary": "这是能源转型的重要里程碑，标志着清洁能源时代的到来。",
    },
    {
        "title": "自动驾驶技术获得新突破",
        "source": "汽车科技",
        "url": "https://example.com/news/autonomous-driving-breakthrough",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=10),
        "summary": "L4 级自动驾驶系统在复杂城市环境中测试成功。",
    },
]


def seed_articles() -> None:
    """
    向数据库插入种子数据。
    
    使用 ON CONFLICT DO NOTHING 实现幂等性，
    重复执行不会产生重复数据。
    """
    print("=" * 50)
    print("开始执行种子数据脚本")
    print(f"数据库连接: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    print("=" * 50)
    
    # 创建数据库引擎和会话
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 确保表存在
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    try:
        inserted_count = 0
        skipped_count = 0
        
        for article_data in SEED_ARTICLES:
            # 检查是否已存在相同 URL 的记录
            existing = session.query(Article).filter(
                Article.url == article_data["url"]
            ).first()
            
            if existing:
                print(f"  [跳过] URL 已存在: {article_data['url']}")
                skipped_count += 1
                continue
            
            # 创建新记录
            article = Article(
                title=article_data["title"],
                source=article_data["source"],
                url=article_data["url"],
                published_at=article_data["published_at"],
                summary=article_data["summary"],
            )
            session.add(article)
            print(f"  [插入] {article_data['title'][:30]}...")
            inserted_count += 1
        
        # 提交事务
        session.commit()
        
        # 统计总数
        total_count = session.query(Article).count()
        
        print("=" * 50)
        print("种子数据脚本执行完成")
        print(f"  新插入: {inserted_count} 条")
        print(f"  已跳过: {skipped_count} 条")
        print(f"  总记录: {total_count} 条")
        print("=" * 50)
        
    except Exception as e:
        session.rollback()
        print(f"错误: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_articles()
