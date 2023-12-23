import logging
import os
import subprocess
import sys
from datetime import datetime

import boto3
from watchtower import CloudWatchLogHandler


def setup_cloudwatch_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    boto3.setup_default_session(region_name="eu-west-2")
    cw_handler = CloudWatchLogHandler(
        log_group="MyTestLogGroup", stream_name="MyTestLogStream"
    )
    logger.addHandler(cw_handler)

    return logger


def run_pytest_benchmark(logger):
    command = [
        sys.executable,
        "-m",
        "pytest",
        "benchmarks/test_splink_50k_synthetic.py",
        "--benchmark-json",
        "benchmarking_results.json",
    ]

    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            logger.info(output.strip())

    rc = process.poll()
    return rc


def upload_file_to_s3(bucket_name, file_name, logger, region_name):
    s3_client = boto3.client("s3", region_name=region_name)
    s3_client.upload_file(file_name, bucket_name, file_name)
    logger.info(f"File '{file_name}' uploaded to bucket '{bucket_name}'.")


if __name__ == "__main__":
    region_name = "eu-west-2"
    bucket = "robinsplinkbenchmarks"
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    logger = setup_cloudwatch_logging()

    # Run pytest benchmark and log its output
    return_code = run_pytest_benchmark(logger)
    if return_code == 0:
        benchmark_file_name = f"benchmarking_results_{current_time}.json"

        # Rename the file to include the timestamp
        os.rename("benchmarking_results.json", benchmark_file_name)

        # Upload the file with the new name
        upload_file_to_s3(bucket, benchmark_file_name, logger, region_name)
    else:
        logger.error("pytest benchmark command failed.")
