import io
import logging
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError
import boto3
from botocore.client import Config

from .base_upload_service import BaseUploadService, UploadResult
from src.config import settings

logger = logging.getLogger(__name__)


class UploadService(BaseUploadService):
    """Сервис загрузки файлов в AWS S3"""
    
    def __init__(self):
        """Инициализация сервиса загрузки"""
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS credentials not configured")
        
        self.bucket_name = getattr(settings, 'AWS_S3_BUCKET_NAME', 'tail-trail-bucket')
        self.region_name = getattr(settings, 'AWS_REGION', 'us-east-1')
        
        # Используем CloudFront URL если настроен, иначе S3 URL
        cloudfront_url = getattr(settings, 'AWS_CLOUDFRONT_URL', None)
        if cloudfront_url:
            self.base_url = cloudfront_url.rstrip('/')
            logger.info(f"Using CloudFront URL: {self.base_url}")
        else:
            self.base_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com"
            logger.info(f"Using S3 URL: {self.base_url}")
        
        # Создаем S3 клиент
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region_name,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3}
                )
            )
            
            # Создаем bucket если не существует
            self._create_bucket_if_not_exists()
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise ValueError("AWS credentials not found")
        except Exception as e:
            logger.error(f"Error creating S3 client: {e}")
            raise
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        folder: str = "posts"
    ) -> UploadResult:
        """Загрузить файл в S3"""
        try:
            # Валидация файла
            validation_error = self.validate_file(filename, content_type, len(file_content))
            if validation_error:
                return UploadResult(success=False, error=validation_error)
            
            # Генерируем уникальное имя файла
            unique_filename = self.generate_unique_filename(filename)
            
            # Формируем ключ для S3
            s3_key = f"{folder}/{unique_filename}"
            
            logger.info(f"Uploading file: {filename} -> {s3_key} (size: {len(file_content)} bytes)")
            
            # Загружаем файл в S3
            file_obj = io.BytesIO(file_content)
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'CacheControl': 'max-age=31536000',
                }
            )
            
            # Формируем URL файла
            file_url = await self.get_file_url(s3_key)
            
            # Проверяем что файл действительно загрузился
            try:
                response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                actual_size = response.get('ContentLength', 0)
                logger.info(f"File uploaded successfully: {file_url} (size: {actual_size} bytes)")
                
                if actual_size == 0:
                    logger.error(f"File uploaded but size is 0: {s3_key}")
                    return UploadResult(success=False, error="Файл загружен с нулевым размером")
                    
            except ClientError as e:
                logger.error(f"Could not verify uploaded file: {e}")
                return UploadResult(success=False, error=f"Не удалось проверить загруженный файл: {e}")
            
            return UploadResult(success=True, file_url=file_url)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS S3 error ({error_code}): {error_message}")
            
            # Специальная обработка ошибок времени
            if "time" in error_message.lower() or "request time" in error_message.lower():
                return UploadResult(
                    success=False, 
                    error="Ошибка синхронизации времени. Проверьте настройки времени системы."
                )
            
            return UploadResult(success=False, error=f"Ошибка загрузки файла: {error_message}")
            
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            
            # Проверяем ошибки времени в общих исключениях
            if "time" in str(e).lower() or "request time" in str(e).lower():
                return UploadResult(
                    success=False,
                    error="Ошибка синхронизации времени. Проверьте настройки времени системы."
                )
            
            return UploadResult(success=False, error=f"Неожиданная ошибка: {str(e)}")
    
    async def delete_file(self, file_url: str) -> bool:
        """Удалить файл из S3"""
        try:
            # Извлекаем ключ S3 из URL
            s3_key = self._extract_s3_key_from_url(file_url)
            if not s3_key:
                logger.error(f"Could not extract S3 key from URL: {file_url}")
                return False
            
            # Удаляем файл из S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"File deleted successfully: {s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3: {s3_key}")
                return True
            else:
                logger.error(f"AWS S3 error deleting file: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}")
            return False
    
    async def get_file_url(self, file_path: str) -> str:
        """Получить URL файла"""
        return f"{self.base_url}/{file_path}"
    
    async def check_file_accessibility(self, file_url: str) -> bool:
        """Проверить доступность файла по URL"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.head(file_url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error checking file accessibility {file_url}: {e}")
            return False
    
    def _extract_s3_key_from_url(self, file_url: str) -> Optional[str]:
        """Извлечь ключ S3 из URL"""
        try:
            if file_url.startswith(self.base_url):
                return file_url[len(self.base_url):].lstrip('/')
            
            # Альтернативные форматы URL
            if f"{self.bucket_name}.s3." in file_url:
                parts = file_url.split('/')
                if len(parts) > 3:
                    return '/'.join(parts[3:])
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting S3 key from URL: {e}")
            return None
    
    def _create_bucket_if_not_exists(self) -> bool:
        """Создать bucket если он не существует"""
        try:
            # Проверяем существование bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    # Создаем bucket
                    if self.region_name == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    
                    # Настраиваем bucket policy для публичного чтения
                    self._set_bucket_public_read_policy()
                    
                    logger.info(f"Bucket {self.bucket_name} created successfully with public read access")
                    return True
                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False
    
    def _set_bucket_public_read_policy(self):
        """Установить bucket policy для публичного чтения"""
        try:
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": [
                            "s3:GetObject",
                            "s3:GetObjectVersion"
                        ],
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                    }
                ]
            }
            
            import json
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            # Отключаем блокировку публичного доступа для работы без ACL
            try:
                self.s3_client.put_public_access_block(
                    Bucket=self.bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,      # Блокируем ACL
                        'IgnorePublicAcls': True,     # Игнорируем ACL
                        'BlockPublicPolicy': False,   # Разрешаем публичную политику
                        'RestrictPublicBuckets': False # Разрешаем публичный доступ
                    }
                )
                logger.info(f"Public access block configured for bucket {self.bucket_name}")
            except ClientError as e:
                logger.warning(f"Could not configure public access block: {e}")
            
            logger.info(f"Public read policy set for bucket {self.bucket_name}")
            
        except ClientError as e:
            logger.warning(f"Could not set bucket policy: {e}. Files may not be publicly accessible.")


# Глобальный экземпляр сервиса
_upload_service = None

def get_upload_service() -> UploadService:
    """Получить экземпляр сервиса загрузки"""
    global _upload_service
    if _upload_service is None:
        _upload_service = UploadService()
    return _upload_service 