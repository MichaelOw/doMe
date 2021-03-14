import sys
import logging
from src.command import Task
from src.chrono import Chrono
from src.command import Command

chrono = Chrono()
logger = logging.getLogger(__name__)
#logger.addHandler(logging.FileHandler('log.log'))
#logger.addHandler(logging.StreamHandler(sys.stdout))

START = ["start"]
HELP = ["help"]
LIST = ['list', 'ls', 'refresh', 'display', 'ref']
LIST_FULL = ['show_all']
LIST_RECUR = ['recurring_tasks']
DEL = ['d', 'del', 'delete']
DEL_RECUR = ['del_r']
EDIT = ['e', 'edit']
UNDO = ['u', 'undo']
REDO = ['r', 'redo']
CLEAR = ['clear']
APPEND = ['append', 'app']
MYTIME = ['mytime']
SEARCH = ['s', 'search']

monthList = {'jan' : 1, 'feb' : 2, 'mar' : 3, 'apr' : 4, 'may' : 5, 'jun' : 6, 'jul' : 7, 'aug' : 8, 'sep' : 9, 'oct' : 10, 'nov' : 11, 'dec' : 12, 'january' : 1, 'february' : 2, 'march' : 3, 'april' : 4, 'may' : 5, 'june' : 6, 'july' : 7, 'august' : 8, 'september' : 9, 'october' : 10, 'november' : 11, 'december' : 12}
dayList = {'monday' : 0,'mon' : 0,'tuesday' : 1,'tue' : 1,'tues' : 1,'wednesday' : 2,'wed' : 2,'thursday' : 3,'thu' : 3,'thur' : 3,'thurs' : 3,'friday' : 4,'fri' : 4,'saturday' : 5,'sat' : 5,'sunday' : 6,'sun' : 6}
pronounList = {'tdy' : 0, 'today' : 0, 'tmr' : 1, 'tomorrow' : 1, 'tomo' : 1, 'ytd' : -1, 'yesterday' : -1}
nextList = ['next', 'n']
fillerWordsList = ['on', 'at', 'by']

class Parser:
    def getCommand(self, text, UTCDiffInSeconds):
        logger.debug('getCommand started processing text: ' + text)
        logger.debug('----------')
        logger.debug('Processing command text:'+ text)
        text = text.strip('/')

        if text[-12:] == '@domedomebot':
            text = text[:-12]

        if text.lower() in HELP:
            return Command('HELP')
        if text.lower() in START:
            return Command('START')

        #asteriskBugThrow(text)

        text = lazyTypingConverter(text)
        text = dateSpaceAdder(text)

        important, text = findImportant(text)
        logger.info('important:'+ str(important))

        wordList = text.split()

        commandType, numberList = findCommandType(wordList)
        logger.info('commandType:'+ commandType)
        logger.info('numberList:'+ str(numberList))
        
        time = findTime(wordList)
        logger.info('time:'+ str(time))

        linkList = findLink(wordList)
        logger.info('linkList:'+ str(linkList))

        date, recurringString = findDate(wordList, UTCDiffInSeconds, commandType)
        recurringInteger = 0
        if len(numberList):
            recurringInteger = numberList[0]
        logger.info('date:'+ str(date))
        logger.info('recurringString:'+ recurringString)
        logger.info('recurringInteger:'+ str(recurringInteger))

        location = findLocation(wordList)
        logger.info('location:'+ location)

#        removeFillerWords(wordList)

        name = (' '.join(wordList)).strip()
        if name: name = '{}{}'.format(name[0].upper(), name[1:])
        name = name.replace("'", "")
        logger.info('name:'+ name)
        logger.info('----------')

        logger.debug('getCommand ended')
        return Command(commandType, Task(name, date, time, location, linkList, important, 1, recurringString, recurringInteger), numberList)

def findImportant(text):
    for i, character in enumerate(reversed(text)):
        if character == '!':
            realIndex = len(text) - 1 - i
            return 1, text[0:realIndex] + text[realIndex+1:]

    return 0, text

