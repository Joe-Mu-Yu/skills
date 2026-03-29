import asyncio
import os
import re
import json
from datetime import datetime
from urllib.parse import urlparse
import requests
from playwright.async_api import async_playwright
from markdownify import markdownify as md
from markitdown import MarkItDown
import trafilatura

async def download_image(session, url, folder, filename):
    try:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        
        path = os.path.join(folder, filename)
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                content = await response.read()
                with open(path, 'wb') as f:
                    f.write(content)
                return path
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return None

async def process_article(url, md_converter):
    try:
        print(f"Fetching article: {url}")
        # Use asyncio to fetch and extract
        downloaded = await asyncio.to_thread(trafilatura.fetch_url, url)
        if downloaded:
            clean_text = await asyncio.to_thread(trafilatura.extract, downloaded, output_format="markdown")
            if not clean_text:
                print(f"Trafilatura fallback for {url}")
                # For markitdown, we still need a session or thread
                response = await asyncio.to_thread(requests.get, url, timeout=15)
                result = await asyncio.to_thread(md_converter.convert, response.content)
                clean_text = result.text_content
            
            if clean_text:
                return f"\n\n## 关联文章: {url}\n\n{clean_text}"
    except Exception as e:
        print(f"Error processing article {url}: {e}")
    return ""

def slugify(text):
    # Safe filename from text
    text = text.strip().split('\n')[0] # Only first line
    text = re.sub(r'[^\w\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '_', text)
    return text[:50] # Limit to 50 chars

async def tweet_to_markdown(tweet_url: str, output_md: str = None):
    tweet_id = tweet_url.split('/')[-1].split('?')[0]
    author = tweet_url.split('/')[3]
    
    default_dir = "/Users/morgan/WorkSpace/07-资产/Clippings"
    if not os.path.exists(default_dir):
        os.makedirs(default_dir, exist_ok=True)
    
    print(f"Starting optimized capture for: {tweet_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        await page.route("**/*", lambda route: route.abort() 
                         if route.request.resource_type in ["font", "media", "manifest", "other"] 
                         else route.continue_())

        try:
            await page.goto(tweet_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('[data-testid="tweet"]', timeout=20000)
        except Exception as e:
            print(f"Navigation warning: {e}")

        for _ in range(2):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(0.8)

        # Extract Tweets
        tweet_elements = await page.locator('[data-testid="tweet"]').all()
        
        all_tweets_md = []
        article_urls = set()
        image_tasks = []
        tweet_text_for_title = ""
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for i, tweet in enumerate(tweet_elements):
                html = await tweet.inner_html()
                
                # Get text for title from first tweet
                if i == 0:
                    raw_text = await tweet.locator('[data-testid="tweetText"]').first.inner_text()
                    tweet_text_for_title = raw_text if raw_text else author
                
                # Images and Links
                images = await tweet.locator('img[src*="media"]').all()
                for img_idx, img in enumerate(images):
                    src = await img.get_attribute('src')
                    if src and 'twimg.com/media/' in src:
                        image_tasks.append((src, i, img_idx))

                links = await tweet.locator('a[href*="t.co"]').all()
                for link in links:
                    href = await link.get_attribute('href')
                    if href: article_urls.add(href)

                t_md = md(html, heading_style="ATX", bullets="*", strip=['script', 'style', 'button'])
                t_md = re.sub(r'@(\w+)', r'[@\1](https://x.com/\1)', t_md)
                t_md = re.sub(r'#(\w+)', r'[#\1](https://x.com/hashtag/\1)', t_md)
                all_tweets_md.append(t_md)

            # Determine Final Output Path
            title_slug = slugify(tweet_text_for_title)
            if not output_md:
                output_md = os.path.join(default_dir, f"{title_slug}_{tweet_id}.md")
            
            img_dir = os.path.join(os.path.dirname(os.path.abspath(output_md)), "imgs", f"{author}_{tweet_id}")

            # Run image downloads
            if image_tasks:
                print(f"Downloading {len(image_tasks)} images...")
                dl_tasks = []
                for src, t_idx, img_idx in image_tasks:
                    clean_src = src.split('?')[0]
                    ext = clean_src.split('.')[-1]
                    img_name = f"tweet_{t_idx}_img_{img_idx}.{ext}"
                    dl_tasks.append(download_image(session, src, img_dir, img_name))
                
                results = await asyncio.gather(*dl_tasks)
                img_mapping = {image_tasks[idx][0]: results[idx] for idx in range(len(image_tasks))}
                
                # Update MD
                final_tweets_md = []
                for t_md in all_tweets_md:
                    for src, local in img_mapping.items():
                        if local:
                            rel_path = f"imgs/{author}_{tweet_id}/{os.path.basename(local)}"
                            t_md = re.sub(re.escape(src), rel_path, t_md)
                            t_md = re.sub(f'\\!\\[.*?\\]\\({re.escape(rel_path)}\\)', f'![img]({rel_path})', t_md)
                    final_tweets_md.append(t_md)
            else:
                final_tweets_md = all_tweets_md

        await browser.close()

    # === Process articles ===
    md_converter = MarkItDown()
    unique_article_urls = list(article_urls)[:5]
    print(f"Processing {len(unique_article_urls)} articles...")
    article_results = await asyncio.gather(*[process_article(url, md_converter) for url in unique_article_urls])
    article_md_list = [res for res in article_results if res]

    # === Final Assembly ===
    yaml_front = f"""---
title: {tweet_text_for_title.splitlines()[0] if tweet_text_for_title else 'X Tweet'}
author: {author}
date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
url: {tweet_url}
tags: [x-archive, twitter]
---

# 推文正文

"""
    final_md = yaml_front + "\n\n---\n\n".join(final_tweets_md) + "\n\n" + "\n\n".join(article_md_list)

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(f"✅ Saved -> {output_md}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://x.com/GoSailGlobal/status/2035945586751619284"
    output = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(tweet_to_markdown(url, output))
