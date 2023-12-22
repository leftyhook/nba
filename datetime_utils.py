from datetime import datetime, timedelta, tzinfo

def weekday_name(weekday: int) -> str:
    if weekday == 0:
        return "Monday"

    if weekday == 1:
        return "Tuesday"

    if weekday == 2:
        return "Wednesday"

    if weekday == 3:
        return "Thursday"

    if weekday == 4:
        return "Friday"

    if weekday == 5:
        return "Saturday"

    if weekday == 6:
        return "Sunday"

    raise ValueError("weekday cannot be less than 0 or greater than 6")


def nth_weekday_in_month(n: int, weekday: int, month: int, year: int) -> datetime:
    day_name = weekday_name(weekday)

    dt = datetime(year, month, 1)
    month_name = datetime.strftime(dt, "%B")
    td_1d = timedelta(days=1)
    while dt.weekday() != weekday:
        dt += td_1d

    instance = 1
    td_7d = timedelta(days=7)
    while True:
        if instance == n:
            return dt

        dt += td_7d

        if dt.month != month:
            raise ValueError("There is no %dth %s of %s" % (n, day_name, month_name))

        instance += 1


def eastern_timezone() -> tzinfo:
    est = EST()
    now_est = datetime.now(tz=est)
    edt_roll_dt = nth_weekday_in_month(2, 6, 3, now_est.year)
    edt_roll = datetime(edt_roll_dt.year, edt_roll_dt.month, edt_roll_dt.day, hour=2, tzinfo=est)

    if now_est < edt_roll:
        return est
    else:
        edt = EDT()
        now_edt = datetime.now(tz=edt)
        est_roll_dt = nth_weekday_in_month(1, 6, 11, now_edt.year)
        est_roll = datetime(est_roll_dt.year, est_roll_dt.month, est_roll_dt.day, hour=2, tzinfo=edt)

        if now_edt < est_roll:
            return edt

        return est


class EST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=-5)

    def tzname(self, dt):
        return "EST"

    def dst(self, dt):
        return timedelta(0)


class EDT(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=-4)

    def tzname(self, dt):
        return "EDT"

    def dst(self, dt):
        return timedelta(0)
