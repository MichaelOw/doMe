import os
import re
import sys
import json
import socket
import sqlite3
import logging
import datetime
import telegram
from time import sleep
from src.chrono import Chrono
from src.command import Task
from src.command import Command
from src.utils import get_api_token
from src.simple_parser import Parser
from telegram.error import NetworkError, Unauthorized

api_token = ''
if not api_token: api_token = get_api_token()

#########
# SETUP #
#########
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s [%(module)s]: %(message)s')
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('log.log', 'w', 'utf-8'))

update_id = None
conn = sqlite3.connect('database.db')
c = conn.cursor()
parser = Parser()
chrono = Chrono()

valid_undo_commands = ['ADD', 'DEL', 'APPEND', 'EDIT', 'ADD_RECUR', 'DEL_RECUR']
recurring_list_commands = ['LIST_RECUR', 'DEL_RECUR']
weekday_integer_list = {'mon':1, 'tue':2, 'wed':3, 'thu':4, 'fri':5, 'sat':6, 'sun':7}

TASK_NUMBER_LIMIT = 20
INVALID_COMMAND_MULTI = 'Whoops! You can only use multiple lines for the "<b>ADD</b>" command. The "<b>{}</b>" command is not allowed in conjunction with other commands.'
INVALID_COMMAND_MYTIME = 'Not enough information to calculate your timezone!'
INVALID_COMMAND_GENERAL = 'Invalid Command Haha! See /help.'
INVALID_COMMAND_INDEX = 'Task {} is out of list range!'
INVALID_COMMAND_APPEND = 'Nothing to append!'
INVALID_COMMAND_UNDO = 'No more undos!'
NOTIFICATION_DEL = '<b>(Deleted!)</b> {}'
NOTIFICATION_MYTIME = 'Your timezone has been calculated and stored!'
COMMAND_LIST_PASS = ['LIST', 'START', 'LIST_FULL', 'LIST_RECUR', 'HELP']

##################
# MAIN FUNCTIONS #
##################

def main():
    global update_id
    logger.warning('(1/3) Loading bot...')
    bot = get_bot(api_token)
    update_id = get_update_id(bot)
    logger.warning('(2/3) Loading database...')
    db_init()
    logger.warning('(3/3) Bot ready.')
    #send('Recipebot has been activated.', 302383988, bot)
    while True:
        try:
            handle_updates(bot)
        except NetworkError:
            sleep(1)
        except Unauthorized:
            update_id += 1
        except Exception as e:
            logger.error('Exception {}'.format(str(e)))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            #print(exc_type, fname, exc_tb.tb_lineno)
            sleep(1)

def handle_updates(bot):
    global update_id
    for update in bot.get_updates(offset=update_id, timeout=10):
        update_id = update.update_id + 1
        if update.message:
            m = update.message
        elif update.edited_message:
            m = update.edited_message
        else:
            continue
        logger.info('{}: {}'.format(m.chat_id, m.text))
        reply = get_reply(m.text, m.chat_id)
        logger.info('Reply:{}'.format(reply))
        send(reply, m.chat_id, bot)


def get_reply(text, id):
    global parser
    logger.debug('get_reply started')
    if not id in db_get_users_list():
        db_add_user(id)
        return set_timezone_message
    command_list = []
    additional_message_list = []
    utc_diff_in_seconds = db_get_utc_diff_in_seconds(id)
    try:
        for line in text.split('\n'):
            command = parser.getCommand(line, utc_diff_in_seconds)
            command_list.append(command)
        check_valid_multiple_line_command(command_list)
        for command in command_list:
            execute(command, id, additional_message_list)
    except Exception as e:
        logger.error('Exception: {}'.format(str(e)))
        return str(e)
    db_add_task_recurring_n_day_only(id)
    message = generate_main_message(id, command_list[0], utc_diff_in_seconds)
    message = attach(additional_message_list, message, id, command_list[0])
    db_save()
    logger.debug('get_reply ended')
    return message

######################
# DATABASE FUNCTIONS #
######################

