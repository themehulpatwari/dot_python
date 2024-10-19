import requests
from icalendar import Calendar
from datetime import datetime, date, timezone

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/tasks"]


def convert_to_rfc3339(event_start):
    
    """
    Converts event_start (which can be a datetime.date or datetime.datetime)
    to an RFC3339 formatted string.
    """
    
    if isinstance(event_start, datetime):
        # Ensure the datetime is timezone aware; if not, assume UTC
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=timezone.utc)
        return event_start.isoformat()
    elif isinstance(event_start, date):
        # Convert date to datetime at midnight UTC
        event_datetime = datetime.combine(event_start, datetime.min.time(), timezone.utc)
        return event_datetime.isoformat()
    else:
        return ''

def get_ics_events(ics_url: str) -> list[dict]:
    
    """
    Fetches and parses events from an ICS (iCalendar) file located at the given URL.
    Args:
        ics_url (str): The URL of the ICS file to fetch.
    Returns:
        dict: A dictionary containing the parsed events. Each event is represented as a dictionary with the following keys:
            - summary (str or None): The summary or title of the event.
            - start (datetime or None): The start date and time of the event.
            - end (datetime or None): The end date and time of the event.
            - location (str or None): The location of the event.
            - description (str or None): A description of the event.
    Raises:
        Exception: If the ICS file cannot be fetched or if the response status code is not 200.
    """

    # Fetch the .ics file from the given URL
    response = requests.get(ics_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the ics file. Status code: {response.status_code}")
    
    # Parse the ICS content
    cal = Calendar.from_ical(response.content)
    
    events = []
    
    for component in cal.walk():
        if component.name == "VEVENT":
            event = {
                "summary": str(component.get('summary')) if component.get('summary') else None,
                "start": component.get('dtstart').dt if component.get('dtstart') else None,
                "end": component.get('dtend').dt if component.get('dtend') else None,
                "location": str(component.get('location')) if component.get('location') else None,
                "description": str(component.get('description')) if component.get('description') else None
            }
                
            events.append(event)
    
    return events

def insert_into_tasklist(events):
    
    """
    Inserts a list of events into a new Google Tasks tasklist.
    This function handles the authentication process with Google API, creates a new tasklist,
    and adds each event from the provided list as a task in the newly created tasklist.
    Args:
        events (list): A list of event dictionaries. Each dictionary should contain:
        - 'summary' (str): The title of the event.
        - 'description' (str): The description of the event.
        - 'start' (datetime): The start time of the event.
    Raises:
        HttpError: If an error occurs while making requests to the Google Tasks API.
    Example:
        events = [
        {
            'summary': 'Meeting with Bob',
            'description': 'Discuss project updates',
            'start': datetime(2023, 10, 1, 10, 0)
        },
        {
            'summary': 'Dentist Appointment',
            'description': 'Routine check-up',
            'start': datetime(2023, 10, 2, 15, 30)
        ]
        insert_into_tasklist(events)
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("tasks", "v1", credentials=creds)

        # Create a new tasklist
        tasklist = {
            'title': 'New Tasklist from ICS Events'
        }
        result = service.tasklists().insert(body=tasklist).execute()
        tasklist_id = result['id']

        # Add events as tasks to the new tasklist
        for event in events:
            
            task = {
                'title': event['summary'] if event['summary'] is not None else '',
                'notes': event['description'] if event['description'] is not None else '',
                'status': 'needsAction'
            }
            
            if event['end']:
                task['due'] = convert_to_rfc3339(event['end'])
            else:
                task['due'] = convert_to_rfc3339(event['start'])
            
            service.tasks().insert(tasklist=tasklist_id, body=task).execute()

        print(f"Successfully created tasklist with ID: {tasklist_id} and added {len(events)} tasks.")
        
    except HttpError as err:
        print(err)
