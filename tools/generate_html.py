#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")
OUTPUT_HTML_FILE = os.path.join(TMP_DIR, "newsletter.html")

def get_category_color(category):
    cat = category.lower()
    if "intelligence" in cat or "ai" in cat:
        return "#7C3AED"  # Violet / AI
    elif "network" in cat:
        return "#0284C7"  # Sky / Networks
    else:
        return "#EA580C"  # Orange / System Design

def render_html():
    if not os.path.exists(SYNTHESIZED_NEWS_FILE):
        print(f"Error: {SYNTHESIZED_NEWS_FILE} not found. Run ai_research.py first.")
        sys.exit(1)
        
    with open(SYNTHESIZED_NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    articles = data.get("articles", [])
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Base HTML template with brand alignment (BUILDR.ai), custom fonts, and minimalist layout
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BUILDR.ai Intel Briefing</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
        
        /* Reset styles */
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        table {{ border-collapse: collapse !important; }}
        
        body {{ 
            height: 100% !important; 
            margin: 0 !important; 
            padding: 0 !important; 
            width: 100% !important; 
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            background-color: #F8FAFC; 
            color: #334155; 
        }}
        
        /* Brand layout */
        .wrapper {{ width: 100%; table-layout: fixed; background-color: #F8FAFC; padding: 40px 0; }}
        .content {{ max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; }}
        
        /* Minimalist Header */
        .header {{ padding: 40px 32px 24px 32px; border-bottom: 1px solid #F1F5F9; background-color: #FFFFFF; }}
        .brand-logo {{ font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.04em; text-decoration: none; }}
        .brand-logo span {{ color: #7C3AED; }}
        .subtitle {{ margin: 6px 0 0 0; font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.15em; text-transform: uppercase; }}
        
        /* Section Body */
        .section-body {{ padding: 32px; }}
        
        /* Article card (minimalist, separator line based) */
        .article-block {{ padding-bottom: 36px; margin-bottom: 36px; border-bottom: 1px solid #F1F5F9; }}
        .article-block:last-child {{ padding-bottom: 0; margin-bottom: 0; border-bottom: none; }}
        
        /* Sleek text category badge */
        .category-badge {{ font-size: 9px; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 12px; display: block; }}
        
        .article-title {{ font-size: 20px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em; }}
        .article-title a {{ color: #0F172A; text-decoration: none; }}
        .article-title a:hover {{ color: #7C3AED; }}
        
        .meta-line {{ font-size: 11px; color: #94A3B8; margin-bottom: 20px; font-weight: 500; }}
        
        .label {{ font-size: 11px; font-weight: 700; color: #64748B; margin: 16px 0 6px 0; text-transform: uppercase; letter-spacing: 0.05em; }}
        .body-text {{ font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 16px 0; }}
        
        /* Monospace technical block */
        .deep-dive-box {{ 
            background-color: #F8FAFC; 
            border-left: 2px solid #E2E8F0; 
            padding: 14px 18px; 
            border-radius: 0 6px 6px 0; 
            font-size: 13px; 
            line-height: 1.6; 
            color: #334155; 
            margin-bottom: 18px;
            font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
        }}
        
        /* Minimalist text link CTA */
        .cta-link {{ 
            display: inline-block; 
            color: #7C3AED; 
            font-weight: 600; 
            font-size: 13px; 
            text-decoration: none; 
            margin-top: 8px;
        }}
        .cta-link:hover {{ text-decoration: underline; }}
        
        /* Minimalist Footer */
        .footer {{ padding: 32px; text-align: left; font-size: 11px; color: #94A3B8; background-color: #F8FAFC; border-top: 1px solid #E2E8F0; }}
        .footer p {{ margin: 6px 0; line-height: 1.6; }}
        .footer a {{ color: #64748B; text-decoration: underline; }}
    </style>
</head>
<body>
    <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
            <td align="center">
                <table class="content" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <!-- HEADER -->
                    <tr>
                        <td class="header">
                            <a href="#" class="brand-logo">BUILDR<span>.ai</span></a>
                            <p class="subtitle">INTELLIGENCE FOR BUILDERS &bull; {current_date}</p>
                        </td>
                    </tr>
                    
                    <!-- MAIN BODY -->
                    <tr>
                        <td class="section-body">
    """
    
    if not articles:
        html_content += """
                            <div style="text-align: center; padding: 48px 0;">
                                <p style="font-size: 15px; color: #94A3B8; font-weight: 500;">No briefing compiles available for this cycle.</p>
                            </div>
        """
    else:
        for idx, art in enumerate(articles):
            primary_col = get_category_color(art["category"])
            
            html_content += f"""
                            <!-- ARTICLE {idx+1} -->
                            <div class="article-block">
                                <span class="category-badge" style="color: {primary_col};">// {art["category"]}</span>
                                <h2 class="article-title">
                                    <a href="{art["url"]}" target="_blank">{art["title"]}</a>
                                </h2>
                                <div class="meta-line">Source: {art["source"]} &bull; Relevance: {art["relevance_score"]}%</div>
                                
                                <div class="label">Overview</div>
                                <p class="body-text">{art["what_it_is"]}</p>
                                
                                <div class="label">Technical Deep-Dive</div>
                                <div class="deep-dive-box" style="border-left-color: {primary_col};">
                                    {art["technical_deep_dive"]}
                                </div>
                                
                                <div class="label">Why it Matters</div>
                                <p class="body-text">{art["why_it_matters"]}</p>
                                
                                <a href="{art["url"]}" class="cta-link" style="color: {primary_col};">Read full story &rarr;</a>
                            </div>
            """
            
    html_content += """
                        </td>
                    </tr>
                    
                    <!-- FOOTER -->
                    <tr>
                        <td class="footer">
                            <p><strong>BUILDR.ai Briefing</strong></p>
                            <p>This daily report is generated using real-time search synthesis and sent to configured developers.</p>
                            <p>&copy; 2026 BUILDR.ai. All rights reserved. <a href="#">Unsubscribe</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated HTML newsletter to {OUTPUT_HTML_FILE}")

if __name__ == "__main__":
    render_html()