def db_init():
    c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER, UTCDiffInSeconds INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS tasks(id INTEGER, name TEXT, date INTEGER, time INTEGER, location TEXT, linkListSerial TEXT, important INTEGER, new INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS tasks_recurring(id INTEGER, name TEXT, date INTEGER, time INTEGER, location TEXT, linkListSerial TEXT, important INTEGER, new INTEGER, recurringString TEXT, recurringInteger INTEGER)')
    conn.commit()

def db_get_users_list():
    temp = []
    c.execute('SELECT id FROM users')
    for row in c.fetchall():
        temp.append(row[0])
    return temp

def db_add_user(id, defaultDiffInSeconds = 28800):
    c.execute('INSERT INTO users (id, UTCDiffInSeconds) VALUES (?,?)', (id, defaultDiffInSeconds))

def db_get_utc_diff_in_seconds(id):
    c.execute('SELECT UTCDiffInSeconds FROM users WHERE id = (?)', (id,))
    return c.fetchall()[0][0]

def db_change_utc_diff_in_seconds(id, UTCDiffInSeconds):
    db_undo_clear(id)
    c.execute('UPDATE users SET UTCDiffInSeconds = (?) WHERE id = (?)', (UTCDiffInSeconds, id))
    conn.commit()

#0-id INTEGER
#1-name TEXT
#2-date INTEGER
#3-time INTEGER
#4-location TEXT
#5-linkListSerial TEXT
#6-important INTEGER
#7-new INTEGER

def db_get_tasklist(id):
    tasklist = []
    c.execute('SELECT * FROM tasks WHERE id = (?) ORDER BY date, time', (id,))
    for row in c.fetchall():
        tasklist.append(Task(name = row[1], date = row[2], time = row[3], location = row[4], linkList = json.loads(row[5]), important = row[6], new = row[7]))
    c.execute('UPDATE tasks SET new = 0 WHERE id = (?)', (id,))
    return tasklist

#0-id INTEGER
#1-name TEXT
#2-date INTEGER
#3-time INTEGER
#4-location TEXT
#5-linkListSerial TEXT
#6-important INTEGER
#7-new INTEGER
#8-recurringString TEXT
#9-recurringInteger INTEGER

def db_get_recurring_tasklist(id):
    tasklist = []
    c.execute('SELECT * FROM tasks_recurring WHERE id = (?) ORDER BY recurringString, substr(date,5,2)||recurringInteger', (id,))
    for row in c.fetchall():
        tasklist.append(Task(name = row[1], date = row[2], time = row[3], location = row[4], linkList = json.loads(row[5]), important = row[6], new = row[7], recurringString = row[8], recurringInteger = row[9]))
    return tasklist

def db_add_task(task, id):
    db_undo_save(id)
    c.execute('INSERT INTO tasks (id, name, date, time, location, linkListSerial, important, new) VALUES (?,?,?,?,?,?,?,?)', (id, task.name, task.date, task.time, task.location, json.dumps(task.linkList), task.important, task.new))
    

def db_add_task_diff_date(task, id, diff_date):
    c.execute('SELECT * FROM tasks WHERE (id, name, date, time, location, linkListSerial, important) = (?,?,?,?,?,?,?)', (id, task.name, diff_date, task.time, task.location, json.dumps(task.linkList), task.important))
    if not c.fetchall():
        c.execute('INSERT INTO tasks (id, name, date, time, location, linkListSerial, important, new) VALUES (?,?,?,?,?,?,?,?)', (id, task.name, diff_date, task.time, task.location, json.dumps(task.linkList), task.important, task.new))

def db_add_task_recurring(task, id):
    db_undo_clear(id)
    c.execute('INSERT INTO tasks_recurring (id, name, date, time, location, linkListSerial, important, new, recurringString, recurringInteger) VALUES (?,?,?,?,?,?,?,?,?,?)', (id, task.name, task.date, task.time, task.location, json.dumps(task.linkList), task.important, task.new, task.recurringString, task.recurringInteger))

def db_delete_task(number_or_task, id):
    db_undo_save(id)
    if isinstance(number_or_task, int):
        c.execute('SELECT * FROM tasks WHERE id = (?) ORDER BY date, time', (id,))
        try: task_tuple = c.fetchall()[number_or_task - 1]
        except IndexError: raise Exception(INVALID_COMMAND_INDEX.format(number_or_task))
    else:
        task_tuple = (id, number_or_task.name, number_or_task.date, number_or_task.time, number_or_task.location, json.dumps(number_or_task.linkList), number_or_task.important, number_or_task.new)
    c.execute('DELETE FROM tasks WHERE rowid = (SELECT rowid FROM tasks WHERE (id, name, date, time, location, linkListSerial, important, new) = (?,?,?,?,?,?,?,?) LIMIT 1)', task_tuple)
    return Task(name = task_tuple[1], date = task_tuple[2], time = task_tuple[3], location = task_tuple[4], linkList = json.loads(task_tuple[5]), important = task_tuple[6], new = task_tuple[7])

def db_delete_task_recurring(number, id):
    db_undo_clear(id)
    c.execute('SELECT * FROM tasks_recurring WHERE id = (?) ORDER BY recurringString, substr(date,5,2)||recurringInteger', (id,))
    try: task_tuple = c.fetchall()[number - 1]
    except IndexError: raise Exception(INVALID_COMMAND_INDEX.format(number))
    c.execute('DELETE FROM tasks_recurring WHERE rowid = (SELECT rowid FROM tasks_recurring WHERE (id, name, date, time, location, linkListSerial, important, new, recurringString, recurringInteger) = (?,?,?,?,?,?,?,?,?,?) LIMIT 1)', task_tuple)
    c.execute('DELETE FROM tasks WHERE (id, name, time, location, linkListSerial, important) = (?,?,?,?,?,?)', task_tuple[:2] + task_tuple[3:-3])

def db_get_task(number, id):
    c.execute('SELECT * FROM tasks WHERE id = (?) ORDER BY date, time', (id,))
    try: task_tuple = c.fetchall()[number - 1]
    except IndexError: raise Exception(INVALID_COMMAND_INDEX.format(number))
    return Task(name = task_tuple[1], date = task_tuple[2], time = task_tuple[3], location = task_tuple[4], linkList = json.loads(task_tuple[5]), important = task_tuple[6], new = task_tuple[7])

def db_append_task(number, id, append_task):
    db_undo_save(id)
    c.execute('SELECT * FROM tasks WHERE id = (?) ORDER BY date, time', (id,))
    try: task_tuple = c.fetchall()[number - 1]
    except IndexError: raise Exception(INVALID_COMMAND_INDEX.format(number))
    c.execute('DELETE FROM tasks WHERE rowid = (SELECT rowid FROM tasks WHERE (id, name, date, time, location, linkListSerial, important, new) = (?,?,?,?,?,?,?,?) LIMIT 1)', task_tuple)
    new_name = task_tuple[1]
    new_location = task_tuple[4]
    new_linkList = json.loads(task_tuple[5])
    if append_task.name: new_name = '{}, {}'.format(new_name, append_task.name)
    if append_task.location: new_location = '{}/{}'.format(new_location, append_task.location)
    if append_task.linkList: new_linkList = new_linkList + append_task.linkList
    new_new = 1
    new_task_tuple = (id, new_name, task_tuple[2], task_tuple[3], new_location, json.dumps(new_linkList), task_tuple[7], new_new)
    c.execute('INSERT INTO tasks (id, name, date, time, location, linkListSerial, important, new) VALUES (?,?,?,?,?,?,?,?)', new_task_tuple)

def db_append_task_with_another_tasks(id, numberList):
    db_undo_save(id)
    append_task = db_get_task(numberList[1], id)
    db_append_task(numberList[0], id, append_task)
    db_delete_task(append_task, id)

def db_edit_task(number, id, edit_task):
    db_undo_save(id)
    c.execute('SELECT * FROM tasks WHERE id = (?) ORDER BY date, time', (id,))
    try: task_tuple = c.fetchall()[number - 1]
    except IndexError: raise Exception(INVALID_COMMAND_INDEX.format(number))
    c.execute('DELETE FROM tasks WHERE rowid = (SELECT rowid FROM tasks WHERE (id, name, date, time, location, linkListSerial, important, new) = (?,?,?,?,?,?,?,?) LIMIT 1)', task_tuple)
    task_listed = list(task_tuple)
    if edit_task.name: task_listed[1] = edit_task.name
    if edit_task.date != 0: task_listed[2] = edit_task.date
    if edit_task.time != -1: task_listed[3] = edit_task.time
    if edit_task.location != '': task_listed[4] = edit_task.location
    if edit_task.linkList: task_listed[5] = json.dumps(edit_task.linkList)
    if edit_task.important != 0: task_listed[6] = edit_task.important
    task_listed[7] = 1
    c.execute('INSERT INTO tasks (id, name, date, time, location, linkListSerial, important, new) VALUES (?,?,?,?,?,?,?,?)', tuple(task_listed))

def db_add_task_recurring_next_n_days(id, task, n = 14):
    utc_diff_in_seconds = db_get_utc_diff_in_seconds(id)
    current_time_delta = Chrono.getCurrentTimeDelta(utc_diff_in_seconds)
    for i in range(n + 1):
        target_time_delta = current_time_delta + datetime.timedelta(days = i)
        target_date_number = chrono.getDateNumberFromTimeDelta(target_time_delta)
        month_number = int(target_time_delta.strftime('%m'))
        day_of_month_number = int(target_time_delta.strftime('%d'))
        day_of_week_string = target_time_delta.strftime('%a').lower()
        if task.recurringString == 'every_year' and task.recurringInteger == day_of_month_number and (task.date // 100 % 100) == month_number: db_add_task_diff_date(task, id, target_date_number)
        elif task.recurringString == 'every_month' and task.recurringInteger == day_of_month_number: db_add_task_diff_date(task, id, target_date_number)
        elif task.recurringString[6:] == day_of_week_string: db_add_task_diff_date(task, id, target_date_number)

def db_add_task_recurring_n_day_only(id, n = 14):
    utc_diff_in_seconds = db_get_utc_diff_in_seconds(id)
    current_time_delta = Chrono.getCurrentTimeDelta(utc_diff_in_seconds)
    recurring_tasklist = db_get_recurring_tasklist(id)
    i = n
    target_time_delta = current_time_delta + datetime.timedelta(days = i)
    target_date_number = chrono.getDateNumberFromTimeDelta(target_time_delta)
    month_number = int(target_time_delta.strftime('%m'))
    day_of_month_number = int(target_time_delta.strftime('%d'))
    day_of_week_string = target_time_delta.strftime('%a').lower()
    for task in recurring_tasklist:
        if task.recurringString == 'every_year' and task.recurringInteger == day_of_month_number and (task.date // 100 % 100) == month_number: db_add_task_diff_date(task, id, target_date_number)
        elif task.recurringString == 'every_month' and task.recurringInteger == day_of_month_number: db_add_task_diff_date(task, id, target_date_number)
        elif task.recurringString[6:] == day_of_week_string: db_add_task_diff_date(task, id, target_date_number)

def db_undo(id):
    c.execute('SELECT * FROM tasks WHERE id = (?)', (id + 1000000000,))
    if not c.fetchall(): raise Exception(INVALID_COMMAND_UNDO)
    c.execute('DELETE FROM tasks WHERE id = (?)', (id,))
    c.execute('UPDATE tasks SET id = (?) WHERE id = (?)', (id, id + 1000000000))

def db_undo_save(id):
    # delete previous undo save
    c.execute('DELETE FROM tasks WHERE id = (?)', (id + 1000000000,))
    # copy current tasks under modified id
    c.execute('INSERT INTO tasks SELECT (id + 1000000000) AS id, name, date, time, location, linkListSerial, important, new FROM tasks WHERE id = (?)', (id,))
#    c.execute('SELECT * FROM tasks WHERE id = (?)', (id + 1000000000,))
#    for row in c.fetchall():
#        print(row)

def db_undo_clear(id):
    c.execute('DELETE FROM tasks WHERE id = (?)', (id + 1000000000,))

def db_save():
    conn.commit()



####################
# HELPER FUNCTIONS #
####################

def get_bot(api_token):
    if api_token == 'insert_your_api_token_here': assert 0, '"Please add you Telegram Bot api token into run.py"'
    while True:
        try:
            try:
                print('Trying to get_bot...')
                bot = telegram.Bot(api_token)
                return bot
            except socket.timeout:
                #logger.error('exception', str(e))
                sleep(2)
                pass
        except Exception as e:
            logger.error('exception', str(e))
            sleep(2)
            pass

def get_update_id(bot):
    try:
        update_id = bot.get_updates()[0].update_id
        return update_id
    except IndexError:
        return None

def send(message, id, bot):
    bot.send_chat_action(chat_id=id, action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=id, text=message, parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=1)

def check_valid_multiple_line_command(command_list):
    if len(command_list) < 2:
        return
    for command in command_list:
        command_type = command.commandType
        if not command_type in ['ADD', 'ADD_RECUR']:
            raise Exception(INVALID_COMMAND_MULTI.format(command_type))

def execute(command, id, messageList):
    logger.debug('execute started')
    commandType = command.commandType
    numberList = command.numberList
    if commandType in COMMAND_LIST_PASS: pass
    elif commandType == 'ADD': db_add_task(command.task, id)
    elif commandType == 'DEL':
        for number in numberList:
            deletedTask = db_delete_task(number, id)
            messageList.append(NOTIFICATION_DEL.format(deletedTask.getName()))
    elif commandType == 'ADD_RECUR':
        db_add_task_recurring(command.task, id)
        db_add_task_recurring_next_n_days(id, command.task)
    elif commandType == 'DEL_RECUR': db_delete_task_recurring(numberList[0], id)
    elif commandType == 'APPEND':
        print(command.task.name)
        print(command.task.location)
        print(command.task.linkList)
        if not command.task.name and not command.task.location and not command.task.linkList: raise Exception(INVALID_COMMAND_APPEND)
        else:
            if len(numberList) > 1 and len(command.task.name.split()) == 1: db_append_task_with_another_tasks(id, numberList)
            else: db_append_task(numberList[0], id, command.task)
    elif commandType == 'SEARCH': pass
    elif commandType == 'UNDO': db_undo(id)
    elif commandType == 'EDIT': db_edit_task(numberList[0], id, command.task)
    elif commandType == 'MYTIME':
        if command.task.time == -1 or command.task.date == 0: raise Exception(INVALID_COMMAND_MYTIME)
        else:
            UTCDiffInSeconds = chrono.getUTCDiffInSeconds(command.task.time, command.task.date)
            db_change_utc_diff_in_seconds(id, UTCDiffInSeconds)
            messageList.append(NOTIFICATION_MYTIME)
    elif commandType == 'CLEAR': raise Exception('Clear command coming soon!')
    elif commandType == 'REDO': raise Exception('Redo command coming soon!')
    else: raise Exception(INVALID_COMMAND_GENERAL)
    logger.debug('execute ended')

def generate_main_message(id, command, UTCDiffInSeconds):
    logger.debug('Generate tasklist_string started')
    tasklist_string = ''
    search_mode = 0
    search_found = 0
    search_task = command.task
    full_list_mode = 0
    recur_list_mode = 0
    today_bar_exists = 0
    end_of_week_bar_exists = 0
    end_of_week_bar_needed = 0
    if command.commandType == 'SEARCH': search_mode = 1
    elif command.commandType == 'HELP': return welcome_message_string
    elif command.commandType == 'START': return set_timezone_message
    elif command.commandType == 'LIST_FULL': full_list_mode = 1
    elif command.commandType in recurring_list_commands: recur_list_mode = 1
    if search_mode:
        tasklist = db_get_tasklist(id)
        for i, task in enumerate(tasklist):
            if task_match(task, search_task):
                search_found = 1
                tasklist_string = '{}<b>{}</b>. {} {}{}{}{}{}\n'.format(tasklist_string, str(i + 1), chrono.getNiceDate(task.date, UTCDiffInSeconds), task.getTime(), bold_term(task.getName(), search_task.name), task.getLocation(), get_link_string(task.linkList, 'full'), task.getImportant())
        if not search_found:
            tasklist_string = '{}No entries match your search :(\n'.format(tasklist_string)
    elif recur_list_mode:
        recurringtasklist = db_get_recurring_tasklist(id)
        if not len(recurringtasklist): return 'No recurring tasks added yet!\n'
        for i, task in enumerate(recurringtasklist):
            tasklist_string = '{}<b>{}</b>. {}{} (<b>{}</b>)/Del_R{}\n'.format(tasklist_string, i + 1, task.name, task.getImportant(), get_nice_recurring_date(task), i + 1)
    else:
        tasklist = db_get_tasklist(id)
        if not len(tasklist): return empty_tasklist_string
        todayDelta = chrono.getCurrentTimeDelta(UTCDiffInSeconds)
        todayDateNumber = chrono.getDateNumberFromTimeDelta(todayDelta)
        mondayDateNumber = chrono.getDateNumberNDaysFromMonday(0, UTCDiffInSeconds)
        sundayDateNumber = chrono.getDateNumberNDaysFromMonday(6, UTCDiffInSeconds)
        for i, task in enumerate(tasklist):
            # Insert Today bar
            if (i+1 <= TASK_NUMBER_LIMIT or full_list_mode) or task.new:
                if not today_bar_exists and task.date > todayDateNumber:
                    today_bar_exists = 1
                    tasklist_string = '{}<b>***({}) {} {}, {} hrs***</b>\n'.format(tasklist_string,
                                                                                    todayDelta.strftime('%a'),      # Mon, Tue
                                                                                    todayDelta.strftime('%d'),     # 1-30
                                                                                    todayDelta.strftime('%b'),      # Jan, Feb
                                                                                    todayDelta.strftime("%H:%M"))   # 14:35
                # Insert End of week bar
                if end_of_week_bar_exists:
                    pass
                elif not end_of_week_bar_exists and task.date > mondayDateNumber and task.date <= sundayDateNumber:
                    end_of_week_bar_needed = 1
                elif end_of_week_bar_needed and task.date > sundayDateNumber:
                    tasklist_string = '{}----------<i>End of Week</i>----------\n'.format(tasklist_string)
                    end_of_week_bar_exists = 1
                tasklist_string = '{}<b>{}</b>.{}{} {}{}{}{}\n'.format(tasklist_string,
                                                                    str(i + 1),
                                                                    chrono.getNiceDate(task.date, UTCDiffInSeconds),
                                                                    task.getTime(),
                                                                    task.getName(),
                                                                    task.getLocation(),
                                                                    get_link_string(task.linkList),
                                                                    task.getImportant())
            # Trim list if not full_list_mode
            if i+1 == TASK_NUMBER_LIMIT and not full_list_mode:
                tasklist_string = '{}<b>{}</b>. ... [/show_all]\n'.format(tasklist_string, str(i+2))
    tasklist_string = reverse_order(tasklist_string)
    logger.debug('Generate tasklist_string ended')
    return tasklist_string

def task_match(task, search_task):
    task_name = task.name.lower()
    search_text = search_task.name.lower()
    task_name = ' {}'.format(task_name)
    search_text = ' {}'.format(search_text)
    if task_name.find(search_text) == -1: return 0
    #if search_task.date and not task.date == search_task.date: return 0
    return 1

def reverse_order(message):
    messageList = message.split('\n')
    messageList.reverse()
    newMessage ='\n'.join(messageList)
    return newMessage

def get_link_string(linkList, type = 'shortened'):
    if len(linkList) == 0:
        return ''
    linkString = ''
    if type == 'shortened':
        for i, link in enumerate(linkList):
            linkString += '(<a href="{}">{}</a>)'.format(link, trim_link(link))
    else:
        for i, link in enumerate(linkList):
            linkString += ' {} '.format(link)
    return linkString

def trim_link(link):
    if link[:5] == 'https':
        link = link[8:]
    elif link[:4] == 'http':
        link = link[7:]
    if link[:4] == 'www.':
        link = link[4:]
    if len(link[:4]) < 1:
        return 'invalid_link'
    return link[:4]+'...'

def get_nice_recurring_date(task):
    if task.recurringString == 'every_year':
        return 'Every {}'.format(chrono.getNiceRecurringDate(task.date, task.recurringInteger))
    elif task.recurringString == 'every_month':
        if task.recurringInteger == 1:
            return 'Every 1st'
        if task.recurringInteger == 2:
            return 'Every 2nd'
        if task.recurringInteger == 3:
            return 'Every 3rd'
        else:
            return 'Every {}th'.format(task.recurringInteger)
    else:
        return task.recurringString.replace('_',' ').title()

def attach(messageList, message, id, command):
    if messageList:
        message = '{}\n-----'.format(message)
        for line in messageList:
            message = '{}\n{}'.format(message, line)
    message = '{}\n[/refresh] [/recurring_tasks]'.format(message)
    return message

def get_date_string():
    today_UTC = datetime.datetime.now()
    today_singapore = today_UTC + datetime.timedelta(seconds=28800)
    year_str = today_singapore.strftime('%Y')
    month_str = today_singapore.strftime('%m')
    day_str = today_singapore.strftime('%d')
    return '{}{}{}'.format(year_str, month_str, day_str)

def bold_term(string, search_term):
    index = ' {}'.format(string.lower()).find(' {}'.format(search_term.lower()))
    print('"{}" found in "{}" at position {}'.format(search_term, string, index))
    if index == -1: return string
    return '{}<b>{}</b>{}'.format(string[:index], string[index:index + len(search_term)], string[index + len(search_term):])

################
# LONG STRINGS #
################

set_timezone_message = """Hi New User! Set your Timezone first by sharing your current time with me!
<b>Type:</b> mytime [Your Currrent Time and Date]

<b>e.g.</b> mytime 11am 25may
<b>e.g.</b> mytime 1125am 25may
<b>e.g.</b> mytime 1pm 25may
<b>e.g.</b> mytime 130pm 25may"""

welcome_message_string = """Welcome to DoMe Task Manager!
<i>Just type in a command! (No "/" needed.)</i>

<b>1) Adding Tasks</b> [Optional Arguments]
eg. <i>Go swimming at pool tmr 8am</i>
<b>Syntax:</b> Task_Name [date][time][location][link][!]
<b>Acceptable Formats</b> (not case-sensitive)
Date: <i>17apr, 17 apr, 17 april, 17 april 2003</i>
Time: <i>7pm, 745pm, 11am</i>
Location: <i>at ang mo kio, @ang_mo_kio</i>
Link: <i>http..., www...</i>

<b>2) Deleting Tasks</b>
eg. delete 10 / d 10 / d10
eg. d 3 1 6 2

<b>3) Refresh Current Tasks</b>
eg.  refresh / ref / list / ls

<b>4) Edit Tasks</b>
eg. edit 3 <i>something new</i>
eg. e 12 <i>19 feb</i>
eg. e 15 <i>something new 19 feb</i>

<b>5) Append</b>
eg. append 5 more_info at location2
eg. app 5 more_info at LOC_2
    <b>Result:</b> Task, <i>more_info @LOC_1/LOC_2</i>

<b>6) Change Timezone</b>
eg. mytime 1125pm 25may

<b>7) Search</b>
eg. s things to buy

<b>8) Undo</b> (Only 1 undo supported)
eg. undo, u
"""

empty_tasklist_string = """- List is empty! -

Just type a task and send!
For example: <b>Buy a goat 17 dec</b>.
See /help for more options."""

#####################
# RUN MAIN FUNCTION #
#####################

if __name__ == '__main__':
    main()