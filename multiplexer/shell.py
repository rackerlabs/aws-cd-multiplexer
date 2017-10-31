'''CLI Entry Point'''

import os
import logging
import multiplexer

from multiplexer import config, merge, __version__


def main(arv=None):
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(
            description='Simple tool to merge multiple Code Deploy sources into an artifact.')

    parser.add_argument('--version', '-v', action='version',
                        version=__version__)

    parser.add_argument('--config', '-c',
                        help='Configuration file to use when building artifact.',
                        required=True)
    parser.add_argument('--github-token', '-T', dest='github_token',
                        help='Token to use when pulling Github packages.')
    parser.add_argument('--destination', '-d',
            help='''Destination to store the artifacts (local or s3).
                    Use s3://bucket/key for S3.''',
                        default=os.getcwd())
    parser.add_argument('artifacts', nargs='*')

    verbose = parser.add_mutually_exclusive_group()
    verbose.add_argument('-V', dest='loglevel', action='store_const',
                         const=logging.INFO,
                         help='Set log level to INFO.')
    verbose.add_argument('-VV', dest='loglevel', action='store_const',
                         const=logging.DEBUG,
                         help='Set log level to DEBUG.')

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    conf = config.load(args.config)
    if args.github_token:
        conf._raw['github']['token'] = args.github_token

    artifacts = [a['name'] for a in conf.artifacts]
    if args.artifacts:
        artifacts = args.artifacts

    for artifact in artifacts:
        merge.build_artifact(artifact, conf, args.destination)
