import os
from datetime import datetime
from services.create_database import AsyncSessionLocal, FileInfo
from sqlalchemy import select
from services.log_service import get_logger

logger = get_logger('database_service')

# 获取数据库会话 - 异步版本
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 数据库操作函数 - 异步版本
async def add_file_info(db, file_name, random_name, pages):
    """添加文件信息到数据库"""
    try:
        logger.info(f"添加文件信息到数据库，file_name: {file_name}, random_name: {random_name}, pages: {pages}")
        file_info = FileInfo(
            file_name=file_name,
            random_name=random_name,
            pages=pages,
            upload_time=datetime.now()
        )
        db.add(file_info)
        await db.commit()
        await db.refresh(file_info)
        return file_info
    except Exception as e:
        logger.error(f"添加文件信息到数据库失败，file_name: {file_name}, random_name: {random_name}, pages: {pages}", e)
        raise

async def update_file_parse_status(db, random_name):
    """更新文件解析状态"""
    try:
        logger.info(f"更新文件解析状态，random_name: {random_name}")
        result = await db.execute(
            select(FileInfo).filter(FileInfo.random_name == random_name)
        )
        file_info = result.scalars().first()
        if file_info:
            file_info.is_parsed = True
            file_info.parse_time = datetime.now()
            await db.commit()
            await db.refresh(file_info)
        return file_info
    except Exception as e:
        logger.error(f"更新文件解析状态失败，random_name: {random_name}", e)
        raise

async def update_file_index_status(db, random_name):
    """更新文件索引状态"""
    try:
        logger.info(f"更新文件索引状态，random_name: {random_name}")
        result = await db.execute(
            select(FileInfo).filter(FileInfo.random_name == random_name)
        )
        file_info = result.scalars().first()
        if file_info:
            file_info.is_builded_index = True
            file_info.build_index_time = datetime.now()
            await db.commit()
            await db.refresh(file_info)
        return file_info
    except Exception as e:
        logger.error(f"更新文件索引状态失败，random_name: {random_name}", e)
        raise

async def get_file_by_random_name(db, random_name):
    """根据随机名称获取文件信息"""
    try:
        logger.info(f"根据随机名称获取文件信息，random_name: {random_name}")
        result = await db.execute(
            select(FileInfo).filter(FileInfo.random_name == random_name)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"根据随机名称获取文件信息失败，random_name: {random_name}", e)
        raise

async def get_file_by_name(db, random_name):
    """根据文件名获取文件信息"""
    try:
        logger.info(f"根据文件名获取文件信息，random_name: {random_name}")
        result = await db.execute(
            select(FileInfo).filter(FileInfo.random_name == random_name)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"根据文件名获取文件信息失败，random_name: {random_name}", e)
        raise

async def get_all_file_names(db):
    """获取所有文件名和对应的随机名"""
    try:
        logger.info("获取所有文件名和对应的随机名")
        result = await db.execute(select(FileInfo.file_name, FileInfo.random_name))
        return result.all()
    except Exception as e:
        logger.error("获取所有文件名和对应的随机名失败", e)
        raise
