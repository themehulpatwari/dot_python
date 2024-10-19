from util import (
    get_ics_events,
    insert_into_tasklist
)

def main():
    url = "https://ics_file_link.ics"
    
    events = get_ics_events(url)
    
    insert_into_tasklist(events)

if __name__ == '__main__':
    main()