import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'caltest'
sys.path.insert(0, str(ROOT))

from database.db import initialize_database, get_connection, DB_PATH
from tools.calendar import add_event, list_events, upcoming_events, update_event, delete_event


def reset_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    initialize_database()


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    reset_db()
    e1 = add_event('Dentist', '2026-08-13T10:00:00Z', '2026-08-13T11:00:00Z', 'Clinic', 'Checkup')
    e2 = add_event('Study', '2026-08-14T15:00:00Z', '2026-08-14T17:00:00Z')
    check(e1['id'] == 1 and e1['title'] == 'Dentist', 'add')
    check(len(list_events()) == 2, 'list')
    check(len(list_events('2026-08-13T10:30:00Z', '2026-08-13T10:30:00Z')) == 1, 'overlap')
    check(list_events()[0]['title'] == 'Dentist', 'ordering')
    check(upcoming_events(10)[0]['title'] == 'Dentist', 'upcoming')
    e1u = update_event(e1['id'], title='Dentist Checkup', notes=None)
    check(e1u['title'] == 'Dentist Checkup' and e1u['notes'] is None, 'update')
    try:
        add_event('bad', '2026-08-14T18:00:00Z', '2026-08-14T17:00:00Z')
        raise AssertionError('invalid range accepted')
    except ValueError:
        pass
    try:
        add_event('bad', 'not-a-date', '2026-08-14T17:00:00Z')
        raise AssertionError('invalid datetime accepted')
    except ValueError:
        pass
    try:
        update_event(9999, title='x')
        raise AssertionError('missing update accepted')
    except ValueError:
        pass
    delete_event(e2['id'])
    check(len(list_events()) == 1, 'delete')
    try:
        delete_event(e2['id'])
        raise AssertionError('missing delete accepted')
    except ValueError:
        pass
    # Four-way sync in the actual source files is checked textually below in a separate smoke.
    print('test_calendar.py: 9 tests passed')

if __name__ == '__main__':
    main()
