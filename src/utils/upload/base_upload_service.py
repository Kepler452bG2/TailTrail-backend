from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from datetime import datetime


class UploadResult:
    def __init__(self, success: bool, file_url: str = None, error: str = None):
        self.success = success
        self.file_url = file_url
        self.error = error


class BaseUploadService(ABC):
    
    @abstractmethod
    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str,
        folder: str = "uploads"
    ) -> UploadResult:
        """
        Загрузить файл
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Имя файла
            content_type: MIME тип файла
            folder: Папка для загрузки
            
        Returns:
            UploadResult: Результат загрузки
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_url: str) -> bool:
        """
        Удалить файл
        
        Args:
            file_url: URL файла для удаления
            
        Returns:
            bool: True если файл успешно удален
        """
        pass
    
    @abstractmethod
    async def get_file_url(self, file_path: str) -> str:
        """
        Получить URL файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            str: URL файла
        """
        pass
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Сгенерировать уникальное имя файла
        
        Args:
            original_filename: Оригинальное имя файла
            
        Returns:
            str: Уникальное имя файла
        """
        # Получаем расширение файла
        extension = original_filename.split('.')[-1] if '.' in original_filename else ''
        
        # Создаем уникальное имя с временной меткой и UUID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        if extension:
            return f"{timestamp}_{unique_id}.{extension}"
        else:
            return f"{timestamp}_{unique_id}"
    
    def validate_file(self, filename: str, content_type: str, file_size: int) -> Optional[str]:
        """
        Валидировать файл
        
        Args:
            filename: Имя файла
            content_type: MIME тип
            file_size: Размер файла в байтах
            
        Returns:
            Optional[str]: Сообщение об ошибке или None если валидация прошла
        """
        # Проверка размера файла (максимум 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return f"Файл слишком большой. Максимальный размер: {max_size // (1024*1024)}MB"
        
        # Разрешенные типы файлов для изображений
        allowed_image_types = [
            'image/jpeg',
            'image/jpg', 
            'image/png',
            'image/gif',
            'image/webp'
        ]
        
        if content_type not in allowed_image_types:
            return f"Неподдерживаемый тип файла: {content_type}"
        
        # Проверка расширения файла
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_extension not in allowed_extensions:
            return f"Неподдерживаемое расширение файла: {file_extension}"
        
        return None

    