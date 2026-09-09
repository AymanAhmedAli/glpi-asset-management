#!/usr/bin/env python3
"""
add_emails.py - GLPI Email Assignment Script
Author: Ayman Ahmed
Description: Assigns email addresses to GLPI users based on username pattern
"""

import requests
import logging
from datetime import datetime

GLPI_URL = "http://your-glpi-server/apirest.php"
APP_TOKEN = "your-app-token"
USER_TOKEN = "your-user-token"
EMAIL_DOMAIN = "@nawy.com"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_session_token():
    headers = {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN,
        "Authorization": f"user_token {USER_TOKEN}"
    }
    response = requests.get(f"{GLPI_URL}/initSession", headers=headers)
    if response.status_code == 200:
        return response.json().get("session_token")
    return None


def get_headers(session_token):
    return {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN,
        "Session-Token": session_token
    }


def get_users_without_email(session_token):
    headers = get_headers(session_token)
    response = requests.get(
        f"{GLPI_URL}/User?range=0-5000&is_deleted=0",
        headers=headers
    )
    if response.status_code == 200:
        users = response.json()
        no_email = [u for u in users if not u.get("email")]
        logger.info(f"Found {len(no_email)} users without email")
        return no_email
    return []


def assign_email(session_token, user_id, username):
    email = f"{username}{EMAIL_DOMAIN}"
    headers = get_headers(session_token)
    payload = {"input": {"email": email}}
    response = requests.put(
        f"{GLPI_URL}/User/{user_id}",
        headers=headers,
        json=payload
    )
    if response.status_code == 200:
        logger.info(f"Assigned email {email} to user ID {user_id}")
        return True
    else:
        logger.error(f"Failed to assign email to {username}: {response.text}")
        return False


def main():
    logger.info("Starting email assignment")
    session_token = get_session_token()
    if not session_token:
        return

    try:
        users = get_users_without_email(session_token)
        success = 0
        for user in users:
            username = user.get("name", "")
            if username and assign_email(session_token, user["id"], username):
                success += 1
        logger.info(f"Successfully assigned {success}/{len(users)} emails")
    finally:
        requests.get(
            f"{GLPI_URL}/killSession",
            headers=get_headers(session_token)
        )


if __name__ == "__main__":
    main()
