import logfire
logfire.configure()
logfire.instrument_pydantic()


def lambda_handler(event, context):
    foo = event['foo']
    bar = event['bar']
    my_lambda_function(foo, bar)


logfire.instrument_aws_lambda(lambda_handler)


def my_lambda_function(foo, bar):
    logfire.info('my_lambda_function entry', foo=foo, bar=bar)
