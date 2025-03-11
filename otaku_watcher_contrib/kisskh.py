from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Optional, Dict

    from mov_cli import Config
    from mov_cli.http_client import HTTPClient
    from mov_cli.scraper import ScraperOptionsT
from typing import Any, Iterable, Optional, Dict, List, Optional # always type check for pydantic to work

from mov_cli.utils import EpisodeSelector
from mov_cli import Scraper, Multi, Single, Metadata, MetadataType

from pydantic import BaseModel, Field, RootModel
from quickjs import Context as quickjsContext

__all__ = ("KissKhScraper",)

class Episode(BaseModel):
    id: int
    number: float
    sub: int

class Drama(BaseModel):
    description: str
    release_date: str = Field(..., alias="releaseDate")
    trailer: str
    country: str
    status: str
    type: str
    next_ep_date_id: int = Field(..., alias="nextEpDateID")
    episodes: List[Episode]
    episodes_count: int = Field(..., alias="episodesCount")
    label: Any
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str

    def __init__(self, **data: Any) -> None:
        data["episodes"] = sorted(data["episodes"], key=lambda episode: episode["number"])
        super().__init__(**data)

    def get_episodes_ids(self) -> Dict[int, int]:
        episode_ids = {}
        for episode in self.episodes:
            episode_ids[episode.number] = episode.id
        return episode_ids

class DramaInfo(BaseModel):
    episodes_count: int = Field(..., alias="episodesCount")
    label: str
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str

class Search(RootModel):
    root: List[DramaInfo]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

class SubItem(BaseModel):
    src: str
    label: str
    land: str
    default: bool

class Sub(RootModel):
    root: List[SubItem]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

class KissKhScraper(Scraper):
    def __init__(
        self,
        config: Config,
        http_client: HTTPClient,
        options: Optional[ScraperOptionsT] = None
    ) -> None:
        self.base_url = "https://kisskh.id"
        super().__init__(config, http_client, options)

    def search(self, query: str, limit: int = None) -> Iterable[Metadata]:
        results = self.search_dramas_by_query(query)
        if limit is not None: results = results[:limit]
        for drama in results:
            yield Metadata(
                id=drama.id,
                title=drama.title,
                type=MetadataType.MULTI if drama.episodes_count > 1 else MetadataType.SINGLE,
            )

    def scrape_episodes(self, metadata: Metadata) -> Dict[int | None, int]:
        drama = self.get_drama(metadata.id)
        episode_map = {}
        episode_map[1] = drama.episodes_count # [season] = episodes
        if not episode_map: return {None: 1}
        return episode_map

    def scrape(self, metadata: Metadata, episode: EpisodeSelector) -> Multi | Single:
        drama = self.get_drama(metadata.id)
        target_episode = None
        if metadata.type == MetadataType.MULTI:
            target_episode = drama.episodes[episode.episode-1] if episode and episode.episode else drama.episodes[0]
        elif drama:
            target_episode = drama.episodes[0]
        video_url = self.get_stream_url(target_episode.id)

        if metadata.type == MetadataType.MULTI:
            return Multi(
                url=video_url,
                title=f"{metadata.title} - Episode {episode.episode}",
                episode=episode
            )
        else:
            return Single(
                url=video_url,
                title=metadata.title
            )

    def _drama_api_url(self, drama_id: int) -> str:
        """API endpoint for drama details

        :param drama_id: drama id
        :return: api url for a specific drama
        """
        return f"{self.base_url}/api/DramaList/Drama/{drama_id}"

    def _search_api_url(self, query: str) -> str:
        """API endpoint for drama search details

        :param query: search string
        :return: api url to get search result
        """
        return f"{self.base_url}/api/DramaList/Search?q={query}"

    def _subtitle_api_url(self, episode_id: int) -> str:
        """API endpoint for subtitles

        :param episode_id: episode id
        :return: api url for subtitles for a specific episode
        """
        return f"{self.base_url}/api/Sub/{episode_id}"

    def _stream_api_url(self, episode_id: int, kkey: str) -> str:
        """API endpoint for stream url

        :param episode_id: episode id
        :return: api url for getting stream video details
        """
        return f"{self.base_url}/api/DramaList/Episode/{episode_id}.png?kkey={kkey}"

    def _request(self, url: str, json: bool=True) -> Any:
        """Helper for all the request call

        :param url: url to do the get request on
        :return: reponse for a specific get request
        """
        response = self.http_client.get(url)
        if not json: return response.content.decode()
        return response.json()

    def get_episode_ids(self, drama_id: int) -> Dict[int, int]:
        """Get episode ids for a specific drama

        :param drama_id: drama id
        :param start: starting episode, defaults to 1
        :param stop: ending episode, defaults to sys.maxsize
        :return: returns episode id for starting episode till ending episode range
        """
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = self._request(drama_api_url)
        drama = Drama.parse_obj(response)
        return drama.get_episodes_ids()

    def get_subtitles(self, episode_id: int, *language_filter: str) -> List[SubItem]:
        """Get subtitle details for a specific episode

        :param episode_id: episode id
        :param language_filter: multiple language filters like 'en', 'id', 'ar' etc.
        :return: subtitles based on language_filter.
        If 'all' is present in language filter, then all subtitles are returned
        """
        subtitle_api_url = self._subtitle_api_url(episode_id=episode_id)
        response = self._request(subtitle_api_url)
        subtitles: Sub = Sub.parse_obj(response)
        filtered_subtitles: List[SubItem] = []
        if "all" in language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles)
        elif language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles if subtitle.land in language_filter)
        return filtered_subtitles

    def search_dramas_by_query(self, query: str) -> Search:
        """Get all drama for a specific search query

        :param query: search string
        :return: dramas for that search query
        """
        search_api_url = self._search_api_url(query)
        response = self._request(search_api_url)
        return Search.parse_obj(response)

    def get_stream_url(self, episode_id: int) -> str:
        """Stream video url for specific episode

        :param episode_id: episode id
        :return: m3u8 stream url for that episode
        """
        kkey = self._get_token(episode_id)
        stream_api_url = self._stream_api_url(episode_id, kkey)
        response = self._request(stream_api_url)
        return response.get("Video")

    def get_drama(self, drama_id: int):
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = self._request(drama_api_url)
        return Drama.parse_obj(response)

    def _get_token(self, episode_id: int) -> str:
        '''
        create token required to fetch stream & subtitle links
        '''
        # js code to generate token from kisskh site
        html_content = self._request(self.base_url, False)
        soup = self.soup(html_content)
        common_js_url = f"{self.base_url}/{[ i['src'] for i in soup.select('script') if i.get('src') and 'common' in i['src'] ][0]}"
        token_generation_js_code = self._request(common_js_url, False)

        # quickjs context for evaluating js code
        quickjs_context = quickjsContext()

        # evaluate js code to generate token
        token = quickjs_context.eval(token_generation_js_code + f'_0x54b991({episode_id}, null, "2.8.10", "62f176f3bb1b5b8e70e39932ad34a0c7", 4830201,  "kisskh", "kisskh", "kisskh", "kisskh", "kisskh", "kisskh")')
        return token