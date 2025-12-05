"""
HeyGen Avatar Video 服務
遵循 Single Responsibility Principle：專注於數位分身影片生成
"""
import os
from pathlib import Path
from typing import Optional
import httpx
import asyncio
from loguru import logger


class HeyGenService:
    """HeyGen 數位分身影片服務"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com/v2"
        self.upload_url = "https://upload.heygen.com/v1"  # 文件上传使用不同的 URL

        if not self.api_key:
            logger.warning("⚠️ HEYGEN_API_KEY 未設定")

    async def upload_audio(self, audio_path: str) -> str:
        """
        上傳音頻到 HeyGen（使用 Upload Asset API）

        Args:
            audio_path: 音頻文件路徑

        Returns:
            音頻 Asset ID
        """
        if not self.api_key:
            raise ValueError("HeyGen API Key 未設定")

        try:
            # 使用新的 Upload Asset API（注意：使用 upload_url 而非 base_url）
            url = f"{self.upload_url}/asset"
            headers = {"X-Api-Key": self.api_key}

            # 使用 httpx 正確的文件上傳方式：在 AsyncClient 上下文中打開文件
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    # 构造 multipart form data - 字段名必须是 "file"
                    files = {"file": (Path(audio_path).name, f, "audio/mpeg")}
                    response = await client.post(url, headers=headers, files=files)

                # 添加詳細的錯誤日誌
                if not response.is_success:
                    error_detail = response.text
                    logger.error(f"❌ HeyGen API 錯誤: {response.status_code} - {error_detail}")

                response.raise_for_status()

                data = response.json()
                # Upload Asset API 返回 asset_id 而不是 URL
                asset_id = data.get("data", {}).get("asset_id")

                if not asset_id:
                    logger.error(f"❌ API 響應無 asset_id: {data}")
                    raise ValueError("未獲取到音頻 Asset ID")

                logger.info(f"📤 音頻上傳成功: {asset_id}")
                return asset_id

        except Exception as e:
            logger.error(f"❌ 音頻上傳失敗: {e}")
            raise

    async def upload_image(self, image_path: str) -> str:
        """
        上傳圖片到 HeyGen（使用 Upload Asset API）

        Args:
            image_path: 圖片路徑

        Returns:
            Image Asset ID
        """
        if not self.api_key:
            raise ValueError("HeyGen API Key 未設定")

        try:
            # 使用新的 Upload Asset API（注意：使用 upload_url 而非 base_url）
            url = f"{self.upload_url}/asset"
            headers = {"X-Api-Key": self.api_key}

            # 根據文件擴展名設置正確的 MIME 類型
            file_ext = Path(image_path).suffix.lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(file_ext, 'image/jpeg')

            # 使用 httpx 正確的文件上傳方式：在 AsyncClient 上下文中打開文件
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(image_path, "rb") as f:
                    # 构造 multipart form data - 字段名必须是 "file"
                    files = {"file": (Path(image_path).name, f, mime_type)}
                    response = await client.post(url, headers=headers, files=files)

                # 添加詳細的錯誤日誌
                if not response.is_success:
                    error_detail = response.text
                    logger.error(f"❌ HeyGen API 錯誤: {response.status_code} - {error_detail}")

                response.raise_for_status()

                data = response.json()
                asset_id = data.get("data", {}).get("asset_id")

                if not asset_id:
                    logger.error(f"❌ API 響應無 asset_id: {data}")
                    raise ValueError("未獲取到圖片 Asset ID")

                logger.info(f"📸 圖片上傳成功: {asset_id}")
                return asset_id

        except Exception as e:
            logger.error(f"❌ 圖片上傳失敗: {e}")
            raise

    async def generate_avatar_video(
        self,
        audio_path: str,
        image_path: str,
        task_id: str,
        output_dir: str = "generated_content/videos"
    ) -> str:
        """
        生成 Avatar Video（會說話的數位分身）

        Args:
            audio_path: 音頻文件路徑
            image_path: 圖片路徑
            task_id: 任務 ID
            output_dir: 輸出目錄

        Returns:
            生成的影片路徑
        """
        if not self.api_key:
            raise ValueError("HeyGen API Key 未設定")

        try:
            # 準備輸出路徑
            output_path = Path(output_dir) / f"{task_id}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"🎬 開始生成 Avatar Video: {task_id}")

            # 步驟 1: 上傳音頻
            logger.info("📤 上傳音頻...")
            audio_asset_id = await self.upload_audio(audio_path)

            # 步驟 2: 上傳圖片
            logger.info("📸 上傳圖片...")
            image_asset_id = await self.upload_image(image_path)

            # 步驟 3: 創建 Avatar Video
            logger.info("🎥 創建 Avatar Video...")
            video_id = await self._create_video(image_asset_id, audio_asset_id)

            # 步驟 4: 輪詢狀態
            logger.info("⏳ 等待影片生成...")
            video_url = await self._poll_video_status(video_id)

            # 步驟 5: 下載影片
            logger.info("📥 下載影片...")
            await self._download_video(video_url, output_path)

            logger.info(f"✅ Avatar Video 生成完成: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Avatar Video 生成失敗: {e}")
            raise

    async def _create_video(self, image_asset_id: str, audio_asset_id: str) -> str:
        """創建 Avatar Video 任務（使用 Asset ID）"""
        url = f"{self.base_url}/video/generate"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # 使用 asset_id 而不是 avatar_id 和 audio_url
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "photo_avatar",
                        "image_asset_id": image_asset_id
                    },
                    "voice": {
                        "type": "audio",
                        "audio_asset_id": audio_asset_id
                    },
                    "background": {
                        "type": "color",
                        "value": "#FFFFFF"
                    }
                }
            ],
            "dimension": {
                "width": 1280,
                "height": 720
            },
            "test": False  # 正式生成（非測試模式）
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            video_id = data.get("data", {}).get("video_id")

            if not video_id:
                raise ValueError("未獲取到 Video ID")

            logger.info(f"🎬 Video 任務創建: {video_id}")
            return video_id

    async def _poll_video_status(self, video_id: str, max_wait: int = 600) -> str:
        """
        輪詢影片生成狀態

        Args:
            video_id: 影片 ID
            max_wait: 最長等待時間（秒），預設 10 分鐘

        Returns:
            影片 URL
        """
        url = f"{self.base_url}/video/{video_id}"
        headers = {"X-Api-Key": self.api_key}

        start_time = asyncio.get_event_loop().time()

        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                status = data.get("data", {}).get("status")

                if status == "completed":
                    video_url = data.get("data", {}).get("video_url")
                    if not video_url:
                        raise ValueError("未獲取到影片 URL")
                    logger.info(f"✅ 影片生成完成")
                    return video_url

                elif status == "failed":
                    error = data.get("data", {}).get("error", "未知錯誤")
                    raise Exception(f"影片生成失敗: {error}")

                # 檢查超時
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait:
                    raise TimeoutError(f"影片生成超時（超過 {max_wait} 秒）")

                # 顯示進度
                logger.info(f"⏳ 影片生成中... ({status})")
                await asyncio.sleep(10)  # 每 10 秒檢查一次

    async def _download_video(self, video_url: str, output_path: Path):
        """下載影片"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"📥 影片下載完成: {output_path}")

    async def get_avatar_list(self) -> list:
        """獲取已創建的 Avatar 列表"""
        if not self.api_key:
            raise ValueError("HeyGen API Key 未設定")

        try:
            url = f"{self.base_url}/avatars"
            headers = {"X-Api-Key": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                avatars = data.get("data", {}).get("avatars", [])
                return avatars

        except Exception as e:
            logger.error(f"❌ 獲取 Avatar 列表失敗: {e}")
            raise
