import asyncio
import os
from argparse import ArgumentParser

from richlib import rconsole, rprompt

from .api import BingDalle


async def main():
    rconsole.clear()

    parser = ArgumentParser(description="Generate images with Bing Image Creator")
    parser.add_argument("prompt", default=None, type=str, nargs="?", help="Your prompt")
    parser.add_argument(
        "-c",
        "--auth_cookie",
        default=None,
        type=str,
        help="Your '_U' cookie value",
    )
    parser.add_argument(
        "-o",
        "--out_directory",
        default=os.getcwd(),
        type=str,
        help="Your downloaded images folder path",
    )
    parser.add_argument(
        "-uc",
        "--update_config",
        action="store_true",
        help="Update the configuration file",
    )
    args = parser.parse_args()

    update_config = args.update_config

    auth_cookie = args.auth_cookie
    # By default 'auth_cookie' is set to None, it will prompt the user to enter the cookie value.
    # └── The cookie will be saved to a JSON file automatically.
    # └── Once set, it will be loaded automatically and reused. There is no need to set 'auth_cookie' again for the next uses.

    out_directory = args.out_directory
    # By default 'out_directory' is set to current project directory, it will save downloaded images in the current project directory.
    # The default folder name is 'Downloaded Images'.

    # Set the different out_directory
    # Example:
    # └── out_directory = r"C:\Users\YOUR_USER_ACCOUNT_NAME\Desktop"
    #     └── It will create the folder on the Desktop.
    #     └── Once set, it will be saved to JSON file and reused. There is no need to set 'out_directory' again for the next uses.
    #     └── If you want to change a path, you can set a new path by overwriting it.

    prompt = args.prompt or rprompt.ask("Your prompt")

    async with BingDalle(
        auth_cookie=auth_cookie,
        out_directory=out_directory,
        update_config=update_config,
    ) as bing:
        img_urls = await bing.generate_images(prompt)
        img_files = [
            bing.save_image_to_file(img_url["url"]) for img_url in img_urls["images"]
        ]
        await asyncio.gather(*img_files)


if __name__ == "__main__":
    asyncio.run(main())
