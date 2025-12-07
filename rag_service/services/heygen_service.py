import os
import asyncio
import httpx
import mimetypes
from pathlib import Path
from loguru import logger

class HeyGenService:
    """
    HeyGen Avatar Video 服務 (Talking Photo 最終修正版)
    修正生成類型並增加等待時間，確保 ID 可用
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com/v2"
        self.upload_url = "https://upload.heygen.com/v1/asset"
        
        if not self.api_key:
            logger.warning("⚠️ HEYGEN_API_KEY 未設定")

    async def generate_avatar_video(self, audio_path: str, image_path: str, task_id: str, base_url: str = None) -> str:
        if not self.api_key:
            raise ValueError("HeyGen API Key 未設定")

        logger.info(f"🎬 [HeyGen] 開始處理任務: {task_id}")
        return await self._generate_via_upload(audio_path, image_path, task_id)

    async def _generate_via_upload(self, audio_path: str, image_path: str, task_id: str) -> str:
        output_path = Path("generated_content/videos") / f"{task_id}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 1. 上傳素材
            logger.info("📤 步驟 1/4: 上傳音頻...")
            audio_data = await self._upload_asset(audio_path, "audio")
            audio_asset_id = audio_data["id"]
            logger.info(f"✅ 音頻上傳完成 (ID: {audio_asset_id})")

            logger.info("📤 步驟 2/4: 上傳圖片...")
            image_data = await self._upload_asset(image_path, "image")
            image_key = image_data.get("image_key") or image_data["id"]
            logger.info(f"✅ 圖片上傳完成 (Key: {image_key})")

            # 2. 註冊 Photo Avatar
            logger.info("🖼️ 步驟 3/4: 註冊 Photo Avatar...")
            avatar_id = await self._create_photo_avatar(image_key, f"Avatar_{task_id}")
            logger.info(f"✅ Avatar 註冊成功 (ID: {avatar_id})")

            logger.info("⏳ 等待 5 秒讓 Avatar 生效...")
            await asyncio.sleep(5)

            # 3. 建立生成任務
            logger.info("🎥 步驟 4/4: 建立生成任務...")
            video_id = await self._create_task(
                voice_input={
                    "type": "audio", 
                    "audio_asset_id": audio_asset_id
                },
                char_input={
                    "type": "talking_photo",
                    "talking_photo_id": avatar_id
                }
            )
            logger.info(f"✅ 任務建立成功 ID: {video_id}")

            # 4. 輪詢與下載
            return await self._poll_and_download(video_id, output_path)

        except Exception as e:
            logger.error(f"❌ 影片生成流程失敗: {e}")
            raise

    async def _upload_asset(self, file_path: str, asset_type: str) -> dict:
        """上傳檔案 (Raw Binary)"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"找不到檔案: {file_path}")

        try:
            with open(path, "rb") as f:
                file_content = f.read()
        except Exception as e:
            raise Exception(f"讀取失敗: {e}")

        if not file_content:
            raise Exception("檔案內容為空")

        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "audio/mpeg" if asset_type == "audio" else "image/jpeg"

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    self.upload_url,
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": mime_type
                    },
                    content=file_content
                )
                
                if resp.status_code != 200:
                    try:
                        err = resp.json()
                        msg = err.get('message', resp.text)
                    except:
                        msg = resp.text
                    raise Exception(f"API Error ({resp.status_code}): {msg}")
                
                return resp.json()["data"]
                
            except httpx.RequestError as e:
                raise Exception(f"連線錯誤: {e}")

    async def _create_photo_avatar(self, image_key: str, name: str) -> str:
        """註冊 Avatar Group"""
        url = f"{self.base_url}/photo_avatar/avatar_group/create"
        payload = { "name": name, "image_key": image_key }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={
                    "X-Api-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if resp.status_code != 200:
                # 自動清理機制：如果額度滿了，刪除舊的再試
                error_msg = resp.text
                if "limit" in error_msg.lower() or "exceeded" in error_msg.lower():
                    logger.warning("⚠️ Avatar 額度已滿，嘗試清理舊資料...")
                    await self._cleanup_oldest_avatar()
                    await asyncio.sleep(2) # 等待刪除生效
                    return await self._create_photo_avatar(image_key, name) # 重試

                raise Exception(f"Avatar 註冊失敗: {error_msg}")

            return resp.json()["data"]["id"]

    async def _cleanup_oldest_avatar(self):
        """清理最舊的 Avatar"""
        list_url = f"{self.base_url}/photo_avatars" # 或 /v2/photo_avatars
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(list_url, headers={"X-Api-Key": self.api_key})
            if resp.status_code == 200:
                avatars = resp.json().get("data", {}).get("avatars", [])
                if avatars:
                    target_id = avatars[-1]["id"] # 刪除最後一個（通常是最舊的）
                    logger.info(f"🗑️ 刪除舊 Avatar: {target_id}")
                    await client.delete(
                        f"{self.base_url}/photo_avatar/{target_id}", 
                        headers={"X-Api-Key": self.api_key}
                    )

    async def _create_task(self, voice_input: dict, char_input: dict) -> str:
        """建立生成任務"""
        payload = {
            "video_inputs": [{
                "character": char_input,
                "voice": voice_input,
            }],
            "dimension": {"width": 1280, "height": 720}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/video/generate",
                headers={
                    "X-Api-Key": self.api_key, 
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get('error', {}).get('message', resp.text)
                except:
                    msg = resp.text
                raise Exception(f"建立任務失敗: {msg}")
            
            return resp.json()["data"]["video_id"]

    async def _poll_and_download(self, video_id: str, output_path: Path) -> str:
        url = f"{self.base_url}/video/{video_id}"
        headers = {"X-Api-Key": self.api_key}
        
        logger.info(f"⏳ 開始輪詢 {video_id}...")
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for i in range(60):
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code != 200:
                        await asyncio.sleep(10)
                        continue

                    data = resp.json().get("data", {})
                    status = data.get("status")
                    
                    if status == "completed":
                        video_url = data["video_url"]
                        logger.info("📥 下載影片...")
                        dl_resp = await client.get(video_url, timeout=600.0)
                        with open(output_path, "wb") as f:
                            f.write(dl_resp.content)
                        logger.info(f"✅ 儲存至: {output_path}")
                        return str(output_path)
                    
                    elif status == "failed":
                        error = data.get('error')
                        raise Exception(f"HeyGen 處理失敗: {error}")
                    
                    if i % 2 == 0:
                        logger.info(f"⏳ 生成中... ({status})")
                    
                    await asyncio.sleep(10)
                    
                except httpx.RequestError:
                    await asyncio.sleep(10)
                
        raise TimeoutError("生成超時")

    async def get_avatar_list(self):
        return []