import re
from urllib.parse import urlparse

def validate_subdomain(subdomain):
    """
    Validate a subdomain name
    
    Args:
        subdomain: The subdomain to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check length
    if len(subdomain) < 1 or len(subdomain) > 63:
        return False, "Subdomain must be between 1 and 63 characters"
    
    # Check format (alphanumeric and hyphens, but not starting/ending with hyphen)
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$', subdomain):
        return False, "Subdomain can only contain letters, numbers, and hyphens, and cannot start or end with a hyphen"
    
    # Reserved names that shouldn't be used as subdomains
    reserved_names = ["www", "mail", "ftp", "admin", "webmail", "dashboard", "api"]
    if subdomain.lower() in reserved_names:
        return False, f"'{subdomain}' is a reserved name and cannot be used"
    
    return True, ""

def validate_url(url):
    """
    Validate a URL
    
    Args:
        url: The URL to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            if result.scheme not in ['http', 'https']:
                return False, "URL must use http or https protocol"
            return True, ""
        return False, "Invalid URL format"
    except:
        return False, "Invalid URL"

def validate_github_username(username):
    """
    Validate a GitHub username
    
    Args:
        username: The GitHub username to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # GitHub username rules: letters, numbers, hyphens, but not starting with a hyphen
    if not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*$', username):
        return False, "Invalid GitHub username format"
    
    # Check length (GitHub usernames are between 1 and 39 characters)
    if len(username) < 1 or len(username) > 39:
        return False, "GitHub username must be between 1 and 39 characters"
    
    return True, ""

def validate_repository_name(repo_name):
    """
    Validate a GitHub repository name
    
    Args:
        repo_name: The repository name to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # GitHub repo name rules: letters, numbers, hyphens, underscores, periods (no spaces)
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo_name):
        return False, "Invalid repository name format"
    
    # Check length
    if len(repo_name) < 1 or len(repo_name) > 100:
        return False, "Repository name must be between 1 and 100 characters"
    
    return True, ""