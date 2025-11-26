"""
統一錯誤處理模組
提供裝飾器和工具函數用於標準化 API 錯誤處理
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException
from loguru import logger


class APIError(Exception):
    """API 統一錯誤類別"""

    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """資料驗證錯誤"""
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=400, detail=detail)


class AuthenticationError(APIError):
    """認證錯誤"""
    def __init__(self, message: str = "未授權訪問", detail: dict = None):
        super().__init__(message, status_code=401, detail=detail)


class NotFoundError(APIError):
    """資源不存在錯誤"""
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=404, detail=detail)


class ServerError(APIError):
    """伺服器內部錯誤"""
    def __init__(self, message: str = "伺服器內部錯誤", detail: dict = None):
        super().__init__(message, status_code=500, detail=detail)


def handle_api_error(
    error_message: str = None,
    log_error: bool = True,
    raise_http_exception: bool = True
) -> Callable:
    """
    統一錯誤處理裝飾器

    Args:
        error_message: 自定義錯誤訊息
        log_error: 是否記錄錯誤日誌
        raise_http_exception: 是否拋出 HTTPException

    Returns:
        裝飾器函數

    Example:
        @handle_api_error(error_message="處理聊天請求失敗")
        async def process_chat(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # 已經是 HTTP 異常，直接拋出
                raise
            except APIError as e:
                # 自定義 API 錯誤
                if log_error:
                    logger.error(f"❌ API Error in {func.__name__}: {e.message}")
                if raise_http_exception:
                    raise HTTPException(
                        status_code=e.status_code,
                        detail=e.message
                    )
                raise
            except Exception as e:
                # 未預期的錯誤
                error_msg = error_message or f"{func.__name__} 執行失敗"
                if log_error:
                    logger.error(
                        f"❌ Unexpected error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                if raise_http_exception:
                    raise HTTPException(
                        status_code=500,
                        detail=f"{error_msg}: {str(e)}"
                    )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except APIError as e:
                if log_error:
                    logger.error(f"❌ API Error in {func.__name__}: {e.message}")
                if raise_http_exception:
                    raise HTTPException(
                        status_code=e.status_code,
                        detail=e.message
                    )
                raise
            except Exception as e:
                error_msg = error_message or f"{func.__name__} 執行失敗"
                if log_error:
                    logger.error(
                        f"❌ Unexpected error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                if raise_http_exception:
                    raise HTTPException(
                        status_code=500,
                        detail=f"{error_msg}: {str(e)}"
                    )
                raise

        # 根據函數類型返回對應的包裝器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def safe_execute(func: Callable, *args, default=None, log_error: bool = True, **kwargs) -> Any:
    """
    安全執行函數，捕獲異常並返回默認值

    Args:
        func: 要執行的函數
        *args: 函數參數
        default: 發生錯誤時的默認返回值
        log_error: 是否記錄錯誤
        **kwargs: 函數關鍵字參數

    Returns:
        函數執行結果或默認值

    Example:
        result = safe_execute(
            risky_function,
            arg1, arg2,
            default=[],
            log_error=True
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"❌ Error in safe_execute({func.__name__}): {str(e)}")
        return default


async def safe_execute_async(
    func: Callable,
    *args,
    default=None,
    log_error: bool = True,
    **kwargs
) -> Any:
    """
    安全執行異步函數，捕獲異常並返回默認值

    Args:
        func: 要執行的異步函數
        *args: 函數參數
        default: 發生錯誤時的默認返回值
        log_error: 是否記錄錯誤
        **kwargs: 函數關鍵字參數

    Returns:
        函數執行結果或默認值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"❌ Error in safe_execute_async({func.__name__}): {str(e)}")
        return default


def format_error_response(error: Exception, include_detail: bool = False) -> dict:
    """
    格式化錯誤響應

    Args:
        error: 異常對象
        include_detail: 是否包含詳細錯誤資訊

    Returns:
        格式化的錯誤字典
    """
    if isinstance(error, APIError):
        response = {
            "success": False,
            "error": error.message,
            "status_code": error.status_code
        }
        if include_detail and error.detail:
            response["detail"] = error.detail
    else:
        response = {
            "success": False,
            "error": str(error),
            "status_code": 500
        }
        if include_detail:
            response["detail"] = {
                "type": type(error).__name__,
                "message": str(error)
            }

    return response
