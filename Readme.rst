MQLog
=====

This is a PubSub Message Queue log handler library, that integrates in standard python logging system as handler. It;s also has an extended log structure `mqlog.LogMessage` that should be extracted (`LogMessage().to_dict()`) in log message in `extra` argument.

Usage
-----

Setup intergation with Logging
""""""""""""""""""""""""""""""

Here an example configuration of logging module::

    import logging.config
    import logging
    from staff import project

    def configure():
        mq_logging = True
        logging_level = 'DEBUG'

        default_handler = {
            'level': logging_level,
            'formatter': 'standard',
        }

        default_handler.update({
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        })

        logging_conf = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '[%(name)s:%(lineno)d] %(asctime)s'
                                ' %(levelname)s: %(message)s'
                },
            },
            'handlers': {'default': default_handler},
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': logging_level,
                    'propagate': True
                },
            }
        }
        if mq_logging:
            params = {'host': 'localhost', 'port': 6379, 'db': 0}
            log_channel = 'results'
            params.update({'channel': log_channel})
            mq_handler = {
                'level': 'DEBUG',
                'class': 'mqlog.MQHandler',
                'mq_params': params
            }
            logging_conf['handlers'].update({'mqlog': mq_handler})
            logging_conf['loggers']['']['handlers'].append('mqlog')

        logging.config.dictConfig(logging_conf)


    if __name__ == '__main__':
        configure()
        log = logging.getLogger(__name__)
        log.error('Runing a project', extra={'object_id': 1, 'object_name': 'Project', 'type': 'Infrastructure'})
        project.run()

After this you can use default logging facility as usual::

  import logging
  log = logging.getLogger(__name__)
  
  log.error('Test log message', exc_info=True)

  log.error('Test message with extra fields',
            extra={'object_name': 'Account',
                   'object_id': 22,
                   'type': 'account.status',
                   'status_code': 2})

.. note:: Depending on the version of Python you’re using, extra might not be an acceptable keyword argument for a logger’s .exception() method (.debug(), .info(), .warning(), .error() and .critical() should work fine regardless of Python version). This should be fixed as of Python 3.2. Official issue here: http://bugs.python.org/issue15541.
