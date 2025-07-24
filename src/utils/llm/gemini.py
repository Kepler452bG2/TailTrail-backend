import logging
from typing import Optional, Dict, Any, List
import asyncio
from functools import wraps
import aiohttp
import io
from PIL import Image
from fastapi import UploadFile, HTTPException, status

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.config import settings

logger = logging.getLogger(__name__)


class GeminiImageAnalyzer:
    """Сервис для анализа изображений через Gemini API на предмет сенситивного контента"""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY не установлен, Gemini анализатор не может быть инициализирован")
            raise ValueError("GEMINI_API_KEY не установлен в настройках")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Настройки безопасности для более точного анализа
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            logger.info("GeminiImageAnalyzer успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Gemini API: {e}")
            raise ValueError(f"Не удалось инициализировать Gemini API: {e}")
    
    async def _download_image(self, url: str) -> bytes:
        """Загружает изображение по URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Не удалось загрузить изображение: HTTP {response.status}")
                    
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        raise Exception(f"URL не содержит изображение: {content_type}")
                    
                    return await response.read()
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {str(e)}")
            raise Exception(f"Не удалось загрузить изображение: {str(e)}")
    
    def _validate_image_file(self, file: UploadFile) -> None:
        """Валидация загруженного файла"""
        if not file.content_type or not file.content_type.startswith('image/'):
            raise ValueError(f"Файл должен быть изображением. Получен: {file.content_type}")
        
        # Проверяем поддерживаемые форматы
        supported_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in supported_formats:
            raise ValueError(f"Неподдерживаемый формат изображения: {file.content_type}")
    
    def _sync_to_async(self, func):
        """Декоратор для конвертации синхронных функций в асинхронные"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
        return wrapper
    
    async def _analyze_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """Внутренний метод для анализа изображения из байтов"""
        try:
            # Создаем объект изображения для Gemini
            image = Image.open(io.BytesIO(image_bytes))
            
            # Создаем промпт для анализа изображения
            prompt = """
            Ты модератор контента для платформы поиска потерянных домашних животных.
            
            Проанализируй это изображение и определи, подходит ли оно для семейной платформы поиска животных.
            
            ОБЫЧНЫЕ ФОТО ЖИВОТНЫХ ВСЕГДА БЕЗОПАСНЫ:
            - Любые фотографии собак, кошек, птиц, кроликов и других домашних питомцев
            - Владельцы с питомцами (дети, взрослые держат животных)
            - Животные дома, на улице, в парке
            - Обычные бытовые сцены с животными
            
            БЛОКИРУЙ ТОЛЬКО ЯВНО НЕПОДХОДЯЩИЙ КОНТЕНТ:
            - Откровенная порнография
            - Жестокость к животным
            - Наркотики
            - Оружие (настоящее)
            - Экстремальное насилие
            
            ВАЖНО: Если видишь обычное фото животного или человека с животным - это ВСЕГДА безопасно!
            
            Ответь ТОЛЬКО одним словом:
            - SAFE - если это нормальное фото животного/человека с животным
            - SENSITIVE - только если есть явно неподходящий контент
            
            Не объясняй, просто ответь одним словом.
            """
            
            # Выполняем синхронный запрос в отдельном потоке
            @self._sync_to_async
            def _generate_content():
                return self.model.generate_content(
                    [prompt, image],
                    safety_settings=self.safety_settings
                )
            
            response = await _generate_content()
            
            # Обрабатываем ответ
            if response.candidates and response.candidates[0].content:
                content_text = response.candidates[0].content.parts[0].text.strip().upper()
                
                # Простая и четкая обработка ответа
                if "SENSITIVE" in content_text:
                    return {
                        "status": "SENSITIVE",
                        "confidence": 0.8,
                        "details": "Обнаружен неподходящий контент",
                        "categories": ["general"],
                        "raw_response": content_text
                    }
                else:
                    # По умолчанию считаем безопасным (включая "SAFE" и любые другие ответы)
                    return {
                        "status": "SAFE",
                        "confidence": 0.9,
                        "details": "Изображение подходит для платформы поиска животных",
                        "categories": [],
                        "raw_response": content_text
                    }
            
            # Проверяем safety ratings только для критических случаев
            if response.candidates and response.candidates[0].safety_ratings:
                for rating in response.candidates[0].safety_ratings:
                    # Блокируем только HIGH уровень опасности
                    if rating.probability.name == "HIGH":
                        return {
                            "status": "SENSITIVE",
                            "confidence": 0.7,
                            "details": f"Обнаружен критический контент: {rating.category.name}",
                            "categories": [rating.category.name],
                            "raw_response": str(response.candidates[0].safety_ratings)
                        }
            
            # По умолчанию безопасно
            return {
                "status": "SAFE",
                "confidence": 0.9,
                "details": "Изображение прошло проверку и подходит для платформы",
                "categories": [],
                "raw_response": "Default safe response"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {str(e)}")
            # В случае ошибки анализа, разрешаем загрузку (fail-safe)
            
            # Специальная обработка для ошибок времени Google API
            if "time" in str(e).lower() or "request time" in str(e).lower():
                logger.warning(f"Проблема с временными метками Google API: {str(e)}")
                return {
                    "status": "SAFE",
                    "confidence": 0.5,
                    "details": "Пропущен анализ из-за проблем с временными метками API",
                    "categories": [],
                    "raw_response": f"Time sync error: {str(e)}"
                }
            
            return {
                "status": "SAFE",
                "confidence": 0.5,
                "details": "Не удалось проанализировать изображение, разрешено по умолчанию",
                "categories": [],
                "raw_response": f"Analysis error: {str(e)}"
            }
    
    async def analyze_image_content(self, image_url: str) -> Dict[str, Any]:
        """
        Анализирует изображение по URL на предмет сенситивного контента
        
        Args:
            image_url: URL изображения для анализа
            
        Returns:
            Dict с результатами анализа:
            {
                "status": "SAFE" | "SENSITIVE",
                "confidence": float,
                "details": str,
                "categories": List[str]
            }
        """
        try:
            # Загружаем изображение
            image_bytes = await self._download_image(image_url)
            return await self._analyze_image_bytes(image_bytes)
            
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения по URL: {str(e)}")
            raise Exception(f"Не удалось проанализировать изображение: {str(e)}")
    
    async def analyze_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Анализирует загруженный файл на предмет сенситивного контента
        
        Args:
            file: UploadFile объект из FastAPI
            
        Returns:
            Dict с результатами анализа:
            {
                "status": "SAFE" | "SENSITIVE",
                "confidence": float,
                "details": str,
                "categories": List[str],
                "filename": str
            }
        """
        try:
            # Валидируем файл
            self._validate_image_file(file)
            
            # Читаем содержимое файла
            file_content = await file.read()
            
            # Анализируем изображение
            result = await self._analyze_image_bytes(file_content)
            
            # Добавляем информацию о файле
            result["filename"] = file.filename
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе загруженного файла: {str(e)}")
            raise Exception(f"Не удалось проанализировать файл: {str(e)}")
    
    async def analyze_uploaded_files(self, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """
        Анализирует список загруженных файлов на предмет сенситивного контента
        
        Args:
            files: Список UploadFile объектов из FastAPI
            
        Returns:
            List[Dict] с результатами анализа для каждого файла
        """
        results = []
        
        for file in files:
            if file is None or not file.filename:
                continue
                
            try:
                result = await self.analyze_uploaded_file(file)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Ошибка при анализе файла {file.filename}: {str(e)}")
                results.append({
                    "status": "ERROR",
                    "confidence": 0.0,
                    "details": f"Ошибка при анализе: {str(e)}",
                    "categories": [],
                    "filename": file.filename
                })
        
        return results
    
    async def get_content_status_code(self, image_url: str) -> str:
        """
        Упрощенный метод, возвращающий только код статуса для URL
        
        Args:
            image_url: URL изображения
            
        Returns:
            "SAFE" - если контент безопасен
            "SENSITIVE" - если обнаружен сенситивный контент
        """
        try:
            result = await self.analyze_image_content(image_url)
            return result["status"]
        except Exception as e:
            logger.error(f"Ошибка при получении статуса контента: {str(e)}")
            raise
    
    async def get_file_status_code(self, file: UploadFile) -> str:
        """
        Упрощенный метод, возвращающий только код статуса для загруженного файла
        
        Args:
            file: UploadFile объект
            
        Returns:
            "SAFE" - если контент безопасен
            "SENSITIVE" - если обнаружен сенситивный контент
        """
        try:
            result = await self.analyze_uploaded_file(file)
            return result["status"]
        except Exception as e:
            logger.error(f"Ошибка при получении статуса файла: {str(e)}")
            raise


    async def validate_files_for_upload(self, files: List[UploadFile]) -> None:
        """
        Валидирует файлы для загрузки. Вызывает HTTPException если найден неподходящий контент.
        
        Args:
            files: Список файлов для проверки
            
        Raises:
            HTTPException: Если обнаружен неподходящий контент
        """
        if not files or len(files) == 0:
            return
            
        # Фильтруем пустые файлы
        valid_files = [f for f in files if f and f.filename]
        if not valid_files:
            return
            
        try:
            logger.info(f"Анализ {len(valid_files)} файлов с помощью Gemini")
            
            # Анализируем все файлы
            results = await self.analyze_uploaded_files(valid_files)
            
            # Проверяем результаты
            sensitive_files = []
            for result in results:
                if result.get("status") == "SENSITIVE":
                    sensitive_files.append(result.get("filename", "неизвестный файл"))
            
            if sensitive_files:
                logger.warning(f"Обнаружен неподходящий контент в файлах: {sensitive_files}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Обнаружен неподходящий контент",
                        "message": f"Файлы содержат неподходящий контент: {', '.join(sensitive_files)}",
                        "sensitive_files": sensitive_files
                    }
                )
            
            logger.info("Все файлы прошли проверку на содержание")
            
        except HTTPException:
            # Передаем HTTPException дальше
            raise
        except Exception as e:
            logger.error(f"Ошибка при анализе файлов: {e}")
            # Не блокируем загрузку при ошибке анализа (fail-safe)
            logger.warning("Продолжаем загрузку несмотря на ошибку анализа")


# Создаем экземпляр анализатора
image_analyzer = None

def initialize_gemini_analyzer():
    """Инициализирует Gemini анализатор только если API ключ доступен"""
    global image_analyzer
    try:
        if settings.GEMINI_API_KEY:
            image_analyzer = GeminiImageAnalyzer()
            logger.info("GeminiImageAnalyzer успешно инициализирован")
        else:
            logger.warning("GEMINI_API_KEY не установлен, Gemini анализатор отключен")
    except Exception as e:
        logger.warning(f"Не удалось инициализировать GeminiImageAnalyzer: {e}")
        image_analyzer = None

# Инициализируем при импорте модуля
initialize_gemini_analyzer()


async def validate_uploaded_files(files: List[UploadFile]) -> None:
    """
    Удобная функция для валидации файлов в контроллерах.
    
    Args:
        files: Список файлов для проверки
        
    Raises:
        HTTPException: Если обнаружен неподходящий контент
    """
    if image_analyzer is None:
        logger.warning("Gemini анализатор не инициализирован, пропускаем проверку файлов")
        return
        
    if not files or len(files) == 0:
        return
        
    try:
        await image_analyzer.validate_files_for_upload(files)
    except HTTPException:
        # Передаем HTTPException дальше
        raise
    except Exception as e:
        logger.error(f"Ошибка при анализе файлов: {e}")
        # Не блокируем загрузку при ошибке анализа (fail-safe)
        logger.warning("Продолжаем загрузку несмотря на ошибку анализа")
