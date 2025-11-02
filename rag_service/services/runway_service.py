"""
Runway 影片生成服務
遵循 Single Responsibility Principle：專注於影片生成
"""
import os
from pathlib import Path
from typing import Optional
import httpx
import asyncio
from loguru import logger


class RunwayService:
    """Runway 圖片轉影片服務"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY")
        self.base_url = "https://api.runwayml.com/v1"
        
        if not self.api_key:
            logger.warning("⚠️ RUNWAY_API_KEY 未設定")
    
    async def generate_video(
        self,
        image_path: str,
        task_id: str,
        prompt: Optional[str] = None,
        output_dir: str = "generated_content/videos"
    ) -> str:
        """
        圖片轉影片
        
        Args:
            image_path: 輸入圖片路徑
            task_id: 任務 ID
            prompt: 影片生成提示詞
            output_dir: 輸出目錄
        
        Returns:
            生成的影片檔案路徑
        """
        if not self.api_key:
            raise ValueError("Runway API Key 未設定")
        
        try:
            # 準備輸出路徑
            output_path = Path(output_dir) / f"{task_id}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🎬 開始生成影片: {task_id}")
            
            # 步驟 1: 上傳圖片
            image_url = await self._upload_image(image_path)
            
            # 步驟 2: 建立影片生成任務
            generation_id = await self._create_generation(image_url, prompt)
            
            # 步驟 3: 輪詢任務狀態直到完成
            video_url = await self._poll_generation(generation_id)
            
            # 步驟 4: 下載影片
            await self._download_video(video_url, output_path)
            
            logger.info(f"✅ 影片生成完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ 影片生成失敗: {e}")
            raise
    
    async def _upload_image(self, image_path: str) -> str:
        """上傳圖片到 Runway"""
        url = f"{self.base_url}/uploads"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        with open(image_path, "rb") as f:
            files = {"file": f}
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, files=files)
                response.raise_for_status()
                
                data = response.json()
                image_url = data["url"]
                logger.info(f"📤 圖片上傳成功: {image_url}")
                return image_url
    
    async def _create_generation(self, image_url: str, prompt: Optional[str]) -> str:
        """建立影片生成任務"""
        url = f"{self.base_url}/image_to_video"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "image_url": image_url,
            "prompt": prompt or "自然動態效果",
            "duration": 5  # 5秒影片
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            generation_id = data["id"]
            logger.info(f"🎬 影片生成任務建立: {generation_id}")
            return generation_id
    
    async def _poll_generation(self, generation_id: str, max_wait: int = 300) -> str:
        """輪詢生成狀態"""
        url = f"{self.base_url}/tasks/{generation_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                status = data["status"]
                
                if status == "completed":
                    video_url = data["output"]["url"]
                    logger.info(f"✅ 影片生成完成")
                    return video_url
                
                elif status == "failed":
                    raise Exception(f"影片生成失敗: {data.get('error')}")
                
                # 檢查超時
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait:
                    raise TimeoutError(f"影片生成超時 ({max_wait}秒)")
                
                # 等待後重試
                logger.info(f"⏳ 影片生成中... ({status})")
                await asyncio.sleep(5)
    
    async def _download_video(self, video_url: str, output_path: Path):
        """下載影片"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"📥 影片下載完成: {output_path}")