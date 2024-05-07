import asyncio
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import quote

import aiofiles
import httpx
from rich.table import Table
from rich.traceback import install as traceback_install

from console import Halo
from richlib import rconsole, rprompt

from .constant import (
    BASE_URL,
    BEEN_BLOCK,
    CREATING_PROBLEM,
    TIMEOUT,
    TOKEN_FILE,
    TOO_VAGUE,
    UNSAFE_IMAGE,
    USER_AGENT,
)

traceback_install(theme="fruity")


class BingDalle:
    def __init__(self, auth_cookie, out_directory, update_config):
        self.sub_directory = None
        self.update_config = update_config
        self.auth_cookie, self.out_directory = self._load_config(
            auth_cookie, out_directory
        )
        self.headers = {
            "User-Agent": USER_AGENT,
            "Cookie": f"_U={self.auth_cookie}",
        }
        self.client = httpx.AsyncClient(
            base_url=BASE_URL, headers=self.headers, timeout=TIMEOUT
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    def _load_config(self, auth_cookie, out_directory):
        try:
            with open(TOKEN_FILE, "r") as file:
                config = json.load(file)
            if self.update_config:
                return self._extracted_from_load_config(
                    auth_cookie, out_directory, config
                )
            if "_U" in config and "out_directory" in config:
                rconsole.print(
                    "\n:white_heavy_check_mark: Cookie and directory paths are found!\n"
                )
                return config.get("_U"), config.get("out_directory")
        except FileNotFoundError:
            return self._handle_file_not_found(auth_cookie, out_directory)

    def _handle_file_not_found(self, auth_cookie, out_directory):
        if auth_cookie:
            return self._save_and_return_config(auth_cookie, out_directory)
        rconsole.print(
            "\n:x: [red1]The cookie is not found! [yellow1]Insert it manually..[/]"
        )
        auth_cookie = rprompt.ask("Enter your '[blue]_U[/]' value")
        return self._save_and_return_config(auth_cookie, out_directory)

    def _save_and_return_config(self, auth_cookie, out_directory):
        self._save_config_to_file({"_U": auth_cookie, "out_directory": out_directory})
        return auth_cookie, out_directory

    def _extracted_from_load_config(self, auth_cookie, out_directory, config):
        updates = {}
        if auth_cookie:
            updates["_U"] = auth_cookie
        if out_directory:
            updates["out_directory"] = out_directory
        if updates:
            config.update(updates)
            rconsole.print(
                "\n:white_heavy_check_mark: The configuration has been updated!"
            )
        self._save_config_to_file(config)
        return config.get("_U"), config.get("out_directory")

    def _save_config_to_file(self, config):
        with open(TOKEN_FILE, "w") as file:
            json.dump(config, file, indent=4)

        rconsole.print(
            "\n:white_heavy_check_mark: [green1]The config file has been saved successfully![/]\n"
        )

    def _print_status(self, status, success_message=None, failure_message=None):
        if not status:
            return

        if success_message:
            status.succeed(success_message)
        elif failure_message:
            status.fail(failure_message)
            sys.exit()

    def _get_response_reason(self, status_code):
        return f"{httpx.codes.get_reason_phrase(status_code)} ({status_code})"

    async def _get_coins(self):
        with Halo("Authenticating cookies..") as status:
            response = await self.client.get("/images/create")
            status_code = response.status_code
            if response.is_success:
                self._print_status(
                    status,
                    success_message=f"Auth cookie status: {self._get_response_reason(status_code)}",
                )
                if not (
                    coins_match := re.search(r'coins available">(\d+)<', response.text)
                ):
                    self._print_status(
                        status,
                        failure_message="Failed to retrieve available coins, perhaps something went wrong with the cookie.",
                    )
                return coins_match[1]
            else:
                self._print_status(
                    status,
                    failure_message=f"Auth cookie status: {self._get_response_reason(status_code)}",
                )

    async def _poll_results(self, prompt, request_id):
        encoded_prompt = quote(prompt)
        result_url = f"/images/create/async/results/{request_id}?q={encoded_prompt}"
        while True:
            with Halo("Generating image..") as status:
                response = await self.client.get(result_url)
                status_code = response.status_code
                if response.is_success:
                    self._print_status(
                        status,
                        success_message=f"Generating image status: {self._get_response_reason(status_code)}",
                    )
                    if "gir_async" in response.text:
                        return response
                    await self._waiting_time(5)
                else:
                    self._print_status(
                        status,
                        failure_message=f"Generating image status: {self._get_response_reason(status_code)}",
                    )

    async def _waiting_time(self, sleep):
        for i in range(sleep):
            rconsole.print(f"Generating image in {(sleep-i)} seconds", end="\r")
            await asyncio.sleep(1)

    def _construct_url(self, coins, prompt):
        with Halo("Constructing url..") as status:
            encoded_prompt = quote(prompt)
            rt_value = "4" if int(coins) > 0 else "3"
            self._print_status(status, success_message=f"RT value: {rt_value}")
            return f"/images/create?q={encoded_prompt}&rt={rt_value}&FORM=GENCRE"

    async def _get_request_id(self, prompt, post_url):
        with Halo("Getting ID..") as status:
            data = {"q": prompt, "qs": "ds"}
            response = await self.client.post(
                post_url, data=data, follow_redirects=True
            )
            status_code = response.status_code
            if response.is_success:
                self._print_status(
                    status,
                    success_message=f"Getting ID status: {self._get_response_reason(status_code)}",
                )

                error_messages = [BEEN_BLOCK, TOO_VAGUE, CREATING_PROBLEM, UNSAFE_IMAGE]
                for error_message in error_messages:
                    if error_message in response.text:
                        self._print_status(status, failure_message=error_message)

                if not (request_id := re.search(r"id=([^&]+)", str(response.url))):
                    self._print_status(
                        status, failure_message="The request ID is not found!"
                    )

                return request_id[1]
            else:
                self._print_status(
                    status,
                    failure_message=f"Getting ID status: {self._get_response_reason(status_code)}",
                )

    def _save_result_to_json(self, filename, result):
        with open(filename, "w") as file:
            json.dump(result, file, indent=4)

    def _setup_table(self, result):
        table = Table(
            title="Image Generation Result",
            title_style="dodger_blue2",
            header_style="yellow",
        )
        table.add_column("Prompt", style="blue1", justify="center")
        table.add_column("Boosts", style="blue", justify="center")
        table.add_column("Images URL", style="blue_violet", justify="center")

        for i, image in enumerate(result.get("images", []), start=1):
            table.add_row(
                result["prompt"] if i == 1 else "",
                result["boosts"] if i == 1 else "",
                image["url"],
            )

        rconsole.print()
        rconsole.print(table)
        rconsole.print()

    def _handle_poll_result(self, poll_results, prompt, coins):
        src_urls = list(
            {
                url.split("?w=")[0]
                for url in re.findall(r'src="([^"]+)"', poll_results.text)
                if url.startswith(("http", "https")) and url.endswith("ImgGn")
            }
        )
        return {
            "prompt": prompt,
            "boosts": f"{coins} remaining",
            "images": [{"url": src_url} for src_url in src_urls],
        }

    def _handle_directory(self):
        date_time = datetime.now().strftime("%d%m%Y-%I%M%S%p")
        json_file = f"{date_time}.json"

        default_folder = "Downloaded Images"
        base_directory = (
            os.path.join(self.out_directory, default_folder)
            if self.out_directory
            else default_folder
        )

        os.makedirs(base_directory, exist_ok=True)
        self.sub_directory = os.path.join(base_directory, date_time)
        os.makedirs(self.sub_directory, exist_ok=True)
        return os.path.join(self.sub_directory, json_file)

    async def generate_images(self, prompt):
        coins = await self._get_coins()
        post_url = self._construct_url(coins, prompt)
        request_id = await self._get_request_id(prompt, post_url)
        poll_results = await self._poll_results(prompt, request_id)
        result = self._handle_poll_result(poll_results, prompt, coins)
        self._setup_table(result)
        filename = self._handle_directory()
        self._save_result_to_json(filename, result)
        return result

    async def save_image_to_file(self, img_url):
        filename = os.path.join(
            self.sub_directory, f"{img_url.split('OIG')[-1][3:]}.png"
        )
        async with aiofiles.open(filename, "wb") as file:
            with Halo("Saving image to file..") as status:
                response = await self.client.get(img_url)
                status_code = response.status_code
                if response.is_success:
                    self._print_status(
                        status,
                        success_message=f"Saving image status: {self._get_response_reason(status_code)}",
                    )
                    await file.write(response.content)
                else:
                    self._print_status(
                        status,
                        failure_message=f"Saving image status: {self._get_response_reason(status_code)}",
                    )
