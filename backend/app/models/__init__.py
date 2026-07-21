"""Import every model module so Base.metadata is fully populated for Alembic autogenerate."""

from app.models.analysis import AnalysisResult  # noqa: F401
from app.models.context import ContextMatch, ContextRecord  # noqa: F401
from app.models.embedding import Embedding  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.theme import Theme, ThemeMember  # noqa: F401
