import logging
import time
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from email.mime.text import MIMEText

gmail_logger = logging.getLogger("Gmail")
gmail_logger.setLevel(logging.INFO)


def build_query(from_email: str, subject: str, n_days: int) -> str:
    """
    Build Gmail search query based on filters.
    
    Args:
        from_email: Email address to filter by sender
        subject: Subject line to filter
        n_days: Number of days to look back
    
    Returns:
        Gmail query string
    """
    query_parts = []
    
    if from_email:
        query_parts.append(f"from:{from_email}")
    
    if subject:
        query_parts.append(f"subject:{subject}")
    
    # Calculate date for n_days ago
    if n_days:
        date_after = datetime.now() - timedelta(days=n_days)
        date_str = date_after.strftime("%Y/%m/%d")
        query_parts.append(f"after:{date_str}")
    
    # Only unread messages
    query_parts.append("is:unread")
    
    query = " ".join(query_parts)
    gmail_logger.info(f"Built query: {query}")
    return query


def extract_email_body(payload: Dict) -> str:
    """
    Extract email body from message payload.
    Handles both plain text and HTML emails.
    
    Args:
        payload: Gmail message payload
    
    Returns:
        Email body as string
    """
    body = ""
    
    # Check if payload has parts (multipart message)
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            
            # Prefer plain text, but also handle HTML
            if mime_type == "text/plain":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
            elif mime_type == "text/html" and not body:
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            
            # Handle nested parts 
            elif "parts" in part:
                nested_body = extract_email_body(part)
                if nested_body:
                    body = nested_body
                    break
    
    # Single part message
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    
    return body


def fetch_emails(service, query: str) -> List[Dict]:
    """
    Fetch emails matching the query.
    
    Args:
        service: Gmail API service instance
        query: Gmail search query
    
    Returns:
        List of email message dictionaries
    """
    try:
        gmail_logger.info(f"Fetching emails with query: {query}")
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        
        if not messages:
            gmail_logger.info("No messages found matching the query")
            return []
        
        gmail_logger.info(f"Found {len(messages)} message(s)")
        
        # Fetch full message details
        email_list = []
        for msg in messages:
            msg_id = msg["id"]
            message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            
            # Extract headers
            headers = message["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
            from_email = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
            date = next((h["value"] for h in headers if h["name"].lower() == "date"), "Unknown")
            
            # Extract body
            body = extract_email_body(message["payload"])
            
            email_data = {
                "id": msg_id,
                "subject": subject,
                "from": from_email,
                "date": date,
                "body": body,
                "snippet": message.get("snippet", "")
            }
            
            email_list.append(email_data)

            # mark email as read
            service.users().messages().modify(userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()
            gmail_logger.info(f"Fetched email - Subject: {subject}, From: {from_email}")
        
        return email_list
    
    except Exception as e:
        gmail_logger.error(f"Error fetching emails: {str(e)}")
        raise


def gmail_poll(service, gmail_config: Dict, processing_config: Dict):
    """
    Poll Gmail for new emails based on configuration.
    
    Args:
        service: Gmail API service instance
        gmail_config: Gmail configuration (n_days, poll_interval)
        processing_config: Processing configuration (from, subject)
    """
    gmail_logger.info("Starting gmail polling")
    
    # Extract configuration
    n_days = gmail_config.get("n_days", 1)
    interval = gmail_config.get("poll_interval", 30)
    from_email = processing_config.get("from", "")
    subject = processing_config.get("subject", "")
    
    gmail_logger.info(f"Configuration - n_days: {n_days}, interval: {interval}s, from: {from_email}, subject: {subject}")
    
    # Build query
    query = build_query(from_email, subject, n_days)
    
    try:
        # Fetch emails
        emails = fetch_emails(service, query)
        
        if emails:
            gmail_logger.info(f"Successfully fetched {len(emails)} email(s)")
            
            # Process each email
            for email in emails:
                gmail_logger.info("=" * 80)
                gmail_logger.info(f"Email ID: {email['id']}")
                gmail_logger.info(f"From: {email['from']}")
                gmail_logger.info(f"Subject: {email['subject']}")
                gmail_logger.info(f"Date: {email['date']}")
                gmail_logger.info(f"Body Preview: {email['body'][:200]}...")
                gmail_logger.info("=" * 80)
                
                # TODO: Add your email processing logic here
                # For example: extract fields, generate PDF, etc.
        else:
            gmail_logger.info("No new emails to process")
        
        # Wait for the next poll interval
        gmail_logger.info(f"Waiting {interval} seconds before next poll...")
        time.sleep(interval)
        
    except Exception as e:
        gmail_logger.error(f"Error during gmail polling: {str(e)}")
        raise
