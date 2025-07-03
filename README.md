## Запуск проекта

1. Убедитесь, что у вас установлен Docker и Docker Compose.
2. Соберите и запустите контейнеры:
   ```sh
   docker-compose -f docker-compose.dev.yml up --build
   ```
3. Открывайте API-документацию в браузере:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Остановка контейнеров

```sh
docker-compose -f docker-compose.dev.yml down
```

## Туда-сюда кто не хочет лезть и искать что-то
```sh
make help
```