#!/usr/bin/env python3
"""
weekly_sync.py - GLPI Weekly Sync Script
Author: Ayman Ahmed
Description: Syncs Active Directory users with GLPI IT Asset Management
             Detects new hires, serial number changes, and inactive users
"""

import requests
import json
import logging
from datetime import datetime

# ================================
# Configuration
# ================================
GLPI_URL = "http://your-glpi-server/apirest.php"
APP_TOKEN = "your-app-token"
USER_TOKEN = "your-user-token"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'sync_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# IT Team — excluded from deactivation
IT_TEAM = [
    "ayman.ahmed", "abdelrahman.gouda", "ahmed.samra",
    "eslam.tryaq", "omar.khaled", "farouk.gaafar",
    "mostafa.mahfouz", "abdelrahman.sayed", "mohamed.abdelrehem"
]


def get_session_token():
    """Initialize GLPI session and return session token"""
    headers = {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN,
        "Authorization": f"user_token {USER_TOKEN}"
    }
    response = requests.get(f"{GLPI_URL}/initSession", headers=headers)
    if response.status_code == 200:
        token = response.json().get("session_token")
        logger.info("Session initialized successfully")
        return token
    else:
        logger.error(f"Failed to initialize session: {response.text}")
        return None


def get_headers(session_token):
    """Return headers with session token"""
    return {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN,
        "Session-Token": session_token
    }


def get_all_users(session_token):
    """Fetch all users from GLPI"""
    headers = get_headers(session_token)
    response = requests.get(
        f"{GLPI_URL}/User?range=0-5000&is_deleted=0",
        headers=headers
    )
    if response.status_code == 200:
        users = response.json()
        logger.info(f"Fetched {len(users)} users from GLPI")
        return users
    else:
        logger.error(f"Failed to fetch users: {response.text}")
        return []


def detect_new_users(glpi_users, ad_users):
    """Detect users in AD but not in GLPI"""
    glpi_usernames = {u.get("name", "").lower() for u in glpi_users}
    new_users = [u for u in ad_users if u["username"].lower() not in glpi_usernames]
    logger.info(f"Detected {len(new_users)} new users")
    return new_users


def detect_inactive_users(glpi_users, ad_users):
    """Detect users in GLPI but disabled/missing in AD"""
    ad_usernames = {u["username"].lower() for u in ad_users if u.get("active")}
    inactive = []
    for user in glpi_users:
        username = user.get("name", "").lower()
        if username not in ad_usernames and username not in IT_TEAM:
            inactive.append(user)
    logger.info(f"Detected {len(inactive)} inactive users")
    return inactive


def detect_serial_changes(glpi_computers, inventory_data):
    """Detect computers with changed serial numbers"""
    changes = []
    glpi_serials = {c.get("name"): c.get("serial") for c in glpi_computers}
    for device in inventory_data:
        name = device.get("name")
        new_serial = device.get("serial")
        old_serial = glpi_serials.get(name)
        if old_serial and new_serial and old_serial != new_serial:
            changes.append({
                "name": name,
                "old_serial": old_serial,
                "new_serial": new_serial
            })
    logger.info(f"Detected {len(changes)} serial number changes")
    return changes


def deactivate_user(session_token, user_id, username):
    """Deactivate a user in GLPI"""
    if username.lower() in IT_TEAM:
        logger.warning(f"Skipping IT team member: {username}")
        return False

    headers = get_headers(session_token)
    payload = {"input": {"is_active": 0}}
    response = requests.put(
        f"{GLPI_URL}/User/{user_id}",
        headers=headers,
        json=payload
    )
    if response.status_code == 200:
        logger.info(f"Deactivated user: {username}")
        return True
    else:
        logger.error(f"Failed to deactivate {username}: {response.text}")
        return False


def kill_session(session_token):
    """Close GLPI session"""
    headers = get_headers(session_token)
    requests.get(f"{GLPI_URL}/killSession", headers=headers)
    logger.info("Session closed")


def generate_report(new_users, inactive_users, serial_changes):
    """Generate weekly sync report"""
    report = f"""
{'='*50}
GLPI Weekly Sync Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*50}

New Users Detected: {len(new_users)}
{chr(10).join([f'  + {u["username"]}' for u in new_users]) if new_users else '  None'}

Inactive Users: {len(inactive_users)}
{chr(10).join([f'  - {u.get("name")}' for u in inactive_users]) if inactive_users else '  None'}

Serial Number Changes: {len(serial_changes)}
{chr(10).join([f'  * {c["name"]}: {c["old_serial"]} → {c["new_serial"]}' for c in serial_changes]) if serial_changes else '  None'}

{'='*50}
"""
    print(report)
    logger.info("Report generated")
    return report


def main():
    logger.info("Starting GLPI Weekly Sync")
    session_token = get_session_token()
    if not session_token:
        logger.error("Cannot proceed without session token")
        return

    try:
        glpi_users = get_all_users(session_token)
        ad_users = [
            {"username": "new.employee", "active": True},
            {"username": "ayman.ahmed", "active": True},
        ]
        inventory_data = []
        new_users = detect_new_users(glpi_users, ad_users)
        inactive_users = detect_inactive_users(glpi_users, ad_users)
        serial_changes = detect_serial_changes([], inventory_data)
        generate_report(new_users, inactive_users, serial_changes)
    finally:
        kill_session(session_token)
        logger.info("Weekly sync completed")


if __name__ == "__main__":
    main()
