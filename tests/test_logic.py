import tempfile
import unittest
from pathlib import Path

from logic import (
    analyze_instagram_data,
    export_result,
    extract_usernames,
    normalize_username,
    scan_instagram_export,
)


class LogicTestCase(unittest.TestCase):
    def test_normalize_username(self):
        self.assertEqual(normalize_username("@Usuario.Test"), "usuario.test")
        self.assertEqual(
            normalize_username("https://www.instagram.com/example_user/"),
            "example_user",
        )
        self.assertEqual(
            normalize_username("https://www.instagram.com/_u/example_user/"),
            "example_user",
        )
        self.assertIsNone(normalize_username("https://www.instagram.com/_u/"))
        self.assertIsNone(normalize_username("explore"))

    def test_extract_usernames_from_html(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "followers.html"
            html.write_text(
                """
                <html>
                    <body>
                        <a href="https://www.instagram.com/ana/">Ana</a>
                        <a href="https://www.instagram.com/luis.dev/">Luis</a>
                    </body>
                </html>
                """,
                encoding="utf-8",
            )

            self.assertEqual(extract_usernames(html), {"ana", "luis.dev"})

    def test_extract_usernames_from_instagram_deep_links(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "following.html"
            html.write_text(
                """
                <html>
                    <body>
                        <a href="https://www.instagram.com/_u/ana/">Ana</a>
                        <a href="https://www.instagram.com/_u/luis.dev/">Luis</a>
                        <h2>pedro_99</h2>
                    </body>
                </html>
                """,
                encoding="utf-8",
            )

            self.assertEqual(extract_usernames(html), {"ana", "luis.dev", "pedro_99"})

    def test_analyze_instagram_data(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            followers = tmp_path / "followers.html"
            following = tmp_path / "following.html"

            followers.write_text(
                """
                <a href="https://www.instagram.com/luis/">Luis</a>
                <a href="https://www.instagram.com/pedro/">Pedro</a>
                """,
                encoding="utf-8",
            )
            following.write_text(
                """
                <a href="https://www.instagram.com/ana/">Ana</a>
                <a href="https://www.instagram.com/luis/">Luis</a>
                <a href="https://www.instagram.com/pedro/">Pedro</a>
                """,
                encoding="utf-8",
            )

            result = analyze_instagram_data(followers, following)

            self.assertEqual(result.followers_count, 2)
            self.assertEqual(result.following_count, 3)
            self.assertEqual(result.not_following_back, ["ana"])
            self.assertEqual(result.mutuals, ["luis", "pedro"])

    def test_scan_export_folder_and_extra_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            files = {
                "followers_1.html": '<a href="https://www.instagram.com/luis/">Luis</a>',
                "following.html": '<a href="https://www.instagram.com/ana/">Ana</a>',
                "close_friends.html": '<a href="https://www.instagram.com/pedro/">Pedro</a>',
                "profiles_you've_favorited.html": '<a href="https://www.instagram.com/sofia/">Sofia</a>',
            }

            for filename, content in files.items():
                (tmp_path / filename).write_text(content, encoding="utf-8")

            detected = scan_instagram_export(tmp_path)
            self.assertIn("followers", detected)
            self.assertIn("following", detected)
            self.assertIn("close_friends", detected)
            self.assertIn("favorited_profiles", detected)

            result = analyze_instagram_data(
                detected["followers"],
                detected["following"],
                {
                    "close_friends": detected["close_friends"],
                    "favorited_profiles": detected["favorited_profiles"],
                },
            )
            self.assertEqual(result.not_following_back, ["ana"])
            self.assertEqual(result.extra_categories["close_friends"], ["pedro"])
            self.assertEqual(result.extra_categories["favorited_profiles"], ["sofia"])

    def test_export_xlsx(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            followers = tmp_path / "followers.html"
            following = tmp_path / "following.html"
            output = tmp_path / "report.xlsx"

            followers.write_text('<a href="https://www.instagram.com/luis/">Luis</a>', encoding="utf-8")
            following.write_text('<a href="https://www.instagram.com/ana/">Ana</a>', encoding="utf-8")

            result = analyze_instagram_data(followers, following)
            export_result(result, output, "xlsx")

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
