"""Project projection for a customer-scoped application service."""

def online_project_list(project_service, customer_id):
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise PermissionError('customer required')
    records = project_service.projects_for_customer(customer_id.strip())
    return [
        {**{'id': str(item.project_id), 'name': str(item.name)},
         **({'number': item.display_number} if getattr(item, 'display_number', None) else {})}
        for item in records
    ]
