"""Aggregate import of all ORM models.

Importing this module ensures every model is registered on ``Base.metadata``.
Used by Alembic (autogenerate / target metadata) and by tests (create_all).
"""

from app.modules.access.models import ModuleAccessLog  # noqa: F401
from app.modules.applications.models import (  # noqa: F401
    ApplicationList,
    ApplicationRecord,
    CalendarEvent,
)
from app.modules.auth.models import PasswordResetToken  # noqa: F401
from app.modules.catalog.models import Category  # noqa: F401
from app.modules.files.models import StoredFile  # noqa: F401
from app.modules.interactions.models import (  # noqa: F401
    Annotation,
    Comment,
    ContentView,
    Reaction,
)
from app.modules.interview.models import (  # noqa: F401
    Company,
    InterviewPost,
    InterviewQA,
)
from app.modules.knowledge.models import KnowledgeItem  # noqa: F401
from app.modules.knowledge_tree.models import KnowledgeNode  # noqa: F401
from app.modules.messages.models import ContactMessage  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.payment.models import Entitlement, Order  # noqa: F401
from app.modules.points.models import PointLedger  # noqa: F401
from app.modules.projects.models import Project, ProjectQA  # noqa: F401
from app.modules.settings.models import SiteSetting  # noqa: F401
from app.modules.sql_bank.models import SqlProgress, SqlQuestion  # noqa: F401
from app.modules.submissions.models import Submission  # noqa: F401
from app.modules.users.models import User  # noqa: F401
