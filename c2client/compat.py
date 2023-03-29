import json

from six.moves.urllib.parse import urlparse

import boto.cloudtrail.layer1
import boto.ec2
import boto.ec2.cloudwatch

from boto.ec2.regioninfo import RegionInfo

from c2client.utils import prettify_xml


def ct_parameters_transformer(parameters):
    if "MaxResults" in parameters:
        parameters["MaxResults"] = int(parameters["MaxResults"])
    if "StartTime" in parameters:
        parameters["StartTime"] = int(parameters["StartTime"])
    if "EndTime" in parameters:
        parameters["EndTime"] = int(parameters["EndTime"])


def json_response_printer(response):
    print(json.dumps(response, indent=4, sort_keys=True))


def xml_response_printer(response):
    print(prettify_xml(response.read()))


COMPAT_MAP = {
    "ct": (
        boto.cloudtrail.layer1.CloudTrailConnection,
        ct_parameters_transformer,
        json_response_printer,
    ),
    "cw": (
        boto.ec2.cloudwatch.CloudWatchConnection,
        None,
        xml_response_printer,
    ),
    "ec2": (
        boto.ec2.EC2Connection,
        None,
        xml_response_printer,
    ),
}
"""Connection class, parameters transformer and response printer map."""


def get_service_things(service, endpoint, **kwargs):
    """Returns connection class, parameters transformer and response printer
    to specified Cloud service.
    """

    parsed = urlparse(endpoint)
    kwargs["port"] = parsed.port
    kwargs["path"] = parsed.path

    kwargs["region"] = RegionInfo(
        name=parsed.hostname, endpoint=parsed.hostname)

    klass, parameters_transformer, response_printer = COMPAT_MAP[service]

    return klass(**kwargs), parameters_transformer, response_printer
