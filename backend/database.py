from sqlalchemy import Column, String, Integer, Boolean, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 创建数据库引擎 - 异步版本
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(
    DATABASE_URL, pool_recycle=3600  # MySQL连接池回收时间设置
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, autocommit=False, autoflush=False
)

# 创建基础模型类
Base = declarative_base()

# 定义FileInfo模型
class FileInfo(Base):
    __tablename__ = "file_info"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), index=True)
    random_name = Column(String(100), unique=True, index=True)
    upload_time = Column(DateTime)
    is_parsed = Column(Boolean, default=False)
    is_builded_index = Column(Boolean, default=False)
    parse_time = Column(DateTime, nullable=True)
    build_index_time = Column(DateTime, nullable=True)
    pages = Column(Integer, nullable=True)

# 初始化数据库
async def init_db():
    # 如果数据库已经创建，则重新创建
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
    print("数据库初始化完成")