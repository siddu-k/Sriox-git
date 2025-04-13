import CloudFlare
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Cloudflare credentials from environment variables
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
EMAIL = os.getenv("CLOUDFLARE_EMAIL")
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "sriox.com")

# Initialize Cloudflare client
cf = CloudFlare.CloudFlare(token=API_TOKEN, email=EMAIL)

def create_subdomain(subdomain, record_type="A", content="", proxied=True):
    """
    Create a subdomain DNS record in Cloudflare
    
    Args:
        subdomain: The subdomain to create (without the main domain)
        record_type: DNS record type (A, CNAME, etc.)
        content: The target IP or domain
        proxied: Whether to proxy through Cloudflare
        
    Returns:
        dict: The created record data or error info
    """
    try:
        record = {
            'name': subdomain,
            'type': record_type,
            'content': content,
            'proxied': proxied
        }
        
        response = cf.zones.dns_records.post(ZONE_ID, data=record)
        logging.info(f"Created {record_type} record for {subdomain}.{DOMAIN_NAME}")
        return {"success": True, "record": response}
    except Exception as e:
        logging.error(f"Failed to create DNS record: {str(e)}")
        return {"success": False, "error": str(e)}

def create_github_pages_mapping(subdomain, github_username):
    """
    Create a CNAME record pointing to GitHub Pages
    
    Args:
        subdomain: The subdomain to create
        github_username: GitHub username for the Pages site
        
    Returns:
        dict: The created record data or error info
    """
    return create_subdomain(
        subdomain=subdomain,
        record_type="CNAME",
        content=f"{github_username}.github.io",
        proxied=True
    )

def delete_subdomain(subdomain):
    """
    Delete a subdomain DNS record from Cloudflare
    
    Args:
        subdomain: The subdomain to delete (without the main domain)
        
    Returns:
        dict: Success status and info
    """
    try:
        # List records to find the ID for the subdomain
        dns_records = cf.zones.dns_records.get(ZONE_ID, params={'name': f"{subdomain}.{DOMAIN_NAME}"})
        
        if not dns_records:
            return {"success": False, "error": "DNS record not found"}
        
        # Delete the record
        for record in dns_records:
            cf.zones.dns_records.delete(ZONE_ID, record['id'])
            
        logging.info(f"Deleted DNS record for {subdomain}.{DOMAIN_NAME}")
        return {"success": True}
    except Exception as e:
        logging.error(f"Failed to delete DNS record: {str(e)}")
        return {"success": False, "error": str(e)}