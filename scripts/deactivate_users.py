#!/usr/bin/env python3
"""
deactivate_users.py - GLPI User Deactivation Script
Author: Ayman Ahmed
Description: Deactivates GLPI users who are no longer active
             IT team members are automatically excluded
"""

import requests
import logging
import csv
from datetime import datetime

GLPI_URL = "http://your-glpi-server/apirest.php"
APP_TOKEN = "your-app-token"
USER_TOKEN = "your-user-token"

IT_TEAM = [
    "ayman.ahmed", "abdelrahman.gouda", "ahmed.samra",
    "eslam.tryaq", "omar.khaled", "farouk.gaafar",
    "mostafa.mahfouz", "abdelrahman.sayed", "mohamed.abdelrehem"
]

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


def load_offboarded_users(csv_file):
    users = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row.get("username", "").lower())
        logger.info(f"Loaded {len(users)} offboarded users from CSV")
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
    return users


def deactivate_user(session_token, user_id, username):
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
        logger.info(f"[DEACTIVATED] {username} (ID: {user_id})")
        return True
    else:
        logger.error(f"Failed to deactivate {username}: {response.text}")
        return False


def main():
    logger.info("Starting user deactivation process")
    session_token = get_session_token()
    if not session_token:
        return

    try:
        offboarded = load_offboarded_users("offboarded_users.csv")
        headers = get_headers(session_token)
        response = requests.get(
            f"{GLPI_URL}/User?range=0-5000&is_deleted=0&is_active=1",
            headers=headers
        )
        if response.status_code != 200:
            logger.error("Failed to fetch users")
            return

        glpi_users = response.json()
        deactivated = 0
        for user in glpi_users:
            username = user.get("name", "").lower()
            if username in offboarded:
                if deactivate_user(session_token, user["id"], username):
                    deactivated += 1

        logger.info(f"Deactivation complete: {deactivated} users deactivated")
    finally:
