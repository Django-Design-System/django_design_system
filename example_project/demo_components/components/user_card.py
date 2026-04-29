from dj_design_system.components import TagComponent
from dj_design_system.parameters import UserParam


class UserCardComponent(TagComponent):
    """Renders a card displaying a user's name, email, and active status.

    Demonstrates ``UserParam`` — the ``user`` object is automatically
    unpacked into ``user_first_name``, ``user_last_name``, ``user_email``
    and ``user_is_active`` template variables, and the ``user-active``
    CSS class is applied when the user is active.

    Example usage::

        {% user_card user %}
    """

    template_format_str = (
        "<div class='user-card {classes}'>"
        "<h3>{user_first_name} {user_last_name}</h3>"
        "<p class='user-card__email'>{user_email}</p>"
        "</div>"
    )
    user = UserParam("The user to display.", required=False)

    class Meta:
        positional_args = ["user"]

    def get_context(self):
        context = super().get_context()
        context.setdefault("user_first_name", "Jane")
        context.setdefault("user_last_name", "Smith")
        context.setdefault("user_email", "jane.smith@example.com")
        return context
