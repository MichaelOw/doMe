class Task:
    def __init__(self, name = '', date = 0, time = -1, location = '', linkList = [], important = 0, new = 0, recurringString = '', recurringInteger = -1):
        self.name = name
        self.date = date
        self.time = time
        self.location = location
        self.linkList = linkList
        self.important = important
        self.new = new
        self.recurringString = recurringString
        self.recurringInteger = recurringInteger
    def getName(self):
        name = self.name
        if name == '': name = ' -No task name-'
        if self.new: return '<b>{}</b>'.format(name)
        return name
    def getImportant(self): 
        if self.important: return u'\u2757'
        return ''
    def getTime(self):
        if self.time != -1: return '<b>{}</b>'.format(timeString(self.time))
        return ''
    def getLocation(self):
        if self.location: return '<i>@{}</i>'.format(self.location)
        return ''

class Command:
    def __init__(self, commandType = 'INVALID', task = Task(), numberList = []):
        self.commandType = commandType
        self.task = task
        self.numberList = numberList

# "4 digit" to "xx.xx am/pm"
def timeString(time):
    if time == -1:
        return ''
    hours = time//100
    minutes = time%100
    meridiem = 'am'
    if hours > 12:
        hours -= 12
        meridiem = 'pm'
    if hours == 12: meridiem = 'pm'
    if hours == 0: hours += 12
    if minutes == 0: return str(hours) + meridiem
    return str(hours) + ':' + str(minutes) + meridiem


