import datetime
import random
import re
import warnings

import instaloader
import requests
import scrapetube
from bs4 import BeautifulSoup
from facebook_scraper import get_posts
from googleapiclient.discovery import build

from zebra_assistant import func


def get_yt_videos(api_key, channel_id, last_yt_video_sent):
    try:
        last_sent = datetime.datetime.strptime(last_yt_video_sent, "%Y-%m-%dT%H:%M:%SZ")
        videos_list = []
        youtube = build('youtube', 'v3', developerKey=api_key)
        videos = scrapetube.get_channel(channel_id=channel_id, limit=10)
        for video in videos:
            video_id = video['videoId']
            request = youtube.videos().list(
                part="snippet",
                id=video_id
            )
            video_details = request.execute().get("items")[0].get("snippet")
            published_at = datetime.datetime.strptime(video_details.get("publishedAt"), "%Y-%m-%dT%H:%M:%SZ")
            if last_sent < published_at:
                video_url = "https://www.youtube.com/watch?v=" + video_id
                title = video_details.get("title")
                thumbnail = video_details.get("thumbnails").get("high").get("url")
                videos_list.append({'url': video_url, 'title': title, 'thumbnail': thumbnail,
                                    'liveBroadcastContent': video_details.get("liveBroadcastContent"),
                                    'publishedAt': published_at})
        return tuple(videos_list[::-1])  # so the latest video is last
    except Exception as e:
        return e


def get_insta_posts(username, last_insta_post_sent):
    try:
        last_sent = datetime.datetime.strptime(last_insta_post_sent, "%Y-%m-%dT%H:%M:%SZ")
        posts_list = []
        insta_bot = instaloader.Instaloader()
        # insta_bot.login(config.INSTA_USER, config.INSTA_PASS)
        profile = instaloader.Profile.from_username(insta_bot.context, username)
        posts = profile.get_posts()
        for index, post in enumerate(posts, 1):
            if index > 10:
                break
            date = str(post.date).replace(" ", "T") + "Z"
            post_date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            if last_sent < post_date:
                caption = post.caption if len(post.caption) < 100 else post.caption[:99] + "..."
                url = f"https://instagram.com/p/{post.shortcode}/"
                thumbnail = post.url
                posts_list.append((url, caption, thumbnail))
        return tuple(posts_list[::-1])  # so the latest post is last
    except Exception as e:
        return e


def get_facebook_posts(username, last_sent):
    # try:
    warnings.filterwarnings("ignore")
    posts_list = []
    for post in get_posts(username, pages=3):
        post_time = post['time'].strftime("%Y-%m-%dT%H:%M:%SZ")
        if last_sent < post_time:
            url = post['post_url']
            text = post['text'] if len(post['text']) < 99 else post['text'][:100] + '...'
            images = post['images'] if len(post['images']) > 0 else None
            video = post['video']
            video_thumbnail = post['video_thumbnail']
            posts_list.append({'url': url, 'text': text, 'images': images, 'video': video,
                               'video_thumbnail': video_thumbnail})
    return posts_list[::-1]
    # except Exception as e:
    #     return e


def get_future_events(url, last_artists_sent):
    try:
        source = requests.get(url, headers={'User-Agent': random.choice(func.USER_AGENTS)}).text
        soup = BeautifulSoup(source, 'lxml')
        response = soup.find_all('div', class_='home-page__djs-container')

        for dj_list in response:
            dj_list = dj_list.find_all('a')
            future_events_list = []
            new_events_fetched = []

            for dj in dj_list:
                dj_url = url + dj.get('href')
                dj_source = requests.get(dj_url, headers={'User-Agent': random.choice(func.USER_AGENTS)}).text
                dj_soup = BeautifulSoup(dj_source, 'lxml')
                future_events = dj_soup.find_all('div', class_='future-events-index')

                for i, _event in enumerate(future_events):
                    if i == 0:
                        continue
                    events = _event.find_all('div', class_='event')

                    for event in events:
                        event_response = []
                        event_img = event.find_all('div', class_='event-image')
                        for img in event_img:
                            img = img.find_all('img')
                            for img_url in img:
                                event_response.append(img_url.get('src'))
                        event_desc = event.find_all('div', class_='event-description')

                        for desc in event_desc:
                            event_name = desc.find('div', class_="event-name").p.text
                            event_venue = desc.find('div', class_="venue-name").p.text
                            event_city = desc.find('div', class_="event-city").p.text
                            if (event_venue+event_city).lower() not in last_artists_sent:
                                event_response.append(event_name)
                                event_response.append(event_venue)
                                event_response.append(event_city)
                                if event_response not in future_events_list:
                                    future_events_list.append(event_response)
                            new_events_fetched.append((event_venue+event_city).lower())
            return future_events_list, new_events_fetched
    except Exception as e:
        return e


def extract_img_param(album):
    album_img_url = album.a.div.img['src']
    try:
        album_title = album.a.p.text.strip().split('\n')[0]
    except:
        album_title = album.a.p.text.strip()
    return album_img_url, album_title


def get_new_bandcamp_albums():
    try:
        # TODO: Proxies
        proxies = {'http': func.get_proxy()}
        source = requests.get("https://zebrarec.bandcamp.com/music",
                              headers={'User-Agent': random.choice(func.USER_AGENTS)}, proxies=proxies).text
        soup = BeautifulSoup(source, 'lxml')

        url = "https://zebrarec.bandcamp.com"
        new_albums = []

        for response in soup.find_all('ol', id="music-grid",
                                      class_=["editable-grid", "music-grid", "columns-4", "public"]):
            for index, _album in enumerate(response.find_all('li', class_=["music-grid-item", "square", "first-four"]),
                                           start=1):
                if index > 10:
                    break
                album_url = _album.a['href']
                if album_url[:5] != "https":
                    album_url = url + album_url
                album_pg = requests.get(album_url, headers={'User-Agent': random.choice(func.USER_AGENTS)}).text
                soup = BeautifulSoup(album_pg, 'lxml')
                date_match = re.search(
                    r"(\w+ \d{1,2}, \d{4})",
                    soup.find('div', class_="tralbumData tralbum-credits").text)
                if date_match:
                    date = date_match.group(1)
                    date = datetime.datetime.strptime(date, '%B %d, %Y')
                    today_date = datetime.datetime.now()
                    if date == today_date-datetime.timedelta(days=1):
                        album_img_url, album_title = extract_img_param(_album)
                        new_albums.append({'url': album_url, 'img_url': album_img_url, 'title': album_title})
        return new_albums[::-1]
    except Exception as e:
        raise e


def get_featured_bandcamp_albums(featured_albums_sent):
    try:
        proxies = {'http': func.get_proxy()}
        source = requests.get("https://zebrarec.bandcamp.com/music",
                              headers={'User-Agent': random.choice(func.USER_AGENTS)}, proxies=proxies).text
        soup = BeautifulSoup(source, 'lxml')

        url = "https://zebrarec.bandcamp.com"
        featured_albums = []
        new_fetched = []

        for featured_album in soup.find_all('ol',
                                            class_=["featured-grid", "featured-items", "featured-music", "occupied"]):
            for _album in featured_album.find_all('li', class_=["featured-item"]):
                album_url = _album.a['href']
                if album_url[:5] != "https":
                    album_url = url + album_url
                if album_url not in featured_albums_sent:
                    album_img_url, album_title = extract_img_param(_album)
                    featured_albums.append({'url': album_url, 'img_url': album_img_url, 'title': album_title})
                new_fetched.append(album_url)
        return featured_albums, new_fetched
    except Exception as e:
        raise e
