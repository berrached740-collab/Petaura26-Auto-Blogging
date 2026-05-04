import feedparser
import google.generativeai as genai
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# المفاتيح المخفية في GitHub
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_ID = os.environ.get("BLOG_ID")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

RSS_URLS = [
    "https://www.petmd.com/rss/dog.health",
    "https://www.petmd.com/rss/cat.health"
]

def fetch_latest_news():
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        if feed.entries:
            latest_entry = feed.entries[0]
            image_url = ""
            if 'media_content' in latest_entry:
                 image_url = latest_entry.media_content[0]['url']
            return {
                "title": latest_entry.title,
                "summary": latest_entry.summary,
                "image": image_url
            }
    return None

def generate_article_gemini(news_data):
    prompt = f"""
    You are an expert pet blogger. Write a highly engaging and SEO-optimized article in English based on this news:
    Title: {news_data['title']}
    Summary: {news_data['summary']}
    
    Requirements:
    1. A catchy H1 Title.
    2. Engaging introduction.
    3. H2 and H3 subheadings.
    4. 100% unique content.
    5. Output ONLY proper HTML code for Blogger.
    """
    response = model.generate_content(prompt)
    article_html = response.text
    
    if news_data['image']:
        article_html = f"<div style='text-align: center;'><img src='{news_data['image']}' alt='{news_data['title']}' style='max-width:100%;'/></div><br>" + article_html
        
    return article_html

def post_to_blogger(title, content):
    # قراءة ملف token.json تماماً كما فعلنا في المرة السابقة
    credentials = Credentials.from_authorized_user_file('token.json')
    service = build('blogger', 'v3', credentials=credentials)
    
    post_body = {
        "title": title,
        "content": content,
        "labels": ["Pets", "Pet Health"]
    }
    
    try:
        request = service.posts().insert(blogId=BLOG_ID, body=post_body)
        response = request.execute()
        print(f"✅ Success! Post published.")
    except Exception as e:
        print(f"❌ Error publishing to Blogger: {e}")

if __name__ == "__main__":
    news = fetch_latest_news()
    if news:
        html_content = generate_article_gemini(news)
        post_to_blogger(news['title'], html_content)
    else:
        print("No news found.")
