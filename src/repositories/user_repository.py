from src.dao.sqlalchemy_dao import SQLAlchemyDAO
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
    dao_class = SQLAlchemyDAO