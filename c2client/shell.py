from __future__ import print_function, unicode_literals

import argparse
import json
import os
import ssl
from abc import abstractmethod
from typing import Dict

import boto
import boto3
import inflection

from functools import wraps

from c2client.compat import get_connection
from c2client.utils import from_dot_notation, get_env_var, prettify_xml

if hasattr(ssl, "_create_unverified_context"):
    ssl._create_default_https_context = ssl._create_unverified_context

if os.environ.get("DEBUG"):
    boto.set_stream_logger("c2")


def get_boto3_client(service: str, endpoint: str,
                     aws_access_key_id: str, aws_secret_access_key: str, verify: bool):
    """Returns boto3 client connection to specified Cloud service."""

    return boto3.client(
        service,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="croc",
        endpoint_url=endpoint,
        verify=verify,
    )


def configure_boto(verify: bool):
    """Configure boto runtime for CROC Cloud"""

    if not boto.config.has_section("Boto"):
        boto.config.add_section("Boto")
    boto.config.set("Boto", "is_secure", "True")
    boto.config.set("Boto", "num_retries", "0")
    boto.config.set("Boto", "https_validate_certificates", str(verify))


def exitcode(func: callable):
    """Wrapper for logging any caught exception."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            return e
    return wrapper


def parse_arguments(program: str):
    """
    Parse incoming action and arguments as a dictionary
    for support AWS API requests format.
    """

    parser = argparse.ArgumentParser(prog=program)
    parser.add_argument("action", help="The action that you want to perform.")
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        help="disable verifying ssl certificate",
        required=False
    )
    parser.add_argument(
        "parameters",
        nargs="*",
        help="Any parameters for the action. "
             "Parameters specified by parameter key and "
             "parameter value separated by space."
    )
    args = parser.parse_args()

    params = args.parameters
    no_verify_ssl = args.no_verify_ssl
    parameters = dict(zip(params[::2], params[1::2]))

    return args.action, parameters, no_verify_ssl


# program name : client class name
_CLIENTS: Dict[str, str] = {}


def get_client_names():

    return _CLIENTS.copy()


class BaseClient:

    program_name: str
    url_key: str
    client_name: str

    @classmethod
    @abstractmethod
    def make_request(cls, method: str, arguments: dict, verify: bool):
        """Run request."""

        raise NotImplementedError

    @classmethod
    @exitcode
    def execute(cls):
        """Main function for API client."""

        action, arguments, verify = parse_arguments(cls.program_name)

        cls.make_request(action, arguments, verify)


class LegacyClient(BaseClient):

    @classmethod
    def get_client(cls, verify: bool):

        configure_boto(verify)
        endpoint = get_env_var(cls.url_key)

        return get_connection(cls.client_name, endpoint)

    @classmethod
    def make_request(cls, method: str, arguments: dict, verify: bool):

        connection = cls.get_client(verify)
        response = connection.make_request(method, arguments)

        print(prettify_xml(response.read()))


class Client(BaseClient):

    @classmethod
    def get_client(cls, verify: bool):

        endpoint = get_env_var(cls.url_key)

        aws_access_key_id = get_env_var("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = get_env_var("AWS_SECRET_ACCESS_KEY")

        return get_boto3_client(cls.client_name, endpoint,
                                aws_access_key_id,
                                aws_secret_access_key,
                                verify)

    @classmethod
    def make_request(cls, method: str, arguments: dict, verify: bool):

        client = cls.get_client(verify)

        for key, value in arguments.items():
            if value.isdigit():
                arguments[key] = int(value)
            elif value.lower() == "true":
                arguments[key] = True
            elif value.lower() == "false":
                arguments[key] = False

        result = getattr(client, inflection.underscore(method))(**from_dot_notation(arguments))

        result.pop("ResponseMetadata", None)

        # default=str is required for serializing Datetime objects
        print(json.dumps(result, indent=4, sort_keys=True, default=str))


class EC2Client(LegacyClient):

    program_name = "c2-ec2"
    url_key = "EC2_URL"
    client_name = "ec2"


class CWClient(LegacyClient):

    program_name = "c2-cw"
    url_key = "AWS_CLOUDWATCH_URL"
    client_name = "cw"


class CTClient(LegacyClient):

    program_name = "c2-ct"
    url_key = "AWS_CLOUDTRAIL_URL"
    client_name = "ct"

    @classmethod
    def make_request(cls, method: str, arguments: dict, verify: bool):

        connection = cls.get_client(verify)

        if "MaxResults" in arguments:
            arguments["MaxResults"] = int(arguments["MaxResults"])
        if "StartTime" in arguments:
            arguments["StartTime"] = int(arguments["StartTime"])
        if "EndTime" in arguments:
            arguments["EndTime"] = int(arguments["EndTime"])

        response = connection.make_request(method, json.dumps(from_dot_notation(arguments)))

        print(json.dumps(response, indent=4, sort_keys=True))


class ASClient(Client):

    program_name = "c2-as"
    url_key = "AUTO_SCALING_URL"
    client_name = "autoscaling"


class BSClient(Client):

    program_name = "c2-bs"
    url_key = "BACKUP_URL"
    client_name = "backup"


class EKSClient(Client):

    program_name = "c2-eks"
    url_key = "EKS_URL"
    client_name = "eks"


class ELBClient(Client):

    program_name = "c2-elb"
    url_key = "ELB_URL"
    client_name = "elbv2"
