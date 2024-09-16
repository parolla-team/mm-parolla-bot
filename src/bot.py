import sys
import aiofiles.os
from mattermostautodriver import AsyncDriver
from typing import Optional
import json
import asyncio
import re
import os
from pathlib import Path
from gptbot import Chatbot
from log import getlogger
import httpx
import imagegen
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from prompt import tutor_prompt_template, WELCOME_MESSAGE
import requests

TOKEN_THRESHOLD_HISTORY = 50000
TOKEN_THRESHOLD_USER_MESSAGE = 10000
logger = getlogger()


class Bot:
    def __init__(
        self,
        server_url: str,
        username: str,
        port: Optional[int] = 443,
        scheme: Optional[str] = "https",
        openai_api_key: Optional[str] = None,
        gpt_api_endpoint: Optional[str] = None,
        gpt_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        reply_count: Optional[int] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        image_generation_endpoint: Optional[str] = None,
        image_generation_backend: Optional[str] = None,
        image_generation_size: Optional[str] = None,
        sdwui_steps: Optional[int] = None,
        sdwui_sampler_name: Optional[str] = None,
        sdwui_cfg_scale: Optional[float] = None,
        image_format: Optional[str] = None,
        timeout: Optional[float] = 120.0,
    ) -> None:
        if server_url is None:
            raise ValueError("server url must be provided")

        if port is None:
            self.port = 443
        else:
            port = int(port)
            if port <= 0 or port > 65535:
                raise ValueError("port must be between 0 and 65535")
            self.port = port

        if scheme is None:
            self.scheme = "https"
        else:
            if scheme.strip().lower() not in ["http", "https"]:
                raise ValueError("scheme must be either http or https")
            self.scheme = scheme

        if image_generation_endpoint and image_generation_backend not in [
            "openai",
            "sdwui",
            "localai",
            None,
        ]:
            logger.error("image_generation_backend must be openai or sdwui or localai")
            sys.exit(1)

        if image_format not in ["jpeg", "png", None]:
            logger.error("image_format should be jpeg or png, leave blank for jpeg")
            sys.exit(1)

        # @chatgpt
        if username is None:
            raise ValueError("username must be provided")
        else:
            self.username = username

        self.openai_api_key: str = openai_api_key
        self.gpt_api_endpoint = (
            gpt_api_endpoint or "https://api.openai.com/v1/chat/completions"
        )
        self.gpt_model: str = gpt_model or "gpt-3.5-turbo"
        self.max_tokens: int = max_tokens or 4000
        self.top_p: float = top_p or 1.0
        self.temperature: float = temperature or 0.8
        self.presence_penalty: float = presence_penalty or 0.0
        self.frequency_penalty: float = frequency_penalty or 0.0
        self.reply_count: int = reply_count or 1
        self.system_prompt: str = (
            system_prompt
            or "You are ChatGPT, \
            a large language model trained by OpenAI. Respond conversationally"
        )
        self.image_generation_endpoint: str = image_generation_endpoint
        self.image_generation_backend: str = image_generation_backend

        if image_format:
            self.image_format: str = image_format
        else:
            self.image_format = "jpeg"

        if image_generation_size is None:
            self.image_generation_size = "512x512"
            self.image_generation_width = 512
            self.image_generation_height = 512
        else:
            self.image_generation_size = image_generation_size
            self.image_generation_width = self.image_generation_size.split("x")[0]
            self.image_generation_height = self.image_generation_size.split("x")[1]

        self.sdwui_steps = sdwui_steps
        self.sdwui_sampler_name = sdwui_sampler_name
        self.sdwui_cfg_scale = sdwui_cfg_scale

        self.timeout = timeout or 120.0

        self.bot_id = None

        self.base_path = Path(os.path.dirname(__file__)).parent

        if not os.path.exists(self.base_path / "images"):
            os.mkdir(self.base_path / "images")

        #  httpx session
        self.httpx_client = httpx.AsyncClient()

        # initialize Chatbot object
        self.chatbot = Chatbot(
            aclient=self.httpx_client,
            api_key=self.openai_api_key,
            api_url=self.gpt_api_endpoint,
            engine=self.gpt_model,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            reply_count=self.reply_count,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
        )

        self.driver = AsyncDriver(
            {
                "token": os.getenv("TOKEN"),
                "url": server_url,
                "port": self.port,
                "request_timeout": self.timeout,
                "scheme": self.scheme,
            }
        )

        # regular expression to match keyword
        self.gpt_prog = re.compile(r"^\s*!gpt\s*(.+)$")
        self.chat_prog = re.compile(r"^\s*!chat\s*(.+)$")
        self.pic_prog = re.compile(r"^\s*!pic\s*(.+)$")
        self.help_prog = re.compile(r"^\s*!help\s*.*$")
        self.new_prog = re.compile(r"^\s*!new\s*.*$")

    # close session
    async def close(self, task: asyncio.Task) -> None:
        await self.httpx_client.aclose()
        self.driver.disconnect()
        task.cancel()

    async def login(self) -> None:
        await self.driver.login()
        # get user id
        resp = await self.driver.users.get_user(user_id="me")
        self.bot_id = resp["id"]

    async def run(self) -> None:
        logger.info("runnnnnnnnn")
        await self.driver.init_websocket(self.websocket_handler)

    # websocket handler
    async def websocket_handler(self, message) -> None:
        logger.info(message)
        response = json.loads(message)
        if "event" not in response:
            return
        event_type = response["event"]
        if event_type == "new_user":
            await self.send_welcome_message(response["data"]["user_id"])
            return
        if event_type != "posted":
            return

        raw_data = response["data"]["post"]
        raw_data_dict = json.loads(raw_data)
        user_id = raw_data_dict["user_id"]
        root_id = (
            raw_data_dict["root_id"]
            if raw_data_dict["root_id"]
            else raw_data_dict["id"]
        )
        channel_id = raw_data_dict["channel_id"]
        sender_name = response["data"]["sender_name"]
        raw_message = raw_data_dict["message"]

        if user_id == self.bot_id:
            return

        members = await self.driver.channels.get_channel_members(channel_id)

        if not (self.username in raw_message or len(members) == 2):
            return

        try:
            function_to_execute = self.message_callback_langchain
            if "!traduire-en-corse" in raw_message or "!traduire-en-francais" in raw_message:
                function_to_execute = self.message_callback_traducteur
            asyncio.create_task(
                function_to_execute(
                    raw_message,
                    channel_id,
                    user_id,
                    sender_name,
                    root_id if len(members) != 2 else None,
                )
            )
        except Exception as e:
            await self.send_message(channel_id, f"{e}", root_id)

    async def send_welcome_message(self, user_id):
        response = await self.driver.channels.create_direct_channel(
            options=[user_id, self.bot_id]
        )
        new_channel_id = response["id"]

        await self.send_message(new_channel_id, WELCOME_MESSAGE)

    async def compute_history(self, posts, user_id):
        history_messages = []
        current_character_count = 0
        for post_id in posts["order"]:
            p = posts["posts"][post_id]

            username = await self.driver.users.get_user(user_id=p["user_id"])
            message_text = f"{username['username']}: {p['message']}\n\n"
            if len(message_text) > TOKEN_THRESHOLD_USER_MESSAGE:
                message_text = (
                    "Message trop long version courte:"
                    + message_text[: TOKEN_THRESHOLD_USER_MESSAGE / 2]
                    + "..."
                )
                continue
            message = ("user" if p["user_id"] == user_id else "assistant", message_text)
            current_character_count += len(message[1])
            if current_character_count > TOKEN_THRESHOLD_HISTORY:
                break
            history_messages.append(message)

        return list(reversed(history_messages))

    async def message_callback_langchain(
        self,
        raw_message: str,
        channel_id: str,
        user_id: str,
        sender_name: str,
        root_id: str | None,
    ) -> None:
        if sender_name == self.username:
            return

        model = ChatOpenAI(model="gpt-4o", temperature=0)
        parser = StrOutputParser()

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", tutor_prompt_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", sender_name + ": {text}"),
            ]
        )
        chain = prompt_template | model | parser
        try:
            # sending typing state
            await self.driver.users.publish_user_typing(
                self.bot_id,
                options={
                    "channel_id": channel_id,
                },
            )
            if root_id is None:
                posts = await self.driver.posts.get_posts_for_channel(
                    channel_id=channel_id
                )
            else:
                posts = await self.driver.posts.get_post_thread(
                    root_id, params={"perPage": 100}
                )
            history = await self.compute_history(posts, user_id)
            print(history)
            output = chain.invoke({"text": raw_message, "chat_history": history})

            output = (
                output.replace("parolla: ", "")
                .replace("parolla:", "")
                .replace("parolla", "")
            )
            await self.send_message(channel_id, output, root_id)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception(e)

    async def message_callback_traducteur(
        self,
        raw_message: str,
        channel_id: str,
        user_id: str,
        sender_name: str,
        root_id: str | None,
        retry: bool = False,
    ) -> None:
        try:
            # sending typing state
            await self.driver.users.publish_user_typing(
                self.bot_id,
                options={
                    "channel_id": channel_id,
                },
            )

            tgt_lang = None
            src_lang = None
            if "!traduire-en-corse" in raw_message:
                tgt_lang = "cor_Latn"
                src_lang = "fra_Latn"
            elif "!traduire-en-francais" in raw_message:
                tgt_lang = "fra_Latn"
                src_lang = "cor_Latn"
            raw_message_clean = raw_message.replace("!traduire-en-corse", "").replace(
                "!traduire-en-francais", ""
            )
            if raw_message_clean == "" or tgt_lang is None or src_lang is None:
                await self.send_message(
                    channel_id,
                    "Veuillez utiliser la commande !traduire-en-corse ou !traduire-en-francais et saisir le texte que vous souhaitez traduire",
                    root_id,
                )
                return
            headers = {
                "Authorization": f"""Bearer {os.environ.get("HF_TOKEN")}""",
                "Content-Type": "application/json",
            }
            payload = {
                "inputs": raw_message_clean.strip(),
                "parameters": {"src_lang": src_lang, "tgt_lang": tgt_lang},
            }
            response = requests.post(
                os.environ.get("HF_API_URL"), headers=headers, json=payload
            )
            data = response.json()
            if response.status_code == 503:
                if retry:
                    await self.send_message(
                        channel_id,
                        "Une erreur est survenue. Veuillez essayer une autre phrase. Si le probleme persiste, contactez le support.",
                        root_id,
                    )
                    return
                await asyncio.sleep(30)
                await self.message_callback_traducteur(
                    raw_message, channel_id, user_id, sender_name, root_id, retry=True
                )
                return
            if not data:
                await self.send_message(
                    channel_id,
                    "La phrase n'a pas pu être traduite. Veuillez essayer une autre phrase. Si le probleme persiste, contactez le support.",
                    root_id,
                )
                return
            await self.send_message(
                channel_id,
                data[0]
                + "\n\n> Le traducteur Parolla peut faire des erreurs. Envisagez de vérifier les traductions à l'aide d'un dictionnaire.",
                root_id,
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception(e)

    # send message to room
    async def send_message(
        self, channel_id: str, message: str, root_id: str | None = None
    ) -> None:
        options = {
            "channel_id": channel_id,
            "message": message,
        }
        if root_id:
            options["root_id"] = root_id
        await self.driver.posts.create_post(options=options)

    # send file to room
    async def send_file(
        self, channel_id: str, message: str, filepath: str, root_id: str
    ) -> None:
        filename = os.path.split(filepath)[-1]
        try:
            file_id = await self.driver.files.upload_file(
                channel_id=channel_id,
                files={
                    "files": (filename, open(filepath, "rb")),
                },
            )
            file_id = file_id["file_infos"][0]["id"]
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception(e)

        try:
            await self.driver.posts.create_post(
                options={
                    "channel_id": channel_id,
                    "message": message,
                    "file_ids": [file_id],
                    "root_id": root_id,
                }
            )

        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception(e)

    # !help command function
    def help(self) -> str:
        help_info = (
            "!gpt [content], generate response without context conversation\n"
            + "!chat [content], chat with context conversation\n"
            + "!pic [prompt], Image generation with DALL·E or LocalAI or stable-diffusion-webui\n"  # noqa: E501
            + "!new, start a new conversation\n"
            + "!help, help message"
        )
        return help_info
