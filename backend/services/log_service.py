# services/log_service.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import traceback

# 日志目录路径
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 默认日志配置
DEFAULT_LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'datefmt': '%Y-%m-%d %H:%M:%S',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,  # 保留5个备份文件
}

class LogService:
    """日志服务类，提供统一的日志记录功能"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def init_logging(cls, config=None):
        """
        初始化日志系统
        
        Args:
            config: 日志配置字典，覆盖默认配置
        """
        if cls._initialized:
            return
        
        # 合并配置
        final_config = DEFAULT_LOG_CONFIG.copy()
        if config:
            final_config.update(config)
        
        # 设置根日志级别
        root_logger = logging.getLogger()
        root_logger.setLevel(final_config['level'])
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(final_config['level'])
        console_formatter = logging.Formatter(
            final_config['format'],
            datefmt=final_config['datefmt']
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 创建文件处理器（带轮转功能）
        log_file = os.path.join(
            LOG_DIR,
            f"app_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=final_config['max_bytes'],
            backupCount=final_config['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(final_config['level'])
        file_formatter = logging.Formatter(
            final_config['format'],
            datefmt=final_config['datefmt']
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        cls._initialized = True
        cls.get_logger('LogService').info('日志系统初始化完成')
    
    @classmethod
    def get_logger(cls, name):
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if not cls._initialized:
            cls.init_logging()
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def debug(cls, name, message):
        """记录调试级别日志"""
        cls.get_logger(name).debug(message)
    
    @classmethod
    def info(cls, name, message):
        """记录信息级别日志"""
        cls.get_logger(name).info(message)
    
    @classmethod
    def warning(cls, name, message):
        """记录警告级别日志"""
        cls.get_logger(name).warning(message)
    
    @classmethod
    def error(cls, name, message, exc_info=False):
        """记录错误级别日志"""
        cls.get_logger(name).error(message, exc_info=exc_info)
    
    @classmethod
    def critical(cls, name, message, exc_info=False):
        """记录严重错误级别日志"""
        cls.get_logger(name).critical(message, exc_info=exc_info)
    
    @classmethod
    def log_exception(cls, name, message, exception):
        """
        记录异常信息
        
        Args:
            name: 日志记录器名称
            message: 自定义错误消息
            exception: 异常对象
        """
        error_info = {
            'message': str(exception),
            'type': type(exception).__name__,
            'traceback': traceback.format_exc()
        }
        cls.get_logger(name).error(
            f"{message}\n异常详情: {error_info['message']}\n" 
            f"异常类型: {error_info['type']}\n" 
            f"堆栈信息:\n{error_info['traceback']}"
        )

# 创建便捷的日志记录函数
def get_logger(name):
    """便捷函数：获取日志记录器"""
    return LogService.get_logger(name)

def debug(name, message):
    """便捷函数：记录调试日志"""
    LogService.debug(name, message)

def info(name, message):
    """便捷函数：记录信息日志"""
    LogService.info(name, message)

def warning(name, message):
    """便捷函数：记录警告日志"""
    LogService.warning(name, message)

def error(name, message, exc_info=False):
    """便捷函数：记录错误日志"""
    LogService.error(name, message, exc_info)

def critical(name, message, exc_info=False):
    """便捷函数：记录严重错误日志"""
    LogService.critical(name, message, exc_info)

def log_exception(name, message, exception):
    """便捷函数：记录异常信息"""
    LogService.log_exception(name, message, exception)

# 初始化日志系统（可选，也可以在应用启动时手动初始化）
LogService.init_logging()