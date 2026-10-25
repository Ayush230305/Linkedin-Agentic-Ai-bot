import sys
from linkedin_api import publish_post

# Usage: python test_linkedin_publish.py [image.jpg ... | video.mp4]
media = sys.argv[1:]

print("This will publish a real, public LinkedIn post.")
if input("Type PUBLISH to continue: ").strip() != "PUBLISH":
    print("Cancelled. Nothing was published.")
else:
    post_id = publish_post(
        "Testing my official LinkedIn API integration for LinkPilot (API test).",
        media,
    )
    print("Published successfully. Post ID:", post_id)