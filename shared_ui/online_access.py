"""Application-level online project access gate."""
from shared_ui.online_projects import online_project_list


def authorized_online_projects(customer_id, *, customer_entry, project_service):
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise PermissionError('customer required')
    customer_entry(customer_id.strip())
    return online_project_list(project_service, customer_id)
