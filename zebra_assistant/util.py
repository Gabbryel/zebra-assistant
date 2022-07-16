"""
All the Constants and Utility functions used in the program.
"""


def welcome_msg(name, chat_title):
    return f"Hello {name} , welcome in {chat_title} 🎶 If you want to be up to date with all the news, " \
           "subscribe to our linktree profile https://linktr.ee/zebra_rec"


class Constants:
    """
    Constants class for the program.
    """

    def __init__(self, token, host_name):
        self._name = None
        self._username = None
        self._admins_list: list = []
        self.__version = "0.1"
        self.__author = "Itsydv"  # GitHub Username
        self.__email = "itsydv@outlook.com"
        self.__github_repo = "zebra-assistant"
        self._website_url = None
        self._yt_api_key = None
        self._yt_channel_id = None
        self._insta_username = None
        self._fb_username = None
        self.bot_owner = 'zebramusic'
        self.token: str = token
        self.host_name = host_name
        self.log_grp = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    @property
    def admins_list(self):
        return self._admins_list

    @admins_list.setter
    def admins_list(self, admins_list):
        self._admins_list = admins_list

    @property
    def website_url(self):
        return self._website_url

    @website_url.setter
    def website_url(self, url):
        self._website_url = url

    @property
    def yt_api_key(self):
        return self._yt_api_key

    @yt_api_key.setter
    def yt_api_key(self, key):
        self._yt_api_key = key

    @property
    def yt_channel_id(self):
        return self._yt_channel_id

    @yt_channel_id.setter
    def yt_channel_id(self, chnl_id):
        self._yt_channel_id = chnl_id

    @property
    def insta_username(self):
        return self._insta_username

    @insta_username.setter
    def insta_username(self, username):
        self._insta_username = username

    @property
    def fb_username(self):
        return self._fb_username

    @fb_username.setter
    def fb_username(self, username):
        self._fb_username = username

    @property
    def webhook_url(self):
        return f'https://{self.host_name}.herokuapp.com/{self.token}'

    @property
    def github_repo(self):
        return rf'https://github.com/{self.__author}/{self.__github_repo}'
