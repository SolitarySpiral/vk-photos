import json
import aiohttp
import aiofiles
import asyncio
import time
import math
from pytils import numeral
from pathlib import Path
from tqdm.asyncio import tqdm
from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker
import yt_dlp
import vk_api

from logger import logger

class Utils:

    def create_dir(self, dir_path: Path):
        if not dir_path.exists():
            dir_path.mkdir()

    def remove_dir(self, dir_path: Path):
        if dir_path.exists():
            dir_path.rmdir()

    def auth_by_token(self, token):
        try:
            vk_session = vk_api.VkApi(
                token=token
            )
            logger.info('Вы успешно авторизовались.')
        except Exception as e:
            logger.info("Неправильный токен")
            logger.info("Токен можно получить здесь https://vkhost.github.io/")
            exit()
        finally:
            return vk_session.get_api()

class Checker:
    def __init__(self, vk = None):
        self.vk = vk

    def check_user_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли пользователь с таким id
            user = self.vk.users.get(user_ids=int(id))
            if len(user) != 0: return True
            return False
        except:
            return False

    def check_user_ids(self, ids_list) -> bool:
        try:
            for user_id in ids_list.split(","):
                if not self.check_user_id(user_id):
                    return False
            return True
        except:
            return False

    def check_group_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли группа с таким id
            group = self.vk.groups.getById(group_id=int(id))
            if len(group) != 0: return True
            return False
        except Exception as e:
            print(e)
            return False

    def check_group_ids(self, ids_list) -> bool:
        try:
            for group_id in ids_list.split(","):
                if not self.check_group_id(group_id):
                    return False
            return True
        except:
            return False

    def check_chat_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли беседа с таким id
            conversation = self.vk.messages.getConversationsById(peer_ids=2000000000 + int(id))
            if conversation["count"] != 0: return True
            return False
        except:
            return False

    def get_user_id(self):
        return self.vk.account.getProfileInfo()["id"]

    def get_username(self, user_id: str):
        user = self.vk.users.get(user_id=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"

    def get_group_title(self, group_id: str):
        group_info = self.vk.groups.getById(group_id=group_id)
        group_name = group_info[0]["name"].replace("/", " ").replace("|", " ").replace(".", " ").strip()
        return group_name

    def get_chat_title(self, chat_id: str) -> str:
        chat_title = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + chat_id
        )["items"][0]["chat_settings"]["title"]
        return chat_title


maker = PetrovichDeclinationMaker()

def decline(first_name, last_name, sex):
    """Возвращает имя и фамилию в родительном падаже."""
    if sex == 1:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.FEMALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.FEMALE, Case.GENITIVE, last_name)
    elif sex == 2:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.MALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.MALE, Case.GENITIVE, last_name)
    return f"{first_name} {last_name}"

def write_json(data, title="data"):
    with open(title + ".json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

async def download_photo(session: aiohttp.ClientSession, photo_url: str, photo_path: Path):
    try:
        if not photo_path.exists():
            async with session.get(photo_url) as response:
                if response.status == 200:
                    async with aiofiles.open(photo_path, "wb") as f:
                        await f.write(await response.read())
    except Exception as e:
        logger.error(e)

async def download_photos(photos_path: Path, photos: list, on_progress=None):
    logger.info("{} {} {}".format(
        numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
        numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
        numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
    ))

    time_start = time.time()

    async with aiohttp.ClientSession() as session:
        futures = []
        for i, photo in enumerate(photos, start=1):
            photo_title = "{}_{}_{}.jpg".format(photo["date"], photo["owner_id"], photo["id"])
            photo_path = photos_path.joinpath(photo_title)
            futures.append(download_photo(session, photo["url"], photo_path))

        for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
            try:
                await future
            except Exception as e:
                logger.error('Got an exception: %s' % e)

    time_finish = time.time()
    download_time = math.ceil(time_finish - time_start)
    logger.info("{} {} за {}".format(
        numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
        numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
        numeral.get_plural(download_time, "секунду, секунды, секунд")
    ))

async def download_video(video_path, video_link):
    ydl_opts = {'outtmpl': '{}'.format(video_path), 'quiet': True, 'retries': 10, 'ignoreerrors': True, 'age_limit': 28}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(video_link)
        logger.info("Видео загружено: %s" % video_link)

async def download_videos(videos_path: Path, videos: list):
    futures = []
    for i, video in enumerate(videos, start=1):
        filename = "{}_{}_{}.mp4".format(video["date"], video["owner_id"], video["id"])
        video_path = videos_path.joinpath(filename)
        futures.append(download_video(video_path, video["player"]))
    logger.info("We will download %s wideos" % len(futures))
    for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
        try:
            await future
        except Exception as e:
            logger.error('Got an exception: %s' % e)