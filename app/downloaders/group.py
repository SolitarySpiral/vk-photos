from datetime import datetime
from logger import logger
from downloaders.loader import (
    download_photos,
    download_videos
)
from filter import check_for_duplicates

class GroupPhotoDownloader:
    def __init__(self, group_id: str, parent_dir, vk, utils, download_videos = False):
        self.group_id = int(group_id)
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils
        self.download_videos = download_videos

    async def get_photos(self):

        offset = 0
        while True:
            posts = self.vk.wall.get(
                owner_id=-self.group_id,
                count=100,
                offset=offset
            )["items"]
            for post in posts:

                # Пропускаем посты с рекламой
                if post["marked_as_ads"]:
                    continue

                # Если пост скопирован с другой группы
                if "copy_history" in post:
                    if "attachments" in post["copy_history"][0]:
                        self.get_single_post(post["copy_history"][0])

                elif "attachments" in post:
                    self.get_single_post(post)

            logger.info("wall getting %s" % len(posts))
            if len(posts) < 100:
                break
            offset += 100
        
        offset = 0
        while True:
            all_photos = self.vk.photos.getAll(
                owner_id=-self.group_id,
                extended=True,
                count=100,
                offset=offset
            )["items"]

            raw_data = all_photos#photos_by_wall + photos_by_profile
            logger.info("getAll getting %s" % len(raw_data))
            for photo in raw_data:
                self.photos.append({
                    "id": photo["id"],
                    "owner_id": photo["owner_id"],
                    "url": photo["sizes"][-1]["url"],
                    "date": datetime.fromtimestamp(int(photo["date"])).strftime('%Y-%m-%d %H-%M-%S')
                })
            #logging.info("getAll getting %s" % len(raw_data))
            if len(raw_data) < 100:
                break
            offset += 100

        if self.download_videos == "1":
            logger.info("Получаем список видео")
            offset = 0
            while True:
                videos = self.vk.video.get(
                    owner_id=-self.group_id,
                    count=100,
                    offset=offset
                )["items"]
                for video in videos:
                    if "player" in video:
                        self.videos_list.append({
                            "type": video.get("type"),
                            "id": video.get("id"),
                            "owner_id": video.get("owner_id"),
                            "title": video.get("title"),
                            "player": video.get("player"),
                            "date": datetime.fromtimestamp(int(video.get("date"))).strftime('%Y-%m-%d %H-%M-%S')
                        })

                if len(videos) < 100:
                    logger.info("Videos got %s" % len(self.videos_list))
                    break

                offset += 100

    def get_single_post(self, post: dict):
        """
        Проходимся по всем вложениям поста и отбираем только картинки
        """
        try:
            for i, attachment in enumerate(post["attachments"]):
                if attachment["type"] == "photo":
                    file_type = attachment["type"]
                    photo_id = post["attachments"][i]["photo"]["id"]
                    owner_id = post["attachments"][i]["photo"]["owner_id"]
                    photo_url = post["attachments"][i]["photo"]["sizes"][-1].get("url")
                    if photo_url != None or photo_url != '':
                        self.photos.append({
                            "type": file_type,
                            "id": photo_id,
                            "owner_id": -owner_id,
                            "url": photo_url,
                            "date": datetime.fromtimestamp(int(post["attachments"][i]["photo"]["date"])).strftime('%Y-%m-%d %H-%M-%S')
                        })
        except Exception as e:
            logger.error(e)

    async def main(self):
        # Получаем информацию о группе
        group_info = self.vk.groups.getById(group_id=self.group_id)[0]
        group_name = group_info["name"].replace("/", " ").replace("|", " ").replace(".", " ").strip()

        group_dir = self.parent_dir.joinpath(group_name)
        self.utils.create_dir(group_dir)

        self.photos = []
        self.videos_list = []

        # Группа закрыта
        if group_info["is_closed"]:
            logger.info(f"Группа '{group_name}' закрыта :(")
            self.photos = [{
                "id": self.group_id,
                "owner_id": self.group_id,
                "url": "https://vk.com/images/community_200.png"
            }]
        else:
            if self.download_videos:
                logger.info(f"Получаем фотографии и видео группы '{group_name}'...")
                await self.get_photos()
                
                # Скачиваем фотографии со стены группы
                await download_photos(group_dir, self.photos, on_progress=None)

                logger.info("Скачиваем видео")
                await download_videos(group_dir, self.videos_list)

            else:
                logger.info(f"Получаем фотографии группы '{group_name}'...")
                await self.get_photos()

                # Скачиваем фотографии со стены группы
                await download_photos(group_dir, self.photos)

        logger.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(group_dir)
        logger.info(f"Дубликатов удалено: {dublicates_count}")

        logger.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class GroupsPhotoDownloader:
    def __init__(self, group_ids: str, parent_dir, vk, utils, download_videos = False):
        self.group_ids = [int(id.strip()) for id in group_ids.split(",")]
        self.parent_dir = parent_dir
        self.vk = vk
        self.utils = utils
        self.download_videos = download_videos

    async def main(self):
        for group_id in self.group_ids:
            await GroupPhotoDownloader(group_id, self.parent_dir, self.vk, self.utils, self.download_videos).main()
