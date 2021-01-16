import datetime

class Chrono:
    def getCurrentTimeDelta(self, UTCDiffInSeconds = 28800):
        UTC_today = datetime.datetime.utcnow()
        userToday = UTC_today + datetime.timedelta(seconds=UTCDiffInSeconds)
        return userToday

    # Raw means yyymmdd
    def getUTCDiffInSeconds(self, currentTimeRaw, currentDateRaw):
        UTC_now = datetime.datetime.utcnow()

        hour = currentTimeRaw // 100
        minute = currentTimeRaw % 100

        day = currentDateRaw % 100
        month = currentDateRaw // 100 % 100
        year = currentDateRaw // 10000

        user_now = datetime.datetime(year, month, day, hour, minute)

        UTCDiffInSeconds = int(round(((user_now - UTC_now).total_seconds())))
        return UTCDiffInSeconds

    def getNiceDate(self, date, UTCDiffInSeconds = 28800):
        if date == 0:
            return ''

        day = date % 100
        month = date // 100 % 100
        year = date // 10000

        dateDelta = datetime.datetime(year, month, day)
        mondayDelta = self.getMondayTimeDelta(UTCDiffInSeconds)
        dateDelta = dateDelta.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
        mondayDelta = mondayDelta.replace(hour = 0, minute = 0, second = 0, microsecond = 0)

        dateDiff = int((dateDelta - mondayDelta).days)

        if dateDiff < 0:        # Before This Week's Monday
            pass

        elif dateDiff < 7:      # In this Week
            return '(<b>{}</b>)'.format(dateDelta.strftime('%a'))

        elif dateDiff < 14:     # In next week
            return '(<b>N.{}</b>)'.format(dateDelta.strftime('%a'))

        if year != int(self.getCurrentTimeDelta(UTCDiffInSeconds).strftime('%Y')):      # 2018, 2019
            return '(<b>{}{}{}</b>)'.format(str(day),
                                            dateDelta.strftime('%b'),   #Jan, Feb...
                                            str(year))
        else:
            return '(<b>{}{}</b>)'.format(str(day),
                                            dateDelta.strftime('%b'))   #Jan, Feb...

    def getNiceRecurringDate(self, date, recurringInteger):
        if date == 0:
            return ''

        day = 1
        month = date // 100 % 100
        year = 2018

        dateDelta = datetime.datetime(year, month, day)

        return '{}{}'.format(recurringInteger,
                             dateDelta.strftime('%b'))   #Jan, Feb...


    def getMondayTimeDelta(self, UTCDiffInSeconds):
        todayDelta = self.getCurrentTimeDelta(UTCDiffInSeconds)
        weekDay = int(todayDelta.strftime('%w'))        # 0-sun, 1-mon, ..., 6-sat

        if weekDay == 0:        # Sunday
            todayDelta = todayDelta - datetime.timedelta(days=6)
        else:
            todayDelta = todayDelta - datetime.timedelta(days=(weekDay - 1))

        return todayDelta

    def getDateNumberFromTimeDelta(self, dateTimeDelta):
        year = int(dateTimeDelta.strftime('%Y'))
        month = int(dateTimeDelta.strftime('%m'))
        day = int(dateTimeDelta.strftime('%d'))
        return 10000 * year + 100 * month + day

    def getTimeDeltaFromDateNumber(self, dateNumber):
        day = dateNumber % 100
        month = dateNumber // 100 % 100
        year = dateNumber // 10000
        return datetime.datetime(year, month, day)

    def getDateNumberNDaysFromMonday(self, n, UTCDiffInSeconds = 28800):
        return self.getDateNumberFromTimeDelta(self.getMondayTimeDelta(UTCDiffInSeconds) + datetime.timedelta(days = n))

    def getDateNumberNDaysFromToday(self, n, UTCDiffInSeconds = 28800):
        return self.getDateNumberFromTimeDelta(self.getCurrentTimeDelta(UTCDiffInSeconds) + datetime.timedelta(days = n))

    def getDateNumberNDaysFromDateNumber(self, n, dateNumber):
        self.getTimeDeltaFromDateNumber(dateNumber)
        return self.getDateNumberFromTimeDelta(self.getTimeDeltaFromDateNumber(dateNumber) + datetime.timedelta(days = n))

    def getCurrentWeekDayInteger(self, UTCDiffInSeconds = 28800):
        todayDelta = self.getCurrentTimeDelta(UTCDiffInSeconds)
        weekDay = int(todayDelta.strftime('%w'))
        if weekDay == 0:
            return 7
        return weekDay

    def getWeekDayIntegerFromDateNumber(self, datenumber):
        dateDelta = self.getTimeDeltaFromDateNumber(datenumber)
        weekDay = int(dateDelta.strftime('%w'))
        if weekDay == 0:
            return 7
        return weekDay

    def getTimeDelta(self, year, month, day):
        return datetime.datetime(year, month, day)


#    def getWeekDay(self, timeDelta):	         #1-mon, ..., 6-sat, 7-sun
#        weekDay = int(timeDelta.strftime('%w'))
#        if weekDay == 0:
#            return 7
#        return weekDay

#    def getCurrentYearInteger(self, UTCDiffInSeconds = 28800):
#        return self.getDateYear(self.getCurrentTimeDelta(UTCDiffInSeconds))

#    def getCurrentMonthInteger(self, UTCDiffInSeconds = 28800):
#        return self.getDateMonth(self.getCurrentTimeDelta(UTCDiffInSeconds))

#    def getCurrentDayInteger(self, UTCDiffInSeconds = 28800):
#        return self.getDateDay(self.getCurrentTimeDelta(UTCDiffInSeconds))

#    def getDateDay(self, timeDelta):
#        return int(timeDelta.strftime('%d'))

#    def getDateMonth(self, timeDelta):
#        return int(timeDelta.strftime('%m'))

#    def getDateMonthStr(self, timeDelta):		#Jan, Feb...
#        return timeDelta.strftime('%b')

#    def getDateYear(self, timeDelta):
#        return int(timeDelta.strftime('%Y'))

#    def getWeekDayStr(self, timeDelta):			#Mon, Tue...
#        return timeDelta.strftime('%a')

#    def getDateDiff(self, timeDelta1, timeDelta2):
#        return int((timeDelta2 - timeDelta1).days)

#    def getDaysAwayFromMonday(self, number):
#        return self.timeDelta2Date(self.getMondayTimeDelta() + datetime.timedelta(days = number))

#    def getDaysAwayFromToday(self, number):
#        return self.timeDelta2Date(self.getCurrentTimeDelta() + datetime.timedelta(days = number))

#    def timeDelta2Date(self, dateTimeDelta):
#        year = self.getDateYear(dateTimeDelta)
#        month = self.getDateMonth(dateTimeDelta)
#        day = self.getDateDay(dateTimeDelta)

#        return 10000 * year + 100 * month + day

#    def getTimeDeltaFromRaw(self, timeRaw, dateRaw):
#        day = dateRaw % 100
#        month = dateRaw // 100 % 100
#        year = dateRaw // 10000

#        hour = timeRaw // 100
#        minute = timeRaw % 100

#        return datetime.datetime(year, month, day, hour, minute)
