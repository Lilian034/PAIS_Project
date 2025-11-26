"""
ElevenLabs 語音克隆服務
遵循 Single Responsibility Principle：專注於語音生成
"""
import os
from pathlib import Path
from typing import Optional
import httpx
from loguru import logger


class ElevenLabsService:
    """ElevenLabs 語音克隆服務"""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("MAYOR_VOICE_ID")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        if not self.api_key:
            logger.warning("⚠️ ELEVENLABS_API_KEY 未設定")
        if not self.voice_id:
            logger.warning("⚠️ MAYOR_VOICE_ID 未設定")
    
    async def generate_voice(
        self, 
        text: str, 
        task_id: str,
        output_dir: str = "generated_content/voices"
    ) -> str:
        """
        生成語音
        
        Args:
            text: 要轉換的文字
            task_id: 任務 ID
            output_dir: 輸出目錄
        
        Returns:
            生成的語音檔案路徑
        """
        if not self.api_key or not self.voice_id:
            raise ValueError("ElevenLabs API Key 或 Voice ID 未設定")
        
        try:
            # 準備輸出路徑
            output_path = Path(output_dir) / f"{task_id}.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 呼叫 API
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",  # 最新多語言模型，更好的中文支援
                "language_code": "zh",  # 明確指定中文
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            logger.info(f"🎤 開始生成語音: {task_id}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                # 儲存檔案
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"✅ 語音生成完成: {output_path}")
                return str(output_path)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ ElevenLabs API 錯誤: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ 語音生成失敗: {e}")
            raise
    
    async def get_available_voices(self) -> list:
        """取得可用的語音列表"""
        if not self.api_key:
            raise ValueError("ElevenLabs API Key 未設定")
        
        try:
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                return data.get("voices", [])
                
        except Exception as e:
            logger.error(f"❌ 取得語音列表失敗: {e}")
            raise