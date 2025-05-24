from datetime import datetime
import requests
from logger import logger
from downloaders.loader import (
    download_photos,
)
from downloaders.user import UsersPhotoDownloader
from filter import check_for_duplicates

class ChatMembersPhotoDownloader:
    def __init__(self, chat_id: str, parent_dir, vk, utils):
        self.chat_id = int(chat_id)
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils

    async def main(self):
        chat_title = self.utils.get_chat_title(self.chat_id)
        chat_path = self.parent_dir.joinpath(chat_title)

        # Создаём папку с фотографиями участников беседы, если её не существует
        self.utils.create_dir(chat_path)

        members = self.vk.messages.getChat(
            chat_id=self.chat_id
        )["users"]

        if members == []:
            logger.info("Вы вышли из этой беседы")
            self.utils.remove_dir(chat_path)
        else:
            members_ids = []

            for member_id in members:
                if member_id > 0:
                    members_ids.append(member_id)

            members_ids.remove(self.utils.get_user_id())

            await UsersPhotoDownloader(user_ids=members_ids, parent_dir=chat_path, vk=self.vk, utils=self.utils).main()


class ChatPhotoDownloader:
    def __init__(self, chat_id: str, parent_dir, vk, utils):
        self.chat_id = int(chat_id)
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils

    def download_chat_photo(self):
        """
        Скачиваем аватарку беседы если она есть
        """
        if "photo" in self.chat:
            sizes = self.chat["photo"]
            max_size = list(sizes)[-2]
            photo_url = sizes[max_size]
            photo_path = self.chat_dir.joinpath("Аватарка беседы.png")

            response = requests.get(photo_url)
            if response.status_code == 200:
                with open(photo_path, mode="wb") as f:
                    f.write(response.content)

    def get_attachments(self):
        raw_data = self.vk.messages.getHistoryAttachments(
            peer_id=2000000000 + self.chat_id,
            media_type="photo"
        )["items"]

        photos = []

        for photo in raw_data:
            photos.append({
                "id": photo["attachment"]["photo"]["id"],
                "owner_id": photo["attachment"]["photo"]["owner_id"],
                "url": photo["attachment"]["photo"]["sizes"][-1]["url"],
                "date": datetime.fromtimestamp(int(photo["attachment"]["photo"]["date"])).strftime('%Y-%m-%d %H-%M-%S')
            })

        return photos

    async def main(self):
        chat_title = self.utils.get_chat_title(self.chat_id)
        photos_path = self.parent_dir.joinpath(chat_title)
        if not photos_path.exists():
            logger.info(f"Создаём папку с фотографиями беседы '{chat_title}'")
            photos_path.mkdir()

        photos = self.get_attachments()

        # Скачиваем вложения беседы
        await download_photos(photos_path, photos)

        logger.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logger.info(f"Дубликатов удалено: {dublicates_count}")

        logger.info(f"Итого скачено: {len(photos) - dublicates_count} фото")


class ChatUserPhotoDownloader:
    def __init__(self, chat_id: str, parent_dir, vk, utils):
        self.chat_id = int(chat_id)
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils

    def get_attachments(self):
        
        photos = []
        offset = 0
        while True:
            raw_data = self.vk.messages.getHistoryAttachments(
                peer_id=self.chat_id,
                count=200,
                offset=offset,
                media_type="photo"
            )["items"]

            for photo in raw_data:
                photos.append({
                    "id": photo["attachment"]["photo"]["id"],
                    "owner_id": photo["attachment"]["photo"]["owner_id"],
                    "url": photo["attachment"]["photo"]["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["attachment"]["photo"]["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            logger('attachments getting {}'.format(len(raw_data)))
            if len(raw_data) < 200:
                break
            offset += 200

        return photos
    
    async def main(self):
        username = self.utils.get_username(self.chat_id)

        photos_path = self.parent_dir.joinpath(f"Переписка {username}")
        self.utils.create_dir(photos_path)

        photos = self.get_attachments()

        await download_photos(photos_path, photos)

        logger.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logger.info(f"Дубликатов удалено: {dublicates_count}")

        logger.info(f"Итого скачено: {len(photos) - dublicates_count} фото")
