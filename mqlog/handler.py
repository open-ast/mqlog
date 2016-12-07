import warnings
import logging
from .base import LogMessage


class MQHandler(logging.Handler):
    """ Handler that could be injected in Standard Logging system to push a log
    in to a redis pubsub

    >>> import redis
    >>> import logging
    >>> from mqlog import Channel, MQHandler
    >>> log = logging.getLogger(__name__)
    >>> log.addHandler(MQHandler(Channel('log', mq=redis.StrictRedis())))
    >>> log.error('the galaxy in danger!',
    >>>           extra={'log_type': 'galaxy', 'status_code': '666'})
    """

    def __init__(self, channel=None, mq_params=None):
        """
        :type channel: mqlog.Channel
        """
        if mq_params:
            try:
                channel = self.get_configured(mq_params, channel)
            except Exception as err:
                warnings.warn('Could not configure MQHandler: {}'.format(self, err))

        logging.Handler.__init__(self)
        self.queue = channel

    def enqueue(self, record):
        """
        :type record: logging.LogRecord
        """
        log_record = LogMessage(
            log_type=record.__dict__.get('log_type')
                     or record.__dict__.get('type')
                     or '{}:{}[{}]'.format(record.name,
                                           record.funcName,str(record.lineno)),
            object_name=record.__dict__.get('object_name'),
            object_id=record.__dict__.get('object_id'),
            level=record.levelno,
            status_code=record.__dict__.get('status_code'),
            datetime=record.__dict__.get('datetime') or record.created
        ).to_dict()
        log_record.update({'msg': record.msg})
        self.queue.send({'log': log_record})

    def close(self):
        pass

    def get_configured(cls, mq_params, channel=None):
        """
        :type mq_params: dict
        :type channel: mqlog.Channel
        """
        if not channel:
            channel_name = mq_params.pop('channel', None)
            assert channel_name, KeyError('You mush specify a {\'channel\': \'name\'}, '
                                          'if you do not pass configured Channel object explicitly')

            import redis
            from mqlog.base import Channel as channel
            mq = redis.StrictRedis(**mq_params)
            return channel(channel_name, mq=mq)

        return channel

    def prepare(self, record):
        """
        Prepares a record for queuing. The object returned by this method is
        enqueued.

        The base implementation formats the record to merge the message
        and arguments, and removes unpickleable items from the record
        in-place.

        You might want to override this method if you want to convert
        the record to a dict or JSON string, or send a modified copy
        of the record while leaving the original intact.
        """
        # The format operation gets traceback text into record.exc_text
        # (if there's exception data), and also puts the message into
        # record.message. We can then use this to replace the original
        # msg + args, as these might be unpickleable. We also zap the
        # exc_info attribute, as it's no longer needed and, if not None,
        # will typically not be pickleable.
        self.format(record)
        record.msg = record.message
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        """
        Emit a record.

        Writes the LogRecord to the queue, preparing it for pickling first.
        """
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            self.handleError(record)
