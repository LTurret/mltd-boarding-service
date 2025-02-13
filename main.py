import aiohttp
import argparse
import asyncio
import json
import os

from src.fetch import GetNewest, Search, FetchBorder, FetchCover
from src.make import makefile
from src.image import makeimg

parser = argparse.ArgumentParser(
    description="Generator that fetches hosting event information and border datasets then generates border image."
)
parser.add_argument("-O", "--output_path", nargs=1, type=str, metavar="",
                    required=False,
                    default="image",
                    help='Image generate output path, default is "./image"'
                )
parser.add_argument("-T", "--output_type", nargs="+", type=str, metavar="",
                    required=False,
                    help="Select fetches border type",
                    choices=["pt", "hs", "lp"],
                    default=["pt"]
                )
parser.add_argument("-I", "--identify", nargs=1, type=int, metavar="",
                    required=False,
                    default=[0],
                    help="Search specific event with unique ID"
                )
parser.add_argument("-C", "--caching", nargs="+", type=bool, metavar="",
                    required=False,
                    default=False,
                    help="Enable saving json file in the directory."
                )
group = parser.add_mutually_exclusive_group()
group.add_argument("--dryrun",
                    action="store_true",
                    help="Not generates image but generates dataset, fetching dataset from API, used for testing dataset"
                )
group.add_argument("--checksum",
                    action="store_true",
                    help="Not generates image and dataset, used for testing API correspondence"
                )
group.add_argument("--static",
                    action="store_true",
                    help="Not generates dataset but generates image using local dataset, will not fetching from API"
)
opt = parser.parse_args()

async def main(output_path, output_type, identify, caching, checksum, dryrun, static):

    check_identified = lambda identify: True if (identify is not None and type(identify) is int and identify > 0) else False
    # identify_maximun = lambda identify, idmax: True if (identify is not None and identify > idmax) else 2
    matchtype = lambda typecode: ([3, 4, 5, 11, 13, 16].count(typecode)) == 1
    border_exists = lambda file: True if (len(file) > 0) else False
    early_announcement = lambda message: True if (len(message) > 0) else False

    announcement = ""
    border_data = None
    event_data = {}
    tasks = []

    if not static:
        async with aiohttp.ClientSession() as session:
            event_data = await GetNewest(session)

            if check_identified(identify[0]):
                event_data = await Search(identify[0], session)

            identify = event_data["id"]

            if matchtype(event_data["type"]):
                border_data = await FetchBorder(identify, session)
            else:
                announcement = "This is an inborderable event."
    else:
        with open("./dataset/information.json", "r", encoding="utf-8") as information:
            event_data = json.load(information)
        with open("./dataset/border.json", "r", encoding="utf-8") as border:
            border_data = json.load(border)

    if checksum:
        announcement = "checksum complete."
    elif early_announcement(announcement):
        pass
    else:

        if not os.path.isdir("./data"):
            os.mkdir("./data")

        os.chdir("./data")
        tasks = [
            asyncio.create_task(makefile(event_data, "information"))
        ]

        if border_exists(border_data):
            tasks.append(asyncio.create_task(makefile(border_data, "border")))

        await asyncio.gather(*tasks)
        os.chdir("../")

        if dryrun:
            announcement = "dryrun complete."
        else:

            if not os.path.isdir(output_path):
                os.mkdir(output_path)
            tasks = []
            for category in output_type:
                tasks.append(makeimg(category, output_path))
            await asyncio.gather(*tasks)
        
        if not caching:
            os.chdir("data")
            for file in os.listdir():
                os.remove(file)
            os.chdir("../")
            os.rmdir("data")

    print(announcement)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(opt.output_path, opt.output_type, opt.identify, opt.caching, opt.checksum, opt.dryrun, opt.static))
