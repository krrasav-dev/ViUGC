import re
import random
import datetime

def extract_platform_and_id(url: str):
    """Extract platform name and video ID from URL."""
    url = url.strip()

    # YouTube
    yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})', url)
    if yt:
        return 'youtube', yt.group(1)

    # TikTok
    tt = re.search(r'tiktok\.com/@[\w.]+/video/(\d+)', url)
    if tt:
        return 'tiktok', tt.group(1)

    # Instagram
    ig = re.search(r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)', url)
    if ig:
        return 'instagram', ig.group(1)

    return None, None

def compute_fraud_score(views: int, likes: int, comments: int, hours_since_publish: float) -> int:
    """
    Simplified anti-fraud scoring.
    Returns 0-100. Higher = more suspicious.
    """
    score = 0

    # Check engagement rate
    if views > 0:
        er = (likes + comments) / views
        if er < 0.003:   # < 0.3% ER
            score += 40
        elif er < 0.01:  # < 1% ER
            score += 15

    # Check growth speed (views per hour)
    if hours_since_publish > 0:
        vph = views / hours_since_publish
        if vph > 50000:   # >50k views/hour
            score += 50
        elif vph > 10000: # >10k views/hour
            score += 20

    return min(score, 100)

def mock_fetch_stats(platform: str, video_id: str, current_views: int = 0) -> dict:
    """
    Mock stats fetcher — simulates realistic growth patterns.
    In production replace with real API calls.
    """
    # Simulate growth: add 500–5000 views per check
    base_growth = random.randint(500, 5000)

    # Occasionally simulate viral spike
    if random.random() < 0.05:
        base_growth *= random.randint(5, 20)

    new_views = current_views + base_growth

    # Simulate realistic engagement
    er = random.uniform(0.02, 0.08)  # 2–8% engagement
    likes = int(new_views * er * 0.8)
    comments = int(new_views * er * 0.2)

    return {
        'views': new_views,
        'likes': likes,
        'comments': comments,
        'fetched_at': datetime.datetime.utcnow().isoformat(),
        'source': 'mock'
    }

def calculate_payout(views_credited: int, cpm_rate: float, max_payout: float) -> float:
    """Calculate payout based on credited views."""
    raw = (views_credited / 1000) * cpm_rate
    return round(min(raw, max_payout), 2)
