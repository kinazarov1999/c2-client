from __future__ import print_function, unicode_literals

import argparse
import codecs
import json
import os
import ssl
import sys

import boto
import boto3
import inflection

from functools import wraps

from c2client.compat import get_service_things
from c2client.utils import from_dot_notation, get_env_var

# Nasty hack to workaround default ascii codec
if sys.version_info[0] < 3:
    sys.stdout = codecs.getwriter("utf8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf8")(sys.stderr)

if hasattr(ssl, "_create_unverified_context"):
    ssl._create_default_https_context = ssl._create_unverified_context

if os.environ.get("DEBUG"):
    boto.set_stream_logger("c2")


def get_boto3_client(service, endpoint, aws_access_key_id, aws_secret_access_key, verify):
    """Returns boto3 client connection to specified Cloud service."""

    return boto3.client(
        service,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="croc",
        endpoint_url=endpoint,
        verify=verify,
    )


def configure_boto(verify):
    """Configure boto runtime for CROC Cloud"""

    if not boto.config.has_section("Boto"):
        boto.config.add_section("Boto")
    boto.config.set("Boto", "is_secure", "True")
    boto.config.set("Boto", "num_retries", "0")
    boto.config.set("Boto", "https_validate_certificates", str(verify))


def exitcode(func):
    """Wrapper for logging any caught exception."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            return e
    return wrapper


def parse_arguments(program):
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
        required=False,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Read json from argument or from stdin instead of paris of parameters.",
        required=False,
    )
    parser.add_argument(
        "parameters",
        nargs="*",
        help=(
            "Any parameters for the action. "
            "Parameters specified by parameter key and "
            "parameter value separated by space."
        ),
    )
    return parser.parse_args()


def read_json(params):
    if params:
        json_str = params[0]
        if json_str == "-":
            json_str = sys.stdin.read()
        return json.loads(json_str)
    return {}


def read_string(params):
    if params:
        params_str = params[0]
        if params_str == "-":
            params_str = sys.stdin.read()
        return params_str
    return ""


def compat_handle(program, url_key, client_name):
    """Main function for services using old boto client."""

    args = parse_arguments(program)
    action = args.action
    verify = args.no_verify_ssl

    configure_boto(verify)
    endpoint = get_env_var(url_key)

    if not args.json:
        parameters = dict(zip(args.parameters[::2], args.parameters[1::2]))
        connection, parameters_transformer, response_printer = get_service_things(
            client_name, endpoint
        )
        if parameters_transformer:
            parameters_transformer(parameters)
        dict_parameters = from_dot_notation(parameters)
        string_parameters = json.dumps(dict_parameters)
    else:
        string_parameters = read_string(args.parameters)

    response = connection.make_request(action, string_parameters)

    response_printer(response)


def handle(program, url_key, client_name):
    """Main function for services using boto3 client."""

    args = parse_arguments(program)
    action = args.action
    verify = args.no_verify_ssl

    endpoint = get_env_var(url_key)

    if not args.json:
        parameters = dict(zip(args.parameters[::2], args.parameters[1::2]))
        for key, value in parameters.items():
            if value.isdigit():
                parameters[key] = int(value)
            elif value.lower() == "true":
                parameters[key] = True
            elif value.lower() == "false":
                parameters[key] = False
        dict_parameters = from_dot_notation(parameters)
    else:
        dict_parameters = read_json(args.parameters)

    aws_access_key_id = get_env_var("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = get_env_var("AWS_SECRET_ACCESS_KEY")

    client = get_boto3_client(
        client_name,
        endpoint,
        aws_access_key_id,
        aws_secret_access_key,
        verify,
    )

    client_method = getattr(client, inflection.underscore(action))
    result = client_method(**dict_parameters)

    result.pop("ResponseMetadata", None)

    print(json.dumps(result, indent=4, sort_keys=True, default=str))


def prepare_func(func, prog_name, url_key, client_name):

    @exitcode
    def generated_func():
        return func(prog_name, url_key, client_name)

    return generated_func


entry_points = {
    compat_handle: (
        # name, url_key, client_name
        ("ec2", "EC2_URL", "ec2"),
        ("cw", "AWS_CLOUDWATCH_URL", "cw"),
        ("ct", "AWS_CLOUDTRAIL_URL", "ct"),
    ),
    handle: (
        # name, url_key, client_name
        ("eks", "EKS_URL", "eks"),
        ("as", "AUTO_SCALING_URL", "autoscaling"),
        ("elb", "ELB_URL", "elbv2"),
        ("bs", "BS_URL", "backup"),
        ("paas", "PAAS_URL", "paas"),
    ),
}

for func, args_list in entry_points.items():
    for name, url_key, client_name in args_list:
        func_name = "{}_main".format(name)
        prog_name = "c2-{}".format(name)
        globals()[func_name] = prepare_func(func, prog_name, url_key, client_name)
