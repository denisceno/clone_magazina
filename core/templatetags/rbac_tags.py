from django import template

register = template.Library()

@register.filter
def has_group(user, group_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    # Cache groups on the user object to avoid repeated DB queries
    if not hasattr(user, '_cached_group_names'):
        user._cached_group_names = set(user.groups.values_list('name', flat=True))
    return group_name in user._cached_group_names
