import sys
import json
import base64
from datetime import datetime

_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('ascii'))


class JsonSerializationMixin(object):
    """ Transforms objects mainly Entity or ValueObject to JSON """
    def to_dict(self):
        """ searches a get-methods in object and fires them """
        field_name = lambda s: s.split('_', 1)[1] if '_' in s else s

        def _parse(_field):
            if _field.startswith('get_'):
                field = field_name(_field)
                value = getattr(self, _field)()
                if hasattr(value, 'to_dict'):
                    value = getattr(value, 'to_dict')()

                if isinstance(value, list):
                    value = list(map(lambda obj: obj.to_dict()
                                     if hasattr(obj, 'to_dict') else obj,
                                     value))

                if isinstance(value, (str, bytes)) and value.isdigit():
                    value = int(value)

                if isinstance(value, bytes):
                    try:
                        value = _b(value)
                    except Exception:
                        value = _b(base64.standard_b64encode(value))
                return field, value
        return dict(filter(lambda x: x, map(_parse, dir(self))))


class ValueObject(JsonSerializationMixin):
    pass


class LogLevel(ValueObject):
    critical = 0
    error = 10
    warning = 20
    info = 30
    debug = 100


class LogMessage(ValueObject):
    """ The log message. Used mainly as a contract. """

    __log_type__ = None
    __object_name__ = None
    __object_id__ = None
    __level__ = None
    __status_code__ = None
    __msg__ = None
    __datetime__ = None
    LOG_LEVEL = LogLevel

    def __init__(self, log_type=None, object_name=None, object_id=None,
                 level=None, status_code=None, datetime=None,
                 *args, **kwargs):

        self.set_type(log_type)
        self.set_level(level)
        self.set_object_name(object_name)
        self.set_object_id(object_id)
        self.set_status_code(status_code)
        self.set_datetime(datetime)

    def set_type(self, log_type):
        self.__log_type__ = log_type

    def get_type(self):
        return self.__log_type__

    def set_object_name(self, s):
        self.__object_name__ = s

    def get_object_name(self):
        return self.__object_name__

    def set_object_id(self, s):
        self.__object_id__ = s

    def get_object_id(self):
        return self.__object_id__

    def set_level(self, level):
        self.__level__ = level

    def get_level(self):
        return self.__level__

    def set_status_code(self, status_code):
        self.__status_code__ = status_code

    def get_status_code(self):
        return self.__status_code__

    def set_datetime(self, t):
        if t is None:
            t = str(datetime.now())

        elif isinstance(t, (int, float)):
            try:
                t = str(datetime.fromtimestamp(t))
            except:
                pass

        self.__datetime__ = t

    def get_datetime(self):
        return self.__datetime__

    @classmethod
    def from_log_record(cls, record):
        """
        :type record: logging.LogRecord
        """
        return cls(**record.__dict__)

    def __str__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.get_log_type())


class AbstractChannel(object):

    def send(self, message):
        raise NotImplementedError()


class BaseChannel(AbstractChannel):
    """ Data channel abstraction.
    """
    name = 'default'

    def __init__(self, name, mq=None, respond_to=None):
        """
        :type mq: redis.StrictRedis
        :type respond_to: Channel
        """
        self.mq = mq
        self.name = name
        self.send_channel = respond_to

    def __postproc_msg(self, fun, data):
        """
        :type fun: types.FunctionType
        :type data: bytes

        this method trows an exceptions while processing data such as
        ValueError. Don't hesitate to catch them.
        """
        if isinstance(data, bytes):
            data = str(data, 'utf-8')
        message = fun(data)
        return message

    def send(self, message):
        """
        :type message: dict
        """
        return self.mq.publish(self.name,
                               self.__postproc_msg(json.dumps, message))

    def __str__(self):
        return '<{} queue name: {} >'.format(self.__class__.__name__,
                                             self.name)

class Channel(BaseChannel):
    """ Results Channel
    """
    name = 'results'

    def transform_fields(self, message):
        if hasattr(message, 'to_dict'):
            return message.to_dict()
        return message

    def send(self, message):
        """
        :type message: ValueObject
        """
        return super(Channel, self).send(self.transform_fields(message))
