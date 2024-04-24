import datetime


class Time:
    def __init__(self):
        self.datetime: datetime.datetime = self.utcnow()
        self.time: int = self.datetime.timestamp()

    def __repr__(self):
        return f"<Time {self.time}>"

    @staticmethod
    def utcnow() -> datetime.datetime:
        """A helper function to return an aware UTC datetime representing the current time.

        This should be preferred to :meth:`datetime.datetime.utcnow` since it is an aware
        datetime, compared to the naive datetime in the standard library.

        .. versionadded:: 2.0

        Returns
        --------
        :class:`datetime.datetime`
            The current aware datetime in UTC.
        """
        return datetime.datetime.utcnow().replace(tzinfo=None)
        # return datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None)
        # return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        # return datetime.datetime.now().replace(tzinfo=None)
