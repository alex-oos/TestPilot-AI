# from app.models.entities import RoleConfig
#
# __all__ = ["RoleConfig"]

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class RoleConfig(Base):
    __tablename__ = "role_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    role_type: Mapped[str] = mapped_column(String, index=True)
    mapped_model_name: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    creator: Mapped[str] = mapped_column(String, default="admin")
    modifier: Mapped[str] = mapped_column(String, default="admin")
