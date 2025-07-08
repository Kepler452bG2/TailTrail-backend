import io
import logging
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError
import boto3
from botocore.client import Config

from .base_upload_service import BaseUploadService, UploadResult

logger = logging.getLogger(__name__)


class S3UploadService(BaseUploadService):
    """Сервис загрузки файлов в AWS S3"""
    
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        bucket_name: str,
        region_name: str = "us-east-1",
        base_url: Optional[str] = None
    ):
        """
        Инициализация S3 сервиса
        
        Args:
            aws_access_key_id: AWS Access Key ID
            aws_secret_access_key: AWS Secret Access Key
            bucket_name: Имя S3 bucket
            region_name: Регион AWS
            base_url: Базовый URL для файлов (если используется CloudFront)
        """
        self.bucket_name = bucket_name
        self.base_url = base_url or f"https://{bucket_name}.s3.{region_name}.amazonaws.com"
        
        # Создаем S3 клиент
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3}
                )
            )
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
        folder: str = "uploads"
    ) -> UploadResult:
        """
        Загрузить файл в S3
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Имя файла
            content_type: MIME тип файла
            folder: Папка для загрузки
            
        Returns:
            UploadResult: Результат загрузки
        """
        try:
            # Валидация файла
            validation_error = self.validate_file(filename, content_type, len(file_content))
            if validation_error:
                return UploadResult(success=False, error=validation_error)
            
            # Генерируем уникальное имя файла
            unique_filename = self.generate_unique_filename(filename)
            
            # Формируем ключ для S3
            s3_key = f"{folder}/{unique_filename}"
            
            # Загружаем файл в S3
            file_obj = io.BytesIO(file_content)
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read',  # Делаем файл публично доступным
                    'CacheControl': 'max-age=31536000',  # Кешируем на год
                }
            )
            
            # Формируем URL файла
            file_url = self.get_file_url(s3_key)
            
            logger.info(f"File uploaded successfully: {file_url}")
            return UploadResult(success=True, file_url=file_url)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS S3 error ({error_code}): {error_message}")
            return UploadResult(success=False, error=f"Ошибка загрузки файла: {error_message}")
            
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return UploadResult(success=False, error=f"Неожиданная ошибка: {str(e)}")
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Удалить файл из S3
        
        Args:
            file_url: URL файла для удаления
            
        Returns:
            bool: True если файл успешно удален
        """
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
                return True  # Файл уже не существует
            else:
                logger.error(f"AWS S3 error deleting file: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}")
            return False
    
    async def get_file_url(self, file_path: str) -> str:
        """
        Получить URL файла
        
        Args:
            file_path: Путь к файлу в S3
            
        Returns:
            str: URL файла
        """
        return f"{self.base_url}/{file_path}"
    
    def _extract_s3_key_from_url(self, file_url: str) -> Optional[str]:
        """
        Извлечь ключ S3 из URL
        
        Args:
            file_url: URL файла
            
        Returns:
            Optional[str]: Ключ S3 или None если не удалось извлечь
        """
        try:
            # Убираем базовый URL
            if file_url.startswith(self.base_url):
                return file_url[len(self.base_url):].lstrip('/')
            
            # Альтернативные форматы URL
            if f"{self.bucket_name}.s3." in file_url:
                # Формат: https://bucket.s3.region.amazonaws.com/key
                parts = file_url.split('/')
                if len(parts) > 3:
                    return '/'.join(parts[3:])
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting S3 key from URL: {e}")
            return None
    
    def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Создать подписанный URL для приватного доступа к файлу
        
        Args:
            file_path: Путь к файлу в S3
            expiration: Время жизни URL в секундах
            
        Returns:
            str: Подписанный URL
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def create_bucket_if_not_exists(self) -> bool:
        """
        Создать bucket если он не существует
        
        Returns:
            bool: True если bucket создан или уже существует
        """
        try:
            # Проверяем существование bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket не существует, создаем его
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket {self.bucket_name} created successfully")
                    return True
                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False 
            