def findCommandType(wordList):
    numberList = []
    firstWord = wordList[0].lower()
    index_every = get_index_every(wordList)

    if firstWord in LIST and len(wordList) == 1:
        return 'LIST', numberList

    elif firstWord in LIST_FULL:
        return 'LIST_FULL', numberList

    elif firstWord in LIST_RECUR:
        return 'LIST_RECUR', numberList

    elif firstWord in DEL:
        # del wordList[0]

        for word in wordList:
            if word.isdigit() and int(word) > 0:
                numberList.append(int(word))

        numberList = list(set(numberList))
        numberList.sort(reverse=True)
        if len(numberList) == 0:
            # return 'INVALID', numberList
            return 'ADD', numberList
        else:
            del wordList[0]
            return 'DEL', numberList

    elif firstWord in EDIT:
        if len(wordList) == 1 or not wordList[1].isdigit():
            return 'ADD', numberList
        else:
            del wordList[0]

            for i, word in enumerate(wordList):
                if word.isdigit():
                    numberList.append(int(word))
                    del wordList[i]
                    #if len(wordList) == 0:
                        #return 'INVALID', numberList
                    return 'EDIT', numberList

            return 'INVALID', numberList

    elif firstWord in MYTIME:
        del wordList[0]
        return 'MYTIME', numberList

    elif firstWord in UNDO and len(wordList) == 1:
        return 'UNDO', numberList
    elif firstWord in REDO and len(wordList) == 1:
        return 'REDO', numberList
    elif firstWord in CLEAR and len(wordList) == 1:
        return 'CLEAR', numberList

    elif firstWord in SEARCH:
        del wordList[0]
        return 'SEARCH', numberList

    elif firstWord in APPEND:
        del wordList[0]
        for i, word in enumerate(wordList):
            if word.isdigit():
                numberList.append(int(word))
                if wordList[i + 1].isdigit(): numberList.append(int(wordList[i + 1]))
                del wordList[i]
                return 'APPEND', numberList

        return 'INVALID', numberList

    elif index_every != -1:
        del wordList[index_every]
        for i, word in enumerate(wordList):
            if word.isdigit() and i >= index_every:
                numberList.append(int(word))
                del wordList[i]
            elif word.isdigit():
                wordList[i] = "'{}".format(word)
        return 'ADD_RECUR', numberList

    elif firstWord[:5] in DEL_RECUR:
        if firstWord[5:].isdigit():
            numberList.append(int(firstWord[5:]))
            return 'DEL_RECUR', numberList

    return 'ADD', numberList

def findLocation(wordList):
    for i, word in enumerate(wordList):
        if word[0] == '@' and len(word) > 1:
            location = word[1:]
            del wordList[i]
            return location

        if word.lower() == 'at':
            if i < len(wordList) - 1:
            #if i < len(wordList) - 1 and not wordList[i+1].isdigit() and wordList[i+1] not in monthList and wordList[i+1] not in dayList and wordList[i+1] not in pronounList and wordList[i+1] not in nextList:
                location = '_'.join(wordList[i + 1:])
                del wordList[i:]
                return location

    return ''

def findLink(wordList):
    linkList = []
    length = len(wordList)
    for i, word in enumerate(reversed(wordList)):
        if word[0:4].lower() in ['http', 'www.']:
            linkList.insert(0, word)
            del wordList[length - 1 - i]

    return linkList

def findTime(wordList):
    timeString = ''
    minutes = 0
    for i, word in enumerate(wordList):
        if len(word) > 2 and word[-2:].lower() in ['am', 'pm']:
            for letter in word[:-2]:
                if letter.isdigit():
                    timeString += letter
                else:
                    return -1

            length = len(timeString)
            if length < 3:
                hours = int(timeString)
            elif length < 5:
                hours = int(timeString[:-2])
                minutes = int(timeString[-2:])
            else:
                raise Exception('Invalid Time Entered Haha! See /help.')

            if hours == 12:
                hours = 0
            elif hours > 12:
                raise Exception('Invalid Time Entered Haha! See /help.')

            if word[-2:].lower() == 'pm':
                hours += 12

            del wordList[i]
            return hours * 100 + minutes
    return -1

