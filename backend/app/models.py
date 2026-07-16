"""Aggregate import of all ORM models.

Importing this module ensures every model is registered on ``Base.metadata``.
Used by Alembic (autogenerate / target metadata) and by tests (create_all).
"""

from app.modules.catalog.models import Category  # noqa: F401
from app.modules.interview.models import Company, InterviewPost  # noqa: F401
from app.modules.knowledge.models import KnowledgeItem  # noqa: F401
from app.modules.payment.models import Entitlement, Order  # noqa: F401
from app.modules.points.models import PointLedger  # noqa: F401
from app.modules.projects.models import Project, ProjectQA  # noqa: F401
from app.modules.sql_bank.models import SqlQuestion  # noqa: F401
from app.modules.submissions.models import Submission  # noqa: F401
from app.modules.users.models import User  # noqa: F401
