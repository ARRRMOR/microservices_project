from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models

# URL базы данных PostgreSQL, который мы передаем через переменные окружения
DATABASE_URL = "postgresql://auth_user:auth_password@auth_db/auth_db"

# Создание движка для подключения
engine = create_engine(DATABASE_URL)

# Создание сессий для взаимодействия с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для создания таблиц в базе данных
def init_db():
    models.Base.metadata.create_all(bind=engine)
