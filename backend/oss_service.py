import os,sys
import math
import time
from urllib.parse import urlparse
from typing import Optional
from oss2 import Auth, Bucket
import oss2

import requests
import json
# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
from config import OSS_CONFIG
import logging

logger = logging.getLogger("media_generation")


class OSSService:
    """OSS操作服务（修复文件大小为0问题，含完整校验机制）"""

    def __init__(self, oss_config: dict):
        self.config = oss_config
        # 初始化OSS认证与Bucket连接
        self.auth = Auth(self.config["access_key_id"], self.config["access_key_secret"])
        self.bucket = Bucket(
            self.auth,
            f"https://{self.config['endpoint']}",
            self.config["bucket_name"],
            connect_timeout=120,  # 建立TCP连接的最大等待时间
        )
        # 从配置获取视频/图片存储根目录
        self.video_folder = self.config["video_folder"]
        self.image_folder = self.config["image_folder"]
        # 验证OSS SDK版本（关键：避免版本不兼容）
        logger.info(f"OSS SDK版本：{oss2.__version__}")

    def download_file(self, oss_url: str, local_folder: str, progress_callback=None) -> Optional[str]:
        """从OSS下载文件到本地指定目录"""
        try:
            # 解析OSS URL，提取文件在OSS中的路径
            parsed_url = urlparse(oss_url)
            object_path = parsed_url.path.lstrip("/")
            filename = os.path.basename(object_path)
            local_path = os.path.join(local_folder, filename)
            
            # 获取文件元数据以获取大小
            try:
                head_info = self.bucket.head_object(object_path)
                total_size = head_info.content_length
            except Exception:
                total_size = 0
                
            # 先检查文件是否存在， 如果存在且大小一致，则直接返回下载路径
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size > 0 and (total_size == 0 or local_size == total_size):
                    logger.info(f"文件已存在，跳过下载 | 本地路径：{local_path}")
                    return local_path

            # 定义默认进度回调
            def default_progress_callback(consumed_bytes, total_bytes):
                if total_bytes:
                    rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
                    logger.info(f"下载进度: {rate}% ({consumed_bytes}/{total_bytes})")

            # 执行下载
            self.bucket.get_object_to_file(
                object_path, 
                local_path, 
                progress_callback=progress_callback if progress_callback else default_progress_callback
            )
            
            # 验证下载结果
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                logger.info(
                    f"OSS文件下载成功 | OSS URL：{oss_url} -> 本地路径：{local_path}"
                )
                return local_path
            else:
                logger.warning(
                    f"OSS下载文件无效 | 本地路径：{local_path}（文件不存在或为空）"
                )
                return None

        except Exception as e:
            logger.error(
                f"OSS文件下载失败 | OSS URL：{oss_url} | 错误信息：{str(e)}",
                exc_info=True,
            )
            return None

    def upload_file(
        self, local_path: str, oss_folder: str, is_video: bool = False
    ) -> Optional[str]:
        """将本地文件上传到OSS，包含完整的文件校验和进度打印"""
        try:
            # 1. 基础有效性校验
            if not os.path.exists(local_path):
                logger.warning(f"OSS上传跳过 | 本地文件不存在：{local_path}")
                return None

            # 检查是否为真实文件（非目录/链接）
            if not os.path.isfile(local_path):
                logger.error(f"OSS上传拒绝 | 路径不是有效文件：{local_path}")
                return None

            # 检查是否为软链接，自动指向真实路径
            if os.path.islink(local_path):
                real_path = os.path.realpath(local_path)
                logger.warning(
                    f"检测到软链接 | 原路径：{local_path} -> 真实路径：{real_path}"
                )
                local_path = real_path  # 使用真实路径

            # 检查文件读权限
            if not os.access(local_path, os.R_OK):
                logger.error(
                    f"OSS上传拒绝 | 无读权限：{local_path}（当前用户：{os.getlogin() or '未知'}）"
                )
                return None

            # 2. 等待文件就绪（解决生成工具未释放句柄问题）
            max_retry = 5  # 最大重试次数
            retry_interval = 10  # 重试间隔（秒）
            local_file_size = 0
            # 先睡眠5秒
            time.sleep(5)

            for retry in range(max_retry):
                local_file_size = os.path.getsize(local_path)
                logger.info(f"文件大小：{local_file_size}")
                if local_file_size > 0:
                    break  # 文件大小正常，退出等待
                # 最后一次重试仍为0，直接报错
                if retry == max_retry - 1:
                    logger.error(
                        f"文件始终为空 | 路径：{local_path}（已重试{max_retry}次）"
                    )
                    return None
                # 继续等待并重试
                logger.warning(
                    f"文件未就绪（大小为0） | 路径：{local_path} | "
                    f"重试次数：{retry+1}/{max_retry} | {retry_interval}秒后重试"
                )
                time.sleep(retry_interval)

            # 3. 构建OSS路径信息
            local_filename = os.path.basename(local_path)
            base_root = self.video_folder if is_video else self.image_folder
            object_path = os.path.join(base_root, oss_folder, local_filename).replace(
                os.sep, "/"
            )
            file_type = "视频" if is_video else "图片"
            file_size_mb = local_file_size / 1024 / 1024  # 转换为MB

            # 4. 上传进度回调函数
            def progress_callback(
                consumed_bytes: int, total_bytes: Optional[int] = None
            ) -> None:
                # 确定实际总字节数（优先用SDK返回值）
                actual_total = (
                    total_bytes
                    if (total_bytes is not None and total_bytes > 0)
                    else local_file_size
                )
                progress_pct = (
                    math.floor((consumed_bytes / actual_total) * 1000) / 10
                    if actual_total > 0
                    else 100.0
                )

                # 转换为MB显示
                consumed_mb = consumed_bytes / 1024 / 1024
                total_mb = actual_total / 1024 / 1024

                logger.info(
                    f"OSS{file_type}上传进度 | "
                    f"文件名：{local_filename} | "
                    f"已上传：{consumed_mb:.2f}MB / 总计：{total_mb:.2f}MB | "
                    f"进度：{progress_pct}%"
                )

            # 5. 执行上传
            logger.info(
                f"开始OSS{file_type}上传 | "
                f"本地路径：{local_path} | "
                f"OSS路径：{object_path} | "
                f"文件大小：{file_size_mb:.2f}MB"
            )
            self.bucket.put_object_from_file(
                key=object_path,
                filename=local_path,
                progress_callback=progress_callback,
            )

            # 6. 返回公网访问URL
            oss_public_url = f"https://{self.config['bucket_name']}.{self.config['endpoint']}/{object_path}"
            logger.info(f"OSS{file_type}上传成功 | 访问链接：{oss_public_url}")
            return oss_public_url

        except Exception as e:
            logger.error(
                f"OSS{('视频' if is_video else '图片')}上传失败 | "
                f"本地路径：{local_path} | 错误：{str(e)}",
                exc_info=True,
            )
            return None

    def upload_file_expire(
        self,
        local_path: str,
        oss_folder: str,
        is_video: bool = False,
        expire_seconds: int = 3600,  # 临时链接过期时间，默认1小时
    ) -> Optional[str]:
        """
        将本地文件上传到OSS，返回有效期内的临时访问链接（官方标准实现）
        核心修复：sign_url使用官方标准参数名+正确调用方式
        """
        try:
            # 1. 基础有效性校验（原有逻辑不变）
            if not os.path.exists(local_path):
                logger.warning(f"OSS上传跳过 | 本地文件不存在：{local_path}")
                return None

            if not os.path.isfile(local_path):
                logger.error(f"OSS上传拒绝 | 路径不是有效文件：{local_path}")
                return None

            if os.path.islink(local_path):
                real_path = os.path.realpath(local_path)
                logger.warning(
                    f"检测到软链接 | 原路径：{local_path} -> 真实路径：{real_path}"
                )
                local_path = real_path

            if not os.access(local_path, os.R_OK):
                logger.error(
                    f"OSS上传拒绝 | 无读权限：{local_path}（当前用户：{os.getlogin() or '未知'}）"
                )
                return None

            # 2. 等待文件就绪（原有逻辑不变）
            max_retry = 5
            retry_interval = 10
            local_file_size = 0
            time.sleep(5)

            for retry in range(max_retry):
                local_file_size = os.path.getsize(local_path)
                logger.info(f"文件大小：{local_file_size}")
                if local_file_size > 0:
                    break
                if retry == max_retry - 1:
                    logger.error(
                        f"文件始终为空 | 路径：{local_path}（已重试{max_retry}次）"
                    )
                    return None
                logger.warning(
                    f"文件未就绪（大小为0） | 路径：{local_path} | "
                    f"重试次数：{retry+1}/{max_retry} | {retry_interval}秒后重试"
                )
                time.sleep(retry_interval)

            # 3. 构建OSS路径信息（原有逻辑不变）
            local_filename = os.path.basename(local_path)
            base_root = self.video_folder if is_video else self.image_folder
            object_path = os.path.join(base_root, oss_folder, local_filename).replace(
                os.sep, "/"
            )
            file_type = "视频" if is_video else "图片"
            file_size_mb = local_file_size / 1024 / 1024

            # 4. 上传进度回调函数（原有逻辑不变）
            def progress_callback(
                consumed_bytes: int, total_bytes: Optional[int] = None
            ) -> None:
                actual_total = (
                    total_bytes
                    if (total_bytes is not None and total_bytes > 0)
                    else local_file_size
                )
                progress_pct = (
                    math.floor((consumed_bytes / actual_total) * 1000) / 10
                    if actual_total > 0
                    else 100.0
                )

                consumed_mb = consumed_bytes / 1024 / 1024
                total_mb = actual_total / 1024 / 1024

                logger.info(
                    f"OSS{file_type}上传进度 | "
                    f"文件名：{local_filename} | "
                    f"已上传：{consumed_mb:.2f}MB / 总计：{total_mb:.2f}MB | "
                    f"进度：{progress_pct}%"
                )

            # 5. 执行上传（原有逻辑不变）
            logger.info(
                f"开始OSS{file_type}上传 | "
                f"本地路径：{local_path} | "
                f"OSS路径：{object_path} | "
                f"文件大小：{file_size_mb:.2f}MB"
            )
            self.bucket.put_object_from_file(
                key=object_path,
                filename=local_path,
                progress_callback=progress_callback,
            )

            # 6. 生成临时访问链接（核心修复：使用官方标准参数名+顺序）
            # 官方标准调用方式：sign_url(method, key, expires, headers=None, params=None)
            try:
                # 关键：参数名是 expires（不是expire/expires_in），且按位置/关键字传参都可
                oss_temp_url = self.bucket.sign_url(
                    method="GET",  # 必选：HTTP方法（GET=下载/访问）
                    key=object_path,  # 必选：OSS对象路径
                    expires=expire_seconds,  # 必选：过期时间（秒）【官方标准参数名】
                    headers=None,  # 可选：需要签名的请求头
                    params=None,  # 可选：需要签名的URL参数
                )
            except Exception as sign_e:
                logger.error(
                    f"生成OSS临时链接失败 | OSS路径：{object_path} | "
                    f"SDK版本：{oss2.__version__} | 错误：{str(sign_e)}",
                    exc_info=True,
                )
                raise  # 抛出异常便于定位根因

            # 日志优化
            expire_hours = expire_seconds / 3600
            logger.info(
                f"OSS{file_type}上传成功 | "
                f"临时访问链接（有效期：{expire_seconds}秒/{expire_hours:.1f}小时）：{oss_temp_url}"
            )
            return oss_temp_url

        except Exception as e:
            logger.error(
                f"OSS{('视频' if is_video else '图片')}上传失败 | "
                f"本地路径：{local_path} | 错误：{str(e)}",
                exc_info=True,
            )
            return None
