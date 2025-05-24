import tkinter as tk
from tkinter import ttk
import webbrowser
import os
import asyncio
import threading
from pathlib import Path
from logger import logger, get_default_formatter
from gui_logger import TextHandler
from tkinter import filedialog
from config import (
    save_token_to_config,
    load_token_from_config,
    save_download_dir_to_config,
    load_download_dir_from_config,
    open_folder,
)
from downloaders.loader import Utils, Checker
from downloaders.user import UserPhotoDownloader, UsersPhotoDownloader
from downloaders.group import GroupPhotoDownloader, GroupsPhotoDownloader
from downloaders.chat import ChatMembersPhotoDownloader, ChatPhotoDownloader, ChatUserPhotoDownloader

loop = asyncio.get_event_loop()

class App:
    def __init__(self, root:tk.Tk):
        self.root = root  # Сохраняем ссылку на root
        self.root.title("VK Photos Downloader")
        self.root.geometry("800x700")

        self.func_var = tk.IntVar(value=1)
        self.video_var = tk.BooleanVar(value=False)
        self.ids_var = tk.StringVar()
        self.utils = Utils()
        self.checker = Checker()
        self.functions = {
            1: ("Скачать все фотографии пользователя", lambda ids: self.checker.check_user_id(ids), UserPhotoDownloader),
            2: ("Скачать все фотографии нескольких пользователей", lambda ids: self.checker.check_user_ids(ids), UsersPhotoDownloader),
            3: ("Скачать все фотографии из группы и её стены", lambda ids: self.checker.check_group_id(ids), GroupPhotoDownloader),
            4: ("Скачать все фотографии из нескольких групп и их стен", lambda ids: self.checker.check_group_ids(ids), GroupsPhotoDownloader),
            5: ("Скачать все фотографии участников беседы", lambda ids: self.checker.check_chat_id(ids), ChatMembersPhotoDownloader),
            6: ("Скачать все вложения беседы", lambda ids: self.checker.check_chat_id(ids), ChatPhotoDownloader),
            7: ("Скачать все фотографии чата с пользователем", lambda ids: self.checker.check_user_id(ids), ChatUserPhotoDownloader),
        }

        self.create_top_frame()
        self.create_root_dir()
        self.create_main_frame()

    def create_top_frame(self):
        # --- Верхний блок: токен ---
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', padx=10, pady=10)

        def btn_open_token_site():
            webbrowser.open("https://vkhost.github.io/")
            logger.info("Открыт сайт https://vkhost.github.io/")
        open_site_btn = ttk.Button(top_frame, text="Получить токен", command=btn_open_token_site)
        open_site_btn.pack(side='left')

        self.token_entry = ttk.Entry(top_frame, width=80)
        self.token_entry.pack(side='left', padx=5)

        # Подгружаем токен из config.yaml
        self.token = load_token_from_config()
        if self.token:
            self.token_entry.insert(0, self.token)
            logger.info("Токен загружен из config.yaml")

        def btn_save_token():
            self.token = self.token_entry.get().strip()
            if self.token:
                save_token_to_config(self.token)
                logger.info("Токен сохранён в config.yaml")
            else:
                logger.warning("Пустое поле: токен не сохранён")
        save_btn = ttk.Button(top_frame, text="Сохранить", command=btn_save_token)
        save_btn.pack(side='left', padx=2)
        
        def btn_clear_token():
            self.token_entry.delete(0, 'end')
            logger.info("Поле токена очищено")
        clear_btn = ttk.Button(top_frame, text="Очистить", command=btn_clear_token)
        clear_btn.pack(side='left', padx=2)
        
    def create_root_dir(self):
        # --- Поле выбора корневой директории ---
        self.dir_frame = ttk.Frame(self.root)
        self.dir_frame.pack(fill='x', padx=10, pady=5)

        dir_label = ttk.Label(self.dir_frame, text="Корневая папка:")
        dir_label.pack(side='left')

        self.dir_var = tk.StringVar()
        dir_entry = ttk.Entry(self.dir_frame, textvariable=self.dir_var, width=80)
        dir_entry.pack(side='left', padx=5)

        def btn_choose_directory():
            folder = filedialog.askdirectory()
            if folder:
                self.dir_var.set(folder)
                save_download_dir_to_config(folder)
                logger.info(f"Корневая папка выбрана: {folder}")
                self.load_folders()
        choose_button = ttk.Button(self.dir_frame, text="Выбрать папку", command=btn_choose_directory)
        choose_button.pack(side='left')

    def create_log_footer(self):
        # self.status_var = tk.StringVar(value="Ожидание")
        # self.status_label = ttk.Label(self.root, textvariable=self.status_var, foreground="blue")
        # self.status_label.pack(pady=10)
        # --- Лог-поле (внизу)---
        log_label = ttk.Label(self.root, text="Лог выполнения программы:")
        log_label.pack(anchor='w', padx=10, pady=(10, 0))

        log_text = tk.Text(self.root, height=10, state='disabled', bg='black', fg='lime')
        log_text.pack(fill='both', expand=True, padx=10, pady=5)
        # --- Подключаем лог в GUI через TextHandler ---
        text_handler = TextHandler(log_text)
        text_handler.setFormatter(get_default_formatter())  # <-- из logger.py, без logging
        logger.addHandler(text_handler)

    def create_main_frame(self):
        # --- Основной фрейм с тремя блоками ---
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.create_log_footer()
        self.create_left_block(main_frame)
        self.create_middle_block(main_frame)


        # Загружаем путь при старте
        initial_dir = load_download_dir_from_config()
        if initial_dir:
            self.dir_var.set(initial_dir)
            logger.info("Корневая папка загружена из config.yaml")
            self.load_folders()

    def create_left_block(self, main_frame):
        left_frame = ttk.LabelFrame(main_frame, text="Загрузчик", width=150)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)

        # Вложенный фрейм для кнопок (горизонтально)
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=0, column=0, sticky='w', padx=5, pady=5)

        btn_auth = ttk.Button(button_frame, text="Авторизоваться по токену", command=self.token_auth_btn)
        btn_auth.grid(row=0, column=0, padx=(0, 5))  # немного отступ справа

        def open_what_vk_id_site():
            webbrowser.open("https://regvk.com/id/")
            logger.info("Открыт сайт https://regvk.com/id/")
        btn_what_id = ttk.Button(button_frame, text="Узнать id страницы или группы VK", command=open_what_vk_id_site)
        btn_what_id.grid(row=0, column=1)

        frame = ttk.LabelFrame(left_frame, text="Выберите функцию", width= 150)
        frame.grid(row=1, column=0, sticky='ew', padx=5, pady=10)
        for key, (label, _, _) in self.functions.items():
            #logger.info(f"Создаю кнопки с ключами {key}, {label}")
            ttk.Radiobutton(frame, text=label, variable=self.func_var, value=key).pack(anchor="w")

        ttk.Label(frame, text="Введите ID (через запятую без пробела, если их несколько):").pack()
        self.ids_entry = ttk.Entry(frame, textvariable=self.ids_var, width=60)
        self.ids_entry.pack()

        video_frame = ttk.LabelFrame(frame, text="Скачивать видео")
        video_frame.pack(side="left", padx=5)
        ttk.Radiobutton(video_frame, text="Нет", variable=self.video_var, value=False).pack(anchor="w")
        ttk.Radiobutton(video_frame, text="Да", variable=self.video_var, value=True).pack(anchor="w")

        ttk.Button(frame, text="Старт", command=self.start_process).pack(pady=10)

    def token_auth_btn(self):
        try:
            self.vk = self.utils.auth_by_token(self.token)
            self.checker = Checker(self.vk)
        except Exception as e:
            logger.error(f"Не могу авторизироваться токеном, его либо нет, либо просрочен. Код ошибки:{e}")

    def start_process(self):
        func_key = self.func_var.get()
        ids = self.ids_var.get().strip()
        download_video = self.video_var.get()
        root_dir = Path(self.dir_var.get())

        try:
            label, check_func, loader_class = self.functions[func_key]
        except KeyError:
            logger.error("Ошибка", "Неверная функция")
            return

        logger.info(f"Запущено {label} для ID: {ids}, видео: {download_video}")

        
        # Валидация
        if check_func(ids):
            downloader = loader_class(ids, root_dir, self.vk, self.utils, download_video)
            def run_async():
                loop.run_until_complete(downloader.main())
                #asyncio.run(downloader.main())  # запускается в фоновом потоке
            threading.Thread(target=run_async, daemon=True).start()
        else:
            logger.error(f"Пользователь/группа/беседа с такими ID {ids} не существуют")
            return
        
    def update_progress(self, current, total):
        self.status_var.set(f"Загружено: {current} / {total}")
        self.root.update_idletasks()

    def create_middle_block(self, main_frame):
        # Блок 2: список папок
        folders_frame = ttk.Frame(main_frame, borderwidth=1, relief="solid")
        folders_frame.pack(side="left", fill="y", padx=(0, 5))

        folders_label = ttk.Label(folders_frame, text="Папки")
        folders_label.pack(anchor="w", padx=5, pady=(5, 0))

        self.folders_listbox = tk.Listbox(folders_frame, height=20, width=60)
        self.folders_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.folders_listbox.bind("<<ListboxSelect>>", self.on_folder_select)
    
    def on_folder_select(self, event):
        sel = self.folders_listbox.curselection()
        if not sel:
            return
        name = self.folders_listbox.get(sel[0])
        full_path = os.path.join(self.dir_var.get(), name)
        logger.info(f"Открываем папку: {full_path}")
        open_folder(full_path)

    def load_folders(self):
        """Заполняем Listbox папками из выбранной директории."""
        self.folders_listbox.delete(0, tk.END)
        root_path = self.dir_var.get()
        if os.path.isdir(root_path):
            for name in sorted(os.listdir(root_path)):
                full_path = os.path.join(root_path, name)
                if os.path.isdir(full_path):
                    self.folders_listbox.insert(tk.END, name)
            logger.info("Список папок обновлён")
        else:
            logger.warning("Неверная папка")



if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()