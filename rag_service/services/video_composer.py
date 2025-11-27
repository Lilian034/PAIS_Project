"""
影片合成服務
遵循 Single Responsibility Principle：專注於音畫合成
"""
import os
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger


class VideoComposer:
    """音畫合成服務 - 使用 FFmpeg 合併音頻和影片"""

    def __init__(self):
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """檢查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ FFmpeg 可用")
            else:
                logger.warning("⚠️ FFmpeg 可能未正確安裝")
        except FileNotFoundError:
            logger.error("❌ FFmpeg 未安裝，請安裝 FFmpeg")
            raise RuntimeError("FFmpeg 未安裝")
        except Exception as e:
            logger.warning(f"⚠️ FFmpeg 檢查失敗: {e}")

    async def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
        audio_delay: float = 0.0
    ) -> str:
        """
        合併音頻和影片

        Args:
            video_path: 原始影片路徑（無聲音）
            audio_path: 音頻檔案路徑
            output_path: 輸出路徑（可選，自動生成）
            audio_delay: 音頻延遲（秒），正值表示延遲，負值表示提前

        Returns:
            合成後的影片路徑
        """
        try:
            # 檢查輸入檔案
            if not Path(video_path).exists():
                raise FileNotFoundError(f"影片不存在: {video_path}")
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"音頻不存在: {audio_path}")

            # 生成輸出路徑
            if not output_path:
                video_dir = Path(video_path).parent
                video_stem = Path(video_path).stem
                output_path = str(video_dir / f"{video_stem}_with_audio.mp4")

            # 確保輸出目錄存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"🎬 開始合成影片")
            logger.info(f"  影片: {video_path}")
            logger.info(f"  音頻: {audio_path}")
            logger.info(f"  輸出: {output_path}")

            # 構建 FFmpeg 命令
            cmd = self._build_ffmpeg_command(
                video_path,
                audio_path,
                output_path,
                audio_delay
            )

            # 執行 FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )

            if result.returncode != 0:
                logger.error(f"❌ FFmpeg 錯誤: {result.stderr}")
                raise RuntimeError(f"FFmpeg 合成失敗: {result.stderr}")

            # 驗證輸出檔案
            if not Path(output_path).exists():
                raise RuntimeError("輸出檔案未生成")

            file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ 影片合成完成: {output_path} ({file_size:.2f} MB)")

            return output_path

        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg 執行超時")
            raise TimeoutError("影片合成超時（超過5分鐘）")
        except Exception as e:
            logger.error(f"❌ 影片合成失敗: {e}")
            raise

    def _build_ffmpeg_command(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_delay: float
    ) -> list:
        """
        構建 FFmpeg 命令

        策略：
        1. 保留原影片的視覺內容
        2. 替換/添加音軌
        3. 如果音頻比影片短，影片繼續播放（無聲）
        4. 如果音頻比影片長，在音頻結束處截斷
        """
        cmd = [
            "ffmpeg",
            "-y",  # 覆蓋輸出檔案
            "-i", video_path,  # 輸入影片
            "-i", audio_path,  # 輸入音頻
        ]

        # 如果有音頻延遲
        if audio_delay != 0:
            cmd.extend(["-itsoffset", str(audio_delay)])

        # 合成策略
        cmd.extend([
            "-c:v", "copy",  # 複製影片流（不重新編碼，速度快）
            "-c:a", "aac",   # 音頻編碼為 AAC
            "-b:a", "192k",  # 音頻比特率
            "-map", "0:v:0", # 使用第一個輸入的視頻流
            "-map", "1:a:0", # 使用第二個輸入的音頻流
            "-shortest",     # 以較短的流為準（通常是影片）
            output_path
        ])

        return cmd

    async def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: Optional[str] = None,
        music_volume: float = 0.3
    ) -> str:
        """
        為影片添加背景音樂（保留原音頻）

        Args:
            video_path: 已有音頻的影片路徑
            music_path: 背景音樂路徑
            output_path: 輸出路徑
            music_volume: 背景音樂音量（0.0-1.0）

        Returns:
            合成後的影片路徑
        """
        try:
            if not Path(video_path).exists():
                raise FileNotFoundError(f"影片不存在: {video_path}")
            if not Path(music_path).exists():
                raise FileNotFoundError(f"音樂不存在: {music_path}")

            if not output_path:
                video_dir = Path(video_path).parent
                video_stem = Path(video_path).stem
                output_path = str(video_dir / f"{video_stem}_with_music.mp4")

            logger.info(f"🎵 開始添加背景音樂")

            # FFmpeg 混音命令
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", music_path,
                "-filter_complex",
                f"[1:a]volume={music_volume}[a1];[0:a][a1]amix=inputs=2:duration=shortest[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(f"添加背景音樂失敗: {result.stderr}")

            logger.info(f"✅ 背景音樂添加完成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ 添加背景音樂失敗: {e}")
            raise

    def get_media_duration(self, file_path: str) -> float:
        """
        獲取媒體文件時長（秒）

        Args:
            file_path: 媒體文件路徑

        Returns:
            時長（秒）
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.warning(f"⚠️ 無法獲取媒體時長: {file_path}")
                return 0.0

        except Exception as e:
            logger.warning(f"⚠️ 獲取媒體時長失敗: {e}")
            return 0.0
