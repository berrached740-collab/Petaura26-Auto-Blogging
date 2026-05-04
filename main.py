import feedparser
import google.generativeai as genai
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# إعدادات مفاتيح API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_ID = os.environ.get("BLOG_ID")

# إعداد نموذج Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# مصادر الأخبار للحيوانات الأليفة (باللغة الإنجليزية)
RSS_URLS = [
    "https://www.petmd.com/rss/dog.health",
    "https://www.petmd.com/rss/cat.health"
]

def fetch_latest_news():
    """هذه الدالة تقوم بالبحث في روابط RSS وجلب أحدث خبر مع صورته"""
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        if feed.entries:
            latest_entry = feed.entries[0]
            
            # محاولة جلب صورة من الـ RSS
            image_url = ""
            if 'media_content' in latest_entry:
                 image_url = latest_entry.media_content[0]['url']
            elif 'links' in latest_entry:
                for link in latest_entry.links:
                    if 'image' in link.get('type', ''):
                        image_url = link.href
                        break
                        
            return {
                "title": latest_entry.title,
                "summary": latest_entry.summary,
                "link": latest_entry.link,
                "image": image_url
            }
    return None

def generate_article_gemini(news_data):
    """هذه الدالة ترسل الخبر إلى Gemini ليقوم بكتابة مقال حصري بالإنجليزية"""
    prompt = f"""
    You are an expert pet blogger and veterinarian. Write a comprehensive, engaging, and SEO-optimized article in English based on this news:
    Title: {news_data['title']}
    Summary: {news_data['summary']}
    
    Requirements:
    1. Write a catchy H1 Title.
    2. Write an engaging introduction.
    3. Use H2 and H3 subheadings to divide the article.
    4. Ensure the content is 100% unique and does not look like a cheap translation.
    5. Output ONLY proper HTML code suitable for Blogger (use <h1>, <h2>, <p> tags). Do not use ```html or Markdown code blocks.
    """
    
    response = model.generate_content(prompt)
    article_html = response.text
    
    # إذا وجدنا صورة، نضعها في أعلى المقال
    if news_data['image']:
        image_html = f"<div style='text-align: center;'><img src='{news_data['image']}' alt='{news_data['title']}' style='max-width:100%; border-radius: 8px;'/></div><br><br>"
        article_html = image_html + article_html
        
    return article_html

def post_to_blogger(title, content):
    """هذه الدالة تقوم بنشر المقال مباشرة في مدونتك على بلوجر"""
    credentials = Credentials(
        None,
        refresh_token=os.environ.get("REFRESH_TOKEN"),
        client_id=os.environ.get("CLIENT_ID"),
        client_secret=os.environ.get("CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    
    service = build('blogger', 'v3', credentials=credentials)
    
    post_body = {
        "title": title, # سيستخدم عنوان الخبر الأصلي كعنوان لمقال بلوجر
        "content": content,
        "labels": ["Pets", "Pet Health", "Dogs", "Cats"] # التصنيفات (Tags)
    }
    
    try:
        request = service.posts().insert(blogId=BLOG_ID, body=post_body)
        response = request.execute()
        print(f"✅ Success! Post published on Petaura26: {response['url']}")
    except Exception as e:
        print(f"❌ Error publishing to Blogger: {e}")

if __name__ == "__main__":
    print("⏳ Searching for new pet news...")
    news = fetch_latest_news()
    if news:
        print(f"✅ Found news: {news['title']}")
        print("⏳ Generating unique article via Gemini...")
        html_content = generate_article_gemini(news)
        print("⏳ Publishing to Blogger...")
        post_to_blogger(news['title'], html_content)
    else:
        print("ℹ️ No new articles found in RSS feeds today.")
