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

def render_html():
    if not os.path.exists(SYNTHESIZED_NEWS_FILE):
        print(f"Error: {SYNTHESIZED_NEWS_FILE} not found. Run ai_research.py first.")
        sys.exit(1)
        
    with open(SYNTHESIZED_NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    current_date = datetime.now().strftime("%B %d, %Y")
    
    launches = data.get("launches", [])
    prompting = data.get("prompting_and_technique", [])
    head_to_head = data.get("head_to_head", [])
    tech_shifts = data.get("tech_shifts", [])
    repo_radar = data.get("repo_radar", [])
    
    total_items = len(launches) + len(prompting) + len(head_to_head) + len(tech_shifts) + len(repo_radar)
    
    # Base HTML template with brand alignment (BUILDR.ai), custom fonts, and minimalist inline styles
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BUILDR.ai Daily Tech Brief</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
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
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #334155;">
    <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0" style="width: 100%; background-color: #F8FAFC; padding: 40px 0;">
        <tr>
            <td align="center">
                <table class="content" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 600px; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden;">
                    <!-- HEADER -->
                    <tr>
                        <td style="padding: 40px 32px 24px 32px; border-bottom: 1px solid #F1F5F9; background-color: #FFFFFF;">
                            <a href="#" style="font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.04em; text-decoration: none; display: inline-block;">BUILDR<span style="color: #7C3AED;">.ai</span></a>
                            <p style="margin: 6px 0 0 0; font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.15em; text-transform: uppercase;">INTELLIGENCE FOR BUILDERS &bull; {current_date}</p>
                        </td>
                    </tr>
                    
                    <!-- MAIN BODY -->
                    <tr>
                        <td style="padding: 32px;">
    """
    
    if total_items == 0:
        html_content += """
                            <div style="text-align: center; padding: 48px 0;">
                                <p style="font-size: 15px; color: #94A3B8; font-weight: 500;">No briefing compiles available for this cycle.</p>
                            </div>
        """
    else:
        # SECTION 1: LAUNCHES
        if launches:
            html_content += """
                            <!-- SECTION HEADER: LAUNCHES -->
                            <div style="margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #7C3AED;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #7C3AED; letter-spacing: 0.1em; text-transform: uppercase;">01 // LAUNCHES & RELEASES</h3>
                            </div>
            """
            for idx, item in enumerate(launches):
                html_content += f"""
                            <div style="padding-bottom: 32px; margin-bottom: 32px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #94A3B8; margin-bottom: 16px; font-weight: 500;">Source: {item['source']}</div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">What It Is</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['what_it_is']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Technical Details</div>
                                <div style="background-color: #F8FAFC; border-left: 2px solid #7C3AED; padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; line-height: 1.6; color: #334155; margin-bottom: 14px; font-family: 'JetBrains Mono', Courier, monospace;">
                                    {item['details']}
                                </div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Why It Matters</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['why_it_matters']}</p>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #7C3AED; font-weight: 600; font-size: 13px; text-decoration: none;">Read full announcement &rarr;</a>
                            </div>
                """
                
        # SECTION 2: PROMPTING & TECHNIQUE
        if prompting:
            html_content += """
                            <!-- SECTION HEADER: PROMPTING -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #0284C7;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #0284C7; letter-spacing: 0.1em; text-transform: uppercase;">02 // PROMPTING & TECHNIQUE</h3>
                            </div>
            """
            for idx, item in enumerate(prompting):
                html_content += f"""
                            <div style="padding-bottom: 32px; margin-bottom: 32px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #94A3B8; margin-bottom: 16px; font-weight: 500;">Technique: {item['technique']} &bull; Source: {item['source']}</div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">How to Apply</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['how_to_apply']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Pattern / Example</div>
                                <div style="background-color: #0F172A; border-left: 3px solid #0284C7; padding: 14px 16px; border-radius: 6px; font-size: 12px; line-height: 1.6; color: #E2E8F0; margin-bottom: 14px; font-family: 'JetBrains Mono', Courier, monospace; white-space: pre-wrap;">{item['example']}</div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #0284C7; font-weight: 600; font-size: 13px; text-decoration: none;">Explore technique &rarr;</a>
                            </div>
                """

        # SECTION 3: HEAD TO HEAD
        if head_to_head:
            html_content += """
                            <!-- SECTION HEADER: HEAD TO HEAD -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #EA580C;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #EA580C; letter-spacing: 0.1em; text-transform: uppercase;">03 // HEAD TO HEAD COMPARISONS</h3>
                            </div>
            """
            for idx, item in enumerate(head_to_head):
                contenders_str = " vs ".join(item.get("contenders", []))
                html_content += f"""
                            <div style="padding-bottom: 32px; margin-bottom: 32px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #EA580C; margin-bottom: 16px; font-weight: 700; font-family: 'JetBrains Mono', monospace;">[ {contenders_str} ]</div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Verdict & Tradeoffs</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['verdict']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Use When</div>
                                <div style="background-color: #FFF7ED; border-left: 2px solid #EA580C; padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; line-height: 1.6; color: #9A3412; margin-bottom: 14px; font-weight: 500;">
                                    {item['use_when']}
                                </div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #EA580C; font-weight: 600; font-size: 13px; text-decoration: none;">View benchmark / breakdown &rarr;</a>
                            </div>
                """

        # SECTION 4: TECH SHIFTS
        if tech_shifts:
            html_content += """
                            <!-- SECTION HEADER: TECH SHIFTS -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #059669;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #059669; letter-spacing: 0.1em; text-transform: uppercase;">04 // TECH SHIFTS & INFRASTRUCTURE</h3>
                            </div>
            """
            for idx, item in enumerate(tech_shifts):
                html_content += f"""
                            <div style="padding-bottom: 32px; margin-bottom: 32px; border-bottom: 1px solid #F1F5F9;">
                                <h2 style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; line-height: 1.4; letter-spacing: -0.02em;">
                                    <a href="{item['url']}" target="_blank" style="color: #0F172A; text-decoration: none;">{item['title']}</a>
                                </h2>
                                <div style="font-size: 11px; color: #94A3B8; margin-bottom: 16px; font-weight: 500;">Source: {item['source']}</div>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Shift Summary</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['what_it_is']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Technical Details</div>
                                <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{item['details']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 12px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Impact on Developers</div>
                                <div style="background-color: #ECFDF5; border-left: 2px solid #059669; padding: 12px 16px; border-radius: 0 6px 6px 0; font-size: 13px; line-height: 1.6; color: #065F46; margin-bottom: 14px;">
                                    {item['why_it_matters']}
                                </div>
                                
                                <a href="{item['url']}" target="_blank" style="display: inline-block; color: #059669; font-weight: 600; font-size: 13px; text-decoration: none;">Read shift breakdown &rarr;</a>
                            </div>
                """

        # SECTION 5: REPO RADAR
        if repo_radar:
            html_content += """
                            <!-- SECTION HEADER: REPO RADAR -->
                            <div style="margin-top: 16px; margin-bottom: 24px; padding-bottom: 8px; border-bottom: 2px solid #4F46E5;">
                                <h3 style="margin: 0; font-size: 14px; font-weight: 800; color: #4F46E5; letter-spacing: 0.1em; text-transform: uppercase;">05 // REPO RADAR</h3>
                            </div>
            """
            for idx, repo in enumerate(repo_radar):
                stars_formatted = f"★ {repo['stars']:,}"
                html_content += f"""
                            <div style="padding: 20px; margin-bottom: 20px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 10px;">
                                    <tr>
                                        <td>
                                            <a href="{repo['html_url']}" target="_blank" style="font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700; color: #4F46E5; text-decoration: none;">{repo['full_name']}</a>
                                        </td>
                                        <td align="right">
                                            <span style="font-size: 11px; font-weight: 700; background-color: #EEF2FF; color: #4F46E5; padding: 4px 8px; border-radius: 12px; font-family: 'JetBrains Mono', monospace; margin-right: 6px;">{stars_formatted}</span>
                                            <span style="font-size: 11px; font-weight: 600; background-color: #E2E8F0; color: #475569; padding: 4px 8px; border-radius: 12px; font-family: 'JetBrains Mono', monospace;">{repo['language']}</span>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 12px 0;">{repo['what_it_does']}</p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 10px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Daily Developer Use Case</div>
                                <p style="font-size: 13px; line-height: 1.5; color: #475569; margin: 0 0 12px 0; background-color: #FFFFFF; padding: 10px 12px; border-radius: 6px; border: 1px solid #E2E8F0;">
                                    {repo['daily_use_case']}
                                </p>
                                
                                <div style="font-size: 11px; font-weight: 700; color: #64748B; margin: 10px 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em;">Getting Started</div>
                                <div style="background-color: #0F172A; color: #38BDF8; font-family: 'JetBrains Mono', Courier, monospace; font-size: 12px; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
                                    {repo['getting_started']}
                                </div>
                                
                                <a href="{repo['html_url']}" target="_blank" style="display: inline-block; color: #4F46E5; font-weight: 600; font-size: 13px; text-decoration: none;">View repository on GitHub &rarr;</a>
                            </div>
                """

    html_content += """
                        </td>
                    </tr>
                    
                    <!-- FOOTER -->
                    <tr>
                        <td style="padding: 32px; text-align: left; font-size: 11px; color: #94A3B8; background-color: #F8FAFC; border-top: 1px solid #E2E8F0;">
                            <p style="margin: 6px 0; line-height: 1.6;"><strong>BUILDR.ai Daily Tech Brief</strong></p>
                            <p style="margin: 6px 0; line-height: 1.6;">This daily briefing is compiled using real-time search synthesis and automated GitHub repository radar for technology builders.</p>
                            <p style="margin: 6px 0; line-height: 1.6;">&copy; 2026 BUILDR.ai. All rights reserved. <a href="#" style="color: #64748B; text-decoration: underline;">Unsubscribe</a></p>
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
