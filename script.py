import feedparser
import google.generativeai as genai
import os
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_ID = os.environ.get("BLOG_ID")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

RSS_URLS = [
    "https://www.dogster.com/feed/",
    "https://www.catster.com/feed/",
    "https://www.petful.com/feed/",
    "https://animalwellnessmagazine.com/feed/",
    "https://moderndogmagazine.com/rss.xml",
    "https://moderncat.com/rss.xml",
    "https://theconsciouscat.net/feed/",
    "https://thatmutt.com/feed/",
    "https://www.wideopenpets.com/feed/",
    "https://www.petsworld.in/blog/feed/"
]

HISTORY_FILE = "posted_urls.txt"

def load_posted_urls():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_url(url):
    with open(HISTORY_FILE, "a") as f:
        f.write(url + "\n")

def fetch_latest_news(max_articles=2):
    """هذه الدالة تقوم بجمع عدد محدد من المقالات الجديدة غير المنشورة"""
    posted_urls = load_posted_urls()
    new_articles = []
    
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.link
            
            # التحقق من أن المقال جديد ولم ينشر سابقاً
            if link not in posted_urls:
                image_url = ""
                if 'media_content' in entry:
                     image_url = entry.media_content[0]['url']
                elif 'links' in entry:
                    for l in entry.links:
                        if 'image' in l.get('type', ''):
                            image_url = l.href
                            break
                            
                new_articles.append({
                    "title": entry.title,
                    "summary": entry.summary,
                    "link": link,
                    "image": image_url
                })
                
                # إضافة الرابط لقائمة المنشورات مؤقتاً حتى لا يتم سحبه مرة أخرى
                posted_urls.add(link)
                
                # التوقف عند جمع العدد المطلوب من المقالات
                if len(new_articles) >= max_articles:
                    return new_articles
                    
    return new_articles

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
    
    adsterra_banner = """
    <div style="text-align: center; margin: 20px 0;">
        <!-- ضع كود البانر الخاص بك هنا -->
    </div>
    """
    
    adsterra_smartlink = """
    <div style="text-align: center; margin: 30px 0;">
        <a href="ضع_الرابط_المباشر_هنا" target="_blank" rel="nofollow" style="background-color: #FF5722; color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 20px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            🐶 Discover More Pet Care Secrets! 🐱
        </a>
    </div>
    """
    
    if news_data['image']:
        article_html = f"<div style='text-align: center;'><img src='{news_data['image']}' alt='{news_data['title']}' style='max-width:100%; border-radius: 10px;'/></div><br>" + adsterra_banner + article_html + adsterra_smartlink
    else:
        article_html = adsterra_banner + article_html + adsterra_smartlink
        
    return article_html

def post_to_blogger(title, content):
    credentials = Credentials.from_authorized_user_file('token.json')
    service = build('blogger', 'v3', credentials=credentials)
    
    post_body = {
        "title": title,
        "content": content,
        "labels": ["Pets", "Pet Health", "Dogs", "Cats"]
    }
    
    try:
        request = service.posts().insert(blogId=BLOG_ID, body=post_body)
        response = request.execute()
        print(f"✅ Success! Post published.")
        return True
    except Exception as e:
        print(f"❌ Error publishing: {e}")
        return False

if __name__ == "__main__":
    print("⏳ Searching for up to 2 new unique articles...")
    news_list = fetch_latest_news(max_articles=2)
    
    if news_list:
        print(f"✅ Found {len(news_list)} new article(s). Processing...")
        
        for index, news in enumerate(news_list):
            print(f"\n👉 Processing Article {index + 1}: {news['title']}")
            html_content = generate_article_gemini(news)
            success = post_to_blogger(news['title'], html_content)
            
            if success:
                save_posted_url(news['link'])
                print(f"✅ Saved URL to history: {news['link']}")
            
            # الانتظار لمدة دقيقة بين كل مقال لتجنب حظر API بلوجر أو الذكاء الاصطناعي
            if index < len(news_list) - 1:
                print("⏳ Waiting 60 seconds before processing the next article to avoid API limits...")
                time.sleep(60)
                
    else:
        print("ℹ️ No new unique news found.")