def findDate(wordList, UTCDiffInSeconds, commandType):
    length = len(wordList)
    year_specified = 0
    recurringString = ''

    for i, word in enumerate(reversed(wordList)):
        realIndex = length - 1 - i

        if word.lower() in monthList:
            month = monthList[word.lower()]
            day = 1
            year = int(chrono.getCurrentTimeDelta(UTCDiffInSeconds).strftime('%Y'))

            if validRange(realIndex + 1, length) and len(wordList[realIndex + 1]) <= 4 and wordList[realIndex + 1].isdigit() and int(wordList[realIndex + 1]) >= year:
                year = int(wordList[realIndex + 1])
                year_specified = 1
                del wordList[realIndex + 1]

            del wordList[realIndex]

            if validRange(realIndex - 1, length) and wordList[realIndex - 1].isdigit():
                day = int(wordList[realIndex - 1])
                del wordList[realIndex - 1]

            checkValidDate(year, month, day)

            dateNumber = 10000 * year + 100 * month + day
            currentDateNumber = chrono.getDateNumberFromTimeDelta(chrono.getCurrentTimeDelta(UTCDiffInSeconds))

            # Set date to next year if the month has already passed for this year
            if not year_specified and dateNumber//100 < currentDateNumber//100:
                print('{} < {}'.format(str(dateNumber//100), str(currentDateNumber//100)))
                dateNumber += 10000

            recurringString = 'every_year'
            return dateNumber, recurringString

        elif word.lower() in dayList:
            diffFromMonday = dayList[word.lower()]      #e.g. On tue, diffFromMonday = 1
            today = chrono.getCurrentWeekDayInteger(UTCDiffInSeconds) #e.g. On tue, today = 2
            del wordList[realIndex]

            if validRange(realIndex - 1, len(wordList)) and wordList[realIndex - 1].lower() in nextList:     # Check if "next" is written
                k = 1
                while validRange(realIndex - k, len(wordList)) and wordList[realIndex - k].lower() in nextList:
                    diffFromMonday = diffFromMonday + 7
                    del wordList[realIndex - k]
                    k+=1
            elif today > diffFromMonday:                                                    # Treat day that has passed as the next week one
                diffFromMonday = diffFromMonday + 7

            dateNumber = chrono.getDateNumberNDaysFromMonday(diffFromMonday, UTCDiffInSeconds)
            recurringString = 'every_{}'.format(word.lower()[0:3])

            return dateNumber, recurringString

        elif word.lower() in pronounList:
            diffFromToday = pronounList[word.lower()]
            del wordList[realIndex]
            return chrono.getDateNumberNDaysFromToday(diffFromToday, UTCDiffInSeconds), ''
    if commandType == 'ADD':
        chrono.getDateNumberNDaysFromToday(0, UTCDiffInSeconds), 'every_month'
    return 0, 'every_month'

def asteriskBugThrow(text):
    if oddNumberAsterisks(text) or oddNumberUnderscore(text):
        raise Exception('Odd number of asterisk/underscore not allowed! See /help.')

def oddNumberAsterisks(text):
    return text.count('*')%2 == 1

def oddNumberUnderscore(text):
    return text.count('_')%2 == 1

def lazyTypingConverter(text):
    for i, letter in enumerate(text):
        if letter == ' ':
            return text
        if letter.isdigit() and (text[:i].lower() in DEL or text[:i].lower() in EDIT or text[:i].lower() in APPEND):
            print('Lazy typing converter converts {} to {} {}'.format(text, text[:i], text[i:]))
            return '{} {}'.format(text[:i], text[i:])
    return text

def validRange(index, length):
    if index < 0:
        return 0
    if index > length - 1:
        return 0
    return 1

def checkValidDate(year, month, day):
    try:
        chrono.getTimeDelta(year, month, day)
    except:
        raise Exception('Invalid date! See /help.')

def dateSpaceAdder(text):
    i = 0
    while i < len(text) - 2:
        if text[i:i+3].lower() in monthList:
            if i-1 > -1 and text[i-1].isdigit():
                text = text[:i] + ' ' + text[i:]
        i+=1
    return text

def removeFillerWords(wordList):
    length = len(wordList)
    for i, word in enumerate(reversed(wordList)):
        if word.lower() in fillerWordsList:
            del wordList[length - 1 - i]

def get_index_every(wordList):
    for i, word in enumerate(wordList):
        if word.lower() == 'every':
            return i
    return -1
