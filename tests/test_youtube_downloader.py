"""
Test suite verifying YouTube video download functionality with real URLs.
"""
import os
import unittest
from services.youtube_downloader import download_youtube_video

class TestYouTubeDownloader(unittest.TestCase):

    def test_download_real_youtube_url(self):
        url = "https://www.youtube.com/watch?v=EUKbVj2iiSE"
        downloaded_file = download_youtube_video(url)
        self.assertTrue(os.path.exists(downloaded_file), f"File missing: {downloaded_file}")
        self.assertTrue(downloaded_file.endswith(".mp4"))
        self.assertGreater(os.path.getsize(downloaded_file), 100000)

if __name__ == "__main__":
    unittest.main()
