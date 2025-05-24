from datetime import datetime
from logger import logger
from downloaders.loader import (
    decline,
    download_photos,
)

class UserPhotoDownloader:
    def __init__(self, user_id, parent_dir, vk, utils):
        self.user_id = int(user_id)
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils

    def get_photos(self):
        photos = []
       
        offset = 0
        while True:
            # Собираем фото с сохраненок
            photos_by_saved = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="saved",
                photo_sizes=True,
                extended=True
            )["items"]

            raw_data = photos_by_saved#photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append({
                    "id": photo["id"],
                    "owner_id": photo["owner_id"],
                    "url": photo["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            logger.info("saved_album getting %s" % len(raw_data))
            if len(raw_data) < 99: #bug with first 100 is 99
                break
            offset += 100

        offset = 0
        while True:
            # Собираем фото с профиля
            photos_by_profile = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="profile",
                photo_sizes=True,
                extended=True
            )["items"]

            raw_data = photos_by_profile#photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append({
                    "id": photo["id"],
                    "owner_id": photo["owner_id"],
                    "url": photo["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            logger.info("profile getting %s" % len(raw_data))
            if len(raw_data) < 100:
                break
            offset += 100

        offset = 0
        while True:
            # Собираем фото со стены
            photos_by_wall = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="wall",
                photo_sizes=True,
                extended=True
            )["items"]

            raw_data = photos_by_wall#photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append({
                    "id": photo["id"],
                    "owner_id": photo["owner_id"],
                    "url": photo["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            logger.info("user_wall getting %s" % len(raw_data))
            if len(raw_data) < 100:
                break
            offset += 100
        
        offset = 0
        while True:
            all_photos = self.vk.photos.getAll(
                owner_id = self.user_id,
                count=100,
                offset=offset,
                photo_sizes=True,
                extended=True
            )["items"]

            raw_data = all_photos#photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append({
                    "id": photo["id"],
                    "owner_id": photo["owner_id"],
                    "url": photo["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            logger.info("getAll getting %s" % len(raw_data))
            if len(raw_data) < 100:
                break
            offset += 100

        return photos

    async def main(self):
        user_info = self.vk.users.get(
            user_ids=self.user_id,
            fields="sex, photo_max_orig"
        )[0]

        decline_username = decline(
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            sex=user_info["sex"]
        )

        username = self.utils.get_username(self.user_id)

        photos_path = self.parent_dir.joinpath(username)
        self.utils.create_dir(photos_path)

        # Страница пользователя удалена
        if "deactivated" in user_info:
            logger.info("Эта страница удалена")
            self.utils.remove_dir(photos_path)
        else:
            # Профиль закрыт
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logger.info(f"Профиль {decline_username} закрыт :(")
                photos = [{
                    "id": self.user_id,
                    "owner_id": self.user_id,
                    "url": user_info["photo_max_orig"],
                    "likes": 0
                }]
            else:
                logger.info(f"Получаем фотографии {decline_username}...")

                # Получаем фотографии пользователя
                photos = self.get_photos()

            # Сортируем фотографии пользователя по дате
            photos.sort(key=lambda k: k["date"], reverse=True)

            # Скачиваем фотографии пользователя
            await download_photos(photos_path, photos)


class UsersPhotoDownloader:
    def __init__(self, user_ids: list, parent_dir, vk, utils):
        self.user_ids = [id for id in user_ids]
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils

    async def main(self):
        for user_id in self.user_ids:
            await UserPhotoDownloader(user_id, self.parent_dir, self.vk, self.utils).main()
