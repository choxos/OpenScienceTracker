from django import template

register = template.Library()

@register.filter
def safe_display(value):
    """Convert 'nan', None, or empty values to 'N/A' for better display"""
    if value is None:
        return 'N/A'
    
    str_value = str(value).strip()
    if str_value.lower() in ['nan', 'none', '']:
        return 'N/A'
    
    return value

@register.filter
def truncate_authors(value, length=80):
    """Truncate author string and handle 'nan' values"""
    safe_value = safe_display(value)
    if safe_value == 'N/A':
        return safe_value
    
    if len(safe_value) > length:
        return safe_value[:length] + '...'
    return safe_value 