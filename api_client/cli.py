"""CLI for running a list of urls through the Chrome User Experience Report API"""

import csv
import os
import random

import click
from dotenv import load_dotenv, find_dotenv

from api_client.crux_api_client import CruxAPIClient, NotFoundException
from api_client.token_bucket import TokenBucket

load_dotenv(find_dotenv())


def format_results(results):
    """Format results for csv file"""
    metrics = results["record"]["metrics"]

    data = [
        results["record"]["key"]["url"],
        metrics.get("experimental_time_to_first_byte", {})
        .get("percentiles", {})
        .get("p75", None),
        metrics.get("first_contentful_paint", {})
        .get("percentiles", {})
        .get("p75", None),
        metrics.get("largest_contentful_paint", {})
        .get("percentiles", {})
        .get("p75", None),
        metrics.get("cumulative_layout_shift", {})
        .get("percentiles", {})
        .get("p75", None),
        metrics.get("interaction_to_next_paint", {})
        .get("percentiles", {})
        .get("p75", None),
    ]

    return data


@click.command()
@click.option(
    "--input-urls", "-i", required=True, help="Input URL or file containing URLs."
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    help="Output file to write responses (prints to console if not provided).",
)
@click.option(
    "--api-key",
    "-k",
    default=os.getenv("GOOGLE_API_KEY_CRUX"),
    help="API key for requests (reads from .env if not provided).",
)
@click.option(
    "--sample-rate",
    "-s",
    default=1.0,
    type=float,
    help="Sample rate to fetch URLs (0 < sample-rate <= 1).",
)
def fetch_urls(input_urls=None, output_file=None, api_key=None, sample_rate=None):
    """
    CLI tool to fetch URLs from a file or CLI arg and save or print the responses.
    """
    if not api_key:
        click.echo("API key is required. Provide it via --api-key or in a .env file.")
        return

    token_bucket = TokenBucket(rate_limit=10, refill_time=5)
    crux_api_client = CruxAPIClient(api_key)

    # Determine if input_urls is a single URL or a file
    if os.path.exists(input_urls):
        with open(input_urls, "r", encoding="utf8") as infile:
            urls = infile.read().splitlines()
    else:
        urls = [input_urls]

    if len(urls) > 1:
        urls = random.sample(urls, int(len(urls) * sample_rate))

    needs_header = True

    # Fetch each URL
    for index, url in enumerate(urls):
        click.echo(f"{index} - Fetching data for {url}")
        try:
            response_data = token_bucket.execute(
                crux_api_client.get_url(
                    url,
                    {
                        "formFactor": "PHONE",
                    },
                )
            )
            if response_data.get("record") is None:
                continue

            click.echo(response_data)
            if output_file:
                with open(output_file, mode="a", newline="", encoding="utf8") as file:
                    writer = csv.writer(file)
                    if needs_header:
                        writer.writerow(
                            [
                                "url",
                                "time_to_first_byte_p75",
                                "first_contentful_paint_p75",
                                "largest_contentful_paint_p75",
                                "cumulative_layout_shift_p75",
                                "interaction_to_next_paint_p75",
                            ]
                        )
                        needs_header = False
                    writer.writerow(format_results(response_data))
            else:
                click.echo(response_data)

        except NotFoundException as e:
            click.echo(f"Failed to fetch {url}: {e}")


if __name__ == "__main__":
    fetch_urls()
